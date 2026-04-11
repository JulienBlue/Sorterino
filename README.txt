SORTERINO v0.99
Automatische Dokumentenablage für Rechnungen, Verträge und mehr

---

WAS IST SORTERINO?

Sorterino ist ein lokales Tool zur automatischen Dokumentenverarbeitung.

Du legst Dateien in einen Ordner – Sorterino erkennt, analysiert und sortiert sie automatisch in eine strukturierte Ablage.

Keine Cloud. Keine Datenübertragung. Alles lokal.

---

SCHNELLSTART

1. Sorterino starten (Sorterino.exe)
2. Speicherort auswählen
3. Einstellungen prüfen
4. Fertig

Sorterino erstellt automatisch:

* Input-Ordner
* Runtime-Umgebung
* Struktur für Dokumente

---

WIE FUNKTIONIERT DAS?

Pipeline:

1. Datei wird erkannt
2. OCR (optional)
3. Textanalyse (Keywords)
4. Klassifikation
5. Ablage im Zielpfad

---

ORDNERSTRUKTUR

Sorterino - Input
→ Eingang für neue Dokumente

Sorterino - Manuelle Sortierung
→ nicht erkannte Dokumente

Sorterino - Runtime
→ interner Arbeitsbereich

Sorterino - Runtime\configs
→ Konfiguration (config, rules, structure)

Sorterino - Runtime\logs
→ Logs + Daily Reports

Sorterino - Runtime\backup
→ Backup der Originaldateien

Sorterino - Runtime\error
→ Dateien mit Fehlern (OCR/Processing)

---

DATEITYPEN

* PDF
* PNG
* JPG / JPEG

---

AUTOMATISCHE SORTIERUNG

Ablage erfolgt nach:

Kategorie → Dokumenttyp → Jahr → Monat

---

E-MAIL INTEGRATION

Einstellungen → "E-Mail Integration"

Features:

* IMAP Abruf
* nur ungelesene Mails
* nur Anhänge
* automatische Speicherung im Input

---

AUTOMATIKMODUS

* läuft im Hintergrund
* verarbeitet regelmäßig neue Dateien

Autostart:

* startet Sorterino automatisch mit Windows

---

LOGGING

* Logs über GUI einsehbar
* Trennung zwischen Datei-Log und Konsole
* Daily Report als TXT im Log-Ordner
* Daily Report JSON in logs\daily_reports

Daily Report Zeit:

* in den Einstellungen setzen
* letzter Report ist per Button erreichbar

---

WENN ETWAS NICHT ERKANNT WIRD

→ landet in "Manuelle Sortierung"

---

WAS DU EINSTELLEN KANNST

* Speicherort (Basis-Pfad)
* Automatikmodus
* Autostart
* Mail Integration (IMAP + Aktivierung)
* Daily Report Zeit
* Persönliche Daten (für Erkennung)
* Rules + Structure (nur über GUI)

---

* Wenn Sortierung nicht passt → melde dich bei mir, ich liefere neue Rules / Structure

---

VERSION 0.99

* Production Build (GUI-only, keine Konsole)
* Runtime Ordner sichtbar und sauber benannt
* Regeln + Extraktion aus rules.json
* Daily Report integriert

---

DATENSCHUTZ

100% lokal
keine Cloud
keine externen Server

---

AUTOR

Julien Blue Hirte
Seraph IT GmbH
