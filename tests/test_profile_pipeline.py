import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.document_pipeline import DocumentPipeline
from src.document_text_extractor import DocumentNeedsReview
from src.models import Classification, Document, DocumentMetadata
from src.profile_matcher import ProfileAssignment
from src.profile_service import ProfileService
from src.storage_utils import FilesystemStorage, SourceFileBusyError
from tests.test_profile_service import FakeConfig


class NullLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class ProfilePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = FakeConfig(self.root)
        self.config.incoming_root = self.root / "incoming"
        self.config.incoming_root.mkdir()
        self.service = ProfileService(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def _pipeline(self):
        return DocumentPipeline(
            config=self.config,
            sources=[],
            ocr_service=None,
            runtime_storage=FilesystemStorage(self.root / "runtime"),
            archive_storage=FilesystemStorage(self.root / "archive"),
            logger=NullLogger(),
            rules={},
            structure={},
            profile_service=self.service,
        )

    def test_family_member_gets_person_folder(self):
        family = self.service.create_family("Familie Hirte")
        child = self.service.create_person("Henri", "Hirte", ["Mika"], is_minor=True)
        self.service.add_membership(family["id"], child["id"], role="child")
        assignment = ProfileAssignment(family["id"], [child["id"]], 1.0)
        result = self._pipeline()._profile_relative_path(
            family, assignment, Path("Gesundheit", "Arztbrief.pdf")
        )
        self.assertEqual(
            result,
            Path("Henri Mika Hirte", "Gesundheit", "Arztbrief.pdf"),
        )

    def test_shared_family_document_gets_common_folder(self):
        family = self.service.create_family("Familie Hirte")
        assignment = ProfileAssignment(family["id"], [], 1.0)
        result = self._pipeline()._profile_relative_path(
            family, assignment, Path("Wohnen", "Strom.pdf")
        )
        self.assertEqual(
            result,
            Path("Gemeinsame Dokumente", "Wohnen", "Strom.pdf"),
        )

    def test_global_company_storage_adds_company_folder(self):
        company = self.service.create_organization("Hades IT")
        assignment = ProfileAssignment(company["id"], [], 1.0)
        result = self._pipeline()._profile_relative_path(
            company, assignment, Path("Buchhaltung", "Rechnung.pdf")
        )
        self.assertEqual(result, Path("Hades IT", "Buchhaltung", "Rechnung.pdf"))

    def test_custom_company_storage_is_already_the_company_folder(self):
        company = self.service.create_organization("Hades IT")
        self.service.update_profile(company["id"], {
            "routing": {
                "use_global_storage": False,
                "storage_root": str(self.root / "Hades IT"),
            }
        })
        company = self.service.get_profile(company["id"])
        assignment = ProfileAssignment(company["id"], [], 1.0)
        result = self._pipeline()._profile_relative_path(
            company, assignment, Path("Buchhaltung", "Rechnung.pdf")
        )
        self.assertEqual(result, Path("Buchhaltung", "Rechnung.pdf"))

    def test_family_invoice_requires_private_or_business_review(self):
        family = self.service.create_family("Familie Hirte")
        metadata = DocumentMetadata("Buchhaltung", "Eingangsrechnungen")

        self.assertTrue(
            self._pipeline()._requires_invoice_context_review(metadata, family)
        )

    def test_company_invoice_does_not_require_context_review(self):
        company = self.service.create_organization("Hades IT")
        metadata = DocumentMetadata("Buchhaltung", "Eingangsrechnungen")

        self.assertFalse(
            self._pipeline()._requires_invoice_context_review(metadata, company)
        )

    def test_family_invoice_manual_suggestion_prefills_private_purchase_folder(self):
        family = self.service.create_family("Familie Hirte")
        assignment = ProfileAssignment(family["id"], [], 1.0)
        document = Document(self.root / "rechnung.pdf")
        document.extracted_text = "Rechnung"
        classification = Classification("Buchhaltung", 0.9, "Eingangsrechnungen")
        metadata = DocumentMetadata("Buchhaltung", "Eingangsrechnungen")

        suggestion = self._pipeline()._manual_suggestion(
            document,
            classification,
            metadata,
            {"date": "12.07.2026", "vendor": "VY MAYAN"},
            assignment,
        )

        self.assertEqual(suggestion["review_kind"], "invoice_context")
        self.assertEqual(suggestion["invoice_usage"], "private")
        self.assertEqual(
            suggestion["suggested_name"],
            "2026-07-12 - Kaufbeleg - VY MAYAN.pdf",
        )
        self.assertEqual(
            suggestion["destination_parts"],
            ["Anschaffungen und Garantien", "Kaufbelege"],
        )

    def test_uncertain_document_named_invoice_still_gets_context_review(self):
        family = self.service.create_family("Familie Hirte")
        assignment = ProfileAssignment(family["id"], [], 1.0)
        document = Document(self.root / "3617_Sabine_Hirte_Rechnung.pdf")
        document.extracted_text = "Beleg"
        classification = Classification("MANUELL", 0.0, "Unsortiert")
        metadata = DocumentMetadata("MANUELL", "Unsortiert")

        suggestion = self._pipeline()._manual_suggestion(
            document,
            classification,
            metadata,
            {"date": "12.07.2026", "vendor": "VY MAYAN", "amount": "19,90"},
            assignment,
        )

        self.assertEqual(suggestion["review_kind"], "invoice_context")
        self.assertEqual(
            suggestion["suggested_name"],
            "2026-07-12 - Kaufbeleg - VY MAYAN - 19,90.pdf",
        )
        self.assertEqual(
            suggestion["destination_parts"],
            ["Anschaffungen und Garantien", "Kaufbelege"],
        )

    def test_generic_bank_terms_get_discard_warning_but_remain_fileable(self):
        family = self.service.create_family("Familie Hirte")
        assignment = ProfileAssignment(family["id"], [], 1.0)
        document = Document(self.root / "Datenschutzinformation zur Vollmacht.pdf")
        document.extracted_text = (
            "Bedingungen Vollmacht\nKontoübergreifende Vollmacht\n"
            "Bedingungen für die Nutzung des Online-Banking\n"
            "Datenschutzinformationen der Volkswagen Bank GmbH"
        )

        suggestion = self._pipeline()._manual_suggestion(
            document,
            Classification("MANUELL", 0.0, "Unsortiert"),
            DocumentMetadata("MANUELL", "Unsortiert"),
            {"date": "04.10.2022", "currency": "EUR"},
            assignment,
        )

        self.assertEqual(
            suggestion["review_kind"], "general_information_attachment"
        )
        self.assertIn("Verwerfen prüfen", suggestion["review_notice"])
        self.assertEqual(
            suggestion["destination_parts"], ["Finanzen", "Banken und Konten"]
        )

    def test_multiple_payroll_periods_in_one_year_are_complete(self):
        document = Document(self.root / "Sammelabrechnung.pdf")
        document.metadata = DocumentMetadata(
            "Arbeit und Karriere", "Gehaltsabrechnungen"
        )
        document.extracted_data = {
            "employer": "Pflegewerk Köln Nord gGmbH",
            "payroll_period": None,
            "payroll_periods": ["11.2025", "12.2025"],
        }

        self.assertEqual(self._pipeline()._missing_required_data(document), [])

    def test_multiple_payroll_years_still_require_review(self):
        document = Document(self.root / "Sammelabrechnung.pdf")
        document.metadata = DocumentMetadata(
            "Arbeit und Karriere", "Gehaltsabrechnungen"
        )
        document.extracted_data = {
            "employer": "Beispiel GmbH",
            "payroll_period": None,
            "payroll_periods": ["12.2025", "01.2026"],
        }

        self.assertEqual(
            self._pipeline()._missing_required_data(document),
            ["payroll_period_years"],
        )

    def test_family_cash_receipt_prefills_receipt_folder_and_usage_review(self):
        family = self.service.create_family("Familie Hirte")
        assignment = ProfileAssignment(family["id"], [], 1.0)
        document = Document(self.root / "Kassenbon.pdf")
        document.extracted_text = "Kassenbon EDEKA SUMME 6,44"

        suggestion = self._pipeline()._manual_suggestion(
            document,
            Classification("Anschaffungen und Garantien", 0.99, "Kassenbons"),
            DocumentMetadata("Anschaffungen und Garantien", "Kassenbons"),
            {
                "date": "28.07.2026",
                "vendor": "EDEKA AKTIV Markt Gebr. Hein",
                "amount": "6,44",
                "currency": "EUR",
            },
            assignment,
        )

        self.assertEqual(suggestion["review_kind"], "invoice_context")
        self.assertEqual(suggestion["document_label"], "Kassenbon")
        self.assertEqual(suggestion["invoice_usage"], "private")
        self.assertEqual(
            suggestion["destination_parts"],
            ["Anschaffungen und Garantien", "Kassenbons"],
        )
        self.assertEqual(
            suggestion["suggested_name"],
            "2026-07-28 - Kassenbon - EDEKA AKTIV Markt Gebr. Hein - 6,44 EUR.pdf",
        )

    def test_storage_failure_is_not_reported_as_success(self):
        source = self.root / "invoice.pdf"
        source.write_bytes(b"data")
        with patch("src.storage_utils.shutil.move", side_effect=PermissionError("locked")):
            with self.assertRaises(OSError):
                FilesystemStorage(self.root).store(source, "archive", source.name)
        self.assertTrue(source.exists())

    def test_open_source_is_reported_as_busy_and_left_in_place(self):
        source = self.root / "open-in-viewer.pdf"
        source.write_bytes(b"data")
        with patch("src.storage_utils.os.rename", side_effect=PermissionError("locked")):
            with self.assertRaises(SourceFileBusyError):
                FilesystemStorage.ensure_movable(source)
        self.assertTrue(source.exists())

    def test_profile_mail_subfolder_provides_a_verified_hint(self):
        company = self.service.create_organization("Beispiel GmbH")
        account = self.service.save_email_account(company["id"], {
            "imap_server": "imap.example.test",
            "username": "office@example.test",
        })
        source = self.config.incoming_root / company["id"] / account["id"] / "invoice.pdf"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"pdf")
        self.assertEqual(self._pipeline()._mail_profile_hint(source), company["id"])

    def test_valid_but_unreadable_format_goes_to_manual_review(self):
        source = self.root / "incoming" / "Ohne Vorschau.pages"
        source.write_bytes(b"pages")

        class Extractor:
            @staticmethod
            def extract_text(_path):
                raise DocumentNeedsReview("Pages-Vorschau fehlt")

        pipeline = self._pipeline()
        pipeline.ocr = Extractor()
        pipeline._process(Document(source))

        self.assertFalse(source.exists())
        self.assertTrue((self.root / "runtime" / "manual_sort" / source.name).exists())


if __name__ == "__main__":
    unittest.main()
