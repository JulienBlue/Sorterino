import email
import hashlib
import imaplib
import json
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

from src.document_formats import SUPPORTED_EXTENSIONS
from src.mail_auth import (
    MailAuthenticationError,
    load_password,
    oauth2_auth_string,
    refresh_access_token,
    secure_ssl_context,
    validate_imap_settings,
)


ALLOWED_EXTENSIONS = SUPPORTED_EXTENSIONS
LEGACY_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_MESSAGE_BYTES = 50 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 50
MAX_MESSAGES_PER_RUN = 250
DEFAULT_INITIAL_LOOKBACK_DAYS = 30
MAX_TRACKED_MESSAGE_KEYS = 5000
MAX_TRACKED_ATTACHMENT_KEYS = 10000


def decode_filename(name):
    if not name:
        return None
    parts = []
    for value, encoding in decode_header(name):
        if isinstance(value, bytes):
            value = value.decode(encoding or "utf-8", errors="replace")
        parts.append(str(value))
    return "".join(parts).strip() or None


class MailImportState:
    """Durable IMAP cursor and invisible source-to-profile routing metadata."""

    def __init__(self, config):
        self.path = Path(config.state_root) / "mail_import_state.json"
        self.data = self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError):
            value = {}
        if not isinstance(value, dict):
            value = {}
        value.setdefault("schema_version", 1)
        value.setdefault("accounts", {})
        value.setdefault("files", {})
        return value

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=".mail_import_state.", suffix=".tmp", delete=False,
            ) as handle:
                json.dump(self.data, handle, indent=2, ensure_ascii=False)
                handle.flush()
                temp_path = Path(handle.name)
            temp_path.replace(self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _file_key(path):
        try:
            value = str(Path(path).resolve())
        except OSError:
            value = str(Path(path).absolute())
        return value.casefold()

    def prepare_account(self, account_id, uid_validity):
        accounts = self.data.setdefault("accounts", {})
        state = accounts.setdefault(account_id, {})
        previous_validity = str(state.get("uid_validity") or "")
        current_validity = str(uid_validity or "unknown")
        if previous_validity and previous_validity != current_validity:
            message_keys = list(state.get("message_keys", []))
            attachment_keys = list(state.get("attachment_keys", []))
            state.clear()
            state["message_keys"] = message_keys[-MAX_TRACKED_MESSAGE_KEYS:]
            state["attachment_keys"] = attachment_keys[-MAX_TRACKED_ATTACHMENT_KEYS:]
        state.setdefault("last_uid", 0)
        state.setdefault("message_keys", [])
        state.setdefault("attachment_keys", [])
        state["uid_validity"] = current_validity
        return state

    def attachment_seen(self, account_state, attachment_key):
        return attachment_key in set(account_state.get("attachment_keys", []))

    def record_attachment(self, account, account_state, attachment_key, path, message_uid):
        keys = account_state.setdefault("attachment_keys", [])
        if attachment_key not in keys:
            keys.append(attachment_key)
            del keys[:-MAX_TRACKED_ATTACHMENT_KEYS]
        self.data.setdefault("files", {})[self._file_key(path)] = {
            "profile_id": account.get("profile_id"),
            "account_id": account.get("id"),
            "message_uid": str(message_uid),
        }
        self.save()

    def finish_message(self, account_state, uid, message_key):
        keys = account_state.setdefault("message_keys", [])
        if message_key not in keys:
            keys.append(message_key)
            del keys[:-MAX_TRACKED_MESSAGE_KEYS]
        account_state["last_uid"] = max(int(account_state.get("last_uid") or 0), int(uid))
        self.save()

    def advance_cursor(self, account_state, uid):
        account_state["last_uid"] = max(int(account_state.get("last_uid") or 0), int(uid))
        self.save()

    def profile_hint(self, source_path, profile_service):
        entry = self.data.get("files", {}).get(self._file_key(source_path)) or {}
        account = profile_service.get_email_account(entry.get("account_id")) if entry else None
        if account and account.get("profile_id") == entry.get("profile_id"):
            return entry.get("profile_id")
        return None

    def file_info(self, source_path):
        """Return non-secret mail provenance for a currently imported file."""
        entry = self.data.get("files", {}).get(self._file_key(source_path)) or {}
        return dict(entry) if entry else None

    def prune(self, active_account_ids=None):
        existing_files = dict(self.data.get("files", {}))
        self.data["files"] = {
            key: value for key, value in existing_files.items()
            if Path(key).exists()
        }
        if active_account_ids is not None:
            active = set(active_account_ids)
            self.data["accounts"] = {
                key: value for key, value in self.data.get("accounts", {}).items()
                if key in active
            }
        self.save()


def mail_profile_hint(config, source_path, profile_service):
    if not getattr(config, "state_root", None):
        return None
    return MailImportState(config).profile_hint(source_path, profile_service)


def fetch_attachments(config, profile_service=None):
    """Fetch every profile mailbox without relying on read/unread flags."""
    if not config.incoming_root:
        print("[MAIL] Eingangsordner fehlt")
        return 0
    accounts = profile_service.list_email_accounts(enabled_only=True) if profile_service else []
    state_store = MailImportState(config)
    state_store.prune(account.get("id") for account in accounts)
    total = 0
    for account in accounts:
        _migrate_legacy_account_folder(config.incoming_root, account, state_store)
        try:
            if account.get("auth_method") == "oauth2":
                credential = refresh_access_token(config, account)
            else:
                credential = load_password(account["id"])
        except MailAuthenticationError as exc:
            print(f"[MAIL] {account.get('label') or 'Postfach'}: {exc}")
            continue
        total += fetch_account(
            account,
            credential,
            Path(config.incoming_root),
            state_store=state_store,
        )
    return total


def fetch_account(
    account, credential, target_directory, imap_factory=imaplib.IMAP4_SSL,
    state_store=None,
):
    try:
        server, port, username = validate_imap_settings(account)
    except MailAuthenticationError as exc:
        print(f"[MAIL] {account.get('label') or 'Postfach'}: {exc}")
        return 0
    if not account.get("enabled", True) or not credential:
        print(f"[MAIL] Konto '{account.get('label') or 'Unbenannt'}' ist unvollständig")
        return 0
    target = Path(target_directory)
    target.mkdir(parents=True, exist_ok=True)
    extensions = {
        str(value).lower() for value in account.get("allowed_extensions", ALLOWED_EXTENSIONS)
    }
    if extensions == LEGACY_ALLOWED_EXTENSIONS:
        extensions = ALLOWED_EXTENSIONS
    mailbox = account.get("mailbox") or "INBOX"
    mail = None
    saved_count = 0
    try:
        try:
            mail = imap_factory(server, port, ssl_context=secure_ssl_context())
        except TypeError:
            mail = imap_factory(server, port)
        if account.get("auth_method") == "oauth2":
            mail.authenticate("XOAUTH2", lambda _challenge: oauth2_auth_string(username, credential))
        else:
            mail.login(username, credential)
        try:
            status, _ = mail.select(mailbox, readonly=True)
        except TypeError:
            status, _ = mail.select(mailbox)
        if status != "OK":
            print(f"[MAIL] Postfach '{mailbox}' konnte nicht geöffnet werden")
            return 0

        uid_validity = _imap_response_number(mail, "UIDVALIDITY") or "unknown"
        account_state = (
            state_store.prepare_account(account["id"], uid_validity)
            if state_store else {"uid_validity": uid_validity, "last_uid": 0, "message_keys": [], "attachment_keys": []}
        )
        last_uid = int(account_state.get("last_uid") or 0)
        first_scan = last_uid <= 0
        if first_scan:
            lookback = _bounded_lookback_days(account.get("initial_lookback_days"))
            if lookback == 0:
                uid_next = _imap_response_number(mail, "UIDNEXT")
                if uid_next and state_store:
                    state_store.advance_cursor(account_state, max(0, int(uid_next) - 1))
                return 0
            since = _imap_date(datetime.now() - timedelta(days=lookback))
            status, messages = mail.uid("search", None, "SINCE", since)
        else:
            status, messages = mail.uid("search", None, "UID", f"{last_uid + 1}:*")
        if status != "OK":
            return 0
        uids = _numeric_uids(messages)
        selected_uids = uids[:MAX_MESSAGES_PER_RUN]
        known_messages = set(account_state.get("message_keys", []))
        completed_all = True

        for uid in selected_uids:
            status, message_data = mail.uid("fetch", str(uid).encode("ascii"), "(BODY.PEEK[])")
            if status != "OK" or not message_data or not message_data[0]:
                # Preserve a gap: a later run must retry this UID before moving on.
                completed_all = False
                break
            raw_message = message_data[0][1]
            if not isinstance(raw_message, bytes) or len(raw_message) > MAX_MESSAGE_BYTES:
                print(f"[MAIL] {account.get('label') or 'Postfach'}: Nachricht ist zu groß und wurde übersprungen")
                if state_store:
                    state_store.advance_cursor(account_state, uid)
                else:
                    account_state["last_uid"] = uid
                continue
            try:
                message = email.message_from_bytes(raw_message)
            except Exception:
                if state_store:
                    state_store.advance_cursor(account_state, uid)
                continue
            message_key = _message_key(message, uid_validity, uid)
            if message_key in known_messages:
                if state_store:
                    state_store.advance_cursor(account_state, uid)
                continue
            examined_attachments = 0
            for index, part in enumerate(message.walk()):
                if part.get_content_disposition() != "attachment":
                    continue
                examined_attachments += 1
                if examined_attachments > MAX_ATTACHMENTS_PER_MESSAGE:
                    break
                filename = decode_filename(part.get_filename())
                safe_name = Path(filename).name if filename else ""
                if (
                    not safe_name
                    or len(safe_name) > 240
                    or any(ord(char) < 32 or ord(char) == 127 for char in safe_name)
                    or Path(safe_name).suffix.lower() not in extensions
                ):
                    continue
                payload = part.get_payload(decode=True)
                if not payload or len(payload) > MAX_ATTACHMENT_BYTES:
                    continue
                attachment_key = _attachment_key(message_key, index, safe_name, payload)
                if state_store and state_store.attachment_seen(account_state, attachment_key):
                    continue
                destination = _unique_path(target / safe_name)
                destination.write_bytes(payload)
                saved_count += 1
                if state_store:
                    state_store.record_attachment(
                        account, account_state, attachment_key, destination, uid
                    )
            if state_store:
                state_store.finish_message(account_state, uid, message_key)
            else:
                account_state["last_uid"] = uid
            known_messages.add(message_key)

        # On an empty/fully drained first scan, UIDNEXT lets us anchor the cursor
        # at the current mailbox end without downloading older mail next time.
        if first_scan and completed_all and len(uids) <= MAX_MESSAGES_PER_RUN:
            uid_next = _imap_response_number(mail, "UIDNEXT")
            if uid_next and state_store:
                state_store.advance_cursor(account_state, max(0, int(uid_next) - 1))
        return saved_count
    except Exception:
        print(f"[MAIL ERROR] {account.get('label') or 'Postfach'}: Sicherer Abruf fehlgeschlagen")
        return saved_count
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def test_account_connection(account, credential, imap_factory=imaplib.IMAP4_SSL):
    """Authenticate and open the configured mailbox without reading a message."""
    server, port, username = validate_imap_settings(account)
    if not credential:
        raise MailAuthenticationError("Für das Postfach sind keine Zugangsdaten gespeichert.")
    mail = None
    try:
        try:
            mail = imap_factory(server, port, ssl_context=secure_ssl_context())
        except TypeError:
            mail = imap_factory(server, port)
        if account.get("auth_method") == "oauth2":
            mail.authenticate("XOAUTH2", lambda _challenge: oauth2_auth_string(username, credential))
        else:
            mail.login(username, credential)
        status, _ = mail.select(account.get("mailbox") or "INBOX", readonly=True)
        if status != "OK":
            raise MailAuthenticationError("Das ausgewählte Postfach konnte nicht geöffnet werden.")
        return True
    except MailAuthenticationError:
        raise
    except Exception as exc:
        raise MailAuthenticationError(
            "Die sichere Anmeldung am Mailserver ist fehlgeschlagen. "
            "Prüfe Adresse, Freigabe und Zugangsdaten."
        ) from exc
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def _migrate_legacy_account_folder(incoming_root, account, state_store):
    root = Path(incoming_root)
    legacy = root / str(account.get("profile_id") or "") / str(account.get("id") or "")
    try:
        if not legacy.is_dir() or root.resolve() not in legacy.resolve().parents:
            return
    except OSError:
        return
    for source in sorted(path for path in legacy.rglob("*") if path.is_file()):
        destination = _unique_path(root / source.name)
        try:
            shutil.move(str(source), str(destination))
        except OSError:
            continue
        legacy_key = hashlib.sha256(str(source).encode("utf-8", errors="replace")).hexdigest()
        account_state = state_store.prepare_account(account["id"], "legacy")
        state_store.record_attachment(
            account, account_state, f"legacy:{legacy_key}", destination, "legacy"
        )
    for directory in sorted(
        (path for path in legacy.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts), reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        legacy.rmdir()
        legacy.parent.rmdir()
    except OSError:
        pass


def _imap_response_number(mail, name):
    response = getattr(mail, "response", None)
    if not callable(response):
        return None
    try:
        _status, values = response(name)
    except Exception:
        return None
    joined = b" ".join(value for value in (values or []) if isinstance(value, bytes))
    match = re.search(rb"\d+", joined)
    return int(match.group()) if match else None


def _numeric_uids(messages):
    if not messages or not messages[0]:
        return []
    values = []
    for raw in messages[0].split():
        try:
            values.append(int(raw))
        except (TypeError, ValueError):
            continue
    return sorted(set(values))


def _bounded_lookback_days(value):
    try:
        days = int(DEFAULT_INITIAL_LOOKBACK_DAYS if value is None else value)
    except (TypeError, ValueError):
        days = DEFAULT_INITIAL_LOOKBACK_DAYS
    return min(max(days, 0), 365)


def _imap_date(value):
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{value.day:02d}-{months[value.month - 1]}-{value.year:04d}"


def _message_key(message, uid_validity, uid):
    message_id = str(message.get("Message-ID") or "").strip().casefold()
    seed = message_id or f"{uid_validity}:{uid}"
    return hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()


def _attachment_key(message_key, index, filename, payload):
    digest = hashlib.sha256(payload).hexdigest()
    seed = f"{message_key}:{index}:{filename.casefold()}:{digest}"
    return hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()


def _unique_path(path):
    if not path.exists():
        return path
    for counter in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError("Kein eindeutiger Dateiname für den E-Mail-Anhang verfügbar.")
