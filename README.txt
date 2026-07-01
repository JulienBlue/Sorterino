SORTERINO
=========

Lokale Dokumentenverarbeitung für Rechnungen


WAS IST SORTERINO?
------------------

Sorterino ist ein lokales Windows-Tool, das Rechnungen aus einem Input-Ordner
oder optional aus E-Mail-Anhängen übernimmt, per OCR ausliest und anschließend
regelbasiert ablegt.

Der aktuelle Stand konzentriert sich bewusst auf zwei Fälle:

- Eingangsrechnungen
- Ausgangsrechnungen

Das Projekt ist als praktisches Entwickler- und Bewerbungsprojekt gedacht. Es
soll nachvollziehbar zeigen, wie Dokumente lokal verarbeitet, geprüft,
klassifiziert und abgelegt werden können.

Alles läuft lokal. Sorterino nutzt keine Cloud und schickt keine Dokumente an
externe Dienste.


WAS SORTERINO NICHT MACHT
-------------------------

Sorterino ist kein vollständiges DMS, keine KI-Lösung und keine steuerliche
Rechnungsprüfung.

Wenn wichtige Daten fehlen oder die Einordnung nicht sicher genug ist, legt
Sorterino das Dokument nicht automatisch irgendwo ab. Solche Fälle landen in der
manuellen Sortierung. Das ist Absicht, damit keine falsche Ablage entsteht.


FUNKTIONEN
----------

- Dokumente aus einem lokalen Input-Ordner verarbeiten
- optional Anhänge per IMAP importieren
- Originaldateien sichern
- OCR mit Tesseract ausführen
- PDFs über Poppler und pdf2image vorbereiten
- Rechnungen regelbasiert einordnen
- Datum, Betrag, Rechnungsnummer und Lieferant/Kunde auslesen
- Dateinamen und Zielpfade erzeugen
- unsichere Fälle in die manuelle Sortierung legen
- technische Fehler in einen Error-Ordner verschieben
- Logs und Daily Reports schreiben


ABLAUF
------

1. Dokumente aus Input-Ordner oder Mailimport übernehmen
2. Backup erstellen
3. Dateiformat prüfen
4. OCR ausführen
5. Text analysieren
6. Dokument klassifizieren
7. Metadaten extrahieren
8. Pflichtdaten prüfen
9. Dateiname und Zielpfad erzeugen
10. Dokument ablegen oder nach Manual/Error verschieben
11. Verarbeitung protokollieren


SCHNELLSTART
------------

1. `Sorterino_Setup_vX.X.exe` ausführen
2. den Installationsdialog durchlaufen
3. Sorterino am Ende des Setups starten
4. Speicherort auswählen
5. Firmendaten in den Einstellungen eintragen
6. Einstellungen speichern
7. Dateien in `Sorterino - Input` legen oder IMAP aktivieren

Beim ersten Start legt Sorterino die benötigte lokale Arbeitsstruktur an. Dazu
gehören unter anderem `Sorterino - Runtime`, `Sorterino - Input` und
`Sorterino - Manuelle Sortierung`.

In der fertigen Windows-Version werden Tesseract und Poppler mitgeliefert. Man
muss sie also normalerweise nicht selbst installieren.

Nur für einen Entwickler-Checkout müssen Tesseract und Poppler separat
installiert oder lokal abgelegt werden:

- Tesseract OCR: `third_party/tesseract/tesseract.exe`
- Poppler: `third_party/poppler/Library/bin`

Wichtig: Die Ordner müssen genau `third_party/tesseract` und
`third_party/poppler` heißen. Keine Versionsnummern im Ordnernamen, sonst
passen die Standardpfade nicht mehr.

Für Windows ist der UB-Mannheim-Installer der einfachste Weg:

https://github.com/UB-Mannheim/tesseract/wiki

Bei der Installation unter `Language data` mit auswählen:

- English
- Orientation and script detection

Zusätzlich unter `Additional language data (download)` mit auswählen:

- German
- French

Danach sollten diese Dateien im Ordner `third_party/tesseract/tessdata/`
liegen:

- `deu.traineddata` für Deutsch
- `eng.traineddata` für Englisch
- `fra.traineddata` für Französisch
- `osd.traineddata` für Orientation/Script Detection

Download-Links stehen in `requirements.txt`.


WICHTIGE EINSTELLUNGEN
----------------------

Diese Angaben sollten gepflegt sein:

- Speicherort
- Firmenname
- Ansprechpartner
- Adresse
- E-Mail
- Telefon
- IBAN
- Steuer-ID

Optionale Einstellungen:

- Automatikmodus
- Autostart
- IMAP-Abruf
- Uhrzeit für den Daily Report


ORDNER
------

Typische Runtime-Struktur:

runtime/
  input/
  backup/
  manual/
  error/
  archive/
  logs/
  configs/

In der Windows-Oberfläche arbeitet Sorterino unter anderem mit:

- `Sorterino - Runtime`
- `Sorterino - Input`
- `Sorterino - Manuelle Sortierung`


UNTERSTÜTZTE DATEIEN
--------------------

- PDF
- PNG
- JPG
- JPEG


DATEINAMEN
----------

Beispiel Eingangsrechnung:

20.04.2026 - Demo Supplier GmbH - 185,40.pdf

Beispiel Ausgangsrechnung:

Rechnung 70015 vom 20.04.2026 Demo Customer GmbH.pdf

Wenn Pflichtdaten fehlen, wird nicht geraten. Das Dokument geht dann in die
manuelle Sortierung.


E-MAIL-IMPORT
-------------

Die E-Mail-Funktion arbeitet per IMAP.

Wenn sie aktiviert ist:

- werden ungelesene Mails geprüft
- werden nur Anhänge übernommen
- werden die Anhänge lokal in den Input verschoben


LOGS UND REPORTS
----------------

Sorterino protokolliert Verarbeitung, Klassifikation, Fehler und Zielpfade.
Zusätzlich werden Daily Reports als TXT und JSON geschrieben.


DATENSCHUTZ
-----------

Die Verarbeitung findet lokal statt. OCR, Klassifikation, Ablage, Logs und
Reports laufen auf dem eigenen System.


LIZENZ
------

MIT License. Siehe `LICENSE`.
