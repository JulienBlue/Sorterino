import unittest

from src.document_analyzer import DocumentAnalyzer
from src.models import Document
from src.storage_utils import StoragePathBuilder


class _Logger:
    def debug(self, *_args):
        pass

    def warning(self, *_args):
        pass


class PayrollStatementTests(unittest.TestCase):
    TEXT = """
Abrechnung der Brutto/Netto-Bezüge für Mai 2023 22.05.2023 Blatt 1
Entyre GmbH*Großer Burstah 25*20457 Hamburg
Sabine Hirte
Gesamt-Brutto
Steuer/Sozialversicherung 3.040,50
Netto-Verdienst
Verdienstbescheinigung Netto-Bezüge/Netto-Abzüge 2.061,34
Bank SV-AG-Anteil Zus. AG-Kosten Gesamtkosten Auszahlungsbetrag
Konto DE87 1101 0100 2991 1938 93 619,36 1.908,34
"""

    def _analyze(self):
        document = Document(source_path="Sabine_Hirte_Entgeltabrechnung_05-2023.pdf")
        document.mark_analyzed(self.TEXT)
        result = DocumentAnalyzer([], {}, _Logger()).analyze(document)
        return document, result

    def test_classifies_and_extracts_datev_payroll_statement(self):
        _document, (classification, _metadata, data) = self._analyze()

        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(classification.document_type, "Gehaltsabrechnungen")
        self.assertEqual(data["date"], "22.05.2023")
        self.assertEqual(data["payroll_period"], "05.2023")
        self.assertEqual(data["payroll_periods"], ["05.2023"])
        self.assertEqual(data["employer"], "Entyre GmbH")
        self.assertEqual(data["gross_amount"], "3.040,50")
        self.assertEqual(data["net_amount"], "2.061,34")
        self.assertEqual(data["payout_amount"], "1.908,34")
        self.assertEqual(data["currency"], "EUR")
        self.assertIsNone(data["invoice_number"])
        self.assertIsNone(data["description"])

    def test_builds_payroll_folder_and_month_based_filename(self):
        document, (classification, metadata, data) = self._analyze()
        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data
        structure = {
            "Arbeit und Karriere": {
                "Gehaltsabrechnungen": {"{year}": {}}
            }
        }

        path = StoragePathBuilder(structure).build(document)

        self.assertEqual(
            str(path),
            str(
                __import__("pathlib").Path(
                    "Arbeit und Karriere",
                    "Gehaltsabrechnungen",
                    "2023",
                    "2023-05 - Entgeltabrechnung - Entyre GmbH.pdf",
                )
            ),
        )

    def test_classifies_correction_payroll_without_datev_heading(self):
        text = """
Theater Hagen gGmbH
Herr Julien Blue Hirte
Korrektur Gehaltsabrechnung 7/2023 (für 8/2023)
Gesamtbrutto 1.740,00
Steuerbrutto 1.818,30
Lohnsteuer (12 Steuertage) 492,46
Nettoverdienst 874,33
Differenz für Folgemonate EUR 796,03
Im ELStAM Verfahren wurden für den Monat 07/2023 folgende Merkmale übermittelt
"""
        document = Document(source_path="Gehaltsabrechnung Theater Hagen.pdf")
        document.mark_analyzed(text)
        classification, _metadata, data = DocumentAnalyzer([], {}, _Logger()).analyze(document)
        self.assertEqual(classification.document_type, "Gehaltsabrechnungen")
        self.assertEqual(data["payroll_period"], "07.2023")
        self.assertEqual(data["employer"], "Theater Hagen gGmbH")
        self.assertEqual(data["document_kind"], "Korrektur Gehaltsabrechnung")
        self.assertEqual(data["payout_amount"], "796,03")

    def test_uses_unambiguous_year_month_from_payroll_filename(self):
        text = """
Entgeltabrechnung
Pflegewerk Köln Nord gGmbH
01.04.2025
Gesamt-Brutto 3.758,68
Netto-Verdienst 2.781,30
Lohnsteuer 440,00
"""
        document = Document(
            source_path="2025-04 - Entgeltabrechnung - Pflegewerk Köln Nord gGmbH.pdf"
        )
        document.mark_analyzed(text)

        classification, _metadata, data = DocumentAnalyzer([], {}, _Logger()).analyze(document)

        self.assertEqual(classification.document_type, "Gehaltsabrechnungen")
        self.assertEqual(data["payroll_period"], "04.2025")

    def test_extracts_correction_payout_when_ocr_splits_the_label(self):
        text = """
Theater Hagen gGmbH
Korrektur Gehaltsabrechnung 7/2023
Nettoverdienst 874,33
Auszahlungsbetrag Lohnsteuer 492,46
EUR 796,03
Differenz für Folgemonate
Auszahlung
796,03
Im ELStAM Verfahren wurden für den Monat 07/2023 Merkmale übermittelt
"""
        document = Document(source_path="Korrektur Gehaltsabrechnung.pdf")
        document.mark_analyzed(text)

        _classification, _metadata, data = DocumentAnalyzer(
            [], {}, _Logger()
        ).analyze(document)

        self.assertEqual(data["payout_amount"], "796,03")
        self.assertEqual(data["amount"], "796,03")

    def test_datev_month_values_ignore_cumulative_totals_and_ocr_spacing(self):
        cases = (
            (
                "April",
                """
Abrechnung der Brutto/Netto-Bezüge für April 2023 21.04.2023
Entyre GmbH
Gesamt-Brutto
Steuer/Sozialversicherung 2.896,12
Netto-Verdienst 1.980,04
Verdienstbescheinigung
Gesamt-Brutto 2.896,12
Auszahlungsbetrag
Konto DE87 1101 0100 2991 1938 93 589,95 1.827, 04
""",
                "2.896,12",
                "1.827,04",
            ),
            (
                "Juli",
                """
Abrechnung der Brutto/Netto-Bezüge für Juli 2023 24.07.2023
Entyre GmbH
Gesamt-Brutto
Steuer/Sozialversicherung 3.052,11
Netto-Verdienst 2.058,66
Verdienstbescheinigung
Gesamt-Brutto 12.144,86
Auszahlungsbetrag 1.916, 66
""",
                "3.052,11",
                "1.916,66",
            ),
            (
                "November",
                """
Abrechnung der Brutto/Netto-Bezüge für November 2023 22.11.2023
Entyre GmbH
Netto-Verdienst 2.134,34
Verdienstbescheinigung
Gesamt-Brutto 24.326,18 SV-Brutto 23.969,86
Gesamt-Brutto
3.047,59
Steuerrechtliche Abzüge
Auszahlungsbetrag 1.814,18
""",
                "3.047,59",
                "1.814,18",
            ),
            (
                "Januar",
                """
Abrechnung der Brutto/Netto-Bezüge für Januar 2024 22.01.2024
Entyre GmbH
Netto-Verdienst 2.180,57
Verdienstbescheinigung
Gesamt-Brutto 3.095,12 SV-Brutto 2.916,96
Gesamt-Brutto
3.095,12
Steuerrechtliche Abzüge
Auszahlungsbetrag 1.860,41
""",
                "3.095,12",
                "1.860,41",
            ),
        )

        analyzer = DocumentAnalyzer([], {}, _Logger())
        for label, text, expected_gross, expected_payout in cases:
            with self.subTest(label=label):
                data = analyzer._extract_payroll_statement(text)
                expected_date = {
                    "April": "21.04.2023",
                    "Juli": "24.07.2023",
                    "November": "22.11.2023",
                    "Januar": "22.01.2024",
                }[label]
                self.assertEqual(data["date"], expected_date)
                self.assertEqual(data["gross_amount"], expected_gross)
                self.assertEqual(data["payout_amount"], expected_payout)
                self.assertEqual(data["amount"], expected_payout)

    def test_multiple_payroll_pages_create_one_period_range(self):
        text = """
Lohn- und Gehaltsabrechnung 12.2025
Pflegewerk Köln Nord gGmbH
Geburtsdatum 17.11.1986 Eintrittsdatum 01.04.2025
Sabine Hirte
GESAMTBRUTTO: 5.250,41
NETTOVERDIENST: 3.755,59
Lohn- und Gehaltsabrechnung 11.2025
1. Rückrechnung: 12.2025
Pflegewerk Köln Nord gGmbH
GESAMTBRUTTO: 5.250,41
NETTOVERDIENST: 3.773,59
"""
        document = Document(source_path="Sammelabrechnung.pdf")
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            [], {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.document_type, "Gehaltsabrechnungen")
        self.assertIsNone(data["payroll_period"])
        self.assertEqual(data["payroll_periods"], ["11.2025", "12.2025"])
        self.assertIsNone(data["date"])

        structure = {
            "Arbeit und Karriere": {
                "Gehaltsabrechnungen": {"{year}": {}}
            }
        }
        self.assertEqual(
            StoragePathBuilder(structure).build(document),
            __import__("pathlib").Path(
                "Arbeit und Karriere", "Gehaltsabrechnungen", "2025",
                "2025-11 bis 2025-12 - Entgeltabrechnungen - "
                "Pflegewerk Köln Nord gGmbH.pdf",
            ),
        )


if __name__ == "__main__":
    unittest.main()
