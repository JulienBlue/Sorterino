import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.config import Config
from src.reporting import DailyReportManager
from src.gui.settings_page import SettingsPage


class SettingsPageTests(unittest.TestCase):
    def test_last_settings_category_is_restored(self):
        owner = type("Owner", (), {"_settings_category": "advanced"})()
        self.assertEqual(SettingsPage.remembered_category(owner), "advanced")

    def test_invalid_remembered_settings_category_falls_back_to_general(self):
        owner = type("Owner", (), {"_settings_category": "missing"})()
        self.assertEqual(SettingsPage.remembered_category(owner), "general")

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
