import json
import unittest
from pathlib import Path

from src.document_analyzer import DocumentAnalyzer
from src.document_pipeline import DocumentPipeline
from src.models import Document
from src.profile_matcher import ProfileAssignment
from src.storage_utils import StoragePathBuilder


class _Logger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class HousingDefectTests(unittest.TestCase):
    TEXT = """
Chronologische Dokumentation des Mangels an der Warmwasserversorgung
Wohnung Nötzold, Schöne Aussicht 1, 51149 Köln
22.03.2025 – Erste Kontaktaufnahme mit der Hausverwaltung wegen Ablagerungen.
31.10.2025 – Offizielle Wasserprobenentnahme durch RheinEnergie.
03.06.2026 – Filtereinbau verzögert sich bis voraussichtlich Ende Juni 2026.
Aktueller Stand: Problem besteht seit März 2025 fort. Empfohlene Maßnahmen noch nicht umgesetzt.
"""

    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads(
            Path("assets/templates/template.rules.json").read_text(encoding="utf-8")
        )

    def test_classifies_housing_defect_and_uses_latest_entry_date(self):
        document = Document("Dokumentation des Mangels an der Warmwasserversorgung.docx")
        document.mark_analyzed(self.TEXT)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = data

        self.assertEqual(classification.category, "Wohnen")
        self.assertEqual(classification.document_type, "Instandhaltung")
        self.assertEqual(data["document_kind"], "Mängeldokumentation")
        self.assertEqual(data["date"], "03.06.2026")
        self.assertEqual(data["documentation_period_start"], "22.03.2025")
        self.assertEqual(data["documentation_period_end"], "03.06.2026")
        self.assertEqual(data["defect_subject"], "Warmwasserversorgung")
        self.assertEqual(data["property_address"], "Schöne Aussicht 1, 51149 Köln")
        self.assertEqual(data["defect_status"], "besteht fort")
        self.assertEqual(data["shared_scope"], "family")
        self.assertIsNone(data["amount"])
        self.assertIsNone(data["currency"])

        path = StoragePathBuilder({
            "Wohnen": {"Instandhaltung": {"{year}": {}}}
        }).build(document)
        self.assertEqual(
            path,
            Path(
                "Wohnen/Instandhaltung/2026/"
                "2026-06-03 - Mängeldokumentation - Warmwasserversorgung.docx"
            ),
        )

    def test_family_scope_overrides_single_author_folder(self):
        pipeline = DocumentPipeline.__new__(DocumentPipeline)
        pipeline.profile_service = None
        family = {
            "type": "family",
            "display_name": "Familie Hirte",
            "archive_name": "Gemeinsame Dokumente",
            "routing": {},
        }
        assignment = ProfileAssignment("family_1", ["person_julien"], 1.0)

        result = pipeline._profile_relative_path(
            family,
            assignment,
            Path("Wohnen/Instandhaltung/Dokument.docx"),
            {"shared_scope": "family"},
        )

        self.assertEqual(
            result,
            Path("Gemeinsame Dokumente/Wohnen/Instandhaltung/Dokument.docx"),
        )


if __name__ == "__main__":
    unittest.main()
