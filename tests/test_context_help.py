import tempfile
import unittest
from pathlib import Path

from src.config import Config
from src.gui.help_window import HELP_CONTENT, diagnose
from src.profile_service import ProfileService


class ContextHelpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = Config(
            app_data_root=self.root / "appdata",
            legacy_home=self.root / "home",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_all_work_areas_have_context_help(self):
        expected = {
            "overview", "documents", "profiles", "person", "profile_edit",
            "profile_new", "membership", "mail", "mail_edit", "manual_review",
            "settings", "advanced", "json_editor", "logs",
        }
        self.assertTrue(expected.issubset(HELP_CONTENT))

    def test_missing_storage_and_profile_produce_actions(self):
        status, issues = diagnose(self.config, "overview")
        self.assertEqual(status, "Sorterino benötigt deine Aufmerksamkeit")
        self.assertTrue(any("Standard-Dokumentenspeicher" in issue for issue in issues))
        self.assertTrue(any("kein Profil" in issue for issue in issues))

    def test_ready_state_is_reported(self):
        documents = self.root / "documents"
        documents.mkdir()
        self.config.set("user_path", documents)
        ProfileService(self.config).create_family("Familie Test")
        status, issues = diagnose(self.config, "profiles")
        self.assertEqual(issues, [])
        self.assertEqual(status, "Sorterino ist einsatzbereit")

    def test_deleted_custom_profile_folder_is_recreatable(self):
        documents = self.root / "documents"
        documents.mkdir()
        self.config.set("user_path", documents)
        service = ProfileService(self.config)
        company = service.create_organization("Hades IT")
        deleted_company_folder = self.root / "external" / "Hades IT"
        deleted_company_folder.parent.mkdir()
        service.update_profile(company["id"], {
            "routing": {
                "use_global_storage": False,
                "storage_root": str(deleted_company_folder),
            }
        })

        status, issues = diagnose(self.config, "profiles")

        self.assertFalse(deleted_company_folder.exists())
        self.assertEqual(issues, [])
        self.assertEqual(status, "Sorterino ist einsatzbereit")


if __name__ == "__main__":
    unittest.main()
