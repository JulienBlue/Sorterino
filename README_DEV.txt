SORTERINO – ENTWICKLERDOKUMENTATION
==================================

Diese Datei beschreibt den aktuellen technischen Stand des lokalen
Windows-Desktopprojekts Sorterino.


ZIEL UND AKTUELLER FUNKTIONSUMFANG
----------------------------------

Sorterino verarbeitet Dokumente lokal, ordnet sie Privatpersonen, Familien oder
Organisationen zu und archiviert eindeutige Fälle regelbasiert. Die gewichtete
Klassifikation deckt Rechnungen, Arbeit, Steuern, Finanzen,
Versicherungen, Gesundheit, Wohnen, Verträge, Identität, Kinder- und
Fahrzeugdokumente ab. Eindeutige Anker und unterstützende Begriffe werden
getrennt bewertet; mehrdeutige Treffer gehen bewusst in die manuelle Prüfung.
Das Profil-, Personen-, Regel- und Ablagemodell unterstützt unterschiedliche
private, familiäre und geschäftliche Kontexte.

Unsichere fachliche Zuordnungen landen in der manuellen Prüfung. Technische
Fehler werden davon getrennt behandelt. Es gibt keine Cloud-Verarbeitung.

Rechnungen mit einem Familien- oder Privatprofil durchlaufen zusätzlich eine
Kontextprüfung. „Privater Kauf“ führt zu den Kaufbelegen oder wahlweise in die
privaten Steuerbelege des gewählten Jahres; „Für eigenes Unternehmen“ verlangt
ein Firmenprofil und ist nicht mit privater steuerlicher Absetzbarkeit gleichzusetzen.
Eindeutig einem Firmenprofil zugeordnete Rechnungen dürfen automatisch laufen.
Auch die manuelle Ablage erstellt vor dem Verschieben ein Original-Backup. Der
Backupname bleibt unverändert; nur die anschließend archivierte Arbeitsdatei
erhält den vorgeschlagenen oder vom Nutzer bestätigten Namen.


TECHNOLOGIEN
------------

- Python
- CustomTkinter
- Tesseract OCR über pytesseract
- Poppler und pdf2image
- Pillow
- pillow-heif für HEIC/HEIF
- olefile für die kontrollierte MSG-Feldextraktion
- IMAP über TLS; Google und Microsoft mit SASL XOAUTH2
- keyring für den Windows-Anmeldeinformationsspeicher
- JSON-Konfiguration
- SQLite-Dokumentregister über Pythons Standardbibliothek `sqlite3`
- PyInstaller
- Inno Setup
- unittest


START UND SETUP
---------------

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

GUI:

python -m src.gui.app

Ein einzelner Pipeline-Lauf:

python main.py

Tests:

python -m unittest discover -s tests -v

Bytecode-/Importsyntax prüfen:

python -m compileall -q main.py src tests

Tesseract und Poppler werden im Source-Repository nicht versioniert. Erwartete
lokale Buildpfade:

- `third_party/tesseract/tesseract.exe`
- `third_party/tesseract/tessdata/deu.traineddata`
- `third_party/tesseract/tessdata/eng.traineddata`
- `third_party/tesseract/tessdata/fra.traineddata`
- `third_party/tesseract/tessdata/osd.traineddata`
- `third_party/poppler/Library/bin`

Der gebaute Windows-Ordner und Installer enthalten diese Laufzeiten. Hinweise
und Bezugsquellen stehen in `requirements.txt`.


STARTPUNKTE UND MODULE
----------------------

Startpunkte:

- `src/gui/app.py`: GUI, Theme, Tray-Integration und Hauptfenster
- `main.py`: Pipeline ohne GUI

Konfiguration und Profile:

- `src/config.py`: AppData-Pfade, Einstellungen und Legacy-Migration
- `src/initialize_workspace.py`: lokale Arbeitsverzeichnisse
- `src/profile_service.py`: Profile, Personen, Mitgliedschaften und E-Mail-Konten
- `src/profile_registry.py`: atomare JSON-Persistenz, Templates und Split-Registry
- `src/profile_labels.py`: Rollenbegriffe und reine Mitgliedschaftsabfragen
- `src/profile_errors.py`: gemeinsame Validierungsfehler ohne Schichtenkopplung
- `src/profile_matcher.py`: profil- und personenbezogene Erkennung
- `src/policy_resolver.py`: Vererbung von Regeln und Strukturen
- `src/identifier_formats.py`: Normalisierung und Validierung von Kennungen

