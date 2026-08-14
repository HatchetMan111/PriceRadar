from app.scraper import extract_price

def test_jsonld():
    html='<script type="application/ld+json">{"@type":"Product","offers":{"price":"14.99","priceCurrency":"EUR"}}</script>'
    p=extract_price(html); assert p.price==14.99; assert p.currency=='EUR'

def test_selector():
    p=extract_price('<div id="x">14,99 €</div>','#x'); assert p.price==14.99

def test_data_price():
    p=extract_price('<span data-price="8.49">now</span>'); assert p.price==8.49
