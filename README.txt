🧠 Sorterino v0.2.5

Automatisierte OCR-Dokumenten-Engine mit strukturierter Ablage, intelligenter Rollen-Erkennung und modularer Architektur.

🚀 Schnellstart
Voraussetzungen

Python 3.10+

pip

Windows (für automatische Junction-Erstellung)

Tesseract und Poppler sind im Ordner third_party/ enthalten und werden automatisch eingebunden.

1️⃣ Konfiguration

Öffne:

config.json

Setze dein Arbeitsverzeichnis:

"user_path": "C:\\Users\\DEINNAME\\Dokumente"

Sorterino erstellt dort automatisch eine interne Runtime-Struktur.

2️⃣ Virtuelle Umgebung
python -m venv .venv
.venv\Scripts\activate
3️⃣ Abhängigkeiten installieren
pip install -r requirements.txt
4️⃣ Start
python main.py
📂 Arbeitsweise

Beim ersten Start wird im Arbeitsverzeichnis erzeugt:

.sorterino_runtime/
    incoming/
    processed/
    manual_sort/
    error/
    logs/
    temp/

Zusätzlich werden sichtbare Verknüpfungen erstellt:

Sorterino - Input

Sorterino - Manuelle Sortierung

🔄 Verarbeitungsablauf

Sorterino führt folgende Schritte automatisch aus:

OCR (PDF & Bildformate)

Textanalyse & Rollen-Erkennung (Eingang / Ausgang)

Metadaten-Extraktion

Rechnungsnummer

Rechnungsdatum

Betrag

Geschäftspartner

Regelbasierte Klassifikation

Kontextbasierte Dateibenennung

Strukturierte Archivierung

Duplikatschutz bei Dateinamen

Tagesbasiertes Logging

Unklare Dokumente werden automatisch verschoben nach:

Sorterino - Manuelle Sortierung

🧠 Architektur

Projektstruktur nach Clean-Architecture-Prinzip:

Domain

Usecases

Infrastructure

Interfaces

Konfiguration erfolgt vollständig über JSON:

config.json

rules.json

structure.json

supported_formats.json

📄 Logging

Logs werden automatisch erzeugt unter:

.sorterino_runtime/logs/

Dateiname:

sorterino_logs_YYYY-MM-DD.log

📦 Release v0.2.5

Stabilisierungs- und Architektur-Release:

Runtime-Isolation (.sorterino_runtime)

Interface-basierte Services

Integriertes Logging-System

Rollen-Erkennung (Eingangs- / Ausgangsrechnung)

Kontextbasierte Dateibenennung

Duplikatschutz im Storage

Modular erweiterbare Pipeline

Struktur-Resolver für dynamische Ordnerpfade

🎯 Status

Release v0.3.0 – Clean Baseline - markiert einen stabilen Architekturstand mit klarer Trennung von Domain, Usecases und Infrastructure.