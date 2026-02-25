# 🧠 Sorterino v0.2.0

Automatisierte OCR-Dokumenten-Engine mit regelbasierter Klassifikation.

---

# 🚀 Schnellstart

## Voraussetzungen

- Python 3.10+
- pip

Tesseract und Poppler sind im Ordner `third_party/` enthalten.

---

## 1️⃣ Konfiguration

Öffne:

config.json

Setze:

"user_path": "C:\\Users\\DEINNAME\\Dokumente"

Dieser Ordner ist dein Arbeitsverzeichnis.

---

## 2️⃣ Virtuelle Umgebung

python -m venv .venv
.venv\Scripts\activate

---

## 3️⃣ Abhängigkeiten installieren

pip install -r requirements.txt

---

## 4️⃣ Start

python main.py

---

# 📂 Verwendung

- Lege Dokumente in „Sorterino - Input“
- Sorterino verarbeitet automatisch:
  - OCR
  - Klassifikation
  - Umbenennung
  - Strukturierte Ablage

Unklare Dokumente landen in:
„Sorterino - Manuelle Sortierung“

---

# 🧠 Architektur

Layer-Struktur:

- Domain
- Usecases
- Infrastructure
- Interfaces

Regeldefinition erfolgt über:

- rules.json
- structure.json
- supported_formats.json

---

# 🧪 Tests

pytest

---

# 📦 Release v0.2.0

- Interface-konformes Storage
- Portable OCR
- JSON Routing stabil
- Modular erweiterbar