Verarbeitung:

- `src/document_pipeline.py`: Orchestrierung des Verarbeitungslaufs
- `src/database.py`: versioniertes SQLite-Schema und Transaktionsgrenzen
- `src/document_registry.py`: dauerhafte Dokumentidentität, Fundorte und Ereignisse
- `src/duplicate_index.py`: SHA-256-Duplikatprüfung auf Basis des SQLite-Registers
- `src/tesseract_ocr.py`: OCR und PDF-Vorbereitung
- `src/document_formats.py`: zentrale Liste unterstützter Dateiformate
- `src/document_text_extractor.py`: sichere Office-, Pages-, E-Mail- und Textauswertung
- `src/document_analyzer.py`: Orchestrierung, Kernklassifikation und generische Felder
- `src/document_classification_support.py`: fachliche Spezialklassifikationen
- `src/document_domain_extractors.py`: Urkunden-, Arbeits- und Steuerextraktoren
- `src/document_transaction_extractors.py`: Energie-, Retouren- und Kassenbonextraktoren
- `src/storage_utils.py`: Dateiquellen, Ablage und Dateinamen
- `src/manual_filing.py`: kontrollierte manuelle Ablage
- `src/mail_fetcher.py`: profilbezogener IMAP-Import
- `src/mail_auth.py`: PKCE-OAuth, Provider-Pinning, TLS und Windows-Tresor
- `src/reporting.py`: Verarbeitungsereignisse und Berichte
- `src/logger.py`: technische Protokollierung
- `src/models.py`: Dokumentmodell und Status

GUI:

- `src/gui/main_window.py`: persistente Navigation und Hauptbereiche
- `src/gui/embedded.py`: eingebettete Seiten
- `src/gui/profile_window.py`: Profile, Personen, Zuordnung und sichere Löschung
- `src/gui/profile_deletion.py`: bestätigte Löschdialoge und sichere Archivpfade
- `src/gui/view_state.py`: testbare Zustandsentscheidungen ohne Tk-Abhängigkeit
- `src/gui/manual_review_window.py`: manuelle Dokumentzuordnung
- `src/gui/mail_window.py`: Profilpostfächer
- `src/gui/config_window.py`: technische JSON-Editoren
- `src/gui/help_window.py`: kontextbezogene Hilfe und Diagnose
- `src/gui/log_window.py`: Logs
- `src/gui/appearance.py`: Hell, Dunkel und Systemdarstellung
- `src/gui/tray.py`: Tray-Anwendung


GUI-ARCHITEKTUR
---------------

Bis auf die Hilfe arbeitet Sorterino in einem Fenster. Das Hauptmenü bleibt
links sichtbar; der rechte Inhaltsbereich wird ausgetauscht. Die Navigation
verwaltet einen Verlauf für Vor und Zurück. Eingebettete Seiten deklarieren
über `help_context`, welchen Hilfetext und welche Diagnose sie benötigen.
Profilbezogene Speichervorgänge laufen zentral über `return_to_profiles()`.
Dabei werden verschachtelte Anlageansichten aus dem Verlauf entfernt, das
betroffene Profil ausgewählt und für fünf Sekunden ein Erfolgsbanner angezeigt.
Ohne `user_path` öffnet `InitialStorageDialog` einmalig den verpflichtenden,
modalen Willkommensschritt. Die Explorer-Auswahl startet erst über dessen
Schaltfläche; Abbrechen lässt den Dialog und den unveränderten Zustand bestehen.

Die sichtbaren Begriffe sind bewusst vom internen Modell getrennt:

- `individual` → Privatperson
- `family` → Familie oder Haushalt
- `organization` → Firma oder Organisation
- `person` → gemeinsame reale Person im Datenmodell

