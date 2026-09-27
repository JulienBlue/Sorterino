import unittest
from pathlib import Path

from src.version import APP_VERSION


class InstallerContractTests(unittest.TestCase):
    def test_installer_version_matches_application_version(self):
        script = Path("installer.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define MyAppVersion "v{APP_VERSION}"', script)

    def test_uninstaller_has_single_safe_options_page(self):
        script = Path("installer.iss").read_text(encoding="utf-8")
        self.assertIn('Name: "{app}\\Sorterino_Uninstaller"', script)
        self.assertIn('/SILENT /SUPPRESSMSGBOXES', script)
        self.assertIn("function ShowUninstallOptions: Boolean;", script)
        self.assertIn("Dokumentarchive bleiben erhalten", script)
        self.assertIn("Sorterino - Eingang bleibt erhalten", script)
        self.assertIn("Sorterino - Backups bleibt erhalten", script)
        self.assertNotIn("Lokale Sorterino-Programmdaten ebenfalls löschen?", script)


if __name__ == "__main__":
    unittest.main()
