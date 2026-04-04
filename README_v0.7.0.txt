🚀 Sorterino v0.7.0

✨ Überblick

Sorterino ist eine lokale Desktop-Anwendung zur automatisierten
Dokumentenverarbeitung.

Das System verarbeitet eingehende Dateien vollständig automatisiert:

OCR → Klassifikation → strukturierte Ablage

Die gesamte Logik ist konfigurierbar und benötigt keine Cloud-Anbindung.

------------------------------------------------------------------------

🧠 Funktionsweise

1.  📥 Dokumente werden aus dem Input-Ordner geladen
2.  🔍 OCR erkennt Textinhalte (Tesseract lokal)
3.  🧠 Klassifikation erfolgt über regelbasierte Analyse (rules.json)
4.  📂 Dokumente werden automatisch strukturiert abgelegt

------------------------------------------------------------------------

⚙️ Architektur

🔹 Pipeline

Die Verarbeitung erfolgt über eine entkoppelte Pipeline:

-   DocumentPipeline
-   DocumentAnalyzer
-   TesseractOCR
-   FilesystemStorage

Die Pipeline ist vollständig unabhängig von GUI und CLI nutzbar.

------------------------------------------------------------------------

🔹 Datenmodell

Zentrale Objekte:

-   Document
-   DocumentStatus
-   Classification
-   DocumentMetadata

Status-Flow:

NEW → ANALYZED → CLASSIFIED → STORED ↘ ERROR

------------------------------------------------------------------------

🔹 Logging-Konzept

Bewusst reduziertes Logging:

Logfile: - logger.log() → Business Events - logger.error() → Fehler

Console: - logger.info() → Ablauf - logger.debug() → Details

------------------------------------------------------------------------

📁 Runtime-Struktur

.sorterino_runtime/ incoming/ logs/ error/ manual_sort/ processed/
rules.json structure.json config.json

------------------------------------------------------------------------

🧾 Konfiguration

rules.json → Klassifikation
structure.json → Ordnerstruktur
config.json → Systemkonfiguration

------------------------------------------------------------------------

🖥 GUI Features

-   Tray-App
-   Einstellungen
-   JSON Editor
-   Log Viewer
-   Automatikmodus
-   Autostart

------------------------------------------------------------------------

🔄 Betriebsmodi

Manuell → Button
Automatik → Loop

------------------------------------------------------------------------

⚠️ Hinweise

-   OCR abhängig von Qualität
-   Unterstützt: PDF, PNG, JPG
-   Unklare Dokumente → manual_sort

------------------------------------------------------------------------

🛠 Installation

python -m venv .venv .venv

pip install -r requirements.txt

python main.py python -m src.gui.app

------------------------------------------------------------------------

🧑‍💻 Kontext

IHK Abschlussprojekt – Anwendungsentwicklung
