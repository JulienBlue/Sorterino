# 🚀 Sorterino v0.7.0

## ✨ Überblick

Sorterino ist eine lokale Desktop-Anwendung zur automatisierten Verarbeitung von Dokumenten.

Das System arbeitet vollständig offline und verarbeitet Dateien nach folgendem Prinzip:

OCR → Klassifikation → strukturierte Ablage

Die gesamte Logik ist konfigurierbar und kommt ohne Cloud-Anbindung aus.

---

## 🧠 Funktionsweise

1. Dokumente werden aus dem Input-Ordner geladen
2. OCR extrahiert Textinhalte (Tesseract lokal)
3. Klassifikation erfolgt regelbasiert über Keywords
4. Dokumente werden automatisch strukturiert abgelegt

Nicht eindeutig zuordenbare Dokumente werden in den Bereich für manuelle Sortierung verschoben.

---

## ⚙️ Architektur

### 🔹 Pipeline

Die Verarbeitung erfolgt über eine entkoppelte Pipeline:

* DocumentPipeline
* DocumentAnalyzer
* TesseractOCR
* FilesystemStorage

Die Pipeline ist unabhängig von GUI und CLI nutzbar.

---

### 🔹 Datenmodell

Zentrale Objekte:

* Document
* DocumentStatus
* Classification
* DocumentMetadata

Status-Flow:

NEW → ANALYZED → CLASSIFIED → STORED
↘ ERROR

---

## 📝 Logging-Konzept

Sorterino verwendet bewusst ein zweigeteiltes Logging-System:

### 📄 Logfile

Wird persistent gespeichert und enthält:

* `logger.log()` → fachliche Ereignisse (Ein- und Ausgang von Dokumenten)
* `logger.error()` → Fehlerfälle

### 🖥 Konsole

Wird nur zur Laufzeit angezeigt und enthält:

* `logger.info()` → Ablauf-Informationen
* `logger.debug()` → technische Details
* `logger.warning()` → Hinweise

👉 Ziel dieses Ansatzes ist eine klare Trennung zwischen:

* **Business-relevanten Logs (persistent)**
* **technischen Laufzeitinformationen (nur während Ausführung sichtbar)**

---

## 📁 Runtime-Struktur

Beim ersten Start wird eine isolierte Laufzeitumgebung erstellt:

.sorterino_runtime/

* incoming/
* logs/
* error/
* manual_sort/
* processed/
* rules.json
* structure.json
* config.json

Zusätzlich werden Verknüpfungen im Benutzerordner erstellt:

* Sorterino - Input
* Sorterino - Manuelle Sortierung

---

## 🧾 Konfiguration

Die Anwendung ist vollständig über JSON-Dateien konfigurierbar:

* `rules.json` → Klassifikationsregeln
* `structure.json` → Zielordnerstruktur
* `config.json` → Systemkonfiguration

Ein globaler Basispfad wird zusätzlich in einer Benutzerkonfiguration gespeichert.

---

## 🖥 GUI Features

* Tray-Anwendung
* Einstellungsdialog
* JSON-Editor für Regeln und Struktur
* Log-Viewer
* Automatikmodus
* Autostart-Funktion

---

## 🔄 Betriebsmodi

### Manuell

Pipeline wird über die GUI gestartet

### Automatikmodus

Pipeline läuft in regelmäßigen Intervallen im Hintergrund

---

## ⚠️ Hinweise

* OCR-Ergebnisse sind abhängig von der Dokumentqualität
* Unterstützte Formate: PDF, PNG, JPG, JPEG
* Nicht erkannte Dokumente werden in `manual_sort` verschoben
* Fehlerhafte Dokumente werden in `error` abgelegt

---

## 🛠 Installation

### Virtuelle Umgebung erstellen

python -m venv .venv

### Aktivieren

.venv\Scripts\activate

### Abhängigkeiten installieren

pip install -r requirements.txt

---

## ▶️ Start

### Pipeline (CLI)

python main.py

### GUI

python -m src.gui.app

---

## 📦 Build

### EXE erstellen

pyinstaller Sorterino.spec --noconfirm

### Installer erstellen

iscc installer.iss

---

## 🧑‍💻 Kontext

IHK Abschlussprojekt – Fachinformatiker Anwendungsentwicklung
