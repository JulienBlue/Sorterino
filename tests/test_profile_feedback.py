import unittest

from src.gui.profile_window import _profile_saved_message


class ProfileFeedbackTests(unittest.TestCase):
    def test_success_message_uses_visible_profile_type_and_name(self):
        self.assertEqual(
            _profile_saved_message({"type": "family", "display_name": "Hirte"}),
            "Familie „Hirte“ wurde erfolgreich gespeichert.",
        )
        self.assertEqual(
            _profile_saved_message({"type": "organization", "display_name": "Beispiel GmbH"}),
            "Firma „Beispiel GmbH“ wurde erfolgreich gespeichert.",
        )
        self.assertEqual(
            _profile_saved_message({"type": "individual", "display_name": "Sabine Hirte"}),
            "Privatperson „Sabine Hirte“ wurde erfolgreich gespeichert.",
        )


if __name__ == "__main__":
    unittest.main()
