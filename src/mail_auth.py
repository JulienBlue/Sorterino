"""Secure authentication primitives for profile-specific mail accounts.

No user secret is stored in Sorterino's JSON configuration.  Passwords and
OAuth refresh tokens are delegated to the operating-system credential vault.
OAuth access tokens deliberately live only in memory.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import secrets
import socket
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import keyring
import msal


KEYRING_SERVICE = "SorterinoMail"
OAUTH_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 30
OAUTH_PROVIDERS = {"google", "microsoft"}
PASSWORD_PROVIDERS = {"apple", "gmx", "webde", "ionos", "custom"}
try:
    from src.oauth_release_config import (
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        MICROSOFT_CLIENT_ID,
    )
except ImportError:
    # Public repository builds use environment variables or the values entered
    # in Sorterino. Official binaries receive these public native-app values
    # from the locally ignored release configuration during packaging.
    GOOGLE_CLIENT_ID = ""
    GOOGLE_CLIENT_SECRET = ""
    MICROSOFT_CLIENT_ID = ""
MICROSOFT_AUTHORITY = "https://login.microsoftonline.com/common"


class MailAuthenticationError(RuntimeError):
    """A deliberately user-safe authentication failure."""


@dataclass(frozen=True)
class ProviderDefinition:
    provider_id: str
    label: str
    imap_server: str
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    scopes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OAuthGrant:
    access_token: str
    refresh_token: str = ""
    token_cache: str = ""


PROVIDERS = {
    "google": ProviderDefinition(
        "google",
        "Google / Gmail",
        "imap.gmail.com",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        ("https://mail.google.com/",),
    ),
    "microsoft": ProviderDefinition(
        "microsoft",
        "Microsoft / Outlook / Live",
        "outlook.office365.com",
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        ("offline_access", "https://outlook.office.com/IMAP.AccessAsUser.All"),
    ),
    "apple": ProviderDefinition("apple", "Apple / iCloud", "imap.mail.me.com"),
    "gmx": ProviderDefinition("gmx", "GMX", "imap.gmx.net"),
    "webde": ProviderDefinition("webde", "WEB.DE", "imap.web.de"),
    "ionos": ProviderDefinition("ionos", "IONOS", "imap.ionos.de"),
    "custom": ProviderDefinition("custom", "Anderer Anbieter", " "),
}

LEGACY_PROVIDER_IDS = {
    "gmail": "google",
    "outlook / hotmail": "microsoft",
    "outlook / hotmail / live": "microsoft",
    "icloud": "apple",
    "apple / icloud": "apple",
    "web.de": "webde",
    "benutzerdefiniert": "custom",
}


def normalize_provider(value):
    candidate = str(value or "").strip().casefold()
    if candidate in PROVIDERS:
        return candidate
    return LEGACY_PROVIDER_IDS.get(candidate, "custom")


def auth_method_for_provider(provider_id):
    return "oauth2" if normalize_provider(provider_id) in OAUTH_PROVIDERS else "app_password"


def account_password_key(account_id):
    # Retain the established key so existing accounts continue to work.
    return f"account:{account_id}:password"


def account_refresh_token_key(account_id):
    return f"account:{account_id}:oauth_refresh_token"


def _microsoft_cache_path(config, account_id):
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(account_id or ""))
    if not safe_id:
        raise MailAuthenticationError("Die Postfachkennung fehlt.")
    return Path(config.app_root) / "credentials" / f"microsoft_{safe_id}.bin"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_transform(data, protect):
    """Protect or unprotect bytes with Windows DPAPI for the current user."""
    if os.name != "nt":
        raise MailAuthenticationError("Die sichere Microsoft-Tokenablage benötigt Windows.")
    raw = bytes(data)
    buffer = ctypes.create_string_buffer(raw, len(raw))
    source = _DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    destination = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    description = "Sorterino Microsoft OAuth" if protect else None
    succeeded = function(
        ctypes.byref(source), description, None, None, None, 0x1,
        ctypes.byref(destination),
    )
    if not succeeded:
        raise MailAuthenticationError("Der Microsoft-Zugriff konnte nicht sicher gespeichert werden.")
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


def store_microsoft_token_cache(config, account_id, serialized_cache):
    payload = str(serialized_cache or "").encode("utf-8")
    if not payload or len(payload) > 1024 * 1024:
        raise MailAuthenticationError("Microsoft hat keinen gültigen Tokenbestand geliefert.")
    protected = _dpapi_transform(payload, True)
    path = _microsoft_cache_path(config, account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=path.parent, prefix=".microsoft_token.", suffix=".tmp", delete=False
        ) as handle:
            handle.write(protected)
            handle.flush()
            temp_path = Path(handle.name)
        temp_path.replace(path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def load_microsoft_token_cache(config, account_id):
    path = _microsoft_cache_path(config, account_id)
    try:
        protected = path.read_bytes()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise MailAuthenticationError("Der Microsoft-Tokenbestand ist nicht lesbar.") from exc
    try:
        return _dpapi_transform(protected, False).decode("utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise MailAuthenticationError(
            "Der Microsoft-Zugriff gehört zu einem anderen Windows-Konto oder ist beschädigt."
        ) from exc


def delete_microsoft_token_cache(config, account_id):
    try:
        _microsoft_cache_path(config, account_id).unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise MailAuthenticationError("Der Microsoft-Tokenbestand konnte nicht gelöscht werden.") from exc


def oauth_client_secret_key(provider_id):
    return f"oauth_client:{provider_id}:client_secret"


def _require_secure_keyring():
    backend = keyring.get_keyring()
    module = backend.__class__.__module__.casefold()
    name = backend.__class__.__name__.casefold()
    if (
        "fail" in module
        or "null" in name
        or "plaintext" in module
        or "plaintext" in name
        or (os.name == "nt" and module != "keyring.backends.windows")
    ):
        raise MailAuthenticationError(
            "Der sichere Windows-Anmeldeinformationsspeicher ist nicht verfügbar. "
            "Sorterino speichert deshalb keine Zugangsdaten."
        )
    return backend


def store_password(account_id, password):
    if not str(password or "").strip():
        raise MailAuthenticationError("Das App-Passwort fehlt.")
    _require_secure_keyring()
    try:
        keyring.set_password(KEYRING_SERVICE, account_password_key(account_id), password)
    except keyring.errors.KeyringError as exc:
        raise MailAuthenticationError("Das App-Passwort konnte nicht sicher gespeichert werden.") from exc


def load_password(account_id):
    _require_secure_keyring()
    try:
        return keyring.get_password(KEYRING_SERVICE, account_password_key(account_id))
    except keyring.errors.KeyringError as exc:
        raise MailAuthenticationError("Der Windows-Anmeldeinformationsspeicher ist nicht verfügbar.") from exc


def store_refresh_token(account_id, refresh_token):
    token = str(refresh_token or "").strip()
    if not token or len(token) > 8192:
        raise MailAuthenticationError("Der Anbieter hat kein dauerhaftes Zugriffstoken geliefert.")
    _require_secure_keyring()
    try:
        keyring.set_password(KEYRING_SERVICE, account_refresh_token_key(account_id), token)
    except keyring.errors.KeyringError as exc:
        raise MailAuthenticationError("Das Zugriffstoken konnte nicht sicher gespeichert werden.") from exc


def load_refresh_token(account_id):
    _require_secure_keyring()
    try:
        return keyring.get_password(KEYRING_SERVICE, account_refresh_token_key(account_id))
    except keyring.errors.KeyringError as exc:
        raise MailAuthenticationError("Der Windows-Anmeldeinformationsspeicher ist nicht verfügbar.") from exc


def delete_account_credentials(account_id, config=None):
    """Delete every credential variant without exposing whether it existed."""
    _require_secure_keyring()
    for key in (account_password_key(account_id), account_refresh_token_key(account_id)):
        try:
            keyring.delete_password(KEYRING_SERVICE, key)
        except keyring.errors.PasswordDeleteError:
            pass
    if config is not None:
        delete_microsoft_token_cache(config, account_id)


def delete_password_credential(account_id):
    _require_secure_keyring()
    try:
        keyring.delete_password(KEYRING_SERVICE, account_password_key(account_id))
    except keyring.errors.PasswordDeleteError:
        pass


def delete_refresh_token(account_id):
    _require_secure_keyring()
    try:
        keyring.delete_password(KEYRING_SERVICE, account_refresh_token_key(account_id))
    except keyring.errors.PasswordDeleteError:
        pass


def has_account_credentials(account, config=None):
    account_id = account.get("id")
    if not account_id:
        return False
    method = str(account.get("auth_method") or "app_password")
    if normalize_provider(account.get("provider")) in OAUTH_PROVIDERS and method != "oauth2":
        return False
    try:
        if method == "oauth2" and normalize_provider(account.get("provider")) == "microsoft":
            return bool(config and load_microsoft_token_cache(config, account_id))
        return bool(load_refresh_token(account_id) if method == "oauth2" else load_password(account_id))
    except MailAuthenticationError:
        return False


def secure_ssl_context():
    context = ssl.create_default_context()
    if hasattr(ssl, "TLSVersion"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def validate_imap_settings(account):
    provider_id = normalize_provider(account.get("provider"))
    server = str(account.get("imap_server") or "").strip().rstrip(".").lower()
    username = str(account.get("username") or "").strip()
    try:
        port = int(account.get("imap_port") or 993)
    except (TypeError, ValueError) as exc:
        raise MailAuthenticationError("Der IMAP-Port ist ungültig.") from exc
    if (
        not username
        or len(username) > 254
        or not re.fullmatch(r"[^\s@\x00-\x1f\x7f]+@[^\s@\x00-\x1f\x7f]+", username)
    ):
        raise MailAuthenticationError("Bitte gib eine vollständige E-Mail-Adresse ein.")
    if not server or len(server) > 253 or not re.fullmatch(r"[A-Za-z0-9.-]+", server):
        raise MailAuthenticationError("Der IMAP-Server ist ungültig.")
    if not 1 <= port <= 65535:
        raise MailAuthenticationError("Der IMAP-Port muss zwischen 1 und 65535 liegen.")
    definition = PROVIDERS[provider_id]
    if provider_id == "custom" and server in {
        PROVIDERS["google"].imap_server,
        PROVIDERS["microsoft"].imap_server,
        "imap-mail.outlook.com",
    }:
        raise MailAuthenticationError(
            "Google- und Microsoft-Server dürfen nicht über die manuelle Passwortanmeldung "
            "verwendet werden. Wähle den passenden Anbieter und OAuth2."
        )
    if provider_id != "custom" and server != definition.imap_server:
        raise MailAuthenticationError(
            f"Für {definition.label} ist ausschließlich {definition.imap_server} zugelassen."
        )
    if provider_id != "custom" and port != 993:
        raise MailAuthenticationError(f"Für {definition.label} ist ausschließlich IMAP-Port 993 zugelassen.")
    expected_method = auth_method_for_provider(provider_id)
    raw_method = account.get("auth_method")
    if provider_id in OAUTH_PROVIDERS and not raw_method:
        raise MailAuthenticationError(
            "Dieses ältere Konto muss einmal sicher im Browser neu verbunden werden."
        )
    method = str(raw_method or expected_method)
    if method != expected_method:
        raise MailAuthenticationError(
            f"Die Anmeldemethode für {definition.label} wurde aus Sicherheitsgründen abgelehnt."
        )
    mailbox = str(account.get("mailbox") or "INBOX")
    if len(mailbox) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in mailbox):
        raise MailAuthenticationError("Der Postfachname ist ungültig.")
    return server, port, username


def _read_oauth_clients(config):
    path = Path(config.oauth_clients_path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        data = {}
    return data if isinstance(data, dict) else {}


def save_oauth_client_config(config, provider_id, client_id, client_secret=""):
    """Save public client metadata atomically; vault the optional Google secret."""
    provider_id = normalize_provider(provider_id)
    if provider_id not in OAUTH_PROVIDERS:
        raise MailAuthenticationError("Unbekannter OAuth2-Anbieter.")
    client_id = str(client_id or "").strip()
    if not client_id or len(client_id) > 300 or any(char.isspace() for char in client_id):
        raise MailAuthenticationError("Die Client-ID ist ungültig.")
    data = _read_oauth_clients(config)
    previous_client_id = str((data.get(provider_id, {}) or {}).get("client_id") or "")
    data.setdefault(provider_id, {})["client_id"] = client_id
    # Never persist a client secret in JSON, even though native clients cannot
    # technically treat a distributed application secret as confidential.
    data[provider_id].pop("client_secret", None)
    path = Path(config.oauth_clients_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".oauth_clients.",
            suffix=".tmp", delete=False,
        ) as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            temp_path = Path(handle.name)
        temp_path.replace(path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    if provider_id == "google":
        _require_secure_keyring()
        if str(client_secret or "").strip():
            try:
                keyring.set_password(
                    KEYRING_SERVICE,
                    oauth_client_secret_key(provider_id),
                    str(client_secret).strip(),
                )
            except keyring.errors.KeyringError as exc:
                raise MailAuthenticationError(
                    "Das Google-Client-Secret konnte nicht sicher gespeichert werden."
                ) from exc
        elif previous_client_id and previous_client_id != client_id:
            try:
                keyring.delete_password(KEYRING_SERVICE, oauth_client_secret_key(provider_id))
            except keyring.errors.PasswordDeleteError:
                pass


def oauth_client_config(config, provider_id):
    provider_id = normalize_provider(provider_id)
    if provider_id not in OAUTH_PROVIDERS:
        raise MailAuthenticationError("Dieser Anbieter verwendet keine OAuth2-Anmeldung.")
    stored = _read_oauth_clients(config).get(provider_id, {}) or {}
    prefix = f"SORTERINO_{provider_id.upper()}_"
    bundled_client_id = {
        "google": GOOGLE_CLIENT_ID,
        "microsoft": MICROSOFT_CLIENT_ID,
    }.get(provider_id, "")
    client_id = str(
        os.environ.get(prefix + "CLIENT_ID")
        or bundled_client_id
        or stored.get("client_id")
        or ""
    ).strip()
    # Google currently requires the generated Desktop-client value at its token
    # endpoint even though an installed application cannot keep it confidential.
    # Prefer a build-time value; a matching locally configured value remains in
    # the OS credential vault and never enters Sorterino's JSON files.
    client_secret = ""
    if provider_id == "google":
        client_secret = str(
            os.environ.get(prefix + "CLIENT_SECRET") or GOOGLE_CLIENT_SECRET or ""
        ).strip()
        if not client_secret and str(stored.get("client_id") or "").strip() == client_id:
            try:
                client_secret = str(
                    keyring.get_password(KEYRING_SERVICE, oauth_client_secret_key(provider_id)) or ""
                ).strip()
            except keyring.errors.KeyringError:
                client_secret = ""
    if not client_id:
        raise MailAuthenticationError(
            f"Die Sorterino-OAuth-Anwendung für {PROVIDERS[provider_id].label} "
            "ist in diesem Build noch nicht eingerichtet."
        )
    if provider_id == "google" and not client_secret:
        raise MailAuthenticationError(
            "Für den neuen Google-Desktop-Client fehlt noch der von Google erzeugte "
            "Clientwert. Er wird lokal im Windows-Anmeldeinformationsspeicher abgelegt."
        )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_port": 0,
    }


def _microsoft_application(client_id, token_cache=None):
    return msal.PublicClientApplication(
        client_id,
        authority=MICROSOFT_AUTHORITY,
        token_cache=token_cache,
    )


def _microsoft_scopes():
    # MSAL adds OIDC/offline_access scopes itself and rejects them when callers
    # include them in the application scope list.
    return [scope for scope in PROVIDERS["microsoft"].scopes if scope != "offline_access"]


def _microsoft_error(result, fallback):
    if str((result or {}).get("error") or "") == "access_denied":
        return MailAuthenticationError("Die Microsoft-Anmeldung wurde abgebrochen oder nicht erlaubt.")
    return MailAuthenticationError(fallback)


def _b64url_sha256(value):
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class _OAuthCallbackServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class _CallbackHandler(BaseHTTPRequestHandler):
    server_version = "SorterinoOAuth"
    sys_version = ""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/oauth/callback":
            self.send_error(404)
            return
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        result = {key: values[0] for key, values in query.items() if values}
        if not secrets.compare_digest(
            str(result.get("state") or ""), str(self.server.expected_state or "")
        ):
            self.send_error(400, "Invalid OAuth state")
            return
        self.server.oauth_result = result
        body = (
            "<!doctype html><html lang='de'><meta charset='utf-8'>"
            "<title>Sorterino</title><body><h1>Anmeldeantwort empfangen</h1>"
            "<p>Du kannst dieses Fenster schließen und zu Sorterino zurückkehren.</p>"
            "</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        # Query strings can contain authorization codes and must never be logged.
        return


def _post_form(url, values):
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("ascii"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Sorterino/1 OAuth",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        try:
            payload = exc.read(64 * 1024)
            result = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            result = {}
        error_code = str(result.get("error") or "").strip().casefold()
        messages = {
            "invalid_client": (
                "Google hat die OAuth-Client-ID abgelehnt. Prüfe, ob sie aus einem "
                "Client vom Typ ‚Desktop-App‘ stammt."
            ),
            "redirect_uri_mismatch": (
                "Google hat die lokale Rücksprungadresse abgelehnt. Der OAuth-Client "
                "muss vom Typ ‚Desktop-App‘ sein."
            ),
            "invalid_grant": (
                "Google hat den einmaligen Anmeldecode abgelehnt oder er ist abgelaufen. "
                "Bitte starte die Verbindung erneut."
            ),
            "invalid_scope": (
                "Google hat den benötigten Gmail-Berechtigungsbereich abgelehnt. Prüfe "
                "unter ‚Datenzugriff‘ den Scope https://mail.google.com/."
            ),
            "unauthorized_client": (
                "Dieser Google-OAuth-Client ist für die Desktop-Anmeldung nicht zugelassen."
            ),
            "access_denied": (
                "Google hat den Zugriff nicht freigegeben. Prüfe Veröffentlichungsstatus, "
                "Testnutzer und die Gmail-Berechtigung."
            ),
        }
        message = messages.get(
            error_code,
            f"Google hat die Anmeldung abgelehnt (Fehler {error_code or exc.code}).",
        )
        raise MailAuthenticationError(message) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MailAuthenticationError(
            "Der Anmeldedienst ist momentan nicht erreichbar. Bitte versuche es später erneut."
        ) from exc
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MailAuthenticationError("Der Anmeldedienst hat ungültig geantwortet.") from exc
    if not isinstance(result, dict) or result.get("error"):
        raise MailAuthenticationError("Der Anbieter hat die Anmeldung abgelehnt.")
    if result.get("access_token") and str(result.get("token_type") or "Bearer").casefold() != "bearer":
        raise MailAuthenticationError("Der Anbieter hat einen unerwarteten Tokentyp geliefert.")
    return result


def authorize_interactively(config, provider_id, browser_open=webbrowser.open):
    """Run RFC 8252 Authorization Code + PKCE using the external browser."""
    provider_id = normalize_provider(provider_id)
    definition = PROVIDERS.get(provider_id)
    if provider_id not in OAUTH_PROVIDERS or not definition:
        raise MailAuthenticationError("Für diesen Anbieter ist keine Browser-Anmeldung verfügbar.")
    client = oauth_client_config(config, provider_id)
    if provider_id == "microsoft":
        cache = msal.SerializableTokenCache()
        try:
            result = _microsoft_application(client["client_id"], cache).acquire_token_interactive(
                scopes=_microsoft_scopes(),
                prompt="select_account",
                timeout=OAUTH_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise MailAuthenticationError(
                "Die Microsoft-Anmeldung konnte nicht sicher geöffnet werden."
            ) from exc
        access_token = str((result or {}).get("access_token") or "")
        if not access_token or len(access_token) > 65536:
            raise _microsoft_error(result, "Microsoft hat kein Zugriffstoken geliefert.")
        return OAuthGrant(access_token=access_token, token_cache=cache.serialize())
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    try:
        server = _OAuthCallbackServer(
            ("127.0.0.1", client.get("redirect_port", 0)), _CallbackHandler
        )
    except OSError as exc:
        raise MailAuthenticationError(
            "Der lokale Sicherheitsport für die Browser-Anmeldung ist belegt. "
            "Schließe die andere Anwendung und versuche es erneut."
        ) from exc
    server.oauth_result = None
    server.expected_state = state
    redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth/callback"
    parameters = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(definition.scopes),
        "state": state,
        "code_challenge": _b64url_sha256(verifier),
        "code_challenge_method": "S256",
    }
    if provider_id == "google":
        parameters.update({"access_type": "offline", "prompt": "consent"})
    else:
        parameters.update({"prompt": "select_account"})
    url = definition.authorization_endpoint + "?" + urllib.parse.urlencode(parameters)
    deadline = time.monotonic() + OAUTH_TIMEOUT_SECONDS
    try:
        server.timeout = 1
        if not browser_open(url):
            raise MailAuthenticationError("Der Standardbrowser konnte nicht geöffnet werden.")
        while server.oauth_result is None and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    result = server.oauth_result
    if not result:
        raise MailAuthenticationError("Die Anmeldung wurde wegen Zeitüberschreitung abgebrochen.")
    if not secrets.compare_digest(str(result.get("state") or ""), state):
        raise MailAuthenticationError("Die Anmeldeantwort konnte nicht sicher bestätigt werden.")
    if result.get("error") or not result.get("code"):
        raise MailAuthenticationError("Die Anmeldung wurde abgebrochen oder nicht erlaubt.")
    token_values = {
        "client_id": client["client_id"],
        "code": result["code"],
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    if client["client_secret"]:
        token_values["client_secret"] = client["client_secret"]
    tokens = _post_form(definition.token_endpoint, token_values)
    access_token = str(tokens.get("access_token") or "")
    refresh_token = str(tokens.get("refresh_token") or "")
    if (
        not access_token
        or not refresh_token
        or len(access_token) > 65536
        or len(refresh_token) > 8192
    ):
        raise MailAuthenticationError("Der Anbieter hat kein Zugriffstoken geliefert.")
    return OAuthGrant(access_token=access_token, refresh_token=refresh_token)


def refresh_access_token(config, account):
    provider_id = normalize_provider(account.get("provider"))
    if provider_id not in OAUTH_PROVIDERS:
        raise MailAuthenticationError("Das Konto verwendet keine OAuth2-Anmeldung.")
    if provider_id == "microsoft":
        cache = msal.SerializableTokenCache()
        serialized = load_microsoft_token_cache(config, account.get("id"))
        if not serialized:
            raise MailAuthenticationError("Das Microsoft-Postfach muss erneut verbunden werden.")
        try:
            cache.deserialize(serialized)
            application = _microsoft_application(oauth_client_config(config, provider_id)["client_id"], cache)
            accounts = application.get_accounts(username=str(account.get("username") or ""))
            if not accounts:
                raise MailAuthenticationError("Das Microsoft-Postfach muss erneut verbunden werden.")
            result = application.acquire_token_silent(_microsoft_scopes(), account=accounts[0])
        except MailAuthenticationError:
            raise
        except Exception as exc:
            raise MailAuthenticationError("Der Microsoft-Zugriff konnte nicht erneuert werden.") from exc
        if cache.has_state_changed:
            store_microsoft_token_cache(config, account.get("id"), cache.serialize())
        access_token = str((result or {}).get("access_token") or "")
        if not access_token or len(access_token) > 65536:
            raise _microsoft_error(result, "Das Microsoft-Postfach muss erneut verbunden werden.")
        return access_token
    refresh_token = load_refresh_token(account.get("id"))
    if not refresh_token:
        raise MailAuthenticationError("Das Postfach muss erneut im Browser verbunden werden.")
    definition = PROVIDERS[provider_id]
    client = oauth_client_config(config, provider_id)
    values = {
        "client_id": client["client_id"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(definition.scopes),
    }
    if client["client_secret"]:
        values["client_secret"] = client["client_secret"]
    tokens = _post_form(definition.token_endpoint, values)
    if tokens.get("refresh_token"):
        store_refresh_token(account["id"], tokens["refresh_token"])
    access_token = str(tokens.get("access_token") or "")
    if not access_token or len(access_token) > 65536:
        raise MailAuthenticationError("Der Anbieter hat kein Zugriffstoken geliefert.")
    return access_token


def oauth2_auth_string(username, access_token):
    if not username or not access_token:
        raise MailAuthenticationError("Die OAuth2-Anmeldedaten sind unvollständig.")
    return f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")


def revoke_remote_access(account):
    """Best-effort provider revocation without requesting broader permissions."""
    provider_id = normalize_provider(account.get("provider"))
    if provider_id != "google":
        # Microsoft has no narrow per-token revocation endpoint for this flow;
        # requesting Graph administration scopes merely to disconnect would
        # violate least privilege. Apple/manual passwords are revoked by users.
        return False
    token = load_refresh_token(account.get("id"))
    if not token:
        return False
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/revoke",
        data=urllib.parse.urlencode({"token": token}).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
