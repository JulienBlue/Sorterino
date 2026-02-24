from usecases.classify_document import extract_bescheinigungszeitraum


def test_extract_standard_period():
    text = "Zeitraum: 01.03.-31.03."
    result = extract_bescheinigungszeitraum(text)

    assert result == "01.03.-31.03."


def test_extract_period_with_noise():
    text = "Zeitraum 09.08  -   12.11."
    result = extract_bescheinigungszeitraum(text)

    assert result == "09.08.-12.11."


def test_no_period_returns_none():
    text = "Kein Zeitraum enthalten"
    result = extract_bescheinigungszeitraum(text)

    assert result is None