import json
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


class PurchaseReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.rules = json.loads(
            (root / "assets/templates/template.rules.json").read_text(encoding="utf-8")
        )
        cls.structure = json.loads(
            (root / "assets/templates/template.structure.json").read_text(encoding="utf-8")
        )["templates"]["family"]

    def test_birkenstock_return_confirmation_extracts_refund_and_product(self):
        text = """
RETOURENBESTÄTIGUNG
Birkenstock Online Shop
Korrekturrechnung-Nr.: 7003685926
Korrekturrechnungsdatum: 17.07.2026
Ihre Bestell-Nr.: 2202185151
Kunden-Nr.: B0072003753
10 1031426 Arizona Birko-Flor Ultra Blue 38;5 1 90,00
Wir erstatten den Warenwert auf das Konto, von dem Sie die Zahlung geleistet haben.
Nettogutschriftsbetrag: EUR 75,63
Gutschriftsbetrag: EUR 90,00
Korrekturgrund: Warenrücksendung
Birkenstock Europe GmbH
"""
        document = Document("Retourenbestätigung-7003685926.pdf")
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.category, "Anschaffungen und Garantien")
        self.assertEqual(classification.document_type, "Retouren und Erstattungen")
        self.assertEqual(data["vendor"], "Birkenstock Europe GmbH")
        self.assertEqual(data["invoice_number"], "7003685926")
        self.assertEqual(data["order_number"], "2202185151")
        self.assertEqual(data["amount"], "90,00")
        self.assertEqual(data["product"], "Arizona Birko-Flor Ultra Blue")

        target = StoragePathBuilder(self.structure).build(document)
        self.assertEqual(
            target,
            Path(
                "Anschaffungen und Garantien", "Retouren und Erstattungen", "2026",
                "2026-07-17 - Retourenbestätigung - Birkenstock - "
                "Arizona Birko-Flor Ultra Blue - 7003685926 - 90,00 EUR.pdf",
            ),
        )


if __name__ == "__main__":
    unittest.main()
