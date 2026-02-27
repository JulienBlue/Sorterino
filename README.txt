# Sorterino v0.3.0

Automatisierte OCR-Dokumenten-Engine mit strukturierter Ablage, intelligenter Rollen-Erkennung, modularer Architektur und optionalem MailDrop-Workflow.

---

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.10+
- pip
- Windows (für automatische Junction-Erstellung)
- Tesseract und Poppler sind im Ordner `third_party/` enthalten und werden automatisch eingebunden.
- Optional für MailDrop: Microsoft Outlook (Classic)

---

## 1️⃣ Konfiguration

Öffne:

`config.json`

Setze dein Arbeitsverzeichnis:

```json
"user_path": "C:\\Users\\DEINNAME\\Dokumente"
```

Sorterino erstellt dort automatisch eine interne Runtime-Struktur.

---

## 2️⃣ Virtuelle Umgebung

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3️⃣ Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 4️⃣ Start

```bash
python main.py
```

---

## 📂 Arbeitsweise

Beim ersten Start wird im Arbeitsverzeichnis erzeugt:

```
.sorterino_runtime/
    incoming/
    processed/
    manual_sort/
    error/
    logs/
    temp/
```

Zusätzlich werden sichtbare Verknüpfungen erstellt:

- Sorterino - Input
- Sorterino - Manuelle Sortierung

---

## 🔄 Verarbeitungsablauf

Sorterino führt folgende Schritte automatisch aus:

- OCR (PDF und Bildformate)
- Textanalyse und Rollen-Erkennung (Eingang / Ausgang)
- Metadaten-Extraktion
  - Rechnungsnummer
  - Rechnungsdatum
  - Betrag
  - Geschäftspartner
- Regelbasierte Klassifikation
- Kontextbasierte Dateibenennung
- Strukturierte Archivierung
- Duplikatschutz bei Dateinamen
- Tagesbasiertes Logging

Unklare Dokumente werden automatisch verschoben nach:

**Sorterino - Manuelle Sortierung**

---

## 📧 MailDrop (ab v0.3.0 – optional)

Sorterino kann E-Mail-Anhänge automatisch verarbeiten. Die E-Mail-Integration erfolgt bewusst nicht über eine API, sondern über eine clientseitige, digital signierte Outlook-VBA-Komponente.

### Funktionsweise

Outlook speichert bei Eingang einer E-Mail mit Anlage die Anhänge automatisch in:

```
.sorterino_runtime/incoming
```

Sorterino verarbeitet diese Dateien wie regulär abgelegte Dokumente.

---

## 🔐 Sicherheitskonzept

- Keine globale Makrofreigabe erforderlich
- Nur digital signierte Makros werden ausgeführt
- Keine IMAP-Anbindung
- Keine Microsoft Graph API
- Keine Cloud-Abhängigkeit
- Klare Systemtrennung zwischen Outlook und Sorterino

---

## 📦 Bereitgestellte Dateien (docs/maildrop)

- `sorterino_maildrop.bas`
- `sorterino_maildrop_certificate.cer`

---

## 🧑‍💼 Einrichtung für Nutzer (z. B. Tanja)

1️⃣ **Zertifikat installieren**
   - `.cer` Datei öffnen
   - In „Vertrauenswürdige Herausgeber“ installieren

2️⃣ **Makroeinstellung prüfen**
   - Outlook → Trust Center → Makroeinstellungen
   - Nur digital signierte Makros, alle anderen deaktivieren

3️⃣ **VBA-Code importieren**
   - Alt + F11
   - Datei importieren: `sorterino_maildrop.bas`
   - Digitale Signatur auswählen
   - Speichern
   - Outlook neu starten

---

## 🧠 Architektur

- Projektstruktur nach Clean-Architecture-Prinzip:
  - Domain
  - Usecases
  - Infrastructure
  - Interfaces
- MailDrop ist eine optionale, externe Erweiterung und kein Bestandteil der Kernlogik.
- Konfiguration erfolgt vollständig über JSON:
  - `config.json`
  - `rules.json`
  - `structure.json`
  - `supported_formats.json`

---

## 📄 Logging

Logs werden automatisch erzeugt unter:

```
.sorterino_runtime/logs/
```

Dateiname:

```
sorterino_logs_YYYY-MM-DD.log
```

---

## 📦 Release v0.3.0

Erweiterung um optionalen MailDrop-Workflow:

- Clientseitige Ereignisautomatisierung via Outlook VBA
- Digitale Signierung der Makro-Komponente
- Keine API-Integration
- Keine Systemkopplung
- Saubere Sicherheitsarchitektur
- Beibehaltung der Clean Architecture

---

## 🎯 Status

**Release v0.3.0 – MailDrop Extension**

Erweitert den stabilen Clean-Baseline-Stand um eine optionale, sicher signierte Client-Automatisierung zur E-Mail-Anlagenverarbeitung.
