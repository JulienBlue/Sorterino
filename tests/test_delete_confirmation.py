import unittest

from src.gui.profile_window import _delete_confirmation_message


class DeleteConfirmationTests(unittest.TestCase):
    def test_file_deletion_warning_says_documents_are_deleted(self):
        message = _delete_confirmation_message("das Profil", "delete_files")
        self.assertIn("Dokumente werden GELÖSCHT", message)
        self.assertNotIn("Dokumente bleiben erhalten", message)

    def test_configuration_only_warning_says_documents_are_retained(self):
        message = _delete_confirmation_message("das Profil", "keep_files")
        self.assertIn("Dokumente bleiben erhalten", message)
        self.assertNotIn("Dokumente werden GELÖSCHT", message)

    def test_membership_warning_preserves_person_and_documents(self):
        message = _delete_confirmation_message("die Zuordnung", "membership_only")
        self.assertIn("Nur diese Zuordnung wird entfernt", message)
        self.assertIn("Dokumente bleiben erhalten", message)


if __name__ == "__main__":
    unittest.main()
