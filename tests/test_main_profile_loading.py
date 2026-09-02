import unittest
from unittest.mock import Mock, patch

import main


class ProfileLoadingTests(unittest.TestCase):
    @patch("main.ProfileService")
    def test_existing_profiles_override_stale_disabled_setting(self, service_class):
        config = Mock()
        config.get.return_value = {
            "enabled": False,
            "minimum_assignment_confidence": 0.8,
        }
        service = service_class.return_value
        service.list_profiles.return_value = [{"id": "family_1"}]
        logger = Mock()

        result = main._load_profile_service(config, logger)

        self.assertIs(result, service)
        config.set.assert_called_once_with(
            "profile_system",
            {"enabled": True, "minimum_assignment_confidence": 0.8},
        )

    @patch("main.ProfileService")
    def test_no_profiles_keeps_profile_matching_disabled(self, service_class):
        config = Mock()
        config.get.return_value = {"enabled": False}
        service_class.return_value.list_profiles.return_value = []

        result = main._load_profile_service(config, Mock())

        self.assertIsNone(result)
        config.set.assert_not_called()

    @patch("main.ProfileService")
    def test_settings_write_failure_does_not_disable_existing_profiles(self, service_class):
        config = Mock()
        config.get.return_value = {"enabled": False}
        config.set.side_effect = PermissionError("gesperrt")
        service = service_class.return_value
        service.list_profiles.return_value = [{"id": "person_1"}]
        logger = Mock()

        result = main._load_profile_service(config, logger)

        self.assertIs(result, service)
        logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
