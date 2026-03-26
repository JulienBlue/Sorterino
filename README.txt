# 📦 Sorterino v0.4.0

Desktop-Anwendung zur automatisierten Dokumentenanalyse und strukturierten Ablage.

Sorterino verarbeitet lokale Dokumente, extrahiert relevante Informationen mittels OCR und legt diese regelbasiert in einer definierten Ordnerstruktur ab.

---

# 🚀 Schnellstart

## Voraussetzungen

* Windows 10/11
* Keine zusätzliche Software notwendig (EXE enthält alle Abhängigkeiten)
* Optional: Microsoft Outlook (für MailDrop)

---

## 🖥 Anwendung starten

Nach Installation:

```text
Sorterino starten → Ordner auswählen → Workspace einrichten
```

---

# ⚙️ Funktionsweise

Beim ersten Start wird automatisch eine Runtime-Umgebung erstellt:

```
<USER_PATH>/.sorterino_runtime/
├── incoming/
├── processed/
├── manual_sort/
├── error/
├── logs/
```

👉 Alle benutzerspezifischen Daten werden ausschließlich dort gespeichert.

---

# 🔄 Verarbeitungsablauf

Sorterino führt folgende Schritte automatisch aus:

1. Dokument einlesen (lokaler Ordner oder MailDrop)
2. Backup erstellen
3. OCR (PDF & Bilder)
4. Textanalyse
5. Klassifikation (regelbasiert)
6. Metadatenextraktion:

   * Rechnungsnummer
   * Datum
   * Betrag
   * Geschäftspartner
7. Dateibenennung
8. Zielpfad-Ermittlung
9. Archivierung
10. Logging

---

# 🖥 GUI (ab v0.4.0)

Die Anwendung verfügt über eine grafische Benutzeroberfläche:

* Ordnerauswahl (Arbeitsverzeichnis)
* Workspace-Initialisierung
* Manuelles Starten der Pipeline
* Automatische Überwachung
* Windows-Autostart
* Live-Loganzeige
* Einstellungen (Config, Rules, Structure)

👉 Die GUI enthält keine Businesslogik und greift ausschließlich auf die Pipeline zu.

---

# ⚙️ Konfiguration

Die Konfiguration erfolgt vollständig über JSON-Dateien im Runtime-Ordner:

```
.sorterino_runtime/
├── config.json
├── rules.json
├── structure.json
├── supported_formats.json
```

👉 Diese können direkt über die GUI bearbeitet werden.

---

# 📧 MailDrop (optional)

Sorterino unterstützt optional eine E-Mail-Integration über Outlook VBA.

Funktionsweise:

* E-Mail-Anhänge werden lokal gespeichert
* Ziel: `.sorterino_runtime/incoming`
* Verarbeitung erfolgt automatisch durch die Pipeline

👉 Keine API, keine Cloud, keine Serverintegration

---

# 🔐 Sicherheitskonzept

* vollständiger Offline-Betrieb
* keine Cloud-Anbindung
* keine API-Zugriffe
* keine Datenübertragung nach außen
* Nutzung digital signierter Outlook-Makros (optional)

---

# 🧠 Architektur

Sorterino basiert auf einer Clean-Architecture:

* Domain (Modelle)
* Usecases (Businesslogik)
* Infrastructure (OCR, Filesystem, Config)
* Interfaces (Abstraktionen)
* GUI (Darstellungsschicht)

👉 Strikte Trennung von Logik und Oberfläche

---

# 🛠 Build & Deployment

Die Anwendung wird als strukturierte Verzeichnisanwendung bereitgestellt:

```
dist/Sorterino/
├── Sorterino.exe
├── _internal/
├── third_party/
```

👉 Gründe:

* bessere Performance beim Start
* höhere Stabilität
* transparente Abhängigkeiten (OCR, Poppler)

Ein Installer wird über Inno Setup erzeugt.

---

# 📄 Logging

Logs befinden sich unter:

```
.sorterino_runtime/logs/
```

Format:

```
sorterino_logs_YYYY-MM-DD.log
```

---

# 📊 Status

**Release v0.4.0**

* GUI vollständig integriert
* Runtime-Konzept umgesetzt
* Installer vorhanden
* OCR stabil
* Klassifikation funktional
* Konfiguration über GUI möglich

---

# 🎯 Ziel

Ziel der Anwendung ist die strukturierte und nachvollziehbare Automatisierung von Dokumentenprozessen im Unternehmen.

---

# 💡 Hinweis

Sorterino ist als funktionale Minimalversion konzipiert und bildet die Grundlage für zukünftige Erweiterungen.

---
