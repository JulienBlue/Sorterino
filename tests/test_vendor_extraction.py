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


if __name__ == "__main__":
    unittest.main()
