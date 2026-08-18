from app.worker import _next_interval


def row(interval=86400, smart=1, minimum=3600, maximum=604800):
    return {
        "interval_seconds": interval,
        "polling_base_seconds": interval,
        "polling_min_seconds": minimum,
        "polling_max_seconds": maximum,
        "smart_polling": smart,
    }


def test_smart_polling_backs_off_when_price_is_stable():
    assert _next_interval(row(), price_changed=False) == 172800


def test_smart_polling_reacts_faster_after_change():
    assert _next_interval(row(), price_changed=True) == 43200


def test_smart_polling_respects_bounds():
    assert _next_interval(row(interval=604800), price_changed=False) == 604800
    assert _next_interval(row(interval=3600), price_changed=True) == 3600


def test_smart_polling_can_be_disabled_per_watch():
    assert _next_interval(row(interval=86400, smart=0), price_changed=False) == 86400
