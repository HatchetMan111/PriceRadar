from app.main import _number


def test_number_plain():
    assert _number("0.79") == 0.79


def test_number_de_decimal_comma():
    assert _number("0,79") == 0.79


def test_number_de_thousands():
    assert _number("1.234,56") == 1234.56


def test_number_en_thousands():
    assert _number("1,234.56") == 1234.56


def test_number_with_currency_symbol():
    assert _number("0,79 €") == 0.79


def test_number_with_unit_text():
    assert _number("125 L") == 125.0


def test_number_empty_returns_none():
    assert _number("") is None
    assert _number("   ") is None


def test_number_garbage_returns_none_not_raise():
    assert _number("abc") is None
    assert _number("-") is None


def test_number_negative():
    assert _number("-4.5") == -4.5