Familienmitglied, Kind und Mitarbeiter sind keine duplizierten Personen,
sondern Rollen beziehungsweise Mitgliedschaften in einem Profil.


PERSISTENZ UNTER APPDATA
------------------------

Alle programmbezogenen Daten liegen standardmäßig unter `%APPDATA%\Sorterino`:

%APPDATA%\Sorterino\
  settings.json
  oauth_clients.json
  sorterino.db
  profiles\
    <profil-id>\
      profile.json
      rules.override.json
      structure.override.json
      persons\<person-id>\...
  persons\
    <person-id>\
      person.json
      rules.override.json
      structure.override.json
  presets\
    family\rules.json + structure.json
    person\rules.json + structure.json
    child\rules.json + structure.json
    organization\rules.json + structure.json
  runtime\
    manual\
    errors\
    logs\
    state\
    legacy-backup\

`profiles/registry.json` enthält den schlanken Index. Profilpostfächer werden ohne
Geheimnisse in der jeweiligen `profile.json` gespeichert. App-Passwörter,
OAuth-Refresh-Tokens und das optionale Google-Client-Secret liegen über
`keyring` im Windows-Anmeldeinformationsspeicher. OAuth-Access-Tokens werden nur
im Arbeitsspeicher gehalten. `oauth_clients.json` enthält ausschließlich die
nicht persönlichen Client-IDs der selbst registrierten Desktop-Anwendungen.

Endgültige Dokumentarchive liegen am globalen Dokumentenspeicher oder am
individuellen `routing.storage_root` eines Profils. AppData-Verarbeitung und
Dokumentenarchiv sind damit bewusst getrennt.

`sorterino.db` enthält ausschließlich technische Dokumenthistorie: SHA-256,
Dateigröße, Originalname, Status, bekannte Ablage-/Backuporte,
Profil-/Personenzuordnung, ausgewählte Metadaten und Verarbeitungsereignisse.
OCR-Volltexte und Dokumentbytes werden nicht persistiert. Das Schema wird in
`schema_migrations` versioniert; Schreiboperationen laufen transaktional und
verwenden Fremdschlüssel. Der alte `runtime/state/duplicate-index.json` wird
einmalig und idempotent importiert.

`Config.incoming_root` ist eine globale Quelle für alle Profile. Ohne explizite
Abweichung zeigt sie auf `<user_path>\Sorterino - Eingang`. Die Werte
`incoming_path` und `incoming_path_custom` unterscheiden den automatisch
mitwandernden Standard vom bewusst gewählten Eingang. Vor der Ersteinrichtung
dient `runtime\incoming` nur als migrationssicherer Fallback.


LEGACY-MIGRATION
----------------

`Config` kann alte Daten aus `%USERPROFILE%\.sorterino_config.json` sowie aus
`<alter user_path>\Sorterino - Runtime` erkennen. Die Migration kopiert Daten
nicht-destruktiv in AppData, teilt Profile und Personen auf und setzt erst nach
erfolgreicher Übernahme einen Marker. Alte Profildaten bleiben zusätzlich als
`legacy.profiles.json` erhalten; alte Laufzeitdaten landen bei Bedarf unter
`runtime\legacy-backup`.


PROFIL- UND PERSONENMODELL
-------------------------

Hauptprofile:

- Privatperson (`individual`)
- Familie (`family`)
- Organisation (`organization`)

Eine Person besitzt Stammdaten, Kontaktangaben, Identifikatoren, Erkennungswerte
und Routingdaten. Mitgliedschaften verbinden Personen mit Familie oder
Organisation und speichern Kontextdaten wie Rolle, Position oder Abteilung.
Ein Kind ist eine Person mit `is_minor = true` und erhält im Familienkontext die
Kindvorlage.

Eine Person kann mehreren Profilen angehören. Deshalb darf UI-Code Personen
nicht für jede Mitgliedschaft neu anlegen, wenn vorhandene Personendaten
zugeordnet werden können.

