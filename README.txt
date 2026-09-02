SORTERINO
=========

Lokale, profilbezogene Dokumentensortierung für Windows


WAS IST SORTERINO?
------------------

Sorterino übernimmt Dokumente aus einem lokalen Eingangsordner oder aus
profilbezogenen E-Mail-Postfächern, liest sie per Textextraktion oder OCR aus
und legt sie anhand von Regeln im passenden privaten, familiären oder
geschäftlichen Kontext ab.

Die Verarbeitung findet lokal statt. Dokumente werden nicht an einen
Cloud-Dienst übertragen. Wenn Profil, Person oder Ablageziel nicht eindeutig
erkannt werden, entscheidet Sorterino nicht auf Verdacht: Das Dokument landet
unter „Zu prüfen“ und kann anschließend manuell zugeordnet werden.


PROFILE
-------

Sorterino unterstützt drei Hauptprofile:

- Privatperson
- Familie oder Haushalt
- Firma oder Organisation

Familien können Familienmitglieder und Kinder enthalten. Firmen können
Mitarbeiter enthalten. Intern wird jede reale Person nur einmal gespeichert.
Dadurch kann dieselbe Person beispielsweise zugleich Familienmitglied,
Privatperson und Mitarbeiter einer Firma sein.

Der Name der Geschäftsführung kann alternativ direkt als Firmenkontakt
gespeichert werden. Dafür ist kein eigenes Personen- oder Mitarbeiterprofil
notwendig.

Jedes Hauptprofil kann einen eigenen Dokumentenspeicher, eigene E-Mail-Konten,
eigene Sortierregeln und eine eigene Ablagestruktur verwenden. Ein gemeinsamer
Standard-Speicherort ist möglich, aber nicht verpflichtend.


FUNKTIONEN
----------

- PDF, Word (`.docx`, `.docm`, `.doc`), ODT, RTF und TXT lokal verarbeiten
- Pages-Dateien über ihre eingebettete PDF- oder Bildvorschau auswerten
- gespeicherte E-Mails (`.eml`, `.msg`) samt Kopfzeilen, Text und unterstützten Anhängen lesen
- PNG, JPG, JPEG, TIFF, WebP, HEIC und HEIF per OCR verarbeiten
- OCR mit Tesseract und PDF-Konvertierung mit Poppler
- Dokumente einem Profil und gegebenenfalls einer Person zuordnen
- Eingangs- und Ausgangsrechnungen regelbasiert klassifizieren
- Einkommens- und Verdienstbescheinigungen unter Arbeit und Karriere erkennen
- Datum, Betrag, Rechnungsnummer und Absender beziehungsweise Empfänger lesen
- unter anderem Arbeits-, Steuer-, Bank-, Versicherungs-, Gesundheits-, Wohn-,
  Vertrags-, Identitäts-, Kinder- und Fahrzeugdokumente erkennen
- Auftragseingangsbestätigungen für Strom- und Gasbelieferung von Rechnungen unterscheiden und unter den Energieverträgen ablegen
- profil- und personenspezifische Regeln und Strukturen vererben
- unsichere Dokumente kontrolliert manuell ablegen
- einzelne Dokumente nacheinander verarbeiten und weitere Klicks sichtbar in einer Warteschlange sammeln
- laufende Verarbeitung am nächsten sicheren Kontrollpunkt stoppen; die aktuelle Datei und noch wartende Dateien bleiben dabei im Eingang
- bytegleiche Dokumente unabhängig vom Dateinamen per SHA-256 erkennen
- bytegleiche Dateien desselben Imports gruppieren und nur die Variante mit dem aussagekräftigsten Namen analysieren
- bei der manuellen Ablage zwischen Sorterinos Namensvorschlag, einem eigenen Namen und dem unveränderten Originalnamen wählen
- Rechnungen im privaten oder familiären Kontext bewusst als privat oder geschäftlich bestätigen; private Steuerbelege werden separat nach Steuerjahr abgelegt
- technische Fehler getrennt behandeln
- einzelne oder alle Dokumente aus „Zu prüfen“ nach Bestätigung verwerfen
- mehrere IMAP-Postfächer je Profil verwenden
- E-Mail-Passwörter im Windows-Anmeldeinformationsspeicher ablegen
- Hell, Dunkel oder „Wie System“ als Darstellung wählen
- kontextbezogene Hilfe mit Diagnose und konkreten Handlungsempfehlungen
- Profile, Zuordnungen und Personen mit mehrstufiger Bestätigung entfernen
- als Tray-Anwendung im Hintergrund weiterlaufen und über das Windows-Infobereichssymbol bedient werden


