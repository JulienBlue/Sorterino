import json
import tempfile
import unittest
from pathlib import Path

from src.manual_filing import ManualFilingService
from src.constants import BACKUP_DIRECTORY_NAME
from src.gui.manual_review_window import available_years
from src.config import Config
from src.profile_service import ProfileService, ProfileValidationError
from tests.test_profile_service import FakeConfig
from src.manual_review_suggestions import (
    ManualReviewSuggestionStore,
    best_destination_label,
    likely_general_information_attachment,
    person_id_from_filename,
    suggested_year,
    tentative_destination,
)


class ManualFilingTests(unittest.TestCase):
    def test_manual_review_suggestion_roundtrip_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            document = config.manual_root / "scan.pdf"
            document.write_bytes(b"pdf")
            store = ManualReviewSuggestionStore(config)
            store.save(document, {"profile_id": "family_1", "year": "2024"})
            self.assertEqual(store.load(document)["profile_id"], "family_1")
            store.remove(document)
            self.assertEqual(store.load(document), {})

    def test_discard_removes_only_document_inside_review_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            profiles = ProfileService(config)
            document = config.manual_root / "agb.pdf"
            document.write_bytes(b"pdf")
            kept = config.incoming_root / "keep.pdf"
            kept.write_bytes(b"pdf")
            service = ManualFilingService(config, profiles)

            removed = service.discard_document(document)

            self.assertEqual(removed, document.resolve())
            self.assertFalse(document.exists())
            self.assertTrue(kept.exists())

    def test_discard_rejects_document_outside_review_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            profiles = ProfileService(config)
            document = config.incoming_root / "keep.pdf"
            document.write_bytes(b"pdf")

            with self.assertRaises(ProfileValidationError):
                ManualFilingService(config, profiles).discard_document(document)
            self.assertTrue(document.exists())

    def test_suggestion_helpers_choose_year_and_deepest_matching_folder(self):
        self.assertEqual(suggested_year({"date": "28.03.2024"}), "2024")
        self.assertEqual(suggested_year({"payroll_period": "07.2023"}), "2023")
        destinations = {
            "Arbeit und Karriere": Path("Arbeit und Karriere"),
            "Arbeit und Karriere › Bescheinigungen": Path("Arbeit und Karriere", "Bescheinigungen"),
            "Buchhaltung": Path("Buchhaltung"),
        }
        self.assertEqual(
            best_destination_label(destinations, {
                "category": "Arbeit und Karriere",
                "document_type": "Bescheinigungen",
                "destination_parts": ["Arbeit und Karriere", "Bescheinigungen"],
            }),
            "Arbeit und Karriere › Bescheinigungen",
        )

    def test_uncertain_termination_gets_review_only_destination_hint(self):
        self.assertEqual(
            tentative_destination(filename="Kuendigung Debeka HR_Hirte_Sabine.pdf"),
            ("Versicherungen", "Kündigungen"),
        )
        self.assertEqual(
            tentative_destination("Kündigung meiner Versicherung"),
            ("Versicherungen", "Kündigungen"),
        )
        self.assertEqual(
            tentative_destination(filename="Beratungsvertrag_systemische-Einzelberatung.pdf"),
            ("Verträge und Abonnements", "Allgemeine Verträge"),
        )
        self.assertEqual(
            tentative_destination(filename="Rückbildungskurs - Teilnahmebescheinigung.pdf"),
            ("Gesundheit", "Kurse und Therapien"),
        )
        members = [
            ({"id": "sabine", "name": {"first_name": "Sabine", "last_name": "Hirte"}}, {}),
            ({"id": "julien", "name": {"first_name": "Julien", "last_name": "Hirte"}}, {}),
        ]
        self.assertEqual(
            person_id_from_filename(members, "Kuendigung_Debeka_HR_Hirte_Sabine.pdf"),
            "sabine",
        )

    def test_general_terms_attachment_is_only_marked_for_review(self):
        self.assertTrue(likely_general_information_attachment(
            "Bedingungen Vollmacht\nBedingungen für die konto-/depotbezogene "
            "Nutzung des Online-Banking\nDatenschutzinformationen der Bank",
            "Datenschutzinformation zur Vollmacht und Bedingungswerk.pdf",
        ))
        self.assertFalse(likely_general_information_attachment(
            "Hiermit bevollmächtige ich Sabine Hirte zur Abholung.",
            "Vollmacht Sabine.pdf",
        ))

    def test_year_choices_end_at_current_year_and_expand_with_calendar(self):
        self.assertEqual(available_years(2026)[:3], ["2026", "2025", "2024"])
        self.assertNotIn("2027", available_years(2026))
        self.assertEqual(available_years(2027)[0], "2027")

    def test_files_family_document_into_selected_member_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FakeConfig(root)
            config.structure_path = root / "structure.json"
            config.structure_path.write_text(json.dumps({
                "templates": {"family": {"Gesundheit": {"Arztberichte": {}}}}
            }), encoding="utf-8")
            profiles = ProfileService(config)
            family = profiles.create_family("Familie Hirte")
            child = profiles.create_person("Henri", "Hirte", ["Mika"], is_minor=True)
            profiles.add_membership(family["id"], child["id"], role="child")
            source = root / "manual" / "arztbrief.pdf"
            source.parent.mkdir()
            source.write_bytes(b"pdf")
            final = Path(ManualFilingService(config, profiles).file_document(
                source,
                family["id"],
                Path("Gesundheit", "Arztberichte"),
                child["id"],
            ))
            self.assertEqual(
                final,
                Path(config.get("user_path"), "Henri Mika Hirte", "Gesundheit", "Arztberichte", "arztbrief.pdf"),
            )
            self.assertTrue(final.exists())

    def test_files_with_selected_year_and_changed_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FakeConfig(root)
            config.structure_path = root / "structure.json"
            config.structure_path.write_text(json.dumps({
                "templates": {"family": {"Arbeit und Karriere": {"Bescheinigungen": {"{year}": {}}}}}
            }), encoding="utf-8")
            profiles = ProfileService(config)
            family = profiles.create_family("Familie Hirte")
            person = profiles.create_person("Sabine", "Hirte")
            profiles.add_membership(family["id"], person["id"], role="member")
            source = root / "manual" / "scan.pdf"
            source.parent.mkdir()
            source.write_bytes(b"pdf")

            final = Path(ManualFilingService(config, profiles).file_document(
                source,
                family["id"],
                Path("Arbeit und Karriere", "Bescheinigungen"),
                person["id"],
                year="2023",
                new_name="Arbeitsbescheinigung - CP Çare.pdf",
            ))

            self.assertEqual(
                final,
                Path(
                    config.get("user_path"),
                    "Sabine Hirte",
                    "Arbeit und Karriere",
                    "Bescheinigungen",
                    "2023",
                    "Arbeitsbescheinigung - CP Çare.pdf",
                ),
            )
            self.assertTrue(final.exists())
            backup = Path(
                config.get("user_path"), BACKUP_DIRECTORY_NAME, "Familie Hirte", "scan.pdf"
            )
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_bytes(), b"pdf")

    def test_rejects_invalid_year_and_filename(self):
        with self.assertRaises(ProfileValidationError):
            ManualFilingService._year("23")
        with self.assertRaises(ProfileValidationError):
            ManualFilingService._filename(Path("scan.pdf"), "../anderer Ordner")

    def test_rejects_unsafe_custom_folder_paths(self):
        for value in ("../Privat", "Ordner//Unterordner", "CON", "Ordner:Name"):
            with self.subTest(value=value), self.assertRaises(ProfileValidationError):
                ManualFilingService._folder_parts(value)

    def test_custom_destination_is_persisted_only_in_selected_person_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            config.set_standard_storage(root / "documents")
            profiles = ProfileService(config)
            family = profiles.create_family("Familie Hirte")
            first = profiles.create_person("Julien", "Hirte")
            second = profiles.create_person("Sabine", "Hirte")
            profiles.add_membership(family["id"], first["id"], role="parent")
            profiles.add_membership(family["id"], second["id"], role="parent")
            filing = ManualFilingService(config, profiles)

            target = filing.add_destination(
                family["id"], Path("Arbeit und Karriere"), "Fortbildungen/Zertifikate", first["id"]
            )

            self.assertEqual(target, Path("Arbeit und Karriere", "Fortbildungen", "Zertifikate"))
            self.assertIn(target, filing.destinations(family["id"], first["id"]))
            self.assertNotIn(target, filing.destinations(family["id"], second["id"]))
            override = config.profiles_root / family["id"] / "persons" / first["id"] / "structure.override.json"
            self.assertTrue(override.exists())

    def test_files_outside_structure_with_changed_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FakeConfig(root)
            profiles = ProfileService(config)
            source = root / "Eingang" / "scan.pdf"
            source.parent.mkdir()
            source.write_bytes(b"neues Dokument")
            destination = root / "Eigener Ordner"
            destination.mkdir()

            final = Path(ManualFilingService(config, profiles).file_document_outside_structure(
                source,
                destination,
                new_name="Eigener Dokumentname",
            ))

            self.assertEqual(final, destination / "Eigener Dokumentname.pdf")
            self.assertTrue(final.exists())
            self.assertFalse(source.exists())
            backup = Path(config.get("user_path"), BACKUP_DIRECTORY_NAME, "scan.pdf")
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_bytes(), b"neues Dokument")

    def test_external_filing_uses_selected_profile_in_central_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FakeConfig(root)
            profiles = ProfileService(config)
            family = profiles.create_family("Familie Hirte")
            profiles.update_profile(family["id"], {
                "routing": {
                    "use_global_storage": False,
                    "storage_root": str(root / "Familie Hirte"),
                }
            })
            source = root / "Eingang" / "scan.pdf"
            source.parent.mkdir()
            source.write_bytes(b"profilbezogenes Backup")
            destination = root / "Freie Ablage"
            destination.mkdir()

            filing = ManualFilingService(config, profiles)
            filing.file_document_outside_structure(
                source,
                destination,
                profile_id=family["id"],
            )

            backup = Path(
                config.get("user_path"), BACKUP_DIRECTORY_NAME, "Familie Hirte", "scan.pdf"
            )
            self.assertTrue(backup.exists())
            self.assertFalse((root / "Familie Hirte" / BACKUP_DIRECTORY_NAME).exists())

    def test_private_tax_receipt_is_filed_in_tax_year_evidence_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            config.set_standard_storage(root / "documents")
            profiles = ProfileService(config)
            family = profiles.create_family("Familie Hirte")
            person = profiles.create_person("Sabine", "Hirte")
            profiles.add_membership(family["id"], person["id"], role="parent")
            source = config.manual_root / "rechnung.pdf"
            source.write_bytes(b"pdf")
            filing = ManualFilingService(config, profiles)

            final = Path(filing.file_document(
                source,
                family["id"],
                Path("Anschaffungen und Garantien", "Kaufbelege"),
                person["id"],
                year="2026",
                tax_receipt=True,
            ))

            self.assertEqual(
                final,
                root / "documents" / "Sabine Hirte" / "Finanzamt und Steuern"
                / "Einkommensteuer" / "2026" / "02 Belege" / "Sonstige Belege"
                / "rechnung.pdf",
            )

    def test_adult_profiles_offer_private_purchase_receipts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            config.set_standard_storage(root / "documents")
            profiles = ProfileService(config)
            person = profiles.create_person("Julien", "Hirte")
            profile = profiles.create_individual(person["id"])

            destinations = ManualFilingService(config, profiles).destinations(
                profile["id"], person["id"]
            )

            self.assertIn(
                Path("Anschaffungen und Garantien", "Kaufbelege"),
                destinations,
            )

    def test_external_filing_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FakeConfig(root)
            profiles = ProfileService(config)
            source = root / "scan.pdf"
            source.write_bytes(b"neu")
            destination = root / "Ziel"
            destination.mkdir()
            existing = destination / "Dokument.pdf"
            existing.write_bytes(b"alt")

            final = Path(ManualFilingService(config, profiles).file_document_outside_structure(
                source,
                destination,
                new_name="Dokument.pdf",
            ))

            self.assertEqual(existing.read_bytes(), b"alt")
            self.assertEqual(final, destination / "Dokument (1).pdf")
            self.assertEqual(final.read_bytes(), b"neu")


if __name__ == "__main__":
    unittest.main()
