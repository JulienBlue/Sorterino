# 🧠 SORTERINO – Projektkontext (Stand: stabile Lohnsteuer-Engine)

Dieses Dokument dient als vollständiger Projekt-Kontext für neue Chats.  
Es enthält:

1. Projektziel  
2. Architekturüberblick  
3. Aktuelle Kernfeatures  
4. Vollständige relevante Dateien (aktuellste Versionen)  
5. Projektordnerstruktur  

---

# 🎯 Projektziel

Sorterino ist eine modulare Dokumenten-Engine zur:

- OCR-Verarbeitung (Tesseract + Poppler, portable im Projekt)
- Score-basierter Klassifikation mit Wortgrenzen
- Kontext-Extraktion (Arbeitgeber, Bank, Zeitraum)
- Dynamischer Dateibenennung
- Strukturierter Pfadauflösung
- Robuster Verarbeitung (OCR-Toleranz)

Aktueller Schwerpunkt:
✔ Lohnsteuerbescheinigungen mit Arbeitgeber + Zeitraum im Dateinamen  
✔ Robuste Zeitraum-Erkennung trotz OCR-Artefakten  

Beispiel Ziel-Dateiname:

```
09.08.-12.11._Theater_Hagen_gGmbH_Lohnsteuerbescheinigung.pdf
```

---

# 🏗 Architekturüberblick

- Clean-ish Layer Separation
- Domain Layer (Entities, Metadata)
- Usecases Layer (Business Logic)
- Infrastructure Layer (OCR, Storage, Config)
- JSON-basierte Struktur- und Regeldefinition

---

# 📁 AKTUELLE RELEVANTE DATEIEN (Vollständig)

---

## 1️⃣ domain/document_metadata.py

```python
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class DocumentMetadata:
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    category: Optional[str] = None
    document_type: Optional[str] = None

    invoice_number: Optional[str] = None

    # Kontexte wie Firma, Zeitraum, Bank etc.
    contexts: Dict[str, str] = field(default_factory=dict)
```

---

## 2️⃣ usecases/classify_document.py (aktuellste Version)

```python
import re
from typing import Optional, List, Dict, Any

from domain.classification import Classification
from domain.document import Document
from domain.document_metadata import DocumentMetadata


# ------------------------------------------
# Keyword Matching mit Wortgrenzen
# ------------------------------------------

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


# ------------------------------------------
# Jahr extrahieren
# ------------------------------------------

def extract_year(text: str) -> Optional[int]:
    match = re.search(r"für\s+(20\d{2})", text.lower())
    if match:
        return int(match.group(1))

    fallback = re.search(r"\b(20\d{2})\b", text)
    if fallback:
        return int(fallback.group(1))

    return None


# ------------------------------------------
# Arbeitgeber extrahieren
# ------------------------------------------

def sanitize(value: str) -> str:
    value = value.strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_äöüÄÖÜß\-]", "", value)
    return value


def extract_employer(text: str) -> Optional[str]:
    match = re.search(
        r"\n([A-ZÄÖÜa-zäöüß\s&\-]+(?:GmbH|GbR|AG|KG|UG|gGmbH))",
        text
    )
    if match:
        return sanitize(match.group(1).strip())
    return None


# ------------------------------------------
# Hardcore Zeitraum-Erkennung
# ------------------------------------------

def extract_bescheinigungszeitraum(text: str):
    match = re.search(
        r"(\d{2}\.\d{2}).{0,5}(\d{2}\.\d{2})",
        text
    )

    if match:
        start = match.group(1)
        end = match.group(2)
        return f"{start}.-{end}."

    return None


# ------------------------------------------
# Hauptklassifikation
# ------------------------------------------

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
```

---

## 3️⃣ usecases/rename_document.py (aktuellste Version)

```python
import re


def sanitize(value: str) -> str:
    value = value.strip()
    value = value.replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_äöüÄÖÜß\-\.]", "", value)
    return value


def rename_document(document):

    metadata = document.metadata

    # ------------------------------------------
    # Lohnsteuerbescheinigung
    # ------------------------------------------

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

    # ------------------------------------------
    # Standard
    # ------------------------------------------

    parts = []

    if metadata.year:
        parts.append(str(metadata.year))

    if metadata.document_type:
        parts.append(metadata.document_type)

    if not parts:
        return "Unbenannt.pdf"

    return "_".join(parts) + ".pdf"
```

---

# 📂 Projektstruktur (relevant für Sorterino)

```
Sorterino/
│
├── src/
│   ├── main.py
│   │
│   ├── domain/
│   │   ├── document.py
│   │   ├── classification.py
│   │   └── document_metadata.py
│   │
│   ├── usecases/
│   │   ├── classify_document.py
│   │   ├── rename_document.py
│   │   ├── document_pipeline.py
│   │   └── path_resolver.py
│   │
│   ├── infrastructure/
│   │   ├── ocr/
│   │   │   └── tesseract_ocr.py
│   │   │
│   │   ├── storage/
│   │   │   └── filesystem_storage.py
│   │   │
│   │   ├── logging/
│   │   │   └── file_logger.py
│   │   │
│   │   └── config/
│   │       ├── config_loader.py
│   │       ├── rules_loader.py
│   │       ├── structure_loader.py
│   │       ├── formats_loader.py
│   │       └── initialize_workspace.py
│
├── rules.json
├── structure.json
├── supported_formats.json
│
├── third_party/
│   ├── Tesseract-OCR/
│   └── poppler-25.x/
│
└── .venv/
```

---

# 🔚 Aktueller Funktionsstand

✔ Score-basierte Klassifikation  
✔ Wortgrenzen-Matching  
✔ Portable Tesseract  
✔ Robuste Zeitraum-Erkennung  
✔ Arbeitgeber-Erkennung  
✔ Kontextbasierte Dateibenennung  
✔ JSON-Struktur-Routing  

---

Wenn du das in einen neuen Chat postest, weiß ich exakt:

- Wo wir architektonisch stehen  
- Welche Version der Dateien aktiv ist  
- Welche Features stabil sind  
- Wo wir als nächstes optimieren können  

🚀 Sorterino ist aktuell eine robuste Dokumenten-Engine.