SCHNELLSTART – INSTALLIERTE VERSION
----------------------------------

1. `Sorterino_Setup_v2.0beta.exe` starten und die Installation abschließen.
2. Sorterino öffnen.
3. Im Willkommensdialog „Standardspeicherort auswählen“ anklicken und den
   gewünschten Ordner im Explorer wählen.
4. Unter „Profile“ eine Privatperson, Familie oder Firma anlegen.
5. Profil bearbeiten und bei Bedarf einen eigenen Speicherort auswählen.
6. Familienmitglieder, Kinder oder Mitarbeiter ergänzen.
7. Dokumente über „Dokumente hinzufügen“ in den gemeinsamen Eingang übernehmen.
8. Auf der Übersicht „Jetzt verarbeiten“ wählen.

Die installierte Version bringt Tesseract und Poppler mit. Fehlt eine wichtige
Voraussetzung oder Konfiguration, zeigt die Hilfe passend zum geöffneten
Bereich, was zu tun ist. Ist alles in Ordnung, steht dort:

Sorterino ist einsatzbereit


OBERFLÄCHE
----------

Alle Arbeitsbereiche befinden sich im Hauptfenster. Das Menü bleibt links
sichtbar; Vor und Zurück befinden sich oben links. Nur die Hilfe öffnet sich in
einem eigenen Fenster.

- Übersicht: Zustand prüfen und Verarbeitung starten
- Dokumente: Eingang, manuelle Prüfung und technische Fehler
- Profile: Privatpersonen, Familien, Firmen und zugehörige Personen
- Einstellungen: globale Programmeinstellungen und Dokumentenquellen
- Erweiterte Einstellungen: Regeln und Strukturen als JSON bearbeiten
- Dokumentregister: SQLite-Integrität prüfen, bekannte Ordner erfassen oder ausschließlich die technische Historie zurücksetzen
- Logs: Verarbeitung nachvollziehen
- Hilfe: Hinweise und Diagnose zum aktuell geöffneten Bereich

Nach dem Speichern profilbezogener Angaben kehrt Sorterino zur Profilübersicht
zurück, öffnet das betroffene Profil und bestätigt den Vorgang fünf Sekunden
lang mit einem grün umrandeten Hinweis.

Beim Schließen über das Windows-X wird das Hauptfenster ausgeblendet, während
Sorterino im Infobereich weiterläuft. Ein einmaliger Hinweis erklärt dieses
Verhalten und kann dauerhaft ausgeblendet werden. Vollständig beendet wird die
Anwendung über „Beenden“ im Tray-Menü.


DOKUMENTENABLAUF
---------------

1. Lokale Dateien und aktivierte Profilpostfächer werden abgerufen.
2. SHA-256-Fingerprints erkennen frühere und innerhalb desselben Imports
   vorhandene bytegleiche Dokumente vor OCR und Klassifikation.
3. Sorterino bestimmt den erwarteten Profilkontext.
4. OCR und Textextraktion werden ausgeführt.
5. Profil, Person, Dokumenttyp und Metadaten werden bewertet.
6. Profil-, Personen- und Kontextregeln werden zusammengeführt.
7. Eindeutige Dokumente werden benannt, gesichert und archiviert.
8. Unsichere Fälle und Duplikatkopien landen unter „Zu prüfen“.
9. Technische Fehler landen unter „Fehler“.
10. Ergebnis, Zielpfade und technische Historie werden protokolliert.

Die Originaldatei und ihre Dateiendung bleiben bei jeder Verarbeitung erhalten.
Temporäre Vorschauen oder Konvertierungen dienen ausschließlich der lokalen
Analyse. Makros werden nicht ausgeführt. Eine Pages-Datei ohne Vorschau sowie
eine alte `.doc`-Datei ohne lokale LibreOffice-Installation landen unter
„Zu prüfen“, statt unsicher verarbeitet zu werden.

Während einer Verarbeitung erscheint oben rechts „Verarbeitung stoppen“.
Dieser kooperative Stopp wartet einen laufenden sicheren Lese- oder OCR-Schritt
ab und verhindert anschließend Klassifikation und Verschieben. Die aktuelle
Quelldatei und alle noch nicht begonnenen Dateien bleiben im Eingangsordner.
Bereits vollständig archivierte Dokumente werden nicht zurückkopiert.


