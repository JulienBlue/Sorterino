import re


GERMAN_MONTH_NAMES = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)

MONTH_NUMBERS = {
    "january": "01", "januar": "01",
    "february": "02", "februar": "02",
    "march": "03", "märz": "03", "maerz": "03",
    "april": "04",
    "may": "05", "mai": "05",
    "june": "06", "juni": "06",
    "july": "07", "juli": "07",
    "august": "08",
    "september": "09",
    "october": "10", "oktober": "10",
    "november": "11",
    "december": "12", "dezember": "12",
}


def split_german_date(value):
    """Return day, month and year for a valid DD.MM.YYYY value."""
    match = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", str(value or ""))
    if not match:
        return None
    day, month, year = match.groups()
    if not 1 <= int(month) <= 12 or not 1 <= int(day) <= 31:
        return None
    return day, month, year


def german_month_name(month):
    try:
        return GERMAN_MONTH_NAMES[int(month) - 1]
    except (TypeError, ValueError, IndexError):
        return None


def extract_document_date(text):
    match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if match:
        return match.group(1)

    match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{2})\b", text)
    if match:
        day, month, year = match.groups()
        return f"{day}.{month}.20{year}"

    text_lower = text.lower()
    for pattern, order in (
        (r"\b([a-zäöü]+)\s+(\d{1,2}),\s*(\d{4})\b", "month_first"),
        (r"\b(\d{1,2})\.\s*([a-zäöü]+)\s+(\d{4})\b", "day_first"),
    ):
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        if not match:
            continue
        if order == "month_first":
            month_name, day, year = match.groups()
        else:
            day, month_name, year = match.groups()
        month = MONTH_NUMBERS.get(month_name.lower())
        if month:
            return f"{int(day):02d}.{month}.{year}"
    return None
