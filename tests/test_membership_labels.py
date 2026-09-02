import unittest

from src.gui.profile_window import _membership_label


class MembershipLabelTests(unittest.TestCase):
    def test_translates_internal_family_roles(self):
        self.assertEqual(
            _membership_label("family", {"is_minor": True, "personal": {}}, {"role": "child"}),
            "Kind",
        )
        self.assertEqual(
            _membership_label("family", {"is_minor": False}, {"role": "member"}),
            "Elternteil",
        )
        self.assertEqual(
            _membership_label("family", {}, {"role": "parent"}),
            "Elternteil",
        )

    def test_uses_gender_appropriate_child_labels(self):
        self.assertEqual(
            _membership_label(
                "family", {"is_minor": True, "personal": {"gender": "male"}}, {"role": "child"}
            ),
            "Sohn",
        )
        self.assertEqual(
            _membership_label(
                "family", {"is_minor": True, "personal": {"gender": "female"}}, {"role": "child"}
            ),
            "Tochter",
        )
        self.assertEqual(
            _membership_label(
                "family", {"is_minor": True, "personal": {"gender": "diverse"}}, {"role": "child"}
            ),
            "Kind",
        )

    def test_uses_gender_appropriate_parent_labels_for_current_and_legacy_roles(self):
        self.assertEqual(
            _membership_label(
                "family", {"personal": {"gender": "male"}}, {"role": "parent"}
            ),
            "Vater",
        )
        self.assertEqual(
            _membership_label(
                "family", {"personal": {"gender": "female"}}, {"role": "member"}
            ),
            "Mutter",
        )
        self.assertEqual(
            _membership_label(
                "family", {"personal": {"gender": "diverse"}}, {"role": "parent"}
            ),
            "Elternteil",
        )

    def test_uses_gender_appropriate_extended_family_roles(self):
        self.assertEqual(
            _membership_label(
                "family", {"personal": {"gender": "male"}}, {"role": "sibling"}
            ),
            "Bruder",
        )
        self.assertEqual(
            _membership_label(
                "family", {"personal": {"gender": "female"}}, {"role": "grandparent"}
            ),
            "Großmutter",
        )

    def test_translates_internal_organization_roles_and_positions(self):
        self.assertEqual(
            _membership_label("organization", {}, {"role": "employee"}),
            "Mitarbeiter/in",
        )
        self.assertEqual(
            _membership_label("organization", {}, {"role": "owner"}),
            "Inhaber/in",
        )
        self.assertEqual(
            _membership_label(
                "organization", {}, {"role": "employee", "position": "CEO"}
            ),
            "Geschäftsführung",
        )

    def test_keeps_user_defined_german_positions(self):
        self.assertEqual(
            _membership_label(
                "organization",
                {},
                {"role": "employee", "position": "Buchhaltung"},
            ),
            "Buchhaltung",
        )

    def test_uses_gender_appropriate_employee_labels(self):
        self.assertEqual(
            _membership_label(
                "organization", {"personal": {"gender": "male"}}, {"role": "employee"}
            ),
            "Mitarbeiter",
        )
        self.assertEqual(
            _membership_label(
                "organization", {"personal": {"gender": "female"}}, {"role": "employee"}
            ),
            "Mitarbeiterin",
        )
        self.assertEqual(
            _membership_label(
                "organization", {"personal": {"gender": "diverse"}}, {"role": "employee"}
            ),
            "Mitarbeiter:in",
        )


if __name__ == "__main__":
    unittest.main()
