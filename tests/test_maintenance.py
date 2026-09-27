import tempfile
import unittest
from pathlib import Path

from src.config import Config
from src.maintenance import cleanup_rebuildable_state


class MaintenanceTests(unittest.TestCase):
    def test_cleanup_resets_rebuildable_state_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            preserved = {
                config.settings_path: config.settings_path.read_bytes(),
                config.oauth_clients_path: config.oauth_clients_path.read_bytes(),
                config.profiles_root / "profile.json": b"profile",
                config.persons_root / "person.json": b"person",
                config.state_root / "mail_import_state.json": b"mail-state",
                config.incoming_root / "pending.pdf": b"document",
                config.app_root / "credentials" / "microsoft_mail.bin": b"credential",
            }
            for path, content in preserved.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

            removable = (
                config.logs_root / "sorterino.log",
                config.app_root / "updates" / "setup.exe",
                config.state_root / "manual-review" / "suggestion.json",
                config.database_path,
                config.app_root / ".settings.json.old.tmp",
            )
            for path in removable:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"temporary")

            cleanup_rebuildable_state(config)

            for path, content in preserved.items():
                self.assertEqual(path.read_bytes(), content)
            for path in removable:
                self.assertFalse(path.exists())

    def test_cleanup_rejects_targets_outside_appdata_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = Config(app_data_root=root / "appdata", legacy_home=root / "home")
            outside = root / "outside.log"
            outside.write_text("keep", encoding="utf-8")
            config.logs_root = outside
            with self.assertRaises(ValueError):
                cleanup_rebuildable_state(config)
            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
