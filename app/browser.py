"""Optional Playwright browser fetcher for JavaScript-heavy pages.

This is a fallback, not an anti-bot bypass. It uses the same SSRF and robots
policy as the normal HTTP fetcher and should only be enabled when needed.
"""
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import (
    BROWSER_ENABLED,
    BROWSER_TIMEOUT,
    MAX_RESPONSE_BYTES,
    MIN_REQUEST_DELAY,
    RESPECT_ROBOTS,
    USER_AGENT,
)
from .scraper import SSRFBlocked, _robots_allowed, _validate_url


def fetch_rendered_html(url: str) -> str:
    """Render a public HTTP(S) URL with Chromium and return its HTML.

    The URL is validated before navigation and robots.txt is checked before
    launching the browser. Playwright is imported lazily so PriceRadar can
    run without a browser installation when this feature is disabled.
    """
    if not BROWSER_ENABLED:
        raise RuntimeError("Browser fallback is disabled")
    _validate_url(url)
    if RESPECT_ROBOTS and not _robots_allowed(url):
        raise RuntimeError("robots.txt disallows this URL for PriceRadar")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed; install it to enable browser mode") from exc

    import time
    time.sleep(MIN_REQUEST_DELAY)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="de-DE",
            ignore_https_errors=False,
        )
        page = context.new_page()
        page.set_default_timeout(int(BROWSER_TIMEOUT * 1000))

        def guard_route(route):
            target = route.request.url
            try:
                _validate_url(target)
            except SSRFBlocked:
                route.abort()
                return
            route.continue_()

        page.route("**/*", guard_route)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=int(BROWSER_TIMEOUT * 1000))
            if response is None:
                raise RuntimeError("Browser navigation returned no response")
            if response.status >= 400:
                raise RuntimeError(f"Browser navigation returned HTTP {response.status}")
            try:
                page.wait_for_load_state("networkidle", timeout=min(int(BROWSER_TIMEOUT * 1000), 10000))
            except Exception:
                # Some pages keep long-lived connections open. DOMContentLoaded
                # is already sufficient for many price pages.
                pass
            html = page.content()
            if len(html.encode("utf-8")) > MAX_RESPONSE_BYTES:
                raise RuntimeError(f"Rendered page too large (> {MAX_RESPONSE_BYTES} bytes)")
            return html
        finally:
            context.close()
            browser.close()
