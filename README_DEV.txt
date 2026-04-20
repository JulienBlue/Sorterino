# SORTERINO v1.0 – DEVELOPER README

---

PROJEKTSTAND

Sorterino 1.0 ist bewusst auf eine stabile Rechnungsverarbeitung reduziert.

Der aktuelle Fokus liegt auf:

* Eingangsrechnungen
* Ausgangsrechnungen
* OCR-basierter Textextraktion
* regelbasierter Klassifikation
* standardisierter Benennung
* manueller Fallback-Ablage bei unsicheren Fällen

Andere Dokumenttypen sind im produktiven Stand bewusst nicht mehr Bestandteil der Templates.

---

ARCHITEKTUR

CORE

* `main.py`
* `src/config.py`
* `src/initialize_workspace.py`
* `src/document_pipeline.py`
* `src/document_analyzer.py`
* `src/storage_utils.py`
* `src/tesseract_ocr.py`
* `src/mail_fetcher.py`
* `src/reporting.py`
* `src/logger.py`
* `src/models.py`
* `src/autostart_service.py`

GUI

* `src/gui/app.py`
* `src/gui/main_window.py`
* `src/gui/config_window.py`
* `src/gui/storage_window.py`
* `src/gui/user_window.py`
* `src/gui/mail_window.py`
* `src/gui/log_window.py`
* `src/gui/daily_report_window.py`
* `src/gui/tray.py`

ASSETS

* `assets/templates/template.config.json`
* `assets/templates/template.rules.json`
* `assets/templates/template.structure.json`
* `assets/icons/*`
* `third_party/*`

---

AKTUELLER FLOW

`run_pipeline()`:

1. Basis- und Runtime-Config laden
2. Workspace initialisieren
3. IMAP-Abruf ausführen, falls aktiviert
4. OCR initialisieren
5. Dokumente aus dem Input laden
6. Backup erstellen
7. OCR und Extraktion durchführen
8. Eingangs- oder Ausgangsrechnung bestimmen
9. Pflichtdaten prüfen
10. Datei benennen und ablegen
11. unklare Fälle in die manuelle Sortierung legen

---

KLASSIFIKATION

Die Klassifikation ist im aktuellen Stand absichtlich schlank.

* `rules.json` enthält eine Rechnungsregel
* Dateiname kann Eingang oder Ausgang zusätzlich erzwingen
* eigener Rechnungssteller wird über die gepflegten Firmendaten erkannt
* alles Unsichere geht in `BUCHHALTUNG\Unsortiert`

Pflichtdaten für automatische Ablage:

* Eingangsrechnung: `date`, `vendor`
* Ausgangsrechnung: `date`, `vendor`, `invoice_number`

---

BENENNUNG

Eingangsrechnungen:
`TT.MM.JJJJ - Lieferant - Betrag.pdf`

Ausgangsrechnungen:
`Rechnung <Nummer> vom <Datum> <Kunde>.pdf`

---

KONFIGURATION

Basis-Config:

* `%USERPROFILE%\.sorterino_config.json`
* enthält den gewählten Speicherort

Runtime:

* `<user_path>\Sorterino - Runtime\configs\config.json`
* `<user_path>\Sorterino - Runtime\configs\rules.json`
* `<user_path>\Sorterino - Runtime\configs\structure.json`

Templates für neue Installationen:

* `assets/templates/template.config.json`
* `assets/templates/template.rules.json`
* `assets/templates/template.structure.json`

Wichtig:
Wenn die Sortierung beim Nutzer nicht sauber passt, sollen bevorzugt `rules.json` und `structure.json` angepasst werden, nicht die Kernlogik.

---

LOGGING UND REPORTING

Logs liegen in:

* `<runtime>\logs`

Daily Reports:

* TXT für Nutzer
* JSON für strukturierte Weiterverarbeitung

Zusätzlich gibt es:

* Backup der Originaldateien
* manuellen Fallback
* Fehlerablage bei technischen Problemen

---

BUILD

Executable:

* `pyinstaller Sorterino.spec --noconfirm`

Installer:

* `iscc installer.iss`

Ziel ist ein produktionsnaher Build für Endnutzer. Konfigurationsanpassungen sollen später möglichst über GUI, `rules.json` und `structure.json` erfolgen.

---

VERSION 1.0

* produktionsorientierter Stand
* Templates auf Rechnungsverarbeitung reduziert
* Eingangs- und Ausgangsrechnungen stabil getrennt
* manuelle Sortierung sauber eingebunden

---

AUTOR

Julien Blue Hirte
Seraph IT GmbH
