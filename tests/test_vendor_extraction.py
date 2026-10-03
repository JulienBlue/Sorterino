import unittest

from src.document_analyzer import DocumentAnalyzer


class _Logger:
    def debug(self, *_args):
        pass

    def warning(self, *_args):
        pass


class VendorExtractionTests(unittest.TestCase):
    def test_combines_split_logo_and_ignores_ag_inside_table_heading(self):
        text = """
IIK
COMPUTER GMBH
ITK Computer GmbH
Robert-Koch-Str. 7-17
52499 Baesweiler
Firma
Hades IT GmbH
Am Frankenturm 5
Rechnung Nr. 9850545
Menge Bezeichnung ArtNr. EUR
Gesamtbetrag EUR 1368,08
"""
        company_profile = {"name": "Hades IT GmbH"}

        vendor = DocumentAnalyzer([], company_profile, _Logger())._extract_vendor(text)

        self.assertEqual(vendor, "ITK Computer GmbH")

    def test_outgoing_invoice_does_not_use_a_slogan_as_customer(self):
        text = """
Hades IT GmbH
Lösungen finden und leicht
Julien Blue Hirte
Musterstraße 1
Hades IT GmbH
Rechnung vom 10.09.2026
"""
        company_profile = {"name": "Hades IT GmbH"}

        vendor = DocumentAnalyzer([], company_profile, _Logger())._extract_vendor(text)

        self.assertEqual(vendor, "Julien Blue Hirte")

    def test_invoice_slogan_with_period_is_not_used_as_vendor(self):
        text = """
Lösungen finden und leicht fühlen.
Natalie Eich
Systemische Beratung und Coaching
Rechnungsnummer: 01-09
Rechnungsdatum: 10.09.2026
"""

        vendor = DocumentAnalyzer([], {}, _Logger())._extract_vendor(text)

        self.assertEqual(vendor, "Natalie Eich")

    def test_recipient_can_be_excluded_when_resolving_invoice_vendor(self):
        text = """
Lösungen finden und leicht fühlen.
Julien Blue Hirte
Schöne Aussicht 1
Natalie Eich
Systemische Beratung und Coaching
Rechnungsnummer: 01-09
"""

        vendor = DocumentAnalyzer([], {}, _Logger())._extract_vendor(
            text, excluded_names=["Julien Blue Hirte"]
        )

        self.assertEqual(vendor, "Natalie Eich")

    def test_invoice_letterhead_before_recipient_is_used_as_vendor(self):
        text = """
Lil' Leo | Kalkarer Straße 10 | 50733 Köln
Sabine Hirte
Schöne Aussicht 1
Rechnung 32337
"""

        vendor = DocumentAnalyzer([], {}, _Logger())._extract_vendor(
            text, excluded_names=["Sabine Hirte"]
        )

        self.assertEqual(vendor, "Lil Leo")


if __name__ == "__main__":
    unittest.main()
