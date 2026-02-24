## Description
Sorterino ist eine lokale Desktop-Anwendung zur automatisierten
Dokumentenverarbeitung. Dokumente werden aus einem Input-Ordner
erfasst, gesichert, analysiert (OCR), klassifiziert und strukturiert
abgelegt.

## Architecture
- Domain-driven modular architecture
- Cyclic processing mode
- Local OCR via Tesseract
- No cloud dependencies

## Requirements
- Python 3.12+
- Tesseract OCR (lokal installiert)
- Poppler (für PDF-Verarbeitung)