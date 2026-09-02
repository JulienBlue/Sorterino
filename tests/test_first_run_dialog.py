import unittest
from unittest.mock import patch

from src.gui.main_window import MainWindow


class FirstRunDialogTests(unittest.TestCase):
    def test_welcome_dialog_is_created_without_standard_storage(self):
        created = []

        class Config:
            def get(self, key, default=None):
                return None

        class Window:
            _initial_storage_prompted = False
            _initial_storage_dialog = None
            config = Config()

        window = Window()
        with patch("src.gui.main_window.InitialStorageDialog", side_effect=lambda owner: created.append(owner) or object()):
            MainWindow._ensure_initial_storage(window)

        self.assertTrue(window._initial_storage_prompted)
        self.assertEqual(created, [window])

    def test_welcome_dialog_is_skipped_when_storage_exists(self):
        class Config:
            def get(self, key, default=None):
                return "D:/Dokumente" if key == "user_path" else default

        class Window:
            _initial_storage_prompted = False
            _initial_storage_dialog = None
            config = Config()

        window = Window()
        with patch("src.gui.main_window.InitialStorageDialog") as dialog:
            MainWindow._ensure_initial_storage(window)

        dialog.assert_not_called()
        self.assertFalse(window._initial_storage_prompted)


if __name__ == "__main__":
    unittest.main()
