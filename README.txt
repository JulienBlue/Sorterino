# 📦 Sorterino v0.5.1

## 🧠 Überblick

Sorterino ist eine lokale Desktop-Anwendung zur automatisierten Verarbeitung von Dokumenten.

Ziel ist es, eingehende Dateien strukturiert zu analysieren, zu klassifizieren und automatisch in eine definierte Ordnerstruktur abzulegen.

Die Anwendung arbeitet vollständig lokal und folgt einem deterministischen, regelbasierten Ansatz.

---

## 🎯 Features

* 📥 Überwachung eines Input-Ordners
* 🔎 OCR-gestützte Textextraktion
* 🧠 Regelbasierte Klassifikation
* 🏷️ Automatische Umbenennung
* 📂 Strukturierte Ablage
* 📜 Logging & Fehlerhandling
* 🔁 Automatikmodus (Polling)
* 🧩 Konfigurierbares Firmenprofil (inkl. Keywords, Adresse etc.)

---

## 🏗️ Architektur

Sorterino folgt einer klaren Clean-Architecture-Struktur:

```
src/
├── domain/           → Modelle & Status
├── usecases/         → Geschäftslogik (Pipeline)
├── infrastructure/   → OCR, Filesystem, Config
├── gui/              → UI (Tray + Fenster)
└── utils/            → Hilfsfunktionen
```

Prinzipien:

* klare Trennung der Verantwortlichkeiten
* keine Abhängigkeiten zwischen falschen Layern
* austauschbare Infrastruktur

---

## 🔁 Verarbeitungspipeline

```
Input →
Validierung →
Backup →
Textextraktion →
Klassifikation →
Metadaten →
Umbenennung →
Pfadauflösung →
Ablage →
Logging
```

Fehler werden pro Dokument behandelt, ohne die Pipeline zu stoppen.

---

## 📁 Runtime-Konzept

Beim Initialisieren wird ein versteckter Runtime-Ordner erstellt:

```
<USER_PATH>/.sorterino_runtime/
├── incoming/
├── logs/
├── backup/
├── error/
├── manual_sort/
├── config.json
├── rules.json
├── structure.json
├── supported_formats.json
```

Zusätzlich werden sichtbare Verknüpfungen erstellt:

* `Sorterino - Input`
* `Sorterino - Manuelle Sortierung`

---

## ⚙️ Konfiguration

Die Anwendung ist vollständig konfigurationsgetrieben.

### config.json

Wird automatisch im Runtime-Ordner erstellt:

```json
{
  "user_path": "",
  "auto_mode": false,
  "autostart": false,
  "company_profile": {
    "name": "",
    "keywords": [],
    "address": {
      "street": "",
      "zip": "",
      "city": ""
    },
    "contact": {
      "email": "",
      "phone": ""
    },
    "financial": {
      "iban": "",
      "tax_id": ""
    }
  }
}
```

### rules.json

Definiert Klassifikationsregeln (keyword-basiert).

### structure.json

Definiert Zielordnerstruktur.

---

## 🖥️ GUI

Die Anwendung wird über ein Tray-Icon gesteuert:

* Start / Stop der Pipeline
* Logs anzeigen
* Einstellungen öffnen

Fenster:

* Konfiguration (inkl. Firmenprofil)
* Speicherort-Verwaltung
* Log-Anzeige

---

## 🚀 Installation (Dev)

```bash
pip install -r requirements-dev.txt
```

Start:

```bash
python -m src.gui.app
```

---

## 📦 Build

```bash
taskkill /f /im Sorterino.exe 2>nul
rmdir /s /q build
rmdir /s /q dist

pyinstaller build_tools/sorterino.spec --noconfirm
```

Installer (Inno Setup):

```bash
iscc build_tools/installer.iss
```

---

## ⚠️ Bekannte Einschränkungen

* OCR-Qualität abhängig von Dokumentqualität
* Klassifikation vollständig regelbasiert
* Konfigurationsfehler können zu falscher Ablage führen
* Keine Cloud / keine Datenbank

---

## 🧠 Designentscheidungen

* bewusst kein ML → nachvollziehbar & deterministisch
* keine externe Infrastruktur → lokal & datenschutzfreundlich
* JSON statt DB → einfache Anpassbarkeit
* klare Architektur → wartbar im IHK-Rahmen

---

## 🧪 Status

Version: **v0.5.1**

* Runtime-System stabil
* GUI funktionsfähig
* Automatikmodus aktiv
* Firmenprofil integriert

---

## 📌 Ziel

Fokus liegt auf:

* Stabilität
* Nachvollziehbarkeit
* einfacher Erweiterbarkeit

---

## 👨‍💻 Hinweis

Dieses Projekt ist Teil eines IHK-Abschlussprojekts und bewusst auf einen klaren, strukturierten Funktionsumfang begrenzt.

---
