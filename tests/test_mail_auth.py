import io
import http.client
import json
import ssl
import tempfile
import threading
import unittest
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from src.mail_auth import (
    MailAuthenticationError,
    _post_form,
    authorize_interactively,
    load_microsoft_token_cache,
    oauth_client_config,
    oauth2_auth_string,
    save_oauth_client_config,
    secure_ssl_context,
    store_microsoft_token_cache,
    validate_imap_settings,
)
from src.mail_fetcher import fetch_account


class _Config:
    def __init__(self, root):
        self.app_root = Path(root)
        self.oauth_clients_path = Path(root) / "oauth_clients.json"
        self.oauth_clients_path.write_text("{}", encoding="utf-8")


class _OAuthImap:
    def __init__(self):
        self.authenticated = False
        self.logged_in = False

    def authenticate(self, mechanism, callback):
        self.authenticated = mechanism == "XOAUTH2"
        self.auth_payload = callback(b"")
        return "OK", []

    def login(self, *_args):
        self.logged_in = True
        return "OK", []

    def select(self, _mailbox, **_kwargs):
        return "OK", []

    def uid(self, action, *_args):
        if action == "search":
            return "OK", [b""]
        raise AssertionError(action)

    def logout(self):
        return "BYE", []


class MailAuthenticationTests(unittest.TestCase):
    def test_google_http_error_is_reported_as_configuration_problem(self):
        error = urllib.error.HTTPError(
            "https://oauth2.googleapis.com/token",
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"error":"invalid_client","error_description":"secret-token"}'),
        )
        with patch("src.mail_auth.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(MailAuthenticationError) as raised:
                _post_form("https://oauth2.googleapis.com/token", {"client_id": "desktop"})
        self.assertIn("Desktop-App", str(raised.exception))
        self.assertNotIn("secret-token", str(raised.exception))

    def test_oauth_provider_is_pinned_to_official_server_and_port(self):
        valid = {
            "provider": "microsoft",
            "auth_method": "oauth2",
            "imap_server": "outlook.office365.com",
            "imap_port": 993,
            "username": "bine@live.de",
        }
        self.assertEqual(validate_imap_settings(valid)[:2], ("outlook.office365.com", 993))
        for changed in (
            {**valid, "imap_server": "mail.attacker.test"},
            {**valid, "imap_port": 1993},
            {**valid, "auth_method": "app_password"},
        ):
            with self.assertRaises(MailAuthenticationError):
                validate_imap_settings(changed)

    def test_custom_provider_cannot_downgrade_google_or_microsoft_to_password(self):
        for server in ("imap.gmail.com", "outlook.office365.com", "imap-mail.outlook.com"):
            with self.assertRaises(MailAuthenticationError):
                validate_imap_settings({
                    "provider": "custom",
                    "auth_method": "app_password",
                    "imap_server": server,
                    "imap_port": 993,
                    "username": "user@example.com",
                })

    def test_legacy_oauth_provider_requires_explicit_reconnection(self):
        with self.assertRaises(MailAuthenticationError):
            validate_imap_settings({
                "provider": "Gmail",
                "imap_server": "imap.gmail.com",
                "username": "user@gmail.com",
            })

    def test_control_characters_are_rejected_from_identity_and_mailbox(self):
        base = {
            "provider": "custom",
            "auth_method": "app_password",
            "imap_server": "imap.example.com",
            "username": "user@example.com",
        }
        with self.assertRaises(MailAuthenticationError):
            validate_imap_settings({**base, "username": "user@example.com\x01auth=x"})
        with self.assertRaises(MailAuthenticationError):
            validate_imap_settings({**base, "mailbox": "INBOX\r\nLOGOUT"})

    def test_tls_context_verifies_certificates_and_rejects_old_tls(self):
        context = secure_ssl_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        if hasattr(ssl, "TLSVersion"):
            self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_oauth_fetch_uses_xoauth2_and_never_password_login(self):
        fake = _OAuthImap()
        account = {
            "id": "mail_1",
            "profile_id": "family_1",
            "provider": "google",
            "auth_method": "oauth2",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "username": "user@gmail.com",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            count = fetch_account(account, "access-token", temp_dir, imap_factory=lambda *_a, **_k: fake)
        self.assertEqual(count, 0)
        self.assertTrue(fake.authenticated)
        self.assertFalse(fake.logged_in)
        self.assertEqual(fake.auth_payload, oauth2_auth_string("user@gmail.com", "access-token"))

    def test_google_client_secret_is_vaulted_not_written_to_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            with patch("src.mail_auth._require_secure_keyring"), patch(
                "src.mail_auth.keyring.set_password"
            ) as store:
                save_oauth_client_config(config, "google", "client-id.apps.googleusercontent.com", "secret")
            stored = json.loads(config.oauth_clients_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["google"]["client_id"], "client-id.apps.googleusercontent.com")
            self.assertNotIn("client_secret", stored["google"])
            self.assertNotIn("secret", config.oauth_clients_path.read_text(encoding="utf-8"))
            self.assertEqual(store.call_args.args[-1], "secret")

    def test_interactive_flow_uses_external_browser_state_and_pkce(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            config.oauth_clients_path.write_text(
                json.dumps({"google": {"client_id": "desktop-client-id"}}),
                encoding="utf-8",
            )
            captured = {}

            def browser_open(url):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                captured.update(query)
                redirect = query["redirect_uri"][0]
                state = query["state"][0]

                def callback():
                    parsed = urllib.parse.urlparse(redirect)
                    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
                    try:
                        query_string = urllib.parse.urlencode(
                            {"code": "one-time-code", "state": state}
                        )
                        connection.request("GET", f"{parsed.path}?{query_string}")
                        connection.getresponse().read()
                    finally:
                        connection.close()

                threading.Thread(target=callback, daemon=True).start()
                return True

            with patch(
                "src.mail_auth._post_form",
                return_value={"access_token": "access", "refresh_token": "refresh"},
            ) as exchange, patch.dict(
                "src.mail_auth.os.environ",
                {"SORTERINO_GOOGLE_CLIENT_SECRET": "desktop-client-value"},
                clear=True,
            ):
                grant = authorize_interactively(config, "google", browser_open=browser_open)
            self.assertEqual(grant.access_token, "access")
            self.assertEqual(grant.refresh_token, "refresh")
            self.assertEqual(captured["code_challenge_method"], ["S256"])
            self.assertGreaterEqual(len(captured["state"][0]), 32)
            self.assertNotIn("client_secret", captured)
            token_values = exchange.call_args.args[1]
            self.assertEqual(token_values["code"], "one-time-code")
            self.assertGreaterEqual(len(token_values["code_verifier"]), 43)
            self.assertEqual(token_values["client_secret"], "desktop-client-value")

    def test_microsoft_uses_bundled_public_client_id_not_stale_user_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            config.oauth_clients_path.write_text(
                json.dumps({"microsoft": {"client_id": "stale-user-id"}}), encoding="utf-8"
            )
            with patch.dict("src.mail_auth.os.environ", {}, clear=True), patch(
                "src.mail_auth.MICROSOFT_CLIENT_ID", "test-microsoft-client-id"
            ):
                client = oauth_client_config(config, "microsoft")
            self.assertEqual(client["client_id"], "test-microsoft-client-id")
            self.assertEqual(client["client_secret"], "")

    def test_google_uses_bundled_public_client_id_and_build_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            config.oauth_clients_path.write_text(
                json.dumps({"google": {"client_id": "stale-user-id", "client_secret": "stale-secret"}}),
                encoding="utf-8",
            )
            with patch.dict(
                "src.mail_auth.os.environ",
                {"SORTERINO_GOOGLE_CLIENT_SECRET": "desktop-client-value"},
                clear=True,
            ), patch("src.mail_auth.GOOGLE_CLIENT_ID", "test-google-client-id"):
                client = oauth_client_config(config, "google")
            self.assertEqual(client["client_id"], "test-google-client-id")
            self.assertEqual(client["client_secret"], "desktop-client-value")

    def test_google_build_contains_the_desktop_client_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            with patch.dict("src.mail_auth.os.environ", {}, clear=True), patch(
                "src.mail_auth.GOOGLE_CLIENT_ID", "test-google-client-id"
            ), patch("src.mail_auth.GOOGLE_CLIENT_SECRET", "test-google-client-value"):
                client = oauth_client_config(config, "google")
            self.assertTrue(client["client_secret"])
            self.assertNotIn("client_secret", config.oauth_clients_path.read_text(encoding="utf-8"))

    def test_google_local_vault_cannot_override_the_bundled_build_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            config.oauth_clients_path.write_text(
                json.dumps({"google": {"client_id": "test-google-client-id"}}),
                encoding="utf-8",
            )
            with patch.dict("src.mail_auth.os.environ", {}, clear=True), patch(
                "src.mail_auth.GOOGLE_CLIENT_ID", "test-google-client-id"
            ), patch(
                "src.mail_auth.GOOGLE_CLIENT_SECRET", "test-google-client-value"
            ), patch("src.mail_auth.keyring.get_password", return_value="vaulted-client-value"):
                client = oauth_client_config(config, "google")
            self.assertTrue(client["client_secret"])
            self.assertNotEqual(client["client_secret"], "vaulted-client-value")

    @unittest.skipUnless(__import__("os").name == "nt", "Windows DPAPI only")
    def test_microsoft_token_cache_is_dpapi_protected_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _Config(temp_dir)
            serialized = '{"AccessToken":{"private":"token-value"}}'
            store_microsoft_token_cache(config, "mail_1", serialized)
            cache_file = config.app_root / "credentials" / "microsoft_mail_1.bin"
            self.assertTrue(cache_file.exists())
            self.assertNotIn(b"token-value", cache_file.read_bytes())
            self.assertEqual(load_microsoft_token_cache(config, "mail_1"), serialized)


if __name__ == "__main__":
    unittest.main()
