from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "docs" / "doku_assets"
EXAMPLES_DIR = ASSET_ROOT / "examples"
SNIPPETS_DIR = ASSET_ROOT / "snippets"
DIAGRAMS_DIR = ASSET_ROOT / "diagrams"


def ensure_dirs() -> None:
    for path in (ASSET_ROOT, EXAMPLES_DIR, SNIPPETS_DIR, DIAGRAMS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_examples() -> None:
    config_example = {
        "auto_mode": False,
        "autostart": False,
        "daily_report_time": "18:00",
        "email": {
            "enabled": True,
            "imap_server": "imap.beispiel.de",
        },
        "company_profile": {
            "name": "Seraph IT GmbH",
            "person": {"first_name": "Julien", "last_name": "Hirte"},
            "keywords": ["seraph it", "seraph-it.de"],
            "address": {"street": "Beispielweg 12", "zip": "12345", "city": "Musterstadt"},
            "contact": {"email": "info@seraph-it.de", "phone": "+49 123 4567890"},
            "financial": {"iban": "DE02120300000000202051", "tax_id": "DE123456789"},
        },
        "ocr": {
            "tesseract_path": "third_party/tesseract/tesseract.exe",
            "poppler_path": "third_party/poppler/Library/bin",
        },
        "targets": {"manual": "manual_sort", "error": "error"},
    }

    rules_example = {
        "extraction": {
            "invoice_number_patterns": [
                "(rechnung\\s*(nr\\.?|nummer)?[:\\s\\-]*)([a-z0-9/\\-]{3,})",
                "(rechn\\.\\s*nr\\.?[:\\s\\-]*)([a-z0-9/\\-]{3,})",
                "(rg[\\.\\-\\s]*nr\\.?[:\\s\\-]*)([a-z0-9/\\-]{3,})",
                "(invoice\\s*(no\\.?|number)?[:\\s\\-]*)([a-z0-9/\\-]{3,})",
                "(rechnung[_\\s\\-]*)(\\d{3,})",
            ],
            "invoice_number_blacklist": ["re", "ref", "re:", "nr", "summe", "seite"],
            "amount_patterns": [
                "\\b\\d{1,3}(?:\\.\\d{3})*,\\d{2}\\b",
                "\\b\\d{1,3}(?:,\\d{3})*\\.\\d{2}\\b",
                "\\b\\d+[.,]\\d{2}\\b",
            ],
            "description_keywords": ["installation", "lizenz", "abo", "vertrag", "leistung", "service"],
            "description_blacklist": ["datum", "rechnung", "betrag", "mwst", "gesamt", "kunde"],
            "description_max_length": 80,
            "description_max_words": 5,
            "vendor_blacklist": [
                "betrag", "summe", "rechnung", "datum", "seite", "total", "mwst", "bank",
                "verbindung", "bankverbindung", "iban", "bic", "konto", "guten tag",
                "vielen dank", "leistung", "zahlungsbedingungen", "rechnungsbetrag",
                "übersicht", "service", "team", "kunde",
            ],
            "vendor_company_suffixes": ["gmbh", "ag", "ug", "kg", "ltd"],
            "vendor_address_terms": ["straße", "str.", "gasse", "platz"],
            "vendor_max_words": 5,
            "vendor_max_digits": 2,
            "vendor_scan_window": 10,
        },
        "rules": [{
            "category": "BUCHHALTUNG",
            "document_type": "Rechnung",
            "keywords": [
                "rechnung", "rechnungsnummer", "invoice", "zahlbar bis",
                "zahlungsbedingungen", "netto", "brutto", "gesamtbetrag", "amount due",
            ],
        }],
    }

    structure_example = {
        "BUCHHALTUNG": {
            "Eingangsrechnungen": {"{year}": {"{month_number} {month_name}": {}}},
            "Ausgangsrechnungen": {"{year}": {"{month_number} {month_name}": {}}},
            "Unsortiert": {},
        }
    }

    write_json(EXAMPLES_DIR / "config.example.json", config_example)
    write_json(EXAMPLES_DIR / "rules.example.json", rules_example)
    write_json(EXAMPLES_DIR / "structure.example.json", structure_example)

    write_text(
        EXAMPLES_DIR / "sorterino.log.example.txt",
        """
        [2026-04-20 08:14:02] [LOG] IN: scan_2026-04-20_001.pdf
        [2026-04-20 08:14:03] [LOG] OUT: scan_2026-04-20_001.pdf F:\\Ablage\\BUCHHALTUNG\\Eingangsrechnungen\\2026\\04 April\\20.04.2026 - Stadtwerke Musterstadt - 185,40.pdf
        [2026-04-20 08:16:11] [LOG] IN: rechnung_70015.pdf
        [2026-04-20 08:16:12] [LOG] OUT: rechnung_70015.pdf F:\\Ablage\\BUCHHALTUNG\\Ausgangsrechnungen\\2026\\04 April\\Rechnung 70015 vom 20.04.2026 Musterkunde GmbH.pdf
        [2026-04-20 08:18:39] [LOG] IN: scan_unscharf.pdf
        [2026-04-20 08:18:40] [ERROR] OCR Fehler -> Datei in Error
        """,
    )

    daily_report = {
        "date": "2026-04-20",
        "summary": {"total": 3, "success": 2, "manual": 0, "error": 1},
        "items": [
            {
                "timestamp": "2026-04-20T08:14:03",
                "status": "success",
                "reason": "ok",
                "original_name": "scan_2026-04-20_001.pdf",
                "final_name": "20.04.2026 - Stadtwerke Musterstadt - 185,40.pdf",
                "target_folder": "F:\\Ablage\\BUCHHALTUNG\\Eingangsrechnungen\\2026\\04 April",
            },
            {
                "timestamp": "2026-04-20T08:16:12",
                "status": "success",
                "reason": "ok",
                "original_name": "rechnung_70015.pdf",
                "final_name": "Rechnung 70015 vom 20.04.2026 Musterkunde GmbH.pdf",
                "target_folder": "F:\\Ablage\\BUCHHALTUNG\\Ausgangsrechnungen\\2026\\04 April",
            },
            {
                "timestamp": "2026-04-20T08:18:40",
                "status": "error",
                "reason": "ocr_error",
                "original_name": "scan_unscharf.pdf",
                "final_name": "scan_unscharf.pdf",
                "target_folder": "F:\\Ablage\\Sorterino - Runtime\\error",
            },
        ],
    }
    write_json(EXAMPLES_DIR / "daily_report_2026-04-20.json", daily_report)
    write_text(
        EXAMPLES_DIR / "daily_report_2026-04-20.txt",
        """
        Sorterino Daily Report - 2026-04-20

        Zusammenfassung
        - Gesamt: 3
        - Erfolgreich: 2
        - Manuell: 0
        - Fehler: 1

        Details
        SUCCESS  | scan_2026-04-20_001.pdf -> 20.04.2026 - Stadtwerke Musterstadt - 185,40.pdf | F:\\Ablage\\BUCHHALTUNG\\Eingangsrechnungen\\2026\\04 April | ok
        SUCCESS  | rechnung_70015.pdf -> Rechnung 70015 vom 20.04.2026 Musterkunde GmbH.pdf | F:\\Ablage\\BUCHHALTUNG\\Ausgangsrechnungen\\2026\\04 April | ok
        ERROR    | scan_unscharf.pdf -> scan_unscharf.pdf | F:\\Ablage\\Sorterino - Runtime\\error | ocr_error
        """,
    )


def create_snippets() -> None:
    write_text(
        SNIPPETS_DIR / "domain_model.py.txt",
        """
        class DocumentStatus:
            NEW = "NEW"
            ANALYZED = "ANALYZED"
            CLASSIFIED = "CLASSIFIED"
            STORED = "STORED"
            ERROR = "ERROR"

        @dataclass
        class Classification:
            category: str
            confidence: float
            document_type: Optional[str] = None

        @dataclass
        class DocumentMetadata:
            category: Optional[str]
            document_type: Optional[str]
            invoice_date: Optional[str] = None

        @dataclass
        class Document:
            source_path: str
            extracted_text: Optional[str] = None
            classification: Optional[Classification] = None
            metadata: Optional[DocumentMetadata] = None
            extracted_data: dict = field(default_factory=dict)
            target_path: Optional[str] = None
            status: str = DocumentStatus.NEW
        """,
    )

    write_text(
        SNIPPETS_DIR / "routing_path_builder.py.txt",
        """
        class StoragePathBuilder:
            def build(self, document: Document) -> Path:
                category = document.metadata.category or "DIVERSES"
                doc_type = document.metadata.document_type or "Unsortiert"
                structure_category = self.structure.get(category, {})
                filename = self._generate_filename(document)

                if doc_type not in structure_category:
                    return Path(category, "Unsortiert", filename)

                path_parts = [category, doc_type]
                date = document.extracted_data.get("date")

                if date:
                    d, m, y = date.split(".")
                    month_name = MONTH_NAMES[int(m) - 1]
                    path_parts.append(y)
                    path_parts.append(f"{m} {month_name}")

                return Path(*path_parts) / filename

            def _generate_filename(self, document: Document) -> str:
                if document.metadata.document_type == "Ausgangsrechnungen":
                    return f"Rechnung {invoice_number} vom {date} {vendor}.pdf"
                if document.metadata.document_type == "Eingangsrechnungen":
                    return f"{date} - {vendor} - {amount}.pdf"
                return f"{fallback_name}.pdf"
        """,
    )

    write_text(
        SNIPPETS_DIR / "document_pipeline.py.txt",
        """
        def _process(self, document: Document):
            filename = os.path.basename(document.source_path)
            self.logger.log(f"IN: {filename}")
            self.runtime.backup(document.source_path, "backup", filename)

            text = self.ocr.extract_text(document.source_path) if self.ocr else ""
            if text is None:
                self._store_runtime(document, self.error_target, filename, "ERROR", "error", "ocr_error")
                return

            if not text.strip():
                self._store_runtime(document, self.manual_sort_target, filename, "MANUAL", "manual", "ocr_empty")
                return

            document.mark_analyzed(text)
            classification, metadata, extracted = self.analyzer.analyze(document)
            document.mark_classified(classification)
            document.metadata = metadata
            document.extracted_data = extracted

            missing_fields = self._missing_required_data(document)
            if missing_fields:
                self._store_runtime(document, self.manual_sort_target, filename, "MANUAL", "manual", "missing_required_data")
                return

            target_path = self.path_builder.build(document)
            final = self.archive.store(document.source_path, target_path.parent, target_path.name)
            self.logger.log(f"OUT: {filename} {final}")
        """,
    )

    write_text(
        SNIPPETS_DIR / "logging_beispiel.txt",
        """
        sorterino.log
        [2026-04-20 08:14:02] [LOG] IN: scan_2026-04-20_001.pdf
        [2026-04-20 08:14:03] [LOG] OUT: scan_2026-04-20_001.pdf F:\\Ablage\\BUCHHALTUNG\\Eingangsrechnungen\\2026\\04 April\\20.04.2026 - Stadtwerke Musterstadt - 185,40.pdf
        [2026-04-20 08:18:40] [ERROR] OCR Fehler -> Datei in Error

        daily_report_2026-04-20.txt
        - Gesamt: 3
        - Erfolgreich: 2
        - Manuell: 0
        - Fehler: 1
        """,
    )


def box(x: int, y: int, w: int, h: int, text: str, fill: str = "#E8F0FE", stroke: str = "#284B63") -> str:
    return dedent(
        f"""
        <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
        <text x="{x + w / 2}" y="{y + h / 2}" text-anchor="middle" dominant-baseline="middle">{text}</text>
        """
    ).strip()


def arrow(x1: int, y1: int, x2: int, y2: int, dashed: bool = False, label: str | None = None) -> str:
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    label_text = ""
    if label:
        lx = (x1 + x2) / 2
        ly = (y1 + y2) / 2 - 10
        label_text = f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="15">{label}</text>'
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1F2937" stroke-width="2.5"{dash} marker-end="url(#arrow)"/>'
        + label_text
    )


def svg_document(width: int, height: int, body: str) -> str:
    return dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
          <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#1F2937"/>
            </marker>
            <style>
              text {{
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 16px;
                fill: #0F172A;
                white-space: pre;
              }}
              .title {{
                font-size: 26px;
                font-weight: 700;
              }}
              .small {{
                font-size: 14px;
              }}
            </style>
          </defs>
          <rect width="100%" height="100%" fill="#F8FAFC"/>
          {body}
        </svg>
        """
    ).strip() + "\n"


def create_diagrams() -> None:
    waterfall = svg_document(
        1400,
        680,
        """
        <text x="60" y="70" class="title">Erweitertes Wasserfallmodell - Sorterino</text>
        <rect x="60" y="120" width="220" height="440" rx="18" fill="#DCEBFF" stroke="#284B63" stroke-width="2"/>
        <rect x="320" y="160" width="220" height="400" rx="18" fill="#FFE3D3" stroke="#8C4A2F" stroke-width="2"/>
        <rect x="580" y="200" width="220" height="360" rx="18" fill="#DFF3E4" stroke="#2F6B4F" stroke-width="2"/>
        <rect x="840" y="240" width="220" height="320" rx="18" fill="#FFF3CD" stroke="#8A6D1F" stroke-width="2"/>
        <rect x="1100" y="280" width="220" height="280" rx="18" fill="#E8DEF8" stroke="#5B4B8A" stroke-width="2"/>
        <text x="170" y="170" text-anchor="middle">Analyse</text>
        <text x="170" y="210" text-anchor="middle" class="small">Ist-Aufnahme, Anforderungen,</text>
        <text x="170" y="235" text-anchor="middle" class="small">Soll-Zielprozess</text>
        <text x="430" y="210" text-anchor="middle">Konzept</text>
        <text x="430" y="250" text-anchor="middle" class="small">Architektur, PSP, Gantt,</text>
        <text x="430" y="275" text-anchor="middle" class="small">GUI-Entwurf</text>
        <text x="690" y="250" text-anchor="middle">Implementierung</text>
        <text x="690" y="290" text-anchor="middle" class="small">Pipeline, OCR, Routing,</text>
        <text x="690" y="315" text-anchor="middle" class="small">GUI, Installer</text>
        <text x="950" y="290" text-anchor="middle">Test &amp; QS</text>
        <text x="950" y="330" text-anchor="middle" class="small">Modul- und Integrationstests,</text>
        <text x="950" y="355" text-anchor="middle" class="small">manuelle Fachtests</text>
        <text x="1210" y="330" text-anchor="middle">Übergabe</text>
        <text x="1210" y="370" text-anchor="middle" class="small">Abnahme, Einweisung,</text>
        <text x="1210" y="395" text-anchor="middle" class="small">Dokumentation</text>
        <line x1="280" y1="340" x2="320" y2="340" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <line x1="540" y1="360" x2="580" y2="360" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <line x1="800" y1="380" x2="840" y2="380" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <line x1="1060" y1="400" x2="1100" y2="400" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <path d="M1160 570 C900 630, 480 630, 180 570" fill="none" stroke="#1F2937" stroke-width="2.5" stroke-dasharray="8 6" marker-end="url(#arrow)"/>
        <text x="670" y="620" text-anchor="middle" class="small">Rückkopplungen zwischen Test, Umsetzung und Analyse</text>
        """,
    )
    write_text(DIAGRAMS_DIR / "waterfall_model.svg", waterfall)

    program_flow = svg_document(
        1100,
        1200,
        """
        <text x="60" y="70" class="title">Programmablaufplan</text>
        """
        + box(370, 110, 360, 70, "Start / run_pipeline()", "#DCEBFF")
        + arrow(550, 180, 550, 230)
        + box(320, 230, 460, 80, "Konfiguration laden und Workspace initialisieren", "#FDE68A")
        + arrow(550, 310, 550, 360)
        + box(320, 360, 460, 80, "E-Mail-Anhänge abrufen (optional)", "#E5E7EB")
        + arrow(550, 440, 550, 490)
        + box(320, 490, 460, 80, "OCR-Dienst initialisieren", "#DFF3E4")
        + arrow(550, 570, 550, 620)
        + box(320, 620, 460, 80, "Dokumente aus Input-Ordner laden", "#FCE7F3")
        + arrow(550, 700, 550, 750)
        + box(320, 750, 460, 80, "Pro Dokument: Backup -> OCR -> Analyse -> Klassifikation", "#E9D5FF")
        + arrow(550, 830, 550, 880)
        + box(320, 880, 460, 90, "Fehlende Pflichtdaten?\nJa -> manuelle Sortierung\nNein -> Zielpfad bestimmen", "#FFE3D3")
        + arrow(550, 970, 550, 1020)
        + box(320, 1020, 460, 90, "Archivablage / Error-Ablage\nDaily Report Event schreiben", "#BFDBFE")
        + arrow(550, 1110, 550, 1140)
        + box(410, 1140, 280, 50, "Ende", "#DCEBFF")
    )
    write_text(DIAGRAMS_DIR / "program_flow.svg", program_flow)

    architecture = svg_document(
        1400,
        820,
        """
        <text x="60" y="70" class="title">Architekturmodell</text>
        <text x="60" y="110" class="small">Schichtenmodell nach Verantwortlichkeiten</text>
        <rect x="80" y="150" width="1240" height="130" rx="18" fill="#DCEBFF" stroke="#284B63" stroke-width="2"/>
        <text x="700" y="200" text-anchor="middle">Präsentation / GUI</text>
        <text x="700" y="235" text-anchor="middle" class="small">app.py, main_window.py, config_window.py, tray.py, log_window.py</text>
        <rect x="80" y="320" width="1240" height="130" rx="18" fill="#FDE68A" stroke="#8A6D1F" stroke-width="2"/>
        <text x="700" y="370" text-anchor="middle">Anwendungslogik / Orchestrierung</text>
        <text x="700" y="405" text-anchor="middle" class="small">main.py, document_pipeline.py, initialize_workspace.py, reporting.py</text>
        <rect x="80" y="490" width="1240" height="130" rx="18" fill="#DFF3E4" stroke="#2F6B4F" stroke-width="2"/>
        <text x="700" y="540" text-anchor="middle">Domäne / Analyse</text>
        <text x="700" y="575" text-anchor="middle" class="small">models.py, document_analyzer.py, Klassifikation, Extraktion, Statusmodell</text>
        <rect x="80" y="660" width="1240" height="110" rx="18" fill="#FFE3D3" stroke="#8C4A2F" stroke-width="2"/>
        <text x="700" y="708" text-anchor="middle">Infrastruktur</text>
        <text x="700" y="742" text-anchor="middle" class="small">storage_utils.py, tesseract_ocr.py, mail_fetcher.py, config.py, Filesystem / IMAP / OCR</text>
        <line x1="700" y1="280" x2="700" y2="320" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <line x1="700" y1="450" x2="700" y2="490" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <line x1="700" y1="620" x2="700" y2="660" stroke="#1F2937" stroke-width="3" marker-end="url(#arrow)"/>
        <text x="1020" y="302" class="small">steuert</text>
        <text x="1020" y="472" class="small">nutzt</text>
        <text x="1020" y="642" class="small">bindet an</text>
        """,
    )
    write_text(DIAGRAMS_DIR / "architecture_model.svg", architecture)

    psp = svg_document(
        1400,
        900,
        """
        <text x="60" y="70" class="title">Projektstrukturplan</text>
        """
        + box(520, 110, 360, 70, "Sorterino 1.0", "#DCEBFF")
        + arrow(700, 180, 250, 260)
        + arrow(700, 180, 520, 260)
        + arrow(700, 180, 790, 260)
        + arrow(700, 180, 1060, 260)
        + box(120, 260, 260, 140, "1 Analyse\n- Ist-Aufnahme\n- Anforderungen\n- Zieldefinition", "#FFE3D3")
        + box(390, 260, 260, 140, "2 Architektur\n- Variantenvergleich\n- Zielarchitektur\n- GUI-Konzept", "#FDE68A")
        + box(660, 260, 260, 140, "3 Implementierung\n- Pipeline\n- OCR / IMAP\n- Routing / GUI", "#DFF3E4")
        + box(930, 260, 260, 140, "4 QS & Übergabe\n- Tests\n- Installer\n- Einweisung / Abnahme", "#E9D5FF")
        + arrow(250, 400, 170, 500)
        + arrow(250, 400, 330, 500)
        + arrow(520, 400, 440, 500)
        + arrow(520, 400, 600, 500)
        + arrow(790, 400, 710, 500)
        + arrow(790, 400, 870, 500)
        + arrow(1060, 400, 980, 500)
        + arrow(1060, 400, 1140, 500)
        + box(80, 500, 180, 110, "1.1 Interview\n1.2 Ist-Prozess", "#FFF7ED")
        + box(280, 500, 180, 110, "1.3 Soll-Prozess\n1.4 Antragabgleich", "#FFF7ED")
        + box(350, 500, 180, 110, "2.1 Architektur\n2.2 Datenfluss", "#FEF3C7")
        + box(550, 500, 180, 110, "2.3 PSP / Gantt\n2.4 Mockup", "#FEF3C7")
        + box(620, 500, 180, 110, "3.1 Config / Runtime\n3.2 Übernahme", "#ECFCCB")
        + box(820, 500, 180, 110, "3.3 Analyse / OCR\n3.4 Ablage", "#ECFCCB")
        + box(890, 500, 180, 110, "4.1 Tests\n4.2 Installer", "#F3E8FF")
        + box(1090, 500, 180, 110, "4.3 Doku\n4.4 Abnahme", "#F3E8FF")
    )
    write_text(DIAGRAMS_DIR / "project_structure_plan.svg", psp)

    use_case = svg_document(
        1400,
        860,
        """
        <text x="60" y="70" class="title">Use-Case Diagramm</text>
        <rect x="300" y="150" width="820" height="580" rx="24" fill="#FFFFFF" stroke="#284B63" stroke-width="2.5"/>
        <text x="710" y="190" text-anchor="middle">Sorterino Anwendung</text>
        <ellipse cx="710" cy="280" rx="170" ry="42" fill="#DCEBFF" stroke="#284B63" stroke-width="2"/>
        <text x="710" y="280" text-anchor="middle" dominant-baseline="middle">Dokument übernehmen</text>
        <ellipse cx="710" cy="370" rx="170" ry="42" fill="#FDE68A" stroke="#8A6D1F" stroke-width="2"/>
        <text x="710" y="370" text-anchor="middle" dominant-baseline="middle">Dokument analysieren</text>
        <ellipse cx="710" cy="460" rx="170" ry="42" fill="#DFF3E4" stroke="#2F6B4F" stroke-width="2"/>
        <text x="710" y="460" text-anchor="middle" dominant-baseline="middle">Dokument klassifizieren</text>
        <ellipse cx="710" cy="550" rx="170" ry="42" fill="#E9D5FF" stroke="#5B4B8A" stroke-width="2"/>
        <text x="710" y="550" text-anchor="middle" dominant-baseline="middle">Datei benennen und ablegen</text>
        <ellipse cx="710" cy="640" rx="170" ry="42" fill="#FFE3D3" stroke="#8C4A2F" stroke-width="2"/>
        <text x="710" y="640" text-anchor="middle" dominant-baseline="middle">Fehlerfall behandeln</text>
        <ellipse cx="520" cy="230" rx="140" ry="36" fill="#E5E7EB" stroke="#475569" stroke-width="2"/>
        <text x="520" y="230" text-anchor="middle" dominant-baseline="middle">E-Mail-Anhang importieren</text>
        <circle cx="120" cy="320" r="42" fill="#FFFFFF" stroke="#1F2937" stroke-width="2"/>
        <line x1="120" y1="362" x2="120" y2="470" stroke="#1F2937" stroke-width="2"/>
        <line x1="70" y1="400" x2="170" y2="400" stroke="#1F2937" stroke-width="2"/>
        <line x1="120" y1="470" x2="75" y2="545" stroke="#1F2937" stroke-width="2"/>
        <line x1="120" y1="470" x2="165" y2="545" stroke="#1F2937" stroke-width="2"/>
        <text x="120" y="585" text-anchor="middle">Benutzer</text>
        <circle cx="1290" cy="320" r="42" fill="#FFFFFF" stroke="#1F2937" stroke-width="2"/>
        <line x1="1290" y1="362" x2="1290" y2="470" stroke="#1F2937" stroke-width="2"/>
        <line x1="1240" y1="400" x2="1340" y2="400" stroke="#1F2937" stroke-width="2"/>
        <line x1="1290" y1="470" x2="1245" y2="545" stroke="#1F2937" stroke-width="2"/>
        <line x1="1290" y1="470" x2="1335" y2="545" stroke="#1F2937" stroke-width="2"/>
        <text x="1290" y="585" text-anchor="middle">E-Mail-Server</text>
        """
        + arrow(162, 400, 540, 290)
        + arrow(1248, 400, 660, 230)
        + arrow(520, 266, 630, 280, True, "&lt;&lt;include&gt;&gt;")
        + arrow(710, 322, 710, 328, True, "&lt;&lt;include&gt;&gt;")
        + arrow(710, 412, 710, 418, True, "&lt;&lt;include&gt;&gt;")
        + arrow(710, 502, 710, 508, True, "&lt;&lt;include&gt;&gt;")
        + arrow(640, 395, 640, 598, True, "&lt;&lt;extend&gt;&gt;")
        + arrow(780, 485, 780, 598, True, "&lt;&lt;extend&gt;&gt;")
    )
    write_text(DIAGRAMS_DIR / "use_case_diagram.svg", use_case)


def main() -> None:
    ensure_dirs()
    create_examples()
    create_snippets()
    create_diagrams()
    print(f"Doku-Assets erzeugt unter: {ASSET_ROOT}")


if __name__ == "__main__":
    main()
