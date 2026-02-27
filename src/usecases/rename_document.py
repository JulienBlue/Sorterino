import os
import re


def sanitize_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = value.lstrip(".\\/- ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def rename_document(document):

    metadata = document.metadata
    contexts = metadata.contexts or {}
    ext = os.path.splitext(document.source_path)[1]

    MAX_LENGTH = 240  # Windows-Sicherheitsgrenze

    def safe(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return None
        return str(value).strip()

    def clean_party(value):
        if not value:
            return "UNBEKANNT"

        value = str(value)

        # OCR-Reste abschneiden
        STOP_WORDS = [
            "LIEFER", "LEISTUNG", "RECHNUNGSDATUM",
            "KUNDENNUMMER", "IBAN", "BIC"
        ]

        upper_value = value.upper()

        for word in STOP_WORDS:
            if word in upper_value:
                upper_value = upper_value.split(word)[0]

        # Adresse nach Bindestrich entfernen
        upper_value = upper_value.split(" - ")[0]

        return sanitize_filename(upper_value.strip(" -")) or "UNBEKANNT"

    document_type = safe(metadata.document_type)

    # --------------------------------------------------
    # AUSGANGSRECHNUNG
    # --------------------------------------------------

    if document_type == "Ausgangsrechnung":

        invoice_number = safe(contexts.get("invoice_number"))
        invoice_date = safe(contexts.get("invoice_date"))
        customer = clean_party(contexts.get("party"))

        if invoice_number and invoice_date:
            filename = f"Rechnung_{invoice_number} vom {invoice_date} {customer}"
        else:
            filename = "Rechnung_UNBEKANNT vom UNBEKANNT UNBEKANNT"

        filename = sanitize_filename(filename)

        if len(filename) > MAX_LENGTH:
            filename = filename[:MAX_LENGTH]

        return filename + ext

    # --------------------------------------------------
    # EINGANGSRECHNUNG
    # --------------------------------------------------

    if document_type == "Eingangsrechnung":

        supplier = clean_party(contexts.get("party"))
        amount = safe(contexts.get("amount"))
        date = safe(contexts.get("invoice_date"))

        parts = []

        if date:
            parts.append(date)

        parts.append(supplier)

        if amount:
            parts.append(amount)

        filename = " - ".join(parts)
        filename = sanitize_filename(filename)

        if len(filename) > MAX_LENGTH:
            filename = filename[:MAX_LENGTH]

        return filename + ext

    # --------------------------------------------------
    # SONSTIGES
    # --------------------------------------------------

    parts = []

    year = safe(metadata.year)
    if year:
        parts.append(year)

    if document_type:
        parts.append(document_type)

    party = clean_party(contexts.get("party"))
    if party and party != "UNBEKANNT":
        parts.append(party)

    if not parts:
        original = os.path.splitext(os.path.basename(document.source_path))[0]
        parts.append(original)

    filename = "_".join(parts)
    filename = sanitize_filename(filename)

    if len(filename) > MAX_LENGTH:
        filename = filename[:MAX_LENGTH]

    return filename + ext