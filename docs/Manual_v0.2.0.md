# 📘 Sorterino – Benutzerhandbuch v0.2.0

## 1. Installation

1. Python 3.10+ installieren
2. Projekt entpacken
3. Virtuelle Umgebung erstellen
4. pip install -r requirements.txt

Tesseract und Poppler sind im Projekt enthalten.

---

## 2. Konfiguration

In config.json muss gesetzt werden:

"user_path": "C:\\Users\\DEINNAME\\Dokumente"

Sorterino erstellt dort automatisch:

- .sorterino_runtime (versteckt)
- Sorterino - Input
- Sorterino - Manuelle Sortierung

---

## 3. Dokumente verarbeiten

1. Dateien in „Sorterino - Input“ legen
2. main.py starten
3. Dokumente werden automatisch verarbeitet

---

## 4. Fallback-Regeln

Ein Dokument wird manuell verschoben wenn:

- kein OCR-Text erkannt wird
- keine Regel passt
- kein Zielpfad ermittelt werden kann
- Dateityp nicht unterstützt ist

---

## 5. Erweiterung

Neue Dokumenttypen können ergänzt werden über:

- rules.json
- structure.json

Keine Codeänderung notwendig.

---

## 6. Technischer Hinweis

- OCR: Tesseract (portable)
- PDF Rendering: Poppler
- Struktur-Routing: JSON-basiert
- Speicher: Interface-konformes FilesystemStorage