SPEICHERORTE
------------

Konfiguration und lokale Verarbeitung liegen unter:

%APPDATA%\Sorterino\
  settings.json
  sorterino.db
  profiles\
  persons\
  presets\
  runtime\
    manual\
    errors\
    logs\
    state\
    legacy-backup\

Die endgültigen Dokumentarchive liegen nicht zwingend in AppData. Jedes Profil
kann entweder den Standard-Dokumentenspeicher oder einen eigenen Speicherort
verwenden. Dadurch können private Familienunterlagen und Firmendokumente auf
unterschiedlichen Laufwerken liegen.

Original-Backups liegen zentral unter
`<Standard-Dokumentenspeicher>\Sorterino - Backups\<Profilname>`. Die
Profilunterordner verhindern Vermischung, während alle Sicherungen an einer
gemeinsamen Stelle erreichbar bleiben.

Der Eingangsordner ist eine gemeinsame Quelle für alle Profile. Beim ersten
Einrichten entsteht im Standard-Dokumentenspeicher automatisch
`Sorterino - Eingang`. Danach kann unter „Einstellungen → Dokumentquellen“ ein
anderer globaler Eingangsordner gewählt werden. Ein individuell gewählter
Eingang bleibt beim Wechsel des Standard-Speicherorts unverändert.

Solange noch kein Standardspeicherort vorhanden ist, zeigt Sorterino beim
Öffnen einen kleinen Willkommensdialog. Erst dessen Schaltfläche öffnet die
Ordnerauswahl; ein Abbruch der Explorer-Auswahl lässt den Dialog geöffnet.

Alte Daten aus `.sorterino_config.json` und `Sorterino - Runtime` werden beim
ersten Start nicht zerstört, sondern in die neue Struktur kopiert und migriert.


LOKALES DOKUMENTREGISTER
-----------------------

`sorterino.db` ist eine lokale SQLite-Datenbank für die technische
Dokumenthistorie. Sie enthält SHA-256-Hashwerte, bekannte Ablage- und
Backuppfade, Zuordnungen, ausgewählte Metadaten und Verarbeitungsereignisse,
aber keine OCR-Volltexte oder Dokumentinhalte. Dadurch bleiben bytegleiche
Dokumente auch dann bekannt, wenn ein Backup später entfernt wurde.

Das Register unterscheidet deshalb zwischen einem noch auffindbaren
bytegleichen Dokument und einem Dokument, das bereits früher verarbeitet
wurde, dessen bekannter Speicherort aber nicht mehr existiert. Ähnliche oder
neu exportierte Dateien mit abweichenden Bytes gelten nicht als bytegleich.

Unter „Erweiterte Einstellungen → Dokumentregister verwalten“ kann die
Datenbank geprüft, kontrolliert aus einem ausgewählten Ordner ergänzt oder nur
die technische Dokumenthistorie zurückgesetzt werden. Dateien, Profile,
E-Mail-Verknüpfungen, Regeln und Strukturen werden dabei nicht gelöscht.
Auch der Mail-UID-Abrufstand wird bei diesem Reset bewusst nicht verändert.


REGELN UND STRUKTUREN
---------------------

Es gibt Standardvorlagen für:

- Familie
- Privatperson
- Kind
- Organisation

Die wirksame Konfiguration wird schrittweise zusammengesetzt:

Standardvorlage → Profilabweichung → Personenabweichung → Person im Profil

Eine Firma kann dadurch anders sortieren als eine Familie, ein Kind anders als
ein Erwachsener und dieselbe Person im Firmenkontext anders als privat.


E-MAIL-IMPORT
-------------

Es gibt kein globales E-Mail-Konto. Jedes IMAP-Postfach gehört genau zu einem
Profil. So erhalten beispielsweise Firmenrechnungen aus der Firmenadresse
bereits beim Import den passenden Kontext. Widerspricht der Dokumentinhalt
diesem Kontext, wird das Dokument zur manuellen Prüfung vorgelegt.

Google- und Microsoft-Postfächer werden ausschließlich per OAuth2 Authorization
Code mit PKCE im Standardbrowser verbunden. Sorterino erhält dabei kein
Kontopasswort. Apple/iCloud, GMX, WEB.DE, IONOS und benutzerdefinierte Anbieter
verwenden ein eigens erzeugtes App-Passwort. Google-Refresh-Tokens und
App-Passwörter liegen im Windows-Anmeldeinformationsspeicher; Microsofts
Tokenbestand ist benutzergebunden per Windows-DPAPI verschlüsselt. Es werden
keine OAuth-Client-Secrets ausgeliefert oder verwendet.

