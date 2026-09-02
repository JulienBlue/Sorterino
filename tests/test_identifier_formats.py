import unittest

from src.identifier_formats import (
    IdentifierFormatError,
    business_id,
    creditor_id,
    employer_number,
    eori,
    family_benefits_number,
    health_insurance_number,
    pension_number,
    tax_id,
    tax_number,
    vat_id,
)


class IdentifierFormatTests(unittest.TestCase):
    def test_personal_identifiers_are_normalized(self):
        self.assertEqual(tax_id("86 095 742 719"), "86095742719")
        self.assertEqual(pension_number("65 170839 J 003"), "65170839J003")
        self.assertEqual(health_insurance_number("a 123 456 789"), "A123456789")
        self.assertEqual(family_benefits_number("123 fk 123456"), "123FK123456")

    def test_tax_numbers_keep_supported_state_or_elster_length(self):
        self.assertEqual(tax_number("12/345/67890"), "1234567890")
        self.assertEqual(tax_number("123/4567/8901"), "12345678901")
        self.assertEqual(tax_number("2812/0345/67890"), "2812034567890")

    def test_company_identifiers_are_normalized(self):
        self.assertEqual(vat_id("de 123 456 789"), "DE123456789")
        self.assertEqual(business_id("de123456789-00001"), "DE123456789-00001")
        self.assertEqual(employer_number("12 345 678"), "12345678")
        self.assertEqual(creditor_id("DE98 ZZZ0 9999 9999 99"), "DE98ZZZ09999999999")
        self.assertEqual(eori("DE 123456789012345"), "DE123456789012345")

    def test_invalid_check_digits_are_rejected(self):
        for normalizer, value in [
            (tax_id, "86095742718"),
            (pension_number, "65170839J004"),
            (creditor_id, "DE99ZZZ09999999999"),
        ]:
            with self.subTest(value=value), self.assertRaises(IdentifierFormatError):
                normalizer(value)


if __name__ == "__main__":
    unittest.main()
