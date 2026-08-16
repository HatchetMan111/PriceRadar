import ipaddress
import json
import re
import socket
import time
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from price_parser import Price

from .config import (
    ALLOWED_SCHEMES,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    MIN_REQUEST_DELAY,
    REQUEST_TIMEOUT,
    RESPECT_ROBOTS,
    USER_AGENT,
)

PRICE_SELECTORS = ['[itemprop="price"]','[data-price]','.price','.product-price','.product__price','.price-current','.current-price','.sale-price','.special-price','.offer-price']


class SSRFBlocked(RuntimeError):
    """Raised when a URL (or a redirect target) points at a disallowed host."""


@dataclass
class ExtractedPrice:
    price: float
    currency: str
    source: str


def _resolves_only_to_public_ips(hostname: str) -> bool:
    """Resolve hostname and reject if ANY resolved address is private/internal."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        raw_ip = info[4][0].split("%")[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    return True


def _validate_url(url: str) -> None:
    """Allow only HTTP(S) URLs that resolve to public IP addresses.

    Validation is repeated for every redirect hop. This closes the common
    redirect-based SSRF bypass, although DNS rebinding still requires
    transport-level IP pinning for complete protection.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFBlocked(f"URL scheme not allowed: {parsed.scheme or '(none)'}")
    if not parsed.hostname:
        raise SSRFBlocked("URL has no hostname")
    if not _resolves_only_to_public_ips(parsed.hostname):
        raise SSRFBlocked(f"URL resolves to a private/internal address: {parsed.hostname}")


def _robots_allowed(url: str) -> bool:
    if not RESPECT_ROBOTS:
        return True
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        _validate_url(robots_url)
        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False, headers=headers) as client:
            response = client.get(robots_url)
    except SSRFBlocked:
        return False
    except Exception:
        # Fail closed if we cannot verify the site's robots policy.
        return False
    if response.status_code in (401, 403):
        return False
    if response.status_code >= 400:
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(response.text.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def fetch_html(url: str) -> str:
    _validate_url(url)
    if not _robots_allowed(url):
        raise RuntimeError("robots.txt disallows this URL for PriceRadar")
    time.sleep(MIN_REQUEST_DELAY)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
    }
    current_url = url
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False, headers=headers) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _validate_url(current_url)
            response = client.get(current_url)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise RuntimeError("Redirect response without Location header")
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                raise RuntimeError(f"URL did not return HTML (content-type: {content_type})")
            if len(response.content) > MAX_RESPONSE_BYTES:
                raise RuntimeError(f"Response too large (> {MAX_RESPONSE_BYTES} bytes)")
            return response.text
    raise RuntimeError("Too many redirects")


def _parse(value: str, currency_hint: str | None = None) -> ExtractedPrice | None:
    if not value:
        return None
    parsed = Price.fromstring(value)
    if parsed.amount is None:
        return None
    try:
        amount = float(parsed.amount)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return ExtractedPrice(amount, currency_hint or parsed.currency or "EUR", "parsed")


def _jsonld_prices(soup: BeautifulSoup) -> list[ExtractedPrice]:
    found = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
            offers = item.get("offers")
            offers_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
            for offer in offers_list:
                if not isinstance(offer, dict):
                    continue
                value = offer.get("price") or offer.get("lowPrice")
                if value is not None:
                    p = _parse(str(value), offer.get("priceCurrency"))
                    if p:
                        p.source = "json-ld"
                        found.append(p)
    return found


def extract_price(html: str, selector: str | None = None) -> ExtractedPrice:
    soup = BeautifulSoup(html, "html.parser")
    if selector:
        nodes = soup.select(selector)
        if not nodes:
            raise RuntimeError(f"CSS selector matched no elements: {selector}")
        for node in nodes:
            for attr in ("content", "data-price", "value"):
                if node.has_attr(attr):
                    p = _parse(node.get(attr, ""))
                    if p:
                        p.source = f"css:{selector}@{attr}"
                        return p
            p = _parse(node.get_text(" ", strip=True))
            if p:
                p.source = f"css:{selector}"
                return p
        raise RuntimeError(f"CSS selector matched elements, but no price could be parsed: {selector}")
    jsonld = _jsonld_prices(soup)
    if jsonld:
        return jsonld[0]
    for css in PRICE_SELECTORS:
        for node in soup.select(css):
            for attr in ("content", "data-price", "value"):
                if node.has_attr(attr):
                    p = _parse(node.get(attr, ""))
                    if p:
                        p.source = f"auto:{css}@{attr}"
                        return p
            p = _parse(node.get_text(" ", strip=True))
            if p:
                p.source = f"auto:{css}"
                return p
    for node in soup.find_all(["main", "article", "body"]):
        text = node.get_text(" ", strip=True)
        matches = re.findall(r"(?:€|EUR)\s*\d{1,5}(?:[.,]\d{2})|\d{1,5}(?:[.,]\d{2})\s*(?:€|EUR)", text, flags=re.I)
        for match in matches[:10]:
            p = _parse(match)
            if p:
                p.source = "regex"
                return p
    raise RuntimeError("No price could be extracted. Add a CSS selector for the exact price element.")


def check_url(url: str, selector: str | None = None) -> ExtractedPrice:
    return extract_price(fetch_html(url), selector)
