import json
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib import robotparser
import httpx
from bs4 import BeautifulSoup
from price_parser import Price
from .config import USER_AGENT, REQUEST_TIMEOUT, MIN_REQUEST_DELAY, RESPECT_ROBOTS

PRICE_SELECTORS = ['[itemprop="price"]','[data-price]','.price','.product-price','.product__price','.price-current','.current-price','.sale-price','.special-price','.offer-price']

@dataclass
class ExtractedPrice:
    price: float
    currency: str
    source: str

def _robots_allowed(url: str) -> bool:
    if not RESPECT_ROBOTS:
        return True
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = robotparser.RobotFileParser(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True

def fetch_html(url: str) -> str:
    if not _robots_allowed(url):
        raise RuntimeError("robots.txt disallows this URL for PriceRadar")
    time.sleep(MIN_REQUEST_DELAY)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8", "Accept-Language": "de-DE,de;q=0.9,en;q=0.7"}
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            raise RuntimeError(f"URL did not return HTML (content-type: {content_type})")
        return response.text

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