Bekannte OAuth-Anbieter sind fest an ihre offiziellen IMAP-Server und TLS-Port
993 gebunden. Eine manipulierte Konfiguration kann nicht unbemerkt auf
Passwortanmeldung oder einen fremden Server zurückfallen.

Der Abruf hängt nicht vom Gelesen-Status ab. Beim Verknüpfen kann gewählt
werden, ob vorhandene Mails ab jetzt oder rückwirkend für 7, 30, 90 oder 365
Tage geprüft werden. Danach merkt sich Sorterino je Postfach
die letzte vollständig geprüfte IMAP-UID. Deshalb werden auch Nachrichten
erfasst, die während eines ausgeschalteten PCs am Handy gelesen wurden. Der
Gelesen- und Stern-Status im Postfach wird nicht verändert. Mailanhänge liegen
mit normalen Dateinamen direkt im Eingangsordner; der Profilhinweis wird nur
intern unter AppData gespeichert.


KENNUNGEN UND PERSONENDATEN
---------------------------

Sorterino kann unter anderem Namen, zweiten Vornamen, Geburtsdatum, Anschrift,
E-Mail-Adressen, Steueridentifikationsnummer, Steuernummern,
Krankenversichertennummer, Rentenversicherungsnummer, Kindergeldnummer,
Schüler-/Matrikelnummern und IBANs zur Erkennung verwenden.

Kennungen werden beim Speichern normalisiert und, soweit eine verlässliche
Prüfung möglich ist, validiert. Pflichtfelder sind mit `*`, für eine bessere
Erkennung empfohlene Felder mit `***` gekennzeichnet.


SICHERES ENTFERNEN UND LÖSCHEN
------------------------------

Bei Familienmitgliedern, Kindern und Mitarbeitern kann entweder nur die
Zuordnung zum aktuellen Profil entfernt oder die Person vollständig aus
Sorterino gelöscht werden. Bei Hauptprofilen kann nur die Konfiguration oder
zusätzlich der eindeutig zugehörige Dateiordner gelöscht werden.

Beim Löschen einer Firma kann gewählt werden, ob alle Mitarbeiter als
Privatpersonen erhalten bleiben, alle vollständig gelöscht werden oder für jede
Person einzeln entschieden wird. Ohne vollständige Personenlöschung gehen keine
Mitarbeiterstammdaten verloren.

- Konfigurationslöschung erfordert die exakte Eingabe `Yeah!`.
- Dateilöschung zeigt vorher die vollständigen Pfade.
- Dateilöschung erfordert zusätzlich `DATEIEN LÖSCHEN`.
- Der gewählte Dokumentenspeicher selbst wird niemals gelöscht.
- Mehrdeutige oder gemeinsam verwendete Ordner bleiben erhalten.
- Ohne gewählte Dateilöschung bleiben alle archivierten Dokumente erhalten.
- „Verwerfen“ und der Papierkorb unter „Zu prüfen“ löschen ausschließlich die
  ausgewählte Prüffassung; „Alle verwerfen“ nennt vorher die genaue Anzahl.
- Verwerfentscheidungen werden im lokalen Dokumentregister protokolliert.


ENTWICKLUNG AUS DEM SOURCE-CHECKOUT
----------------------------------

Virtuelle Umgebung erstellen und aktivieren:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

GUI starten:

python -m src.gui.app

Nur einen Pipeline-Lauf starten:

python main.py

Für den Source-Checkout müssen Tesseract und Poppler installiert oder in diesen
stabilen Ordnern abgelegt sein:

- `third_party/tesseract/tesseract.exe`
- `third_party/poppler/Library/bin`

Weitere technische Informationen stehen in `README_DEV.txt`; eine kompakte
Befehlsübersicht für Tests, Build und Release in `docs/commands.md`.


GRENZEN
-------

Sorterino ist kein revisionssicheres Dokumentenmanagementsystem und ersetzt
weder steuerliche noch rechtliche Prüfung. Die Klassifikation ist bewusst
regelbasiert. Der manuelle Prüfbereich ist eine Sicherheitsfunktion und kein
Fehlerzustand.


LIZENZ
------

MIT License. Siehe `LICENSE`.
