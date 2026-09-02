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


class CashReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.rules = json.loads(
            (root / "assets/templates/template.rules.json").read_text(encoding="utf-8")
        )
        cls.structure = json.loads(
            (root / "assets/templates/template.structure.json").read_text(encoding="utf-8")
        )["templates"]["family"]

    def test_edeka_receipt_recognizes_store_total_and_receipt_fields(self):
        text = """
AKTIV Markt Gebr. Hein
Gilgaustr. 29
51149 Köln-Ensen
www.edeka-hein.de
Bio E.Vollmilch 1,45 A
Iglo Fischstäbch. 4,99 A
SUMME EUR 6,44
Visa EUR 6,44
Kundenbeleg
Datum: 28.07.2026
Beleg-Nr. 5997
Datum Uhrzeit Filiale Pos Bed Bon
28.07.26 13:20 0070570 004 013 8708
Betrag EUR 6,44
Zahlung erfolgt
MwSt NETTO MwSt UMSATZ
TSE Transaktionsnummer: 1590536
Seriennr. Kasse: KAS04-EH070570
"""
        document = Document("Kassenbon_2026-07-28_13.20.pdf")
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.category, "Anschaffungen und Garantien")
        self.assertEqual(classification.document_type, "Kassenbons")
        self.assertEqual(classification.reason, "Kassenbon")
        self.assertEqual(data["document_kind"], "Kassenbon")
        self.assertEqual(data["brand"], "EDEKA")
        self.assertEqual(data["store_name"], "AKTIV Markt Gebr. Hein")
        self.assertEqual(data["vendor"], "EDEKA AKTIV Markt Gebr. Hein")
        self.assertEqual(data["date"], "28.07.2026")
        self.assertEqual(data["amount"], "6,44")
        self.assertEqual(data["receipt_number"], "5997")
        self.assertEqual(data["branch_number"], "0070570")
        self.assertEqual(data["tse_transaction_number"], "1590536")

        self.assertEqual(
            StoragePathBuilder(self.structure).build(document),
            Path(
                "Anschaffungen und Garantien", "Kassenbons", "2026",
                "2026-07-28 - Kassenbon - EDEKA AKTIV Markt Gebr. Hein - 6,44 EUR.pdf",
            ),
        )

    def test_invoice_with_sum_is_not_mistaken_for_cash_receipt(self):
        analyzer = DocumentAnalyzer(self.rules, {}, _Logger())
        self.assertIsNone(analyzer._extract_cash_receipt(
            "Rechnung Nr. 123\nSumme 99,00 EUR\nZahlbar innerhalb von 14 Tagen"
        ))


if __name__ == "__main__":
    unittest.main()
