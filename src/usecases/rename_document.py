import re


def sanitize(value: str) -> str:
    value = value.strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_äöüÄÖÜß\-]", "", value)
    return value


def rename_document(document):

    metadata = document.metadata

    # --------------------------------------------------
    # Lohnsteuerbescheinigung (ISO-Zeitraum)
    # --------------------------------------------------

    if metadata.document_type == "Lohnsteuerbescheinigung":

        parts = []

        zeitraum = metadata.contexts.get("Zeitraum")
        if zeitraum:
            parts.append(zeitraum)

        firma = metadata.contexts.get("Firma")
        if firma:
            parts.append(firma)

        parts.append("Lohnsteuerbescheinigung")

        return "_".join(parts) + ".pdf"

    # --------------------------------------------------
    # Jahr immer zuerst
    # --------------------------------------------------
    if year:
        parts.append(str(year))

    # --------------------------------------------------
    # Zeitraum-Logik
    # --------------------------------------------------
    if start_iso and end_iso:

        try:
            sy, sm, sd = start_iso.split("-")
            ey, em, ed = end_iso.split("-")

            # Ganzjahres-Erkennung
            if sm == "01" and sd == "01" and em == "12" and ed == "31":
                parts.append("Ganzjahr")
            else:
                period = f"{sd}.{sm}.-{ed}.{em}."
                parts.append(period)

        except ValueError:
            # Falls ISO unerwartet formatiert ist → ignorieren
            pass

    # --------------------------------------------------
    # Arbeitgeber
    # --------------------------------------------------
    firma = metadata.contexts.get("Firma")
    if firma:
        parts.append(firma)

    parts.append("Lohnsteuerbescheinigung")

    return "_".join(parts) + ".pdf"

    # --------------------------------------------------
    # Standard
    # --------------------------------------------------

    date_part = None

    if metadata.year and metadata.month and metadata.day:
        date_part = f"{metadata.year:04d}-{metadata.month:02d}-{metadata.day:02d}"
    elif metadata.year:
        date_part = str(metadata.year)

    parts = []

    if date_part:
        parts.append(date_part)

    if metadata.document_type:
        parts.append(metadata.document_type)

    if not parts:
        return "Unbenannt.pdf"

    return "_".join(parts) + ".pdf"