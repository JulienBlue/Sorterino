# 📦 Sorterino – Rekonstruierte Versionshistorie

Diese Historie ist technisch-architektonisch gegliedert und nicht rein chronologisch aufgebaut.

---

## 🟢 V0.0.1 – Projektgrundlage & Pipeline-Prototyp

**Charakter:** Technischer Rohbau

### Enthalten

- Erste `DocumentPipeline`
- Basis-OCR Integration
- Erste Klassifikation mit einfachen `if`-Abfragen
- Rename-Logik
- `FilesystemStorage`
- Backup-Modul (erste Version)
- Workspace-Initialisierung
- Ordnerstruktur: `Input / Backup / Manuell / Processing`

### Architektur

- Noch relativ monolithisch
- Harte Keyword-Logik
- Keine externe Konfiguration für Rules
- Keine Struktur-Engine

---

## 🟢 V0.1.0 – Struktur-Engine & Package-Refactor

**Charakter:** Architektur-Sprung

Diese Version markiert den Übergang von einer funktionalen Pipeline zu einer konfigurierbaren Systemarchitektur.

### 🔹 1. Strukturgetriebene Ablage

- Einführung von `structure.json`
- Dynamischer `PathResolver`
- Platzhalter-System `{Jahr}`, `{Firma}`, `{Bank}`, etc.
- Lazy Folder Creation (Ordner nur bei Bedarf)

### 🔹 2. Metadata-Refactor

- Weg von starren Feldern (`bank`, `employer`, etc.)
- Einführung von `contexts: dict`
- Generisches Kontextsystem

### 🔹 3. Config-Externalisierung

- `rules.json`
- `supported_formats.json`
- `structure.json`
- Loader-Klassen für Konfigurationen

### 🔹 4. Python-Package-Fix

- Relative Imports
- Start via `python -m src.main`
- Einführung von `__init__.py`
- Saubere Package-Struktur

> Erste Version mit echter Systemarchitektur.

---

## 🟢 V0.2.0 – Architektur-Stabilisierung & Release

**Charakter:** Stabilisierung & Produktionsreife

### Enthalten

- Testarchitektur mit `pytest`
- Qualitätssicherung der Klassifikationslogik
- Runtime-Isolation über `.sorterino_runtime`
- Stabilisierung von `FilesystemStorage`
- Fallback für nicht unterstützte Dateitypen
- Cleanup leerer Input-Ordner
- Robustere Fehlerbehandlung innerhalb der Pipeline

### Bugfixes

- Korrekturen in `determine_target_path`
- Stabilisierung von `rename_document`
- Verbesserte Backup-Integration

> Fokus lag auf Robustheit, Fehlerbehandlung und Edge-Cases.

---

## 🟢 V0.2.1 – Erweiterte Klassifikationslogik

**Charakter:** Fachliche Vertiefung

### Umgesetzt

- Deutliche Erweiterung der `rules.json`
- Erweiterte steuerliche Dokumenttypen
- Erweiterte Versicherungs-Dokumenttypen
- Erweiterte Finanz- und Rechnungsregeln
- Zusätzliche Schlüsselwörter für bessere Trefferquote
- Präzisere Zuordnung über Score-basierte Regelbewertung

### Wirkung

- Höhere Klassifikationsgenauigkeit
- Reduzierung manueller Nachsortierung
- Verbesserte Abdeckung realer Geschäftsdokumente

> Architektur unverändert, Fokus ausschließlich auf fachlicher Erweiterung.

---

## 🟢 V0.2.2 – Buchhaltungslogik & Pipeline-Refactor

**Charakter:** Funktionale Erweiterung & interne Strukturverbesserung

### 1. Automatische Eingangsrechnungs-Erkennung

Neu implementiert:

- `looks_like_invoice()` zur heuristischen Rechnungserkennung
- Supplier-Erkennung (`extract_supplier`)
- Betrags-Extraktion (`extract_amount`)
- Monats-Extraktion (`extract_month`)
- Erweiterte Kontextfelder:
  - `supplier`
  - `amount`
  - `month_number`
  - `month_name`

Neue automatische Klassifikation:

- Kategorie: `BUCHHALTUNG`
- Dokumenttyp: `Eingangsrechnung`
- Erhöhte Confidence bei Rechnungserkennung

### 2. Erweiterte Klassifikationssignatur

Anpassung von:

```python
classify_document(document, rules)

zu:

classify_document(document, rules, company_profile)

Integration eines company_profile

Eigene Firma wird bei Supplier-Erkennung bewusst ausgeschlossen

3. Pipeline-Refactor

Erweiterung der DocumentPipeline:

Trennung von Runtime-Storage und Archiv-Storage

Einführung zusätzlicher Zielpfade:

manual_sort_target

error_target

unsupported_target

Übergabe von company_profile an die Klassifikation

4. Interne Strukturverbesserungen

Erweiterte Kontextverarbeitung innerhalb von DocumentMetadata

Verbesserte Fehlerbehandlung bei Spezialfällen

Stabilisierung der Testfälle für Zeitraum- und Routing-Logik

V0.2.2 erweitert Sorterino um echte buchhalterische Intelligenz und bereitet die Architektur auf komplexere Analysefunktionen vor.