SORTERINO v1.0
Automatische Dokumentenablage für Eingangs- und Ausgangsrechnungen

---

WAS IST SORTERINO?

Sorterino ist ein lokales Windows-Tool zur automatischen Rechnungsverarbeitung.

Du legst Dokumente in den Input-Ordner oder lässt Anhänge per IMAP abrufen. Sorterino liest die Dateien per OCR aus, unterscheidet Eingangs- und Ausgangsrechnungen und legt sie passend ab.

Alles läuft lokal. Keine Cloud. Keine externe Datenverarbeitung.

---

WAS SORTERINO IN VERSION 1.0 KANN

* Eingangsrechnungen erkennen
* Ausgangsrechnungen erkennen
* Datum, Betrag, Rechnungsnummer und Firma/Kunde extrahieren
* Dateien automatisch passend benennen
* unklare Fälle in die manuelle Sortierung legen
* Logs und Daily Reports schreiben

Wenn die Sortierung in Einzelfällen nicht passt, melde dich bei mir. Dann passe ich dir die Rules oder die Structure an, ohne dass der Code geändert werden muss.

---

SCHNELLSTART

1. `Sorterino.exe` starten
2. Speicherort auswählen
3. Firmendaten in den Einstellungen vollständig eintragen
4. Einstellungen speichern
5. Dateien in `Sorterino - Input` legen oder IMAP aktivieren

Beim ersten Start erstellt Sorterino automatisch:

* `Sorterino - Runtime`
* `Sorterino - Input`
* `Sorterino - Manuelle Sortierung`

---

WICHTIGE EINSTELLUNGEN

Diese Angaben müssen sauber gepflegt sein:

* Speicherort
* Firmenname
* Ansprechpartner
* Adresse
* E-Mail
* Telefon
* IBAN
* Steuer-ID

Diese Angaben kannst du zusätzlich nutzen:

* Automatikmodus
* Autostart
* IMAP-Abruf
* Daily-Report-Zeit

---

ORDNER

`Sorterino - Runtime`
interner Arbeitsbereich

`Sorterino - Input`
Eingang für neue Dateien

`Sorterino - Manuelle Sortierung`
Ablage für unklare oder unvollständige Fälle

`Sorterino - Runtime\configs`
`config.json`, `rules.json`, `structure.json`

`Sorterino - Runtime\logs`
Logs und Daily Reports

`Sorterino - Runtime\backup`
Sicherung der Originaldateien

`Sorterino - Runtime\error`
Dateien mit technischen Fehlern

---

UNTERSTÜTZTE DATEIEN

* PDF
* PNG
* JPG
* JPEG

---

BENENNUNG

Eingangsrechnungen:
`TT.MM.JJJJ - Lieferant - Betrag.pdf`

Ausgangsrechnungen:
`Rechnung <Nummer> vom <Datum> <Kunde>.pdf`

Wenn wichtige Informationen fehlen, wird nicht unsauber geraten. Solche Dateien landen in `Sorterino - Manuelle Sortierung`.

---

E-MAIL

Die E-Mail-Integration arbeitet per IMAP.

Wenn aktiviert:

* werden ungelesene Mails geprüft
* werden nur Anhänge übernommen
* werden die Anhänge lokal in den Input überführt

---

LOGS UND DAILY REPORT

Sorterino protokolliert:

* Verarbeitung
* Klassifikation
* Fehler
* Zielpfade

Zusätzlich gibt es Daily Reports als TXT und JSON im Log-Ordner.

---

HINWEIS

Sorterino 1.0 ist bewusst auf die produktive Nutzung für Rechnungen reduziert. Weitere Dokumenttypen können später wieder ergänzt werden, aktuell ist der Fokus aber eine stabile und nachvollziehbare Rechnungsverarbeitung.

---

DATENSCHUTZ

100 % lokal
keine Cloud
keine externen Server

---

AUTOR

Julien Blue Hirte
Seraph IT GmbH
