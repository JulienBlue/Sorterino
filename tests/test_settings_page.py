import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.config import Config
from src.gui.settings_page import matching_settings_category
from src.reporting import DailyReportManager


class SettingsPageTests(unittest.TestCase):
    def test_search_finds_user_facing_categories_and_synonyms(self):
        self.assertEqual(matching_settings_category("Daily Report"), "reports")
        self.assertEqual(matching_settings_category("OCR"), "recognition")
        self.assertEqual(matching_settings_category("Postfach"), "email")
        self.assertEqual(matching_settings_category("Backup"), "storage")
        self.assertIsNone(matching_settings_category("Steuersatz"))

    def test_daily_report_stays_enabled_for_existing_and_fresh_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            self.assertTrue(config.get("daily_report_enabled"))
            self.assertTrue(config.get("automatic_update_checks"))
            self.assertEqual(config.get("update_channel"), "beta")
            config.set("daily_report_enabled", False)
            reloaded = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            self.assertFalse(reloaded.get("daily_report_enabled"))

    def test_manual_report_is_visible_without_consuming_scheduled_run(self):
        with tempfile.TemporaryDirectory() as temp:
            reporter = DailyReportManager(Path(temp))
            reporter.generate_daily_report()
            self.assertEqual(reporter.get_latest_report_date(), date.today().isoformat())
            self.assertIsNone(reporter.get_last_report_date())


if __name__ == "__main__":
    unittest.main()
