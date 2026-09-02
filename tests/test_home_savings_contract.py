import unittest
from pathlib import Path

from src.document_analyzer import DocumentAnalyzer
from src.models import Document
from src.storage_utils import StoragePathBuilder


class _Logger:
    def debug(self, *_args):
        pass

    def warning(self, *_args):
        pass


class HomeSavingsContractTests(unittest.TestCase):
    TEXT = """
Bausparkasse Schwäbisch Hall AG
12. September 2018
Ihr neuer Bausparvertrag Nr. 20 251 089 T 03
Bausparurkunde
Ihr Bausparvertrag im Überblick:
Bausparnummer: 20 251 089 T 03
Bausparsumme: 50.000 €
Regelsparbeitrag: 250 €
Guthabenzins: 0,10 % jährlich
Wahlzuteilung: 25 %
Freistellungsauftrag für Kapitalerträge
"""

    def _analyze(self):
        document = Document(source_path="Unsere_Nachricht_fuer_Sie.pdf")
        document.mark_analyzed(self.TEXT)
        classification, metadata, data = DocumentAnalyzer([], {}, _Logger()).analyze(document)
        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data
        return document, classification, data

    def test_classifies_and_extracts_home_savings_contract(self):
        _document, classification, data = self._analyze()

        self.assertEqual(classification.category, "Finanzen")
        self.assertEqual(classification.document_type, "Sparen und Vermögen")
        self.assertEqual(classification.reason, "Bausparvertrag")
        self.assertEqual(data["provider"], "Schwäbisch Hall")
        self.assertEqual(data["contract_number"], "20 251 089 T 03")
        self.assertEqual(data["contract_reference"], "T 03")
        self.assertEqual(data["contract_sum"], "50.000,00")
        self.assertIsNone(data["amount"])
        self.assertEqual(data["currency"], "EUR")

    def test_builds_finance_folder_and_descriptive_filename(self):
        document, _classification, _data = self._analyze()
        structure = {
            "Finanzen": {"Sparen und Vermögen": {"{year}": {}}}
        }

        path = StoragePathBuilder(structure).build(document)

        self.assertEqual(
            path,
            Path(
                "Finanzen",
                "Sparen und Vermögen",
                "2018",
                "2018-09-12 - Bausparvertrag - Schwäbisch Hall - T 03.pdf",
            ),
        )


if __name__ == "__main__":
    unittest.main()
