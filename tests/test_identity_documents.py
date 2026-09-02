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


class IdentityDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads(
            Path("assets/templates/template.rules.json").read_text(encoding="utf-8")
        )

    def _analyze(self, filename, text):
        document = Document(source_path=filename)
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data
        return document, classification, data

    def test_marriage_certificate_uses_marriage_date_and_registry(self):
        document, classification, data = self._analyze(
            "Heiratsurkunde - Hirte.pdf",
            """
Eheurkunde
Standesamt Köln
Registernummer Niederschrift über die Eheschließung E 3091/2022
Ort, Tag der Eheschließung Köln, 12.08.2022
1. Ehemann Julien Blue Hirte
2. Ehefrau Sabine Schirmer
""",
        )

        self.assertEqual(classification.document_type, "Eheurkunde")
        self.assertEqual(data["date"], "12.08.2022")
        self.assertEqual(data["register_number"], "E 3091/2022")
        self.assertEqual(data["registry_office"], "Köln")
        self.assertIsNone(data["amount"])

        path = StoragePathBuilder({
            "Identität und Urkunden": {"Eheurkunde": {}}
        }).build(document)
        self.assertEqual(
            path.name,
            "2022-08-12 - Eheurkunde - Standesamt Köln.pdf",
        )

    def test_identity_card_keeps_birth_date_out_of_document_date(self):
        document, classification, data = self._analyze(
            "Personalausweis - Hirte.pdf",
            """
IDENTITY CARD
L2CW38C59
Name/Surname/Nom HIRTE
Vornamen/Given names/Prénoms JULIEN BLUE
Geburtstag/Date of birth 04.05.1990
Geburtsort/Place of birth BERLIN
Gültig bis/Date of expiry 11.01.2028
IDD<<L2CW38C59<<<<<<<<<<<<
HIRTE<<JULIEN<BLUE<<<<<<<<<<<<
""",
        )

        self.assertEqual(classification.document_type, "Identitätsdokumente")
        self.assertEqual(data["document_kind"], "Personalausweis")
        self.assertIsNone(data["date"])
        self.assertEqual(data["date_of_birth"], "04.05.1990")
        self.assertEqual(data["valid_until"], "11.01.2028")
        self.assertEqual(data["document_number"], "L2CW38C59")
        self.assertEqual(data["holder_name"], "Julien Blue Hirte")

        path = StoragePathBuilder({
            "Identität und Urkunden": {"Identitätsdokumente": {}}
        }).build(document)
        self.assertEqual(path.name, "Personalausweis - gültig bis 2028-01-11.pdf")

    def test_birth_certificate_has_its_own_destination(self):
        _document, classification, _data = self._analyze(
            "Geburtsurkunde.pdf",
            "Geburtsurkunde Standesamt Köln Geburtenregister Tag der Geburt",
        )

        self.assertEqual(classification.document_type, "Geburtsurkunden")

    def test_certificate_of_conduct_ignores_birth_date_as_amount(self):
        document, classification, data = self._analyze(
            "Führungszeugnis.pdf",
            """
Bundesamt für Justiz
Bonn, den 12.03.2024
Geburtsdatum/Date of birth/Date de naissance 17.11.1986
Verarbeitungsdaten: 332345864/02956290/12032024190058000/
Führungszeugnis Certificate of Conduct Extrait du casier judiciaire
Keine Eintragung (No record/Néant)
""",
        )

        self.assertEqual(classification.category, "Behörden und Leistungen")
        self.assertEqual(classification.document_type, "Führungszeugnisse")
        self.assertEqual(data["date"], "12.03.2024")
        self.assertEqual(data["vendor"], "Bundesamt für Justiz")
        self.assertEqual(data["record_status"], "Keine Eintragung")
        self.assertEqual(
            data["processing_reference"],
            "332345864/02956290/12032024190058000/",
        )
        self.assertIsNone(data["amount"])
        self.assertIsNone(data["currency"])
        self.assertIsNone(data["invoice_number"])

        path = StoragePathBuilder({
            "Behörden und Leistungen": {"Führungszeugnisse": {"{year}": {}}}
        }).build(document)
        self.assertEqual(
            path,
            Path(
                "Behörden und Leistungen/Führungszeugnisse/2024/"
                "2024-03-12 - Führungszeugnis - Bundesamt für Justiz.pdf"
            ),
        )


if __name__ == "__main__":
    unittest.main()
