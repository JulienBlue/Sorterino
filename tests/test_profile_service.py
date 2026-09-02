import json
import tempfile
import unittest
from pathlib import Path

from src.profile_service import ProfileService, ProfileValidationError


class FakeConfig:
    def __init__(self, root):
        self.profiles_path = Path(root) / "profiles.json"
        self.logs_root = Path(root) / "logs"
        self._values = {"company_profile": {}, "user_path": str(Path(root) / "global")}
        self.raw = {
            "company_profile": {},
            "targets": {"manual": "manual_sort", "error": "error"},
            "profile_system": {"minimum_assignment_confidence": 0.8},
        }

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value
        self.raw[key] = value


class ProfileServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = FakeConfig(self.temp.name)
        self.service = ProfileService(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def test_creates_family_child_and_membership(self):
        family = self.service.create_family("Familie Hirte")
        child = self.service.create_person(
            "Henri", "Hirte", ["Mika"], is_minor=True
        )
        membership = self.service.add_membership(
            family["id"], child["id"], role="child"
        )

        self.assertEqual(child["display_name"], "Henri Mika Hirte")
        self.assertEqual(child["name"]["second_first_name"], "Mika")
        self.assertIn("Henri Mika Hirte", child["matching"]["name_variants"])
        self.assertIn("Henri Hirte", child["matching"]["name_variants"])
        self.assertEqual(child["routing"]["structure_template"], "child")
        self.assertEqual(membership["role"], "child")
        self.assertEqual(len(self.service.profile_members(family["id"])), 1)

    def test_birth_date_calculates_minor_status_instead_of_manual_flag(self):
        minor = self.service.create_person(
            "Henri", "Hirte", date_of_birth="10.08.2010", is_minor=False
        )
        adult = self.service.create_person(
            "Julien", "Hirte", date_of_birth="04.05.1990", is_minor=True
        )

        self.assertTrue(minor["is_minor"])
        self.assertEqual(minor["routing"]["structure_template"], "child")
        self.assertFalse(adult["is_minor"])
        self.assertEqual(adult["routing"]["structure_template"], "adult")

    def test_same_person_can_belong_to_family_and_company(self):
        person = self.service.create_person("Julien", "Hirte", ["Blue"])
        family = self.service.create_family("Familie Hirte")
        company = self.service.create_organization("Beispiel GmbH")

        self.service.add_membership(family["id"], person["id"], role="parent")
        self.service.add_membership(
            company["id"], person["id"], role="owner", position="Geschäftsführer"
        )

        self.assertEqual(len(self.service.profile_members(family["id"])), 1)
        self.assertEqual(len(self.service.profile_members(company["id"])), 1)
        self.assertEqual(len(self.service.list_persons()), 1)

    def test_family_partner_relationship_is_contextual_and_cleaned_with_membership(self):
        first = self.service.create_person("Julien", "Hirte")
        second = self.service.create_person("Sabine", "Hirte")
        family = self.service.create_family("Familie Hirte")
        self.service.add_membership(family["id"], first["id"], role="partner")
        self.service.add_membership(family["id"], second["id"], role="partner")

        relationship = self.service.set_partner_relationship(
            family["id"], first["id"], second["id"], "married"
        )
        self.assertEqual(relationship["person_ids"], [first["id"], second["id"]])

        self.service.remove_membership(family["id"], second["id"])
        self.assertEqual(self.service.get_profile(family["id"])["partner_relationships"], [])

    def test_deleting_partner_removes_stale_family_relationship(self):
        first = self.service.create_person("Julien", "Hirte")
        second = self.service.create_person("Sabine", "Hirte")
        family = self.service.create_family("Familie Hirte")
        self.service.add_membership(family["id"], first["id"], role="partner")
        self.service.add_membership(family["id"], second["id"], role="partner")
        self.service.set_partner_relationship(family["id"], first["id"], second["id"])

        self.service.delete_person(first["id"])

        self.assertEqual(self.service.get_profile(family["id"])["partner_relationships"], [])

    def test_person_can_have_individual_family_and_company_contexts(self):
        person = self.service.create_person("Julien", "Hirte")
        individual = self.service.create_individual(person["id"])
        family = self.service.create_family("Familie Hirte")
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(family["id"], person["id"], role="parent")
        self.service.add_membership(company["id"], person["id"], position="Geschäftsführer")
        self.assertEqual(individual["person_id"], person["id"])
        self.assertEqual(len(self.service.list_persons()), 1)

    def test_delete_profile_removes_configuration_but_keeps_people(self):
        person = self.service.create_person("Sabine", "Hirte")
        family = self.service.create_family("Familie Hirte")
        self.service.add_membership(family["id"], person["id"], role="parent")

        self.service.delete_profile(family["id"])

        self.assertIsNone(self.service.get_profile(family["id"]))
        self.assertIsNotNone(self.service.get_person(person["id"]))

    def test_delete_person_removes_memberships_and_private_profile(self):
        person = self.service.create_person("Julien", "Hirte")
        private_profile = self.service.create_individual(person["id"])
        family = self.service.create_family("Familie Hirte")
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(family["id"], person["id"], role="parent")
        self.service.add_membership(company["id"], person["id"], position="Geschäftsführer")

        self.service.delete_person(person["id"])

        self.assertIsNone(self.service.get_person(person["id"]))
        self.assertIsNone(self.service.get_profile(private_profile["id"]))
        self.assertEqual(self.service.profile_members(family["id"]), [])
        self.assertEqual(self.service.profile_members(company["id"]), [])

    def test_deleting_only_individual_profile_keeps_family_membership(self):
        person = self.service.create_person("Sabine", "Hirte")
        private_profile = self.service.create_individual(person["id"])
        family = self.service.create_family("Familie Hirte")
        self.service.add_membership(family["id"], person["id"], role="parent")

        self.service.delete_profile(private_profile["id"])

        self.assertIsNone(self.service.get_profile(private_profile["id"]))
        self.assertIsNotNone(self.service.get_person(person["id"]))
        self.assertEqual(
            [member["id"] for member, _membership in self.service.profile_members(family["id"])],
            [person["id"]],
        )

    def test_orphaned_employee_is_promoted_to_private_profile(self):
        person = self.service.create_person("Mara", "Muster")
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(company["id"], person["id"], position="Buchhaltung")
        self.service.delete_profile(company["id"])

        promoted = self.service.promote_unassigned_persons()

        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["type"], "individual")
        self.assertEqual(promoted[0]["person_id"], person["id"])

    def test_promoting_orphans_does_not_duplicate_private_profiles(self):
        person = self.service.create_person("Mara", "Muster")
        private_profile = self.service.create_individual(person["id"])

        promoted = self.service.promote_unassigned_persons()

        self.assertEqual(promoted, [])
        self.assertEqual(self.service.individual_profile_for(person["id"])["id"], private_profile["id"])

    def test_only_one_active_individual_profile_per_person(self):
        person = self.service.create_person("Sabine", "Hirte")
        self.service.create_individual(person["id"])
        with self.assertRaises(ProfileValidationError):
            self.service.create_individual(person["id"])

    def test_rejects_duplicate_active_profile_names(self):
        self.service.create_family("Familie Hirte")
        with self.assertRaises(ProfileValidationError):
            self.service.create_family("familie hirte")

    def test_rejects_duplicate_name_during_update(self):
        first = self.service.create_family("Familie Hirte")
        second = self.service.create_organization("Hirte GmbH")
        with self.assertRaises(ProfileValidationError):
            self.service.update_profile(
                second["id"], {"display_name": first["display_name"]}
            )

    def test_registry_is_valid_json_after_save(self):
        self.service.create_person("Sabine", "Hirte")
        with open(self.config.profiles_path, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        self.assertEqual(saved["persons"][0]["display_name"], "Sabine Hirte")

    def test_rejects_profile_folder_path_traversal(self):
        family = self.service.create_family("Familie Hirte")
        with self.assertRaises(ProfileValidationError):
            self.service.update_profile(
                family["id"], {"routing": {"archive_folder": "..\\Andere Daten"}}
            )

    def test_legacy_company_data_can_be_migrated_explicitly(self):
        self.config._values["company_profile"] = {
            "name": "Beispiel GmbH",
            "person": {"first_name": "Julien", "last_name": "Hirte"},
            "address": {"street": "Musterweg 1", "zip": "12345", "city": "Berlin"},
            "contact": {"email": "info@example.test", "phone": ""},
            "financial": {"tax_id": "DE123456789"},
            "keywords": ["beispiel"],
        }
        self.assertTrue(self.service.legacy_migration_available())
        result = self.service.migrate_legacy_company_profile()
        self.assertEqual(result["organization"]["display_name"], "Beispiel GmbH")
        self.assertEqual(result["person"]["display_name"], "Julien Hirte")
        self.assertFalse(self.service.legacy_migration_available())

    def test_profile_can_have_multiple_email_accounts_without_passwords(self):
        company = self.service.create_organization("Beispiel GmbH")
        first = self.service.save_email_account(company["id"], {
            "label": "Rechnungen",
            "imap_server": "imap.example.test",
            "username": "invoice@example.test",
            "initial_lookback_days": 7,
        })
        second = self.service.save_email_account(company["id"], {
            "label": "Allgemein",
            "imap_server": "imap.example.test",
            "username": "office@example.test",
        })
        self.assertEqual(len(self.service.list_email_accounts(company["id"])), 2)
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotIn("password", first)
        self.assertEqual(first["initial_lookback_days"], 7)

    def test_profile_can_use_a_separate_storage_root(self):
        company = self.service.create_organization("Beispiel GmbH")
        custom_root = Path(self.temp.name) / "company-archive"
        self.service.update_profile(company["id"], {
            "routing": {
                "use_global_storage": False,
                "storage_root": str(custom_root),
            }
        })
        self.assertEqual(self.service.resolve_storage_root(company["id"]), custom_root)

    def test_company_can_store_managing_director_without_person_profile(self):
        company = self.service.create_organization("Beispiel GmbH")
        self.service.update_profile(company["id"], {
            "management": {
                "managing_director": {
                    "first_name": "Julien",
                    "second_first_name": "Blue",
                    "last_name": "Hirte",
                }
            }
        })
        self.service.reload()

        director = self.service.get_profile(company["id"])["management"]["managing_director"]
        self.assertEqual(director["first_name"], "Julien")
        self.assertEqual(director["second_first_name"], "Blue")
        self.assertEqual(director["last_name"], "Hirte")
        self.assertEqual(self.service.list_persons(), [])

    def test_family_profile_can_use_a_separate_storage_root(self):
        family = self.service.create_family("Familie Hirte")
        custom_root = Path(self.temp.name) / "family-archive"
        self.service.update_profile(family["id"], {
            "routing": {
                "use_global_storage": False,
                "storage_root": str(custom_root),
            }
        })
        self.service.reload()
        stored = self.service.get_profile(family["id"])
        self.assertFalse(stored["routing"]["use_global_storage"])
        self.assertEqual(stored["routing"]["storage_root"], str(custom_root))
        self.assertEqual(self.service.resolve_storage_root(family["id"]), custom_root)

    def test_family_identifiers_are_replaced_by_joint_tax_numbers(self):
        family = self.service.create_family("Familie Hirte")
        family["household_identifiers"] = {
            "broadcasting_contribution_number": "123456789",
            "landlord_or_tenant_numbers": ["MIET-1"],
        }
        self.service.update_profile(family["id"], {
            "household_identifiers": {"tax_numbers": ["12/345/67890"]}
        })
        self.assertEqual(
            self.service.get_profile(family["id"])["household_identifiers"],
            {"tax_numbers": ["1234567890"]},
        )

    def test_ibans_are_normalized_and_validated(self):
        family = self.service.create_family("Familie Hirte")
        self.service.update_profile(family["id"], {
            "household_identifiers": {
                "tax_numbers": [],
                "ibans": ["de89 3704 0044 0532 0130 00"],
            }
        })
        self.assertEqual(
            self.service.get_profile(family["id"])["household_identifiers"]["ibans"],
            ["DE89370400440532013000"],
        )
        with self.assertRaises(ProfileValidationError):
            self.service.update_profile(family["id"], {
                "household_identifiers": {"ibans": ["DE001234"]}
            })

    def test_profile_without_override_uses_global_storage(self):
        family = self.service.create_family("Familie Hirte")
        self.assertEqual(
            self.service.resolve_storage_root(family["id"]),
            Path(self.config.get("user_path")),
        )


if __name__ == "__main__":
    unittest.main()
