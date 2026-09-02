import unittest
from datetime import date

from src.person_age import is_minor_from_birth_date, person_is_minor


class PersonAgeTests(unittest.TestCase):
    def test_calculates_minor_status_at_birthday_boundary(self):
        today = date(2026, 8, 9)
        self.assertTrue(is_minor_from_birth_date("10.08.2008", today))
        self.assertFalse(is_minor_from_birth_date("09.08.2008", today))

    def test_birth_date_overrides_legacy_minor_flag(self):
        adult = {"is_minor": True, "personal": {"date_of_birth": "04.05.1990"}}
        self.assertFalse(person_is_minor(adult, date(2026, 8, 9)))

    def test_legacy_flag_remains_fallback_without_birth_date(self):
        self.assertTrue(person_is_minor({"is_minor": True, "personal": {}}))


if __name__ == "__main__":
    unittest.main()