Organisationen können unter `management.managing_director` Vorname, zweiten
Vornamen und Nachnamen der Geschäftsführung direkt speichern. Diese reine
Firmenangabe erzeugt absichtlich keine `person` und keine Mitgliedschaft. Die
sichtbaren Firmenkennungen sind auf Register­nummer, Steuernummer,
Umsatzsteuer-ID, Betriebsnummer und IBAN beschränkt; ältere zusätzliche Werte
bleiben beim Bearbeiten bestehender Profile unangetastet.


REGEL- UND STRUKTURVERERBUNG
----------------------------

`PolicyResolver` führt JSON-Daten in dieser Reihenfolge zusammen:

1. Preset des wirksamen Typs
2. Profil-Override
3. Personen-Override
4. Override der Person innerhalb dieses Profils

Die Typauswahl berücksichtigt Privatperson, Familie, Kind und Organisation.
Spätere Ebenen überschreiben gleichnamige Werte früherer Ebenen, ohne die
übrige Vorlage zu verlieren.


PIPELINE
--------

Der wesentliche Ablauf:

1. `Config` laden und AppData-Workspace sicherstellen
2. Profile und profilbezogene Mailkonten laden
3. aktivierte IMAP-Konten über App-Passwort oder erneuertes OAuth-Access-Token abrufen
4. Dateien aus `Config.incoming_root` erfassen und SHA-256 berechnen
5. bytegleiche Dateien desselben Laufs gruppieren; den aussagekräftigsten
   Dateinamen deterministisch als Hauptdatei auswählen
6. dauerhafte frühere Duplikate über `DocumentRegistry` prüfen
7. direkte Textextraktion oder OCR passend zum Dateiformat ausführen
8. Profil und Personen mit `ProfileMatcher` bewerten
9. Dokumenttyp und Metadaten analysieren
10. wirksame Regeln und Struktur mit `PolicyResolver` bestimmen
11. eindeutigen Zielpfad und Dateinamen erzeugen
12. erfolgreiche Datei im Profilspeicher ablegen und zentral sichern
13. unsichere Fälle und Duplikatkopien nach `runtime\manual` verschieben
14. technische Fehler nach `runtime\errors` verschieben
15. Datenbank, Logs und Ereignisbericht aktualisieren

`request_pipeline_stop()` setzt ein thread-sicheres Ereignis. Die Pipeline
prüft es vor und nach teuren beziehungsweise zustandsändernden Phasen. Ein
laufender OCR-Aufruf wird nicht gewaltsam beendet; anschließend bleibt die
Quelldatei im Eingang. Nach einem bereits abgeschlossenen Archiv-Move erfolgt
keine Rückkopie. Dies verhindert beschädigte Dateien und künstliche Duplikate.

E-Mail-Herkunft ist ein Profilhinweis, keine blinde Festlegung. Widerspricht der
Inhalt deutlich dem erwarteten Profil, wird manuelle Prüfung bevorzugt.
`MailImportState` speichert pro Konto `UIDVALIDITY`, den letzten lückenlos
verarbeiteten UID-Cursor und begrenzte Nachrichten-/Anhangsfingerprints unter
`runtime/state/mail_import_state.json`. Der Abruf verwendet bewusst weder
`UNSEEN` noch Mail-Flags. Anhänge werden flach im Eingang abgelegt; die interne
Datei-zu-Profil-Zuordnung bleibt in der Zustandsdatei und wird nach dem
Verschieben bereinigt. Alte technische Profil-/Postfachordner werden migriert.

DOCX/DOCM und ODT werden direkt aus ihren XML-Containern gelesen; eingebettete
Scans erhalten bei wenig Dokumenttext einen OCR-Fallback. TXT unterstützt BOM,
UTF-8, UTF-16 und Windows-1252, RTF wird ohne aktive Inhalte gelesen. EML und
MSG liefern Kopfzeilen, Nachrichtentext, Anhangsnamen und begrenzt den Text
unterstützter Anhänge. Pages verwendet ausschließlich eine enthaltene PDF- oder
Bildvorschau. Alte DOC-Dateien werden nur über LibreOffice im Headless-/Safe-
Mode temporär in DOCX konvertiert. Originale werden nie verändert und Makros
nie ausgeführt.


MANUELLE PRÜFUNG
----------------

