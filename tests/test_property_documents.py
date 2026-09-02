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


class PropertyDocumentTests(unittest.TestCase):
    def analyze(self, filename, text):
        document = Document(filename, filename)
        document.extracted_text = text
        classification, metadata, data = DocumentAnalyzer([], {}, _Logger()).analyze(document)
        document.metadata = metadata
        document.extracted_data = data
        return document, classification, data

    def test_energy_certificate_uses_validity_and_discards_false_financial_data(self):
        document, classification, data = self.analyze(
            "Energieausweis Schöne Aussicht 1 1300_2030-10-16.pdf",
            "ENERGIEAUSWEIS für Wohngebäude\nAusstellungsdatum 16.10.2020\n18,11",
        )

        self.assertEqual(classification.category, "Wohnen")
        self.assertEqual(classification.document_type, "Immobilienunterlagen")
        self.assertEqual(data["document_kind"], "Energieausweis")
        self.assertEqual(data["valid_until"], "16.10.2030")
        self.assertIsNone(data["amount"])
        self.assertIsNone(data["vendor"])
        self.assertEqual(data["shared_scope"], "family")
        self.assertEqual(
            StoragePathBuilder({"Wohnen": {"Immobilienunterlagen": {}}}).build(document),
            Path("Wohnen/Immobilienunterlagen/Energieausweis - gültig bis 2030-10-16.pdf"),
        )

    def test_floor_plan_is_recognized_from_its_unambiguous_filename(self):
        document, classification, data = self.analyze(
            "Grundriss[1].pdf",
            "WASCH TROCKENR. 48,70",
        )
        self.assertEqual(classification.document_type, "Immobilienunterlagen")
        self.assertEqual(data["document_kind"], "Grundriss")
        self.assertIsNone(data["amount"])
        self.assertEqual(
            StoragePathBuilder({"Wohnen": {"Immobilienunterlagen": {}}}).build(document),
            Path("Wohnen/Immobilienunterlagen/Grundriss.pdf"),
        )

    def test_declaration_of_division_ignores_dates_and_amounts_from_legal_text(self):
        document, classification, data = self.analyze(
            "Auszug aus Teilungserklärung(1).pdf",
            "Auszug aus der Teilungserklärung vom 16.10.1937 Betrag 16,10 USD",
        )
        self.assertEqual(classification.document_type, "Immobilienunterlagen")
        self.assertEqual(data["document_kind"], "Teilungserklärung")
        self.assertIsNone(data["date"])
        self.assertIsNone(data["currency"])
        self.assertEqual(
            StoragePathBuilder({"Wohnen": {"Immobilienunterlagen": {}}}).build(document),
            Path("Wohnen/Immobilienunterlagen/Teilungserklärung.pdf"),
        )


if __name__ == "__main__":
    unittest.main()
