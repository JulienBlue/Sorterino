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


class EnergyOrderConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.rules = json.loads(
            (root / "assets" / "templates" / "template.rules.json").read_text(encoding="utf-8")
        )
        cls.structure = json.loads(
            (root / "assets" / "templates" / "template.structure.json").read_text(encoding="utf-8")
        )["templates"]["family"]

    def test_plusstrom_order_confirmation_is_not_an_invoice(self):
        text = """
Fuxx - Die Sparenergie GmbH - Postfach 21 03 68 - 50529 Köln
Sabine Schirmer
Schöne Aussicht 1
51149 Köln
Auftragsnummer: 9013775192 13.07.2026
Auftragseingangsbestätigung Strombelieferung
vielen Dank, dass Sie sich für PlusStrom entschieden haben.
Ihr voraussichtlicher Liefertermin ist der 15.07.2026.
Tarif: PlusStrom GRÜNFAIR
Jahresverbrauch 2.500,00 kWh
Arbeitspreis 23,59 Cent/kWh
Grundpreis 24,12 EUR/Monat
"""
        document = Document("2026-07-13 - Kaufbeleg - Sabine Schirmer - 2500,00 USD.pdf")
        document.mark_analyzed(text)

        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.category, "Wohnen")
        self.assertEqual(classification.document_type, "Energieverträge")
        self.assertEqual(classification.reason, "Auftragseingangsbestätigung Energie")
        self.assertEqual(data["document_kind"], "Auftragseingangsbestätigung")
        self.assertEqual(data["vendor"], "Fuxx - Die Sparenergie GmbH")
        self.assertEqual(data["order_number"], "9013775192")
        self.assertEqual(data["contract_number"], "9013775192")
        self.assertEqual(data["expected_delivery_date"], "15.07.2026")
        self.assertEqual(data["tariff"], "PlusStrom GRÜNFAIR")
        self.assertIsNone(data["amount"])
        self.assertIsNone(data["currency"])
        self.assertIsNone(data["invoice_number"])
        self.assertEqual(data["shared_scope"], "family")

        target = StoragePathBuilder(self.structure).build(document)
        self.assertEqual(
            target,
            Path(
                "Wohnen", "Energieverträge", "2026",
                "2026-07-13 - Auftragseingangsbestätigung Strombelieferung - PlusStrom - Auftrag 9013775192.pdf",
            ),
        )

    def test_title_tolerates_ocr_line_break_and_missing_umlaut(self):
        text = """
Fuxx - Die Sparenergie GmbH
Auftrags Nr.: 9013775192                         13.07.2026
Auftragseingangsbestatigung
Strom bel ieferung
PlusStrom
"""
        # A split inside the word itself is unusually destructive OCR. The
        # relevant real-world variant is whitespace between Strom and Belieferung.
        text = text.replace("bel ieferung", "belieferung")
        document = Document("12345.pdf")
        document.mark_analyzed(text)

        classification, _metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)

        self.assertEqual(classification.document_type, "Energieverträge")
        self.assertEqual(data["order_number"], "9013775192")
        self.assertIsNone(data["amount"])
        self.assertIsNone(data["currency"])

    def test_plusstrom_contract_confirmation_uses_energy_contract_folder(self):
        text = """
Fuxx - Die Sparenergie GmbH
Sabine Schirmer
Vertragsnummer: 9013775192 17.07.2026
Vertragsbestätigung Strombelieferung
Ihr Wechsel zu PlusStrom war erfolgreich.
Damit steht Ihr Belieferungsbeginn durch uns zum 01.12.2026 definitiv fest.
Kundennummer: 9JUL26019256
Lieferbeginn: 01.12.2026
Marktlokations ID: 50202369663
Tarif: PlusStrom GRÜNFAIR
Monatlicher Zahlbetrag: 73,00 EUR (brutto)
"""
        document = Document("Vertragsbestätigung14264231.pdf")
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.category, "Wohnen")
        self.assertEqual(classification.document_type, "Energieverträge")
        self.assertEqual(classification.reason, "Vertragsbestätigung Energie")
        self.assertEqual(data["vendor"], "Fuxx - Die Sparenergie GmbH")
        self.assertEqual(data["contract_number"], "9013775192")
        self.assertEqual(data["delivery_start"], "01.12.2026")
        self.assertEqual(data["monthly_payment"], "73,00")
        self.assertEqual(data["amount"], "73,00")
        self.assertEqual(data["currency"], "EUR")
        self.assertEqual(data["shared_scope"], "family")

        target = StoragePathBuilder(self.structure).build(document)
        self.assertEqual(
            target,
            Path(
                "Wohnen", "Energieverträge", "2026",
                "2026-07-17 - Vertragsbestätigung Strombelieferung - PlusStrom - "
                "Vertrag 9013775192.pdf",
            ),
        )


if __name__ == "__main__":
    unittest.main()
