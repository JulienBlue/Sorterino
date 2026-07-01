SORTERINO DEVELOPER README
==========================

Diese Datei beschreibt den technischen Stand von Sorterino: Setup, Aufbau,
wichtige Module, Pipeline, Konfiguration und Build.


PROJEKTSTAND
------------

Sorterino ist ein lokales Python-Desktopprojekt für OCR-basierte und
regelbasierte Rechnungsablage.

Der aktuelle Fokus liegt auf:

- Eingangsrechnungen
- Ausgangsrechnungen
- OCR-basierter Textextraktion
- regelbasierter Klassifikation
- nachvollziehbarer Dateibenennung
- manuellem Fallback bei unsicheren Fällen

Andere Dokumenttypen sind bewusst nicht der Kern des aktuellen MVP.


TECHNOLOGIEN
------------

- Python
- CustomTkinter
- Tesseract OCR
- Poppler / pdf2image
- Pillow
- IMAP-Mailimport
- keyring
- JSON-Konfiguration
- PyInstaller
- Inno Setup


SETUP
-----

Virtuelle Umgebung erstellen:

python -m venv .venv

Unter Windows aktivieren:

.\.venv\Scripts\Activate.ps1

Abhängigkeiten installieren:

pip install -r requirements.txt

GUI starten:

python -m src.gui.app

Nur die Pipeline ausführen:

python main.py

Tesseract und Poppler werden nicht im Source-Repository mitgeliefert. Die Pfade
werden in der Konfiguration gesetzt, zum Beispiel:

- third_party/tesseract/tesseract.exe
- third_party/poppler/Library/bin

Beim PyInstaller-Build wird der Ordner `third_party` mit in `dist/Sorterino`
übernommen. Die fertige EXE beziehungsweise der Installer bringt Tesseract und
Poppler deshalb mit. Separat nötig ist das Setup nur für den Source-Checkout
oder wenn direkt aus der Entwicklungsumgebung gestartet wird.

Die Ordnernamen müssen dabei stabil bleiben:

- `third_party/tesseract`
- `third_party/poppler`

Bitte keine Versionsnummern in die Ordnernamen übernehmen. Poppler wird einfach
nach `third_party/poppler` kopiert, sodass der Binärpfad
`third_party/poppler/Library/bin` erhalten bleibt.

Für Windows ist der UB-Mannheim-Installer der einfachste Weg:

https://github.com/UB-Mannheim/tesseract/wiki

Bei der Installation unter `Language data` mit auswählen:

- English
- Orientation and script detection

Zusätzlich unter `Additional language data (download)` mit auswählen:

- German
- French

Am Ende müssen diese Sprachdateien vorhanden sein:

- `deu.traineddata` für Deutsch
- `eng.traineddata` für Englisch
- `fra.traineddata` für Französisch
- `osd.traineddata` für Orientation/Script Detection

Sorterino nutzt aktuell `deu+eng+fra` als OCR-Sprachen.

Aktuelle Download-Links stehen auch in `requirements.txt`:

- Tesseract Windows Installer: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler Windows Builds: https://github.com/oschwartz10612/poppler-windows/releases

Lokale Third-Party-Binaries bleiben lokal und werden nicht committed.


WICHTIGE MODULE
---------------

Startpunkte:

- `src/gui/app.py` startet die Desktop-GUI.
- `main.py` führt nur den Pipeline-Lauf aus.

Core:

- `src/config.py`
- `src/initialize_workspace.py`
- `src/document_pipeline.py`
- `src/document_analyzer.py`
- `src/storage_utils.py`
- `src/tesseract_ocr.py`
- `src/mail_fetcher.py`
- `src/reporting.py`
- `src/logger.py`
- `src/models.py`
- `src/autostart_service.py`

GUI:

- `src/gui/app.py`
- `src/gui/main_window.py`
- `src/gui/config_window.py`
- `src/gui/storage_window.py`
- `src/gui/user_window.py`
- `src/gui/mail_window.py`
- `src/gui/log_window.py`
- `src/gui/daily_report_window.py`
- `src/gui/tray.py`

Assets:

- `assets/templates/template.config.json`
- `assets/templates/template.rules.json`
- `assets/templates/template.structure.json`
- `assets/icons/`


ARCHITEKTUR
-----------

Die Architektur ist schichtenorientiert, aber pragmatisch. Mir war wichtiger,
dass die Verantwortlichkeiten nachvollziehbar getrennt sind, als eine
lehrbuchreine Clean Architecture zu bauen.

Grob gesagt:

