import unittest
from pathlib import Path

from src.gui.main_window import MainWindow


class ProfileNavigationTests(unittest.TestCase):
    def test_profiles_menu_opens_profile_manager_directly(self):
        calls = []

        class Window:
            show_profiles = lambda self, selected_id=None, add_history=True: calls.append(
                (selected_id, add_history)
            )

        MainWindow.show_page(Window(), "profiles", add_history=False)

        self.assertEqual(calls, [(None, False)])

    def test_return_to_profiles_discards_nested_profile_steps(self):
        rendered = []

        class Window:
            _back_stack = [
                ("main", "overview"),
                ("custom", object(), "profiles"),
                ("custom", object(), "profiles"),
            ]
            _forward_stack = [("main", "documents")]
            _render_view = lambda self, view: rendered.append(view)
            _show_success_banner = lambda self, message: None

        window = Window()
        MainWindow.return_to_profiles(window, "family_123")

        self.assertEqual(window._back_stack, [("main", "overview")])
        self.assertEqual(window._forward_stack, [])
        self.assertEqual(rendered[0][0], "custom")
        self.assertEqual(rendered[0][2], "profiles")

    def test_new_family_or_organization_continues_with_detail_editor(self):
        opened = []

        class Window:
            service = object()
            _return_to_profiles = object()
            _open = lambda self, *args: opened.append(args)

        handled = __import__(
            "src.gui.profile_window", fromlist=["ProfileWindow"]
        ).ProfileWindow._edit_new_profile(Window(), "organization_123")

        self.assertTrue(handled)
        self.assertEqual(opened[0][2], "organization_123")

    def test_creation_wizard_dispatches_to_the_existing_profile_flows(self):
        opened = []

        class Window:
            service = object()
            _return_to_profiles = object()
            _edit_new_profile = object()
            _open = lambda self, *args: opened.append(args)

        profile_module = __import__(
            "src.gui.profile_window", fromlist=["ProfileWindow"]
        )
        profile_module.ProfileWindow._start_profile_creation(Window(), "individual")
        profile_module.ProfileWindow._start_profile_creation(Window(), "family")
        profile_module.ProfileWindow._start_profile_creation(Window(), "organization")

        self.assertIs(opened[0][0], profile_module.IndividualDialog)
        self.assertIs(opened[1][0], profile_module.NewProfilePage)
        self.assertEqual(opened[1][2], "family")
        self.assertEqual(opened[2][2], "organization")

    def test_technical_profile_editors_are_not_exposed_in_profile_overview(self):
        source = Path("src/gui/profile_window.py").read_text(encoding="utf-8")
        self.assertNotIn("Regeln anpassen", source)
        self.assertNotIn("Struktur anpassen", source)
        self.assertNotIn("_open_profile_override", source)


if __name__ == "__main__":
    unittest.main()
