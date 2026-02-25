import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from domain.classification import Classification
from domain.document import Document
from domain.document_metadata import DocumentMetadata


# --------------------------------------------------
# Wortgrenzen-Matching
# --------------------------------------------------

def keyword_matches(text: str, keyword: str) -> bool:
    pattern = rf"\b{re.escape(keyword.lower())}\b"
    return re.search(pattern, text) is not None


def score_rule(text: str, rule: Dict[str, Any]) -> int:
    return sum(1 for k in rule["keywords"] if keyword_matches(text, k))


def apply_rules(text_lower: str, rules: List[Dict[str, Any]]):
    best_score = 0
    best_rule = None

    for rule in rules:
        score = score_rule(text_lower, rule)
        if score > best_score:
            best_score = score
            best_rule = rule

    if best_rule and best_score >= 1:
        return best_rule["category"], best_rule["document_type"]

    return None, None


# --------------------------------------------------
# Jahr extrahieren (für Steuerjahr)
# --------------------------------------------------

def extract_year(text: str) -> Optional[int]:
    match = re.search(r"für\s+(20\d{2})", text.lower())
    if match:
        return int(match.group(1))

    fallback = re.search(r"\b(20\d{2})\b", text)
    if fallback:
        return int(fallback.group(1))

    return None


# --------------------------------------------------
# Arbeitgeber extrahieren
# --------------------------------------------------

def extract_employer(text: str) -> Optional[str]:
    match = re.search(
        r"\n([A-ZÄÖÜa-zäöüß\s&\-]+(?:GmbH|GbR|AG|KG|UG))",
        text
    )
    if match:
        name = match.group(1).strip()
        return sanitize(name)

    return None


# --------------------------------------------------
# Zeitraum extrahieren (01.01.-31.07.)
# --------------------------------------------------

def extract_bescheinigungszeitraum(text: str):
    match = re.search(
        r"(\d{2}\.\d{2})\.?\s*[-–]\s*(\d{2}\.\d{2})\.?",
        text
    )

    if match:
        start = match.group(1)
        end = match.group(2)
        return f"{start}.-{end}."

    return None


# --------------------------------------------------
# Sanitizer
# --------------------------------------------------

def sanitize(value: str) -> str:
    value = value.strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_äöüÄÖÜß\-]", "", value)
    return value


# --------------------------------------------------
# Hauptklassifikation
# --------------------------------------------------

def classify_document(document: Document, rules: List[Dict[str, Any]]):

    text = document.extracted_text or ""

    if not text.strip():
        return Classification(category="Manuell", confidence=0.1)

    text_lower = text.lower()

    category, document_type = apply_rules(text_lower, rules)

    contexts: Dict[str, str] = {}

    year = extract_year(text)

    if document_type == "Lohnsteuerbescheinigung":

        employer = extract_employer(text)
        if employer:
            contexts["Firma"] = employer

        zeitraum = extract_bescheinigungszeitraum(text)
        if zeitraum:
            contexts["Zeitraum"] = zeitraum

    metadata = DocumentMetadata(
        year=year,
        category=category,
        document_type=document_type,
        contexts=contexts
    )

    document.set_metadata(metadata)

    if category:
        return Classification(category=category, confidence=0.9)

    return Classification(category="Manuell", confidence=0.2)