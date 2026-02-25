import re


def sanitize(value: str) -> str:
    value = value.strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_äöüÄÖÜß\-\.]", "", value)
    return value


def rename_document(document):

    metadata = document.metadata

    # --------------------------------------------------
    # Lohnsteuerbescheinigung
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
    # Standardfall
    # --------------------------------------------------

    parts = []

    if metadata.year:
        parts.append(str(metadata.year))

    if metadata.document_type:
        parts.append(metadata.document_type)

    if not parts:
        return "Unbenannt.pdf"

    return "_".join(parts) + ".pdf"