`ManualFilingService` bietet nur Ziele aus der aufgelösten Struktur an und
prüft das gewählte Ziel erneut vor dem Verschieben. Bei Familien kann zwischen
„Gemeinsame Dokumente“ und einer konkreten Person unterschieden werden.

Manual bedeutet fachlich unsicher oder unvollständig. Error bedeutet ein
technisches Problem. Diese Zustände dürfen nicht zusammengelegt werden.

Die Dokumentliste bietet je Prüffall „Prüfen“ und einen Papierkorb sowie eine
Sammelaktion „Alle verwerfen“. Jede Löschung wird auf `config.manual_root`
begrenzt, bestätigt und als `discarded` im Dokumentregister erfasst. Zugehörige
JSON-Vorschläge unter `runtime/state/manual-review` werden mit entfernt.


DOKUMENTREGISTER UND DUPLIKATE
------------------------------

`DocumentRegistry` ist die fachliche Schnittstelle zu `SorterinoDatabase`.
Ein SHA-256-Treffer bleibt historisch erhalten, auch wenn Backup und Archiv
später fehlen. Die UI unterscheidet:

- bytegleich und an einem bekannten Ort vorhanden
- früher verarbeitet, aktuell nicht mehr auffindbar
- bytegleiche Kopie aus demselben Import

Nur exakte Bytegleichheit gilt als Duplikat. Ähnliche Bilder oder neu erzeugte
PDFs mit verändertem Container benötigen künftig eine separate inhaltliche
Ähnlichkeitserkennung. Der erweiterte Einstellungsbereich bietet SQLite-
Integritätsprüfung, gezieltes Scannen eines Ordners sowie einen zweifach
bestätigten Reset ausschließlich der technischen Dokumenthistorie.


KENNUNGEN
---------

`identifier_formats.py` normalisiert und validiert unter anderem:

- deutsche Steueridentifikationsnummer
- Steuernummer
- Krankenversichertennummer
- Renten-/Sozialversicherungsnummer
- Kindergeldnummer
- IBAN

Persistiert wird die normalisierte Form. Ungültige Prüfziffern oder Formate
führen zu einer verständlichen Validierungsmeldung. Kennungen bleiben bei der
Eingabe sichtbar; nur echte Zugangsdaten wie App-Passwörter werden verdeckt.


SICHERES LÖSCHEN
----------------

Konfigurationslöschung und Dateilöschung sind getrennte Aktionen:

- Mitgliedschaft entfernen: nur Relation löschen
- Person löschen: Person, Mitgliedschaften und Privatpersonenprofil entfernen
- Profil löschen: Profil, Overrides und zugehörige E-Mail-Konfiguration löschen
- optionale Dateilöschung: ausschließlich zuvor aufgelistete Archivunterordner

Beim Löschen einer Organisation wird für deren Mitarbeiter eine Strategie
gewählt: als Privatpersonen fördern, vollständig löschen oder pro Person
entscheiden. Vollständige Personenlöschung entfernt bewusst auch andere
Mitgliedschaften; der Bestätigungsdialog nennt diese Auswirkung. Verwaiste
Personen aus älteren Ständen werden beim Öffnen der Profilverwaltung über
`promote_unassigned_persons()` als Privatpersonenprofile wieder sichtbar.

Konfigurationslöschung benötigt exakt `Yeah!`; Dateilöschung zusätzlich exakt
`DATEIEN LÖSCHEN`. Der Speicherwurzelordner selbst ist als Ziel ausgeschlossen.
Pfade müssen aufgelöst unterhalb des Profilspeichers liegen. Gemeinsam genutzte
oder mehrdeutige Ordner werden nicht gelöscht. Bereits archivierte Dokumente
bleiben bei reiner Konfigurationslöschung erhalten.


KONTEXTBEZOGENE HILFE
---------------------

`HelpWindow` enthält Hilfetexte je Arbeitsbereich und führt offensichtliche,
nicht-invasive Diagnosen aus, darunter:

- AppData erreichbar und beschreibbar
- Presets vorhanden
- Dokumentenspeicher erreichbar
- Profile valide
- Profilpfade erreichbar
- Tesseract und Poppler verfügbar
- JSON-Dateien lesbar

