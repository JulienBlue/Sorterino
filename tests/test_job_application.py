import json
import unittest
from pathlib import Path

from src.document_analyzer import DocumentAnalyzer
from src.models import Document
from src.storage_utils import StoragePathBuilder


class _Logger:
    def debug(self, _message):
        pass

    def warning(self, _message):
        pass


class JobApplicationTests(unittest.TestCase):
    def test_application_uses_closing_date_and_prospective_employer(self):
        rules = json.loads(Path("assets/templates/template.rules.json").read_text(encoding="utf-8"))
        document = Document(source_path=Path("Anschreiben Sabine Hirte.pdf"))
        document.mark_analyzed(
            "BEWERBUNG ALS PFLEGEBERATERIN IM GROSSRAUM KÖLN\n"
            "Sehr geehrte Damen und Herren,\n"
            "Hiermit bewerbe ich mich zum nächstmöglichen Zeitpunkt bei der Agentur\n"
            "für Haushaltshilfe auf die Stelle als Pflegeberaterin.\n"
            "Am 25.01.2024 wurde mir gekündigt.\n"
            "Mit freundlichen Grüßen\nSabine Hirte\nKöln 10.02.2024"
        )

        classification, metadata, data = DocumentAnalyzer(rules, {}, _Logger()).analyze(document)

        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(classification.document_type, "Bewerbungen")
        self.assertEqual(data["date"], "10.02.2024")
        self.assertEqual(data["prospective_employer"], "Agentur für Haushaltshilfe")
        self.assertEqual(data["job_title"], "Pflegeberaterin")
        self.assertIsNone(data["amount"])

        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data
        structure = {"Arbeit und Karriere": {"Bewerbungen": {"{year}": {}}}}
        path = StoragePathBuilder(structure).build(document)
        self.assertEqual(
            str(path),
            str(Path("Arbeit und Karriere/ Bewerbungen".replace("/ ", "/")) / "2024" /
                "2024-02-10 - Bewerbungsanschreiben - Pflegeberaterin - Agentur für Haushaltshilfe.pdf"),
        )

    def test_application_extracts_job_title_from_heading_without_location(self):
        data = DocumentAnalyzer._extract_job_application(
            "BEWERBUNG ALS SOFTWAREENTWICKLERIN IM GROSSRAUM BERLIN\n"
            "Mit freundlichen Grüßen\nBerlin 01.03.2026"
        )

        self.assertEqual(data["job_title"], "Softwareentwicklerin")

    def test_cover_letter_without_heading_is_still_classified_conservatively(self):
        rules = json.loads(Path("assets/templates/template.rules.json").read_text(encoding="utf-8"))
        document = Document(source_path=Path("Anschreiben - Hirte, Julien Blue.pdf"))
        document.mark_analyzed(
            "Sehr geehrte Damen und Herren, nach meiner Abschlussprüfung suche ich den "
            "Einstieg ins Berufsleben. Als Berufseinsteiger möchte ich mich weiterentwickeln. "
            "Im Praktikum automatisierte ich Prozesse, bei denen es unter anderem um "
            "Datenverarbeitung ging. "
            "Ich würde mich freuen, wenn Sie meine Unterlagen für die ausgeschriebene Stelle "
            "berücksichtigen und mich zu einem persönlichen Gespräch einladen. "
            "Mit freundlichen Grüßen, Julien Blue Hirte. Köln, 07.08.2026"
        )

        classification, _metadata, data = DocumentAnalyzer(rules, {}, _Logger()).analyze(document)

        self.assertEqual(classification.document_type, "Bewerbungen")
        self.assertEqual(data["date"], "07.08.2026")
        self.assertIsNone(data["prospective_employer"])
        self.assertIsNone(data["job_title"])


if __name__ == "__main__":
    unittest.main()
