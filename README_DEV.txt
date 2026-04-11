# SORTERINO v0.99 – DEVELOPER README

---

ARCHITEKTUR

Klare Trennung:

CORE

* document_pipeline.py
* document_analyzer.py
* storage_utils.py
* mail_fetcher.py
* initialize_workspace.py
* tesseract_ocr.py
* reporting.py
* logger.py
* config.py
* models.py
* autostart_service.py

GUI

* main_window.py
* config_window.py
* mail_window.py (separat)
* log_window.py
* daily_report_window.py
* user_window.py
* storage_window.py
* tray.py

ASSETS

* assets/templates/template.config.json
* assets/templates/template.rules.json
* assets/templates/template.structure.json
* assets/icons/*
* third_party/*

---

WICHTIGE ÄNDERUNGEN

* Runtime Ordner: "Sorterino - Runtime"
* config/rules/structure liegen in "Sorterino - Runtime\configs"
* Daily Report erzeugt JSON + TXT
* Production Build: GUI-only (keine Konsole)
* Regeln + Extraktion kommen aus rules.json

---

PIPELINE FLOW

run_pipeline():

1. Config laden
2. Workspace initialisieren
3. Mail Fetch (1x, vor Pipeline)
4. OCR init
5. Dokumente laden
6. Verarbeitung

---

KLASSIFIKATION

Keyword-basiert:

Score = Treffer / Keywords

Fallback:

* Dateiname kann Eingang/Ausgang erzwingen
* sonst → MANUELL

Dateiname-Overrides:

* Ausgangsrechnungen: "Rechnung_100012 vom 03.03.2025 Kunde.pdf"
* Eingangsrechnungen: "03.03.2025 Lieferant - 123,45.pdf"

---

SCHWACHSTELLE (AKTUELL!)

Regel-Engine:

* rein keyword-basiert
* kein Kontextverständnis
* Konflikte nur über einfache Prioritäten gelöst

→ nächster Fokusbereich

---

STORAGE

Path Builder basiert auf:

* Kategorie
* Dokumenttyp
* Datum

Fallback:

→ DIVERSES / Unsortiert

---

MAIL SYSTEM

* IMAP (UNSEEN)
* Attachments only
* nur aktiv, wenn Mail in config aktiviert ist

---

LOGGING

FILE:

* log()
* error()

CONSOLE:

* info
* warning
* debug

Daily:

* daily_events.jsonl
* daily_report_YYYY-MM-DD.txt
* daily_reports\YYYY-MM-DD.json

Daily Report Ablauf:

* Sammeln in daily_events.jsonl
* Generierung per Scheduler (Zeit in config)
* TXT für Nutzer + JSON für Struktur

---


→ Wenn Sortierung beim Nutzer hakt, liefere ich neue Rules / Structure

---

IHK RELEVANZ

Projekt zeigt:

* modulare Architektur
* GUI/Logic Separation
* lokale Datenverarbeitung
* erweiterbares Regelwerk

---

VERSION 0.99

* rules.json enthält Regeln + Extraktion
* Dateiname kann Klassifikation überschreiben
* Daily Report integriert
* Build: Production ready

---

AUTHOR

Julien Blue Hirte
Seraph IT GmbH
