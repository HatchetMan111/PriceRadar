import pytest

from app.scraper import SSRFBlocked, _validate_url, extract_price


def test_jsonld():
    html='<script type="application/ld+json">{"@type":"Product","offers":{"price":"14.99","priceCurrency":"EUR"}}</script>'
    p=extract_price(html); assert p.price==14.99; assert p.currency=='EUR'


def test_selector():
    p=extract_price('<div id="x">14,99 €</div>','#x'); assert p.price==14.99


def test_data_price():
    p=extract_price('<span data-price="8.49">now</span>'); assert p.price==8.49


def test_ssrf_blocks_loopback():
    with pytest.raises(SSRFBlocked):
        _validate_url("http://127.0.0.1/secret")


def test_ssrf_blocks_localhost_hostname():
    with pytest.raises(SSRFBlocked):
        _validate_url("http://localhost:8080/")


def test_ssrf_blocks_non_http_scheme():
    with pytest.raises(SSRFBlocked):
        _validate_url("file:///etc/passwd")


def test_ssrf_allows_plain_https():
    # example.com resolves publicly; should not raise.
    _validate_url("https://example.com/product")
