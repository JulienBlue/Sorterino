import re
from typing import Optional, List, Dict, Any

from domain.classification import Classification
from domain.document import Document
from domain.document_metadata import DocumentMetadata

from interfaces.logger_service import LoggerService


# --------------------------------------------------
# MONATSNAMEN
# --------------------------------------------------

MONTH_NAMES = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


# --------------------------------------------------
# DATUM (inkl. Textformate)
# --------------------------------------------------

def extract_invoice_date(text: str) -> Optional[str]:

    MONTH_MAP = {
        "januar": "01",
        "februar": "02",
        "märz": "03",
        "maerz": "03",
        "april": "04",
        "mai": "05",
        "juni": "06",
        "juli": "07",
        "august": "08",
        "september": "09",
        "oktober": "10",
        "november": "11",
        "dezember": "12",
    }

    EN_MONTH_MAP = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }

    # 1️⃣ Rechnungsdatum explizit
    match = re.search(
        r"Rechnungsdatum\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})",
        text,
        re.IGNORECASE
    )
    if match:
        return match.group(1)

    # 2️⃣ Klassisches Format
    match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if match:
        return match.group(1)

    # 3️⃣ Deutsches Textformat
    match = re.search(
        r"(\d{1,2})\.\s*(januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember)\s*(20\d{2})",
        text,
        re.IGNORECASE
    )
    if match:
        day = match.group(1).zfill(2)
        month = MONTH_MAP[match.group(2).lower()]
        year = match.group(3)
        return f"{day}.{month}.{year}"

    # 4️⃣ Englisches Format
    match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),\s*(20\d{2})",
        text,
        re.IGNORECASE
    )
    if match:
        month = EN_MONTH_MAP[match.group(1).lower()]
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{day}.{month}.{year}"

    return None


# --------------------------------------------------
# RECHNUNGSNUMMER
# --------------------------------------------------

def extract_invoice_number(text: str) -> Optional[str]:

    patterns = [
        r"Rechnungsnummer\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"Rechnungs[- ]?ID\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"Invoice\s*number\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"Invoice\s*ID\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"Auftragsnr\.?\s*[:\-]?\s*([A-Z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


# --------------------------------------------------
# JAHR
# --------------------------------------------------

def extract_year(text: str) -> Optional[int]:
    match = re.search(r"\b(20\d{2})\b", text)
    if match:
        return int(match.group(1))
    return None


# --------------------------------------------------
# BETRAG
# --------------------------------------------------

def extract_amount(text: str) -> Optional[str]:

    # 1️⃣ Bevorzugte Muster (kontextbasiert)
    priority_patterns = [
        r"Gesamtsumme\s*[:\-]?\s*€?\s*([0-9]+,[0-9]{2})",
        r"Rechnungsbetrag\s*[:\-]?\s*€?\s*([0-9]+,[0-9]{2})",
        r"Gesamtbetrag\s*[:\-]?\s*€?\s*([0-9]+,[0-9]{2})",
        r"Restbetrag\s*[:\-]?\s*€?\s*([0-9]+,[0-9]{2})",
        r"Total\s*€?\s*([0-9]+,[0-9]{2})",
    ]

    for pattern in priority_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).replace(".", "")

    # 2️⃣ Fallback: größten Betrag im Dokument nehmen
    all_amounts = re.findall(
        r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})",
        text
    )

    if all_amounts:

        def normalize(a: str) -> float:
            return float(a.replace(".", "").replace(",", "."))

        largest = max(all_amounts, key=normalize)
        return largest.replace(".", "")

    return None


# --------------------------------------------------
# ROLLENERKENNUNG (ROBUST)
# --------------------------------------------------

def detect_invoice_role(text: str, company_profile: Dict[str, Any]) -> str:

    own_company = company_profile.get("name", "")
    if not own_company:
        return "unknown"

    normalized_text = re.sub(r"\W+", "", text.lower())
    normalized_own = re.sub(r"\W+", "", own_company.lower())

    invoice_number = extract_invoice_number(text)

    if normalized_own in normalized_text and invoice_number:
        return "outgoing"

    return "incoming"


# --------------------------------------------------
# SUPPLIER
# --------------------------------------------------

def extract_supplier(text: str, company_profile: Dict[str, Any]) -> Optional[str]:

    own_company = re.sub(r"\W+", "", company_profile.get("name", "").lower())
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines[:25]:

        normalized_line = re.sub(r"\W+", "", line.lower())
        if own_company and own_company in normalized_line:
            continue

        if re.search(r"\b(GmbH|AG|KG|GbR|mbH)\b", line):
            return line.strip()

    return None


