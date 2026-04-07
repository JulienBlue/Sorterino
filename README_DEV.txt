# SORTERINO v0.7.5 – DEVELOPER README

---

ARCHITEKTUR

Klare Trennung:

CORE

* document_pipeline.py
* document_analyzer.py
* storage_utils.py
* mail_fetcher.py

GUI

* main_window.py
* config_window.py
* mail_window.py (NEU → entkoppelt)
* log_window.py

---

WICHTIGE ÄNDERUNG (v0.7.5)

E-Mail Integration wurde vollständig aus ConfigWindow entfernt.

→ eigenes Window: mail_window.py
→ eigene Config-Verwaltung
→ klare Separation of Concerns

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

Boost:

* Firmenkeywords → Ausgangsrechnung
* Zahlungsbegriffe → Eingangsrechnung

Fallback:

→ MANUELL

---

SCHWACHSTELLE (AKTUELL!)

Regel-Engine:

* rein keyword-basiert
* keine Gewichtung
* kein Kontextverständnis
* Konflikte nicht sauber gelöst

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
* Keyring für Credentials
* Flagging nach Verarbeitung

---

LOGGING

FILE:

* log()
* error()

CONSOLE:

* info
* warning
* debug

---

KNOWN ISSUES

* Regeln zu simpel
* wenig Robustheit bei OCR-Ausfall
* keine Confidence-Schwellen
* keine Mehrfachklassifikation

---

NÄCHSTER SCHRITT

→ Regel-Engine überarbeiten

Ziele:

* stabilere Klassifikation
* bessere Trennung Eingangs/Ausgang
* Score-System verbessern
* Gewichtungen einführen

---

IHK RELEVANZ

Projekt zeigt:

* modulare Architektur
* GUI/Logic Separation
* lokale Datenverarbeitung
* erweiterbares Regelwerk

---

VERSION 0.7.5

* Mail-System refactored
* Architektur verbessert
* Grundlage für Regel-Engine Upgrade

---

AUTHOR

Julien Blue Hirte
Seraph IT GmbH
