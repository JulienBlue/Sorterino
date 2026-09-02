import json
import tempfile
import unittest
from pathlib import Path

from src.document_analyzer import DocumentAnalyzer
from src.document_pipeline import DocumentPipeline
from src.models import Document
from src.storage_utils import StoragePathBuilder


SAMPLE_TEXT = """
Einkommensbescheinigung
- Nachweis über die Höhe des Arbeitsentgelts -
Name: Hirte                 Vorname: Julien Blue             Geburtsdatum: 04.05.1990
Bruttoarbeitsentgelt (ohne Einmalzahlungen): 135,00 Euro
Nettoarbeitsentgelt: 112,12 Euro
Weitere Angaben zum Beschäftigungsverhältnis
Betriebsnummer: 93325730                         EIKON Media GmbH
04.04.2024
Datum / Unterschrift des Arbeitgebers oder seines Beauftragten
Lizenz: adag Payroll Services GmbH - Vertrieb: SESAM Software GmbH
"""


class NullLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class IncomeCertificateTests(unittest.TestCase):
    def _analyze(self):
        rules_path = Path(__file__).parents[1] / "assets" / "templates" / "template.rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        document = Document("Verdienstbescheinigung_115.pdf", extracted_text=SAMPLE_TEXT)
        return document, DocumentAnalyzer(rules, {}, NullLogger()).analyze(document)

    def test_classifies_and_extracts_labeled_certificate_values(self):
        _document, (classification, _metadata, extracted) = self._analyze()

        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(classification.document_type, "Bescheinigungen")
        self.assertEqual(extracted["date"], "04.04.2024")
        self.assertEqual(extracted["employer"], "EIKON Media GmbH")
        self.assertEqual(extracted["employee_name"], "Julien Blue Hirte")
        self.assertEqual(extracted["gross_amount"], "135,00")
        self.assertEqual(extracted["net_amount"], "112,12")

    def test_builds_certificate_folder_and_descriptive_filename(self):
        document, (classification, metadata, extracted) = self._analyze()
        document.classification = classification
        document.metadata = metadata
        document.extracted_data = extracted
        structure = {
            "Arbeit und Karriere": {
                "Bescheinigungen": {"{year}": {}}
            }
        }

        result = StoragePathBuilder(structure).build(document)

        self.assertEqual(
            result,
            Path(
                "Arbeit und Karriere",
                "Bescheinigungen",
                "2024",
                "2024-04-04 - Einkommensbescheinigung - EIKON Media GmbH.pdf",
            ),
        )

    def test_certificate_requires_date_and_employer_for_automatic_filing(self):
        document = Document("test.pdf")
        document.metadata = type("Metadata", (), {"document_type": "Bescheinigungen"})()
        document.extracted_data = {"date": "04.04.2024", "employer": ""}
        pipeline = object.__new__(DocumentPipeline)

        self.assertEqual(pipeline._missing_required_data(document), ["employer"])


if __name__ == "__main__":
    unittest.main()
