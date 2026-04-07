# SORTERINO v0.7.5 – DEVELOPER README

---

PROJEKTÜBERBLICK

Sorterino ist eine lokal laufende Dokumentenverarbeitungspipeline mit:

* regelbasierter Klassifikation
* optionaler OCR (Tesseract)
* IMAP-Mail-Integration
* GUI + Tray-Anwendung

Ziel: Automatisierte Ablage von Dokumenten ohne Cloud-Abhängigkeit

---

ARCHITEKTUR

CORE MODULE:

* main.py → Einstiegspunkt
* document_pipeline.py → zentrale Verarbeitung
* document_analyzer.py → Klassifikation + Extraktion
* storage_utils.py → Filesystem Handling
* tesseract_ocr.py → OCR Service
* mail_fetcher.py → IMAP Import
* config.py → zentrale Konfiguration

GUI:

* tray.py → Systemtray
* main_window.py → Hauptfenster
* config_window.py → Einstellungen
* log_window.py → Log Viewer

---

PIPELINE FLOW

run_pipeline():

1. Config laden
2. Workspace initialisieren
3. Mail-Abruf (IMAP)
4. OCR initialisieren (optional)
5. Dokumentquelle laden
6. Pipeline ausführen

DocumentPipeline.run():

FOR each document:
Backup
Format Check
OCR
Analyse (Classification + Metadata)
Storage (strukturierter Pfad)

---

KLASSIFIKATION

* Keyword-basiert
* Score = Treffer / Gesamtkeywords
* Bonuslogik:

  * Firmenkeywords → Ausgangsrechnung Boost
  * Zahlungsbegriffe → Eingangsrechnung Boost

Fallback:

→ Kategorie: MANUELL

---

DATEINAMEN-GENERIERUNG

Bestandteile:

* Datum
* Anbieter (z. B. GmbH)
* Betrag

Beispiel:

2025-03-19_Akoza GmbH_123,45.pdf

---

CONFIG SYSTEM

2 Ebenen:

1. Global:
   ~/.sorterino_config.json
   → enthält user_path

2. Runtime:
   .sorterino_runtime/config.json

Weitere Dateien:

* rules.json → Klassifikation
* structure.json → Ordnerstruktur

Templates liegen unter:

assets/templates/

---

WORKSPACE

Beim ersten Start:

.sorterino_runtime/
│
├── incoming/
├── logs/
├── backup/
├── error/
├── manual_sort/
├── processed/

Zusätzlich:

* Junctions im User-Ordner
* Hidden Flag auf Runtime

---

MAIL FETCHER

* IMAP4_SSL
* Filter: UNSEEN
* Attachments only
* Extensions whitelist
* Keyring für Credentials

Flagging:
→ Mail wird als verarbeitet markiert

---

OCR

Abhängigkeiten:

* Tesseract
* Poppler

Flow:

PDF → Image → Text
Image → Text

Fallback:
→ OCR deaktiviert → manuell

---

LOGGING

Zwei Ebenen:

FILE:

* logger.log()
* logger.error()

CONSOLE:

* info
* debug
* warning

Ziel:
Trennung zwischen Business-Logs und Debug

---

THREADING / LOCKING

* Lockfile verhindert Doppelstart
* GUI nutzt Threads für Pipeline
* Tray Singleton via Mutex

---

BUILD & RELEASE

EXE:

pyinstaller Sorterino.spec --noconfirm

INSTALLER:

iscc installer.iss

Wichtig:
README.txt wird mit installiert

---

KNOWN ISSUES

* Exception Handling teilweise zu generisch
* OCR abhängig von externer Installation
* Mail Debug-Ausgaben sehr verbose
* Auto-Mode Loop unvollständig implementiert

---

ROADMAP IDEEN

* ML-basierte Klassifikation
* bessere Fehleranalyse
* Retry-Mechanismen
* Batch-Verarbeitung
* Cloud optional

---

IHK KONTEXT

Projekt zeigt:

* modulare Architektur
* Trennung von GUI / Logik
* lokale Datenverarbeitung
* konfigurierbares System
* reale Business-Anwendung

---

VERSION 0.7.5

* Mail-Import stabilisiert
* UNSEEN Filter sauber implementiert
* Duplicate Handling verbessert
* Logging erweitert
* OCR robuster integriert

---

Dieses Projekt steht unter der MIT-Lizenz.

---

AUTHOR / CONTEXT

Entwickelt von:
Julien Blue Hirte

Im Auftrag der:
Seraph IT GmbH

Kontext:
Ausbildungsprojekt (Fachinformatiker Anwendungsentwicklung)