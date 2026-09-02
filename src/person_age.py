from datetime import date, datetime


def is_minor_from_birth_date(value, today=None):
    """Return minority from a German/ISO birth date, or None if unavailable."""
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = None
    for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, date_format).date()
            break
        except ValueError:
            continue
    if parsed is None:
        return None
    today = today or date.today()
    age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
    return age < 18


def person_is_minor(person, today=None):
    calculated = is_minor_from_birth_date(
        ((person or {}).get("personal", {}) or {}).get("date_of_birth"),
        today,
    )
    return bool((person or {}).get("is_minor")) if calculated is None else calculated
