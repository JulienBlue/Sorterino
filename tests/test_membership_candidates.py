import tempfile
import unittest

from src.gui.profile_window import (
    _all_people_assigned_message,
    _available_people_for_profile,
)
from src.profile_service import ProfileService
from tests.test_profile_service import FakeConfig


class MembershipCandidateTests(unittest.TestCase):
    def test_excludes_people_already_assigned_to_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ProfileService(FakeConfig(temp_dir))
            family = service.create_family("Familie Hirte")
            assigned = service.create_person("Sabine", "Hirte")
            available = service.create_person("Julien", "Hirte")
            service.add_membership(family["id"], assigned["id"], role="parent")

            candidates = _available_people_for_profile(service, family["id"])

            self.assertEqual([person["id"] for person in candidates], [available["id"]])

    def test_empty_state_messages_are_context_specific_and_clear(self):
        family_message = _all_people_assigned_message("family")
        organization_message = _all_people_assigned_message("organization")

        self.assertIn("dieser Familie", family_message)
        self.assertIn("neue Person", family_message)
        self.assertIn("Firma oder Organisation", organization_message)
        self.assertIn("neue Person", organization_message)


if __name__ == "__main__":
    unittest.main()
