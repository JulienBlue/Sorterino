import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Config
from src.database import SorterinoDatabase
from src.report_mailer import deliver_daily_report, normalize_recipients
from src.reporting import DailyReportManager


class _FakeSMTP:
    def __init__(self):
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def send_message(self, message):
        self.messages.append(message)


class ReportMailerTests(unittest.TestCase):
    def test_recipients_are_validated_deduplicated_and_bounded(self):
        values = "A@example.de; invalid, a@example.de\nb@example.org"
        self.assertEqual(normalize_recipients(values), ["a@example.de", "b@example.org"])

    def test_report_delivery_tables_are_migrated(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(app_data_root=Path(temp) / "app", legacy_home=Path(temp) / "home")
            database = SorterinoDatabase(config)
            with database.read() as connection:
                tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertIn("report_runs", tables)
            self.assertIn("report_deliveries", tables)

    def test_report_and_developer_defaults_are_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(app_data_root=Path(temp) / "app", legacy_home=Path(temp) / "home")
            self.assertFalse(config.get("daily_report_email_enabled"))
            self.assertFalse(config.get("developer_mode"))
            self.assertEqual(config.get("daily_report_content_level"), "compact")

    def test_each_recipient_receives_a_separate_message_and_delivery_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(app_data_root=Path(temp) / "app", legacy_home=Path(temp) / "home")
            config.set("daily_report_sender_mode", "dedicated")
            config.set("daily_report_sender", {
                "id": "report_sender", "email": "sender@example.de", "username": "sender@example.de",
                "provider": "custom", "auth_method": "app_password",
                "smtp_server": "smtp.example.de", "smtp_port": 465,
            })
            config.set("daily_report_recipients", ["one@example.de", "two@example.de"])
            DailyReportManager(config.logs_root).record_event({
                "status": "success", "original_name": "a.pdf", "final_name": "b.pdf",
                "target_folder": "Dokumente", "reason": "ok",
            })
            smtp = _FakeSMTP()
            with patch("src.report_mailer._smtp_connection", return_value=smtp), patch(
                "src.report_mailer._authenticate", return_value="sender@example.de"
            ):
                result = deliver_daily_report(config, force=True)
            self.assertEqual(result["sent"], 2)
            self.assertEqual([message["To"] for message in smtp.messages], ["one@example.de", "two@example.de"])
            with SorterinoDatabase(config).read() as connection:
                statuses = [row[0] for row in connection.execute("SELECT status FROM report_deliveries ORDER BY recipient")]
            self.assertEqual(statuses, ["delivered", "delivered"])


if __name__ == "__main__":
    unittest.main()
