import tempfile
import unittest
from pathlib import Path

from src.profile_matcher import ProfileMatcher
from src.profile_service import ProfileService
from tests.test_profile_service import FakeConfig


class ProfileMatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = ProfileService(FakeConfig(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_assigns_child_to_only_family_context(self):
        family = self.service.create_family("Familie Hirte")
        child = self.service.create_person("Henri", "Hirte", ["Mika"], is_minor=True)
        self.service.add_membership(family["id"], child["id"], role="child")
        result = ProfileMatcher(self.service).match("Arztbrief für Henri Mika Hirte")
        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(result.person_ids, [child["id"]])

    def test_matches_name_printed_in_separate_form_fields(self):
        family = self.service.create_family("Familie Hirte")
        person = self.service.create_person("Julien Blue", "Hirte")
        self.service.add_membership(family["id"], person["id"], role="member")

        result = ProfileMatcher(self.service).match(
            "Name: Hirte   Vorname: Julien Blue   Geburtsdatum: 04.05.1990"
        )

        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(result.person_ids, [person["id"]])
        self.assertIn("Personenname in Formularfeldern", result.matched_by)

    def test_name_matching_uses_later_close_occurrences_from_signature(self):
        family = self.service.create_family("Familie Hirte")
        person = self.service.create_person("Julien Blue", "Hirte")
        self.service.add_membership(family["id"], person["id"], role="member")

        result = ProfileMatcher(self.service).match(
            "JULIEN BLUE " + ("Lebenslauf und Erfahrungen " * 20) +
            " HIRTE " + ("Bewerbungstext " * 20) + " Julien Blue Hirte"
        )

        self.assertEqual(result.person_ids, [person["id"]])

    def test_does_not_assign_on_family_name_alone(self):
        family = self.service.create_family("Familie Hirte")
        person = self.service.create_person("Julien Blue", "Hirte")
        self.service.add_membership(family["id"], person["id"], role="member")

        self.assertIsNone(ProfileMatcher(self.service).match("Brief an Herrn Hirte"))

    def test_shared_household_address_does_not_assign_every_family_member(self):
        family = self.service.create_family("Familie Hirte")
        people = [
            self.service.create_person("Sabine", "Hirte"),
            self.service.create_person("Julien Blue", "Hirte"),
            self.service.create_person("Henri", "Hirte", ["Mika"]),
        ]
        address = {
            "street": "Schöne Aussicht",
            "house_number": "1",
            "postal_code": "51149",
            "city": "Köln",
        }
        for person in people:
            self.service.update_person(person["id"], {"address": address})
            self.service.add_membership(family["id"], person["id"], role="member")

        result = ProfileMatcher(self.service).match(
            "Bewerbung von Sabine Hirte, Schöne Aussicht 1, 51149 Köln"
        )

        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(result.person_ids, [people[0]["id"]])

    def test_rejects_ambiguous_person_in_private_and_company_context(self):
        person = self.service.create_person("Julien", "Hirte")
        self.service.create_individual(person["id"])
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(company["id"], person["id"], position="Geschäftsführer")
        self.assertIsNone(ProfileMatcher(self.service).match("Brief an Julien Hirte"))

    def test_company_identifier_resolves_ambiguous_person(self):
        person = self.service.create_person("Julien", "Hirte")
        self.service.create_individual(person["id"])
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(company["id"], person["id"], position="Geschäftsführer")
        self.service.update_profile(company["id"], {
            "registration": {"vat_identification_number": "DE123456789"}
        })
        result = ProfileMatcher(self.service).match("Julien Hirte Beispiel GmbH DE123456789")
        self.assertEqual(result.profile_id, company["id"])

    def test_unambiguous_filename_resolves_content_with_former_employer(self):
        family = self.service.create_family("Familie Hirte")
        person = self.service.create_person("Julien Blue", "Hirte")
        self.service.add_membership(family["id"], person["id"], role="member")
        self.service.create_organization("Seraph")

        result = ProfileMatcher(self.service).match_document(
            "Im Praktikum bei der Seraph IT GmbH sammelte ich Erfahrung.",
            "Anschreiben - Hirte, Julien Blue.pdf",
        )

        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(result.person_ids, [person["id"]])
        self.assertIn("Eindeutiger Dateiname", result.matched_by)

    def test_personal_name_and_email_win_over_mentioned_former_employer(self):
        family = self.service.create_family("Familie Hirte")
        person = self.service.create_person("Julien Blue", "Hirte")
        self.service.update_person(person["id"], {
            "contacts": {
                "emails": [{"type": "private", "value": "julien@example.de"}],
            },
        })
        self.service.add_membership(family["id"], person["id"], role="member")
        self.service.create_organization("Seraph")

        result = ProfileMatcher(self.service).match_document(
            "Julien Blue Hirte, julien@example.de. Im Praktikum bei Seraph sammelte ich Erfahrung.",
            "2026-08-07 - Bewerbungsanschreiben.pdf",
        )

        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(result.person_ids, [person["id"]])
        self.assertIn("Persönlicher Absender vor erwähnter Firma", result.matched_by)

    def test_joint_tax_number_identifies_family_profile(self):
        family = self.service.create_family("Familie Hirte")
        self.service.update_profile(family["id"], {
            "household_identifiers": {"tax_numbers": ["12/345/67890"]}
        })
        result = ProfileMatcher(self.service).match(
            "Bescheid zur Einkommensteuer, Steuernummer 12/345/67890"
        )
        self.assertEqual(result.profile_id, family["id"])

    def test_iban_identifies_family_profile(self):
        family = self.service.create_family("Familie Hirte")
        self.service.update_profile(family["id"], {
            "household_identifiers": {
                "tax_numbers": [],
                "ibans": ["DE89370400440532013000"],
            }
        })
        result = ProfileMatcher(self.service).match(
            "SEPA-Mandat für DE89 3704 0044 0532 0130 00"
        )
        self.assertEqual(result.profile_id, family["id"])

    def test_linked_spouses_strengthen_joint_family_assignment(self):
        first = self.service.create_person("Julien Blue", "Hirte")
        second = self.service.create_person("Sabine", "Hirte")
        self.service.create_individual(first["id"])
        self.service.create_individual(second["id"])
        family = self.service.create_family("Familie Hirte")
        self.service.add_membership(family["id"], first["id"], role="partner")
        self.service.add_membership(family["id"], second["id"], role="partner")
        self.service.set_partner_relationship(family["id"], first["id"], second["id"], "married")

        result = ProfileMatcher(self.service).match(
            "Gemeinsamer Versicherungsvertrag für die Ehegatten Julien Blue Hirte und Sabine Hirte"
        )

        self.assertEqual(result.profile_id, family["id"])
        self.assertEqual(set(result.person_ids), {first["id"], second["id"]})
        self.assertIn("Verknüpfte Ehe-/Lebenspartner", result.matched_by)

    def test_company_contact_and_employee_function_support_company_context(self):
        person = self.service.create_person("Mara", "Muster")
        self.service.create_individual(person["id"])
        company = self.service.create_organization("Beispiel GmbH")
        self.service.add_membership(
            company["id"], person["id"], position="Buchhaltung", department="Finanzen"
        )
        self.service.update_profile(company["id"], {
            "contacts": {"emails": [{"type": "general", "value": "rechnung@beispiel.de"}]}
        })

        result = ProfileMatcher(self.service).match(
            "Mara Muster Buchhaltung Finanzen rechnung@beispiel.de"
        )

        self.assertEqual(result.profile_id, company["id"])
        self.assertIn("Profil-E-Mail-Adresse", result.matched_by)
        self.assertIn("Firmenfunktion oder Abteilung", result.matched_by)


if __name__ == "__main__":
    unittest.main()