- `DocumentPipeline` steuert den Gesamtprozess.
- `FolderDocumentSource` holt Dokumente aus dem Input-Ordner.
- `TesseractOCR` kümmert sich um OCR und PDF-Konvertierung.
- `DocumentAnalyzer` klassifiziert Dokumente und extrahiert Metadaten.
- `StoragePathBuilder` erzeugt Zielpfade und Dateinamen.
- `FilesystemStorage` verschiebt Dateien in Archiv, Manual oder Error.
- `Document` und `DocumentStatus` halten den Verarbeitungszustand fest.


PIPELINE
--------

Der Ablauf in `run_pipeline()`:

1. Basis- und Runtime-Konfiguration laden
2. Workspace initialisieren
3. IMAP-Abruf ausführen, falls aktiviert
4. OCR initialisieren
5. Dokumente aus dem Input laden
6. Backup erstellen
7. OCR und Textextraktion ausführen
8. Eingangs- oder Ausgangsrechnung erkennen
9. Pflichtdaten prüfen
10. Datei benennen und ablegen
11. unklare Fälle in die manuelle Sortierung legen
12. technische Fehler in Error ablegen
13. Logs und Daily Reports schreiben


KLASSIFIKATION
--------------

Die Klassifikation ist absichtlich regelbasiert und überschaubar.

- `rules.json` enthält Rechnungsregeln und Extraktionsmuster.
- Dateinamen können Eingang oder Ausgang zusätzlich beeinflussen.
- Die eigene Firma wird über gepflegte Firmendaten und Keywords erkannt.
- Unsichere Fälle gehen in die manuelle Sortierung.

Pflichtdaten für automatische Ablage:

- Eingangsrechnung: `date`, `vendor`
- Ausgangsrechnung: `date`, `vendor`, `invoice_number`


KONFIGURATION
-------------

Basis-Konfiguration:

%USERPROFILE%\.sorterino_config.json

Runtime-Konfiguration:

<user_path>\Sorterino - Runtime\configs\config.json
<user_path>\Sorterino - Runtime\configs\rules.json
<user_path>\Sorterino - Runtime\configs\structure.json

Templates:

assets/templates/template.config.json
assets/templates/template.rules.json
assets/templates/template.structure.json

Dokumentation und Screenshots liegen unter:

docs/diagrams/
docs/screenshots/
docs/commands.md
docs/Produktstände/

Wenn die Sortierung nicht passt, sollten zuerst `rules.json` und
`structure.json` angepasst werden. Die Kernlogik sollte dafür möglichst nicht
angefasst werden.


DATEINAMEN UND PFADBAU
----------------------

OCR-Text wird in `Document.extracted_text` gespeichert.

`sanitize` bereinigt Dateinamen für Windows-Dateisysteme. Die Funktion ist für
Dateinamen gedacht und kein Schutz gegen SQL Injection.

Beispiel Eingangsrechnung:

20.04.2026 - Demo Supplier GmbH - 185,40.pdf

Beispiel Ausgangsrechnung:

Rechnung 70015 vom 20.04.2026 Demo Customer GmbH.pdf


MANUAL UND ERROR
----------------

Manual bedeutet: fachlich unsicher oder unvollständig.

Error bedeutet: technischer Fehler.

Der Manual-Fallback ist eine bewusste Schutzmaßnahme gegen falsche Ablage.


BUILD
-----

PyInstaller-Build:

pyinstaller Sorterino.spec --noconfirm

Windows-Installer mit Inno Setup:

iscc installer.iss

Fertige Installer-EXEs gehören in GitHub Releases, nicht in den Source-Stand.


GIT-HYGIENE
-----------

Nicht ins Source-Repository gehören:

- lokale virtuelle Umgebungen
- lokale IDE-Ordner
- Python-Caches
- lokale Third-Party-Binaries
- lokale Build- und Dist-Artefakte
- fertige Installer-EXEs
- Runtime-Daten, Logs und echte Nutzerdokumente


TESTIDEEN
---------

Sinnvolle nächste Tests:

- `sanitize`
- `StoragePathBuilder`
- Basisfälle für `DocumentAnalyzer`
- Pflichtdatenprüfung
- Dateinamenbildung
- kleiner Pipeline-Smoke-Test mit Mock-OCR


ROADMAP
-------

- Tests ergänzen
- Screenshots mit neutraler Demo-Konfiguration neu aufnehmen
- Tesseract-/Poppler-Setup genauer dokumentieren
- Dateinamenskonventionen vereinheitlichen
- Doku-Struktur weiter aufräumen, wenn sie im Repo bleibt