# --------------------------------------------------
# CUSTOMER
# --------------------------------------------------

import re
from typing import Dict, Any, Optional


def extract_customer(text: str, company_profile: Dict[str, Any]) -> Optional[str]:

    own_company = re.sub(r"\W+", "", company_profile.get("name", "").lower())
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    STOP_WORDS = [
        "LIEFER", "LEISTUNG", "RECHNUNGSDATUM",
        "KUNDENNUMMER", "RECHNUNG", "SEHR GEEHRTE",
        "IBAN", "BIC", "UST", "HRB"
    ]

    for i, line in enumerate(lines[:40]):

        normalized = re.sub(r"\W+", "", line.lower())

        # Eigene Firma erkannt → danach kommt Kunde
        if own_company in normalized:

            for l in lines[i + 1:i + 10]:

                candidate = l.strip()

                # Keine Adresszeilen
                if any(char.isdigit() for char in candidate):
                    continue

                upper_candidate = candidate.upper()

                # Stop bei typischen Folgebegriffen
                for word in STOP_WORDS:
                    if word in upper_candidate:
                        upper_candidate = upper_candidate.split(word)[0]

                upper_candidate = upper_candidate.split(" - ")[0]
                upper_candidate = upper_candidate.strip(" -")

                # Firmen mit Rechtsform bevorzugen
                if re.search(r"\b(GmbH|AG|KG|GbR|mbH|UG)\b", upper_candidate):
                    return upper_candidate

                # Personenname-Fallback (2-3 Wörter, Großbuchstaben)
                words = upper_candidate.split()
                if 2 <= len(words) <= 3 and all(
                        w[0].isupper() for w in words if w and w[0].isalpha()):
                    return upper_candidate

    return None


# --------------------------------------------------
# HAUPTFUNKTION
# --------------------------------------------------

def classify_document(
    document: Document,
    rules: List[Dict[str, Any]],
    company_profile: Dict[str, Any],
    logger: LoggerService
):

    text = document.extracted_text or ""

    if not text.strip():
        metadata = DocumentMetadata(
            year=None,
            category=None,
            document_type=None,
            contexts={}
        )
        document.set_metadata(metadata)
        return Classification(None, 0.0)

    invoice_number = extract_invoice_number(text)
    invoice_date = extract_invoice_date(text)
    year = extract_year(text)
    role = detect_invoice_role(text, company_profile)

    contexts: Dict[str, Any] = {}

    if invoice_number:
        contexts["invoice_number"] = invoice_number

    if invoice_date:
        contexts["invoice_date"] = invoice_date
        year = int(invoice_date.split(".")[2])

        month_number = int(invoice_date.split(".")[1])
        contexts["month_number"] = str(month_number).zfill(2)
        contexts["month_name"] = MONTH_NAMES.get(month_number)

    # Gebührenbescheid
    if "gebührenbescheid" in text.lower():
        metadata = DocumentMetadata(
            year=year,
            category="BUCHHALTUNG",
            document_type="Gebührenbescheid",
            contexts=contexts
        )
        document.set_metadata(metadata)
        return Classification("BUCHHALTUNG", 0.9)

    # AUSGANG
    if role == "outgoing" and invoice_number and invoice_date:
        customer = extract_customer(text, company_profile)
        logger.debug(f"Customer erkannt: {customer}")
        if customer:
            contexts["party"] = customer
        metadata = DocumentMetadata(
            year=year,
            category="BUCHHALTUNG",
            document_type="Ausgangsrechnung",
            contexts=contexts
        )
        document.set_metadata(metadata)
        return Classification("BUCHHALTUNG", 1.0)

    # EINGANG
    if role == "incoming" and (invoice_number or invoice_date):
        supplier = extract_supplier(text, company_profile)
        amount = extract_amount(text)
        if supplier:
            contexts["party"] = supplier
        if amount:
            contexts["amount"] = amount

        metadata = DocumentMetadata(
            year=year,
            category="BUCHHALTUNG",
            document_type="Eingangsrechnung",
            contexts=contexts
        )
        document.set_metadata(metadata)
        return Classification("BUCHHALTUNG", 0.95)

    # UNKLAR
    if invoice_number or invoice_date:
        metadata = DocumentMetadata(
            year=year,
            category="MANUELL",
            document_type="Unklare Rechnung",
            contexts=contexts
        )
        document.set_metadata(metadata)
        return Classification("MANUELL", 0.6)

    # MANUELL
    metadata = DocumentMetadata(
        year=year,
        category="MANUELL",
        document_type=None,
        contexts=contexts
   )
    document.set_metadata(metadata)
    return Classification("Manuell", 0.0)