Ohne Befund zeigt sie exakt „Sorterino ist einsatzbereit“. Sensible Werte werden
nicht ausgegeben.


TEMPLATES
---------

Unter `assets/templates` liegen ausschließlich aktuell verwendete Vorlagen:

- `template.config.json`
- `template.profiles.json`
- `template.person.json`
- `template.individual.json`
- `template.family.json`
- `template.organization.json`
- `template.membership.json`
- `template.email_account.json`
- `template.oauth_clients.json`
- `template.rules.json`
- `template.structure.json`

Beim ersten Start werden Regeln und Strukturen als vier Presets nach AppData
kopiert. Änderungen an Assets wirken nicht rückwirkend auf bereits angelegte
AppData-Presets.


TESTS UND QUALITÄT
------------------

Die Tests unter `tests` decken aktuell über 220 Fälle ab, insbesondere:

- AppData-Struktur und Legacy-Migration
- Profil- und Personenservice
- Mehrfachmitgliedschaften
- profilbezogenen E-Mail-Import, OAuth-Downgrade-Schutz und Provider-Pinning
- Profil- und Personenabgleich
- Policy-Vererbung
- manuelle Ablage
- Identifier-Normalisierung
- kontextbezogene Hilfe
- direkte Extraktion aus Word, ODT, RTF, TXT, EML und MSG
- Pages-Vorschauen sowie mehrseitige TIFF- und HEIC-Verarbeitung
- geschützte Dokumente, fehlende Vorschauen und Office-Sperrdateien
- sichere Konfigurationslöschung und Erhalt von Dokumentarchiven
- direkte Profilnavigation und Rückkehr aus verschachtelten Anlageabläufen
- widerspruchsfreie Warntexte für Zuordnungs-, Konfigurations- und Dateilöschung
- SQLite-Schema, Legacy-Import, dauerhafte Hashhistorie und Integritätsprüfung
- Duplikate innerhalb eines Imports sowie den kooperativen Verarbeitungsstopp

Vor Übergabe oder Build ausführen:

python -m compileall -q main.py src tests
python -m unittest discover -s tests -v
git diff --check


BUILD UND RELEASE
-----------------

PyInstaller:

pyinstaller Sorterino.spec --noconfirm

Inno Setup:

iscc installer.iss

Ergebnisse:

- `dist\Sorterino\`
- `installer\Sorterino_Setup_v2.0beta.exe`

Buildverzeichnisse, lokale Third-Party-Binaries, AppData, echte Dokumente und
Installer-EXEs sind keine Source-Dateien. Release-Artefakte gehören in einen
Release-Download.


BEKANNTE GRENZEN
----------------

- Die Standardregeln sind konservativ gewichtet und werden über versionierte
  Presets erweitert. Eigene Regeln bleiben bei Preset-Aktualisierungen erhalten.
- Sorterino ist kein revisionssicheres DMS.
- Regeln und Strukturen werden im erweiterten Bereich noch direkt als JSON
  bearbeitet.
- Die Duplikaterkennung ist absichtlich bytegenau; semantisch gleiche Dateien
  mit unterschiedlichen Bytes werden nicht zusammengeführt.
- Mitarbeiter verwenden derzeit grundsätzlich den Firmenkontext; ein
  persönlicher Firmen-Unterordner wird nur gelöscht, wenn er eindeutig als
  persönlicher Ordner aufgelöst werden kann.
- Tesseract und Poppler müssen im Entwickler-Checkout separat bereitstehen.


GIT-HYGIENE
-----------

Nicht versionieren:

- `.venv`, IDE-Daten und Python-Caches
- `build`, `dist` und Installer-Binärdateien
- lokale Tesseract-/Poppler-Binärdateien
- `%APPDATA%\Sorterino`
- Logs, echte Profile, Zugangsdaten und Nutzerdokumente

Die maßgeblichen Prüf-, Build- und Releasebefehle stehen in den Abschnitten
„Start und Setup“, „Tests und Qualität“ sowie „Build und Release“ dieser Datei.
Eine kompakte Befehlsübersicht bietet zusätzlich `docs/commands.md`.
