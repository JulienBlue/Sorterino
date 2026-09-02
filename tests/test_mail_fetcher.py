import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from src.mail_fetcher import MailImportState, _migrate_legacy_account_folder, fetch_account


class FakeImap:
    def __init__(self, message_bytes):
        self.message_bytes = message_bytes
        self.stored = False
        self.search_calls = []

    def login(self, _username, _password):
        return "OK", []

    def select(self, _mailbox, **_kwargs):
        return "OK", []

    def response(self, name):
        if name == "UIDVALIDITY":
            return "OK", [b"777"]
        if name == "UIDNEXT":
            return "OK", [b"43"]
        return None, []

    def uid(self, action, *_args):
        if action == "search":
            self.search_calls.append(_args)
            return "OK", [b"42"]
        if action == "fetch":
            return "OK", [(b"42", self.message_bytes)]
        if action == "store":
            self.stored = True
            return "OK", []
        raise AssertionError(action)

    def logout(self):
        return "BYE", []


class GapImap(FakeImap):
    def uid(self, action, *_args):
        if action == "search":
            self.search_calls.append(_args)
            return "OK", [b"42 43"]
        if action == "fetch":
            return "NO", []
        raise AssertionError(action)


class MailFetcherTests(unittest.TestCase):
    def test_attachment_is_saved_flat_without_technical_id_directories(self):
        message = EmailMessage()
        message["Subject"] = "Invoice"
        message.set_content("Attached")
        message.add_attachment(b"pdf-data", maintype="application", subtype="pdf", filename="invoice.pdf")
        fake = FakeImap(message.as_bytes())
        account = {
            "id": "mail_1",
            "profile_id": "organization_1",
            "label": "Firma",
            "enabled": True,
            "imap_server": "imap.example.test",
            "username": "office@example.test",
            "allowed_extensions": [".pdf"],
            "mark_processed": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            count = fetch_account(account, "secret", target, imap_factory=lambda *_args: fake)
            self.assertEqual(count, 1)
            self.assertEqual((target / "invoice.pdf").read_bytes(), b"pdf-data")
            self.assertFalse((target / account["profile_id"]).exists())
            self.assertFalse(fake.stored)
            self.assertNotIn("UNSEEN", str(fake.search_calls))

    def test_new_default_formats_are_downloaded_for_legacy_accounts(self):
        message = EmailMessage()
        message["Subject"] = "Contract"
        message.set_content("Attached")
        message.add_attachment(
            b"docx-data",
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="contract.docx",
        )
        fake = FakeImap(message.as_bytes())
        account = {
            "id": "mail_1",
            "profile_id": "family_1",
            "enabled": True,
            "imap_server": "imap.example.test",
            "username": "family@example.test",
            "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            count = fetch_account(account, "secret", target, imap_factory=lambda *_args: fake)
            self.assertEqual(count, 1)
            self.assertEqual((target / "contract.docx").read_bytes(), b"docx-data")

    def test_persistent_uid_cursor_imports_read_mail_once(self):
        message = EmailMessage()
        message["Message-ID"] = "<one@example.test>"
        message.set_content("Attached")
        message.add_attachment(b"pdf-data", maintype="application", subtype="pdf", filename="invoice.pdf")
        account = {
            "id": "mail_1", "profile_id": "family_1", "enabled": True,
            "imap_server": "imap.example.test", "username": "family@example.test",
            "allowed_extensions": [".pdf"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            config = type("Config", (), {"state_root": Path(temp_dir) / "state"})()
            state = MailImportState(config)
            first = FakeImap(message.as_bytes())
            self.assertEqual(
                fetch_account(account, "secret", temp_dir, lambda *_a, **_k: first, state), 1
            )
            second = FakeImap(message.as_bytes())
            self.assertEqual(
                fetch_account(account, "secret", temp_dir, lambda *_a, **_k: second, state), 0
            )
            self.assertIn("UID", second.search_calls[0])
            self.assertIn("43:*", second.search_calls[0])
            self.assertEqual(len(list(Path(temp_dir).glob("invoice*.pdf"))), 1)

    def test_flat_attachment_keeps_invisible_profile_hint(self):
        account = {"id": "mail_1", "profile_id": "family_1"}
        with tempfile.TemporaryDirectory() as temp_dir:
            config = type("Config", (), {"state_root": Path(temp_dir) / "state"})()
            source = Path(temp_dir) / "invoice.pdf"
            source.write_bytes(b"pdf")
            state = MailImportState(config)
            account_state = state.prepare_account(account["id"], "777")
            state.record_attachment(account, account_state, "attachment", source, "42")
            service = type(
                "Service", (), {"get_email_account": lambda _self, value: account if value == "mail_1" else None}
            )()
            self.assertEqual(state.profile_hint(source, service), "family_1")
            self.assertEqual(state.file_info(source)["account_id"], "mail_1")
            self.assertIsNone(state.file_info(Path(temp_dir) / "local.pdf"))

    def test_legacy_id_directories_are_flattened_and_keep_profile_hint(self):
        account = {"id": "mail_1", "profile_id": "family_1"}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "incoming"
            legacy = root / "family_1" / "mail_1"
            legacy.mkdir(parents=True)
            (legacy / "document.pdf").write_bytes(b"pdf")
            config = type("Config", (), {"state_root": Path(temp_dir) / "state"})()
            state = MailImportState(config)

            _migrate_legacy_account_folder(root, account, state)

            migrated = root / "document.pdf"
            self.assertEqual(migrated.read_bytes(), b"pdf")
            self.assertFalse((root / "family_1").exists())
            service = type(
                "Service", (),
                {"get_email_account": lambda _self, value: account if value == "mail_1" else None},
            )()
            self.assertEqual(state.profile_hint(migrated, service), "family_1")

    def test_failed_uid_fetch_does_not_skip_the_mail(self):
        message = EmailMessage()
        message.set_content("Body")
        account = {
            "id": "mail_1", "profile_id": "family_1", "enabled": True,
            "imap_server": "imap.example.test", "username": "family@example.test",
            "allowed_extensions": [".pdf"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            config = type("Config", (), {"state_root": Path(temp_dir) / "state"})()
            state = MailImportState(config)
            fake = GapImap(message.as_bytes())

            self.assertEqual(
                fetch_account(account, "secret", temp_dir, lambda *_a, **_k: fake, state), 0
            )
            self.assertEqual(state.data["accounts"]["mail_1"]["last_uid"], 0)

    def test_zero_lookback_starts_at_current_mailbox_end(self):
        message = EmailMessage()
        message.set_content("Old mail")
        message.add_attachment(b"pdf", maintype="application", subtype="pdf", filename="old.pdf")
        account = {
            "id": "mail_1", "profile_id": "family_1", "enabled": True,
            "imap_server": "imap.example.test", "username": "family@example.test",
            "allowed_extensions": [".pdf"], "initial_lookback_days": 0,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            config = type("Config", (), {"state_root": Path(temp_dir) / "state"})()
            state = MailImportState(config)
            fake = FakeImap(message.as_bytes())
            self.assertEqual(
                fetch_account(account, "secret", temp_dir, lambda *_a, **_k: fake, state), 0
            )
            self.assertEqual(state.data["accounts"]["mail_1"]["last_uid"], 42)
            self.assertEqual(fake.search_calls, [])
            self.assertFalse((Path(temp_dir) / "old.pdf").exists())


if __name__ == "__main__":
    unittest.main()
