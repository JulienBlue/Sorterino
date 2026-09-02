import unittest

from src.document_analyzer import DocumentAnalyzer
from src.models import Document
from src.storage_utils import StoragePathBuilder


class _Logger:
    def debug(self, *_args):
        pass

    def warning(self, *_args):
        pass


class EmploymentCertificateTests(unittest.TestCase):
    TEXT = """
Bundesagentur für Arbeit
Arbeitsbescheinigung
Nach § 312 Drittes Buch Sozialgesetzbuch (SGB III)
A. Angaben zum Arbeitgeber
CP care Pflegeexperten GmbH
B. Angaben zur Arbeitnehmerin/zum Arbeitnehmer
C. Angaben zum Beschäftigungsverhältnis
"""

    def _analyze(self, filename="Arbeitsbescheinigung CP Care.pdf"):
        document = Document(source_path=filename)
        document.mark_analyzed(self.TEXT)
        classification, metadata, data = DocumentAnalyzer([], {}, _Logger()).analyze(document)
        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data
        return document, classification, data

    def test_recognizes_official_employment_certificate(self):
        _document, classification, data = self._analyze()

        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(classification.document_type, "Bescheinigungen")
        self.assertEqual(classification.reason, "Arbeitsbescheinigung")
        self.assertEqual(data["document_kind"], "Arbeitsbescheinigung")
        self.assertEqual(data["employer"], "CP care Pflegeexperten GmbH")

    def test_builds_descriptive_filename_without_inventing_a_date(self):
        document, _classification, _data = self._analyze()
        structure = {
            "Arbeit und Karriere": {"Bescheinigungen": {"{year}": {}}}
        }

        path = StoragePathBuilder(structure).build(document)

        self.assertEqual(
            path.name,
            "Arbeitsbescheinigung - CP care Pflegeexperten GmbH.pdf",
        )
        self.assertEqual(path.parent.name, "Bescheinigungen")

    def test_prefers_labeled_employer_field_with_combined_legal_form(self):
        text = """
Arbeitsbescheinigung
Angaben zu den betrieblichen Daten des Arbeitgebers:
Name: Bäckerei Brinkhege GmbH & Co.KG
Straße: Mindener Str. 8
Angaben zur Arbeitnehmerin / zum Arbeitnehmer
Angaben zum Beschäftigungsverhältnis
Bundesagentur für Arbeit
"""
        data = DocumentAnalyzer([], {}, _Logger())._extract_employment_certificate(
            text,
            "Arbeitsbescheinigung Brinkhege.pdf",
        )

        self.assertEqual(data["employer"], "Bäckerei Brinkhege GmbH & Co. KG")


if __name__ == "__main__":
    unittest.main()
