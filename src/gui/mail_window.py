import queue
import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from src.gui.embedded import EmbeddedPage
from src.mail_auth import (
    MailAuthenticationError,
    PROVIDERS,
    auth_method_for_provider,
    authorize_interactively,
    delete_account_credentials,
    delete_password_credential,
    delete_refresh_token,
    delete_microsoft_token_cache,
    has_account_credentials,
    load_password,
    normalize_provider,
    oauth_client_config,
    refresh_access_token,
    revoke_remote_access,
    store_microsoft_token_cache,
    store_refresh_token,
    store_password,
)
from src.mail_fetcher import test_account_connection
from src.profile_service import ProfileService


PROVIDER_LABELS = {definition.label: provider_id for provider_id, definition in PROVIDERS.items()}
PROVIDER_IDS_TO_LABELS = {value: key for key, value in PROVIDER_LABELS.items()}
OAUTH_PROVIDER_IDS = {"google", "microsoft"}
LOOKBACK_OPTIONS = {
    "Ab jetzt – keine vorhandenen Mails": 0,
    "Letzte 7 Tage": 7,
    "Letzte 30 Tage (Standard)": 30,
    "Letzte 90 Tage": 90,
    "Letzte 365 Tage": 365,
}
LOOKBACK_DAYS_TO_LABEL = {days: label for label, days in LOOKBACK_OPTIONS.items()}


def _credential_status(account, config=None):
    if not account:
        return "Noch nicht gespeichert"
    if has_account_credentials(account, config):
        return "Verbunden"
    return "Anmeldung erforderlich"


class ProfileMailAccountsWindow(EmbeddedPage):
    help_context = "mail"

    def __init__(self, master, config, profile_id, on_saved=None):
        super().__init__(master)
        self.config = config
        self.service = ProfileService(config)
        self.profile_id = profile_id
        self.on_saved = on_saved
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(20, 10))
        ctk.CTkLabel(header, text="Profilbezogene Postfächer", font=("Arial", 19, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Postfach hinzufügen", command=self._add).pack(side="right")
        ctk.CTkLabel(
            self,
            text=(
                "Google und Microsoft werden sicher im Browser verbunden. Apple und andere "
                "Anbieter verwenden ein separates App-Passwort."
            ),
            wraplength=720,
        ).pack(anchor="w", padx=22, pady=(0, 10))
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        self.refresh()

    def _add(self):
        self.open_page(
            lambda parent: ProfileMailAccountDialog(
                parent, self.service, self.profile_id, on_saved=self.on_saved
            ),
            "profiles",
        )

    def refresh(self):
        self.service.reload()
        for child in self.list_frame.winfo_children():
            child.destroy()
        accounts = self.service.list_email_accounts(self.profile_id)
        if not accounts:
            ctk.CTkLabel(self.list_frame, text="Noch kein Postfach eingerichtet.").pack(pady=30)
            return
        for account in accounts:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=4)
            provider = PROVIDERS[normalize_provider(account.get("provider"))].label
            ctk.CTkLabel(
                row, text=account.get("label") or account["username"], font=("Arial", 14, "bold")
            ).pack(anchor="w", padx=12, pady=(9, 0))
            state = "Aktiv" if account.get("enabled", True) else "Pausiert"
            ctk.CTkLabel(
                row,
                text=f"{account['username']} · {provider} · {state} · {_credential_status(account, self.config)}",
            ).pack(anchor="w", padx=12, pady=(0, 9))
            ctk.CTkButton(
                row,
                text="Bearbeiten",
                width=90,
                command=lambda account_id=account["id"]: self.open_page(
                    lambda parent: ProfileMailAccountDialog(
                        parent, self.service, self.profile_id, account_id, self.on_saved
                    ),
                    "profiles",
                ),
            ).pack(side="right", padx=10, pady=8)


class ProfileMailAccountDialog(EmbeddedPage):
    help_context = "mail_edit"

    def __init__(self, master, service, profile_id, account_id=None, on_saved=None):
        super().__init__(master)
        self.service = service
        self.config = service.config
        self.profile_id = profile_id
        self.account = service.get_email_account(account_id) if account_id else None
        self.on_saved = on_saved
        self._busy = False
        self._build()
        self._load()

    def _build(self):
        ctk.CTkLabel(
            self,
            text="Postfach bearbeiten" if self.account else "Postfach hinzufügen",
            font=("Arial", 22, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))
        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.form = form
        self.enabled = ctk.CTkCheckBox(form, text="Postfach automatisch abrufen")
        self.enabled.pack(anchor="w", padx=24, pady=(22, 8))
        ctk.CTkLabel(form, text="Anbieter").pack(anchor="w", padx=24, pady=(7, 2))
        self.provider = ctk.CTkOptionMenu(
            form, values=list(PROVIDER_LABELS), command=self._provider_changed
        )
        self.provider.pack(fill="x", padx=24)
        self.label = self._entry("Bezeichnung", "z. B. Familienpostfach")
        self.username = self._entry("E-Mail-Adresse *", "name@example.de")
        ctk.CTkLabel(form, text="Vorhandene Mails beim ersten Abruf prüfen").pack(
            anchor="w", padx=24, pady=(12, 2)
        )
        self.initial_lookback = ctk.CTkOptionMenu(form, values=list(LOOKBACK_OPTIONS))
        self.initial_lookback.pack(fill="x", padx=24)
        ctk.CTkLabel(
            form,
            text=(
                "Diese Auswahl gilt nur beim ersten erfolgreichen Abruf. Danach erkennt "
                "Sorterino alle neuen Mails unabhängig vom Gelesen-Status."
            ),
            justify="left",
            wraplength=670,
        ).pack(anchor="w", padx=24, pady=(3, 4))

        self.connection = ctk.CTkFrame(form)
        self.connection.pack(fill="x", padx=24, pady=(16, 4))
        self.connection_title = ctk.CTkLabel(
            self.connection, text="Sichere Verbindung", font=("Arial", 15, "bold")
        )
        self.connection_title.pack(anchor="w", padx=14, pady=(12, 2))
        self.connection_info = ctk.CTkLabel(
            self.connection, text="", justify="left", wraplength=670
        )
        self.connection_info.pack(anchor="w", padx=14, pady=(0, 8))
        self.oauth_button = ctk.CTkButton(
            self.connection, text="Im Browser verbinden", command=self._connect_oauth
        )
        self.oauth_button.pack(anchor="w", padx=14, pady=(0, 8))

        self.password_frame = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.password_frame, text="App-Passwort *").pack(anchor="w", pady=(7, 2))
        self.password = ctk.CTkEntry(self.password_frame, show="•")
        self.password.pack(fill="x")
        self.apple_help = ctk.CTkButton(
            self.password_frame,
            text="App-Passwort bei Apple erstellen",
            fg_color="transparent",
            border_width=1,
            command=lambda: webbrowser.open("https://account.apple.com/account/manage"),
        )

        self.advanced = ctk.CTkFrame(form, fg_color="transparent")
        self.advanced.pack(fill="x", padx=24, pady=(4, 0))
        self.server = self._entry_in(self.advanced, "IMAP-Server", "imap.example.de")
        self.port = self._entry_in(self.advanced, "IMAP-Port", "993")
        self.mailbox = self._entry_in(self.advanced, "Postfach", "INBOX")

        self.status = ctk.CTkLabel(form, text="", justify="left")
        self.status.pack(anchor="w", padx=24, pady=(12, 2))
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=20)
        self.test_button = ctk.CTkButton(actions, text="Verbindung testen", command=self._test)
        self.test_button.pack(side="left")
        ctk.CTkButton(actions, text="Speichern", command=self._save).pack(side="right")
        if self.account:
            ctk.CTkButton(
                form,
                text="Postfach entfernen",
                fg_color="transparent",
                text_color=("#8a1f1f", "#ff8a8a"),
                border_width=1,
                command=self._remove,
            ).pack(side="bottom", pady=(20, 8))

    def _entry(self, label, placeholder):
        return self._entry_in(self.form, label, placeholder, padx=24)

    @staticmethod
    def _entry_in(parent, label, placeholder, padx=0):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=padx, pady=(7, 2))
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        entry.pack(fill="x", padx=padx)
        return entry

    def _load(self):
        self.enabled.select()
        self.initial_lookback.set(LOOKBACK_DAYS_TO_LABEL[30])
        provider_id = "custom"
        self.mailbox.insert(0, "INBOX")
        self.port.insert(0, "993")
        if self.account:
            provider_id = normalize_provider(self.account.get("provider"))
            if not self.account.get("enabled", True):
                self.enabled.deselect()
            for entry, value in (
                (self.label, self.account.get("label")),
                (self.username, self.account.get("username")),
                (self.server, self.account.get("imap_server")),
            ):
                if value:
                    entry.insert(0, value)
            self.port.delete(0, "end")
            self.port.insert(0, str(self.account.get("imap_port") or 993))
            self.mailbox.delete(0, "end")
            self.mailbox.insert(0, self.account.get("mailbox") or "INBOX")
            try:
                lookback_days = int(self.account.get("initial_lookback_days", 30))
            except (TypeError, ValueError):
                lookback_days = 30
            self.initial_lookback.set(LOOKBACK_DAYS_TO_LABEL.get(lookback_days, LOOKBACK_DAYS_TO_LABEL[30]))
            if has_account_credentials(self.account, self.config):
                self.initial_lookback.configure(state="disabled")
        self.provider.set(PROVIDER_IDS_TO_LABELS[provider_id])
        if self.account:
            self.provider.configure(state="disabled")
        self._render_auth_mode(provider_id, populate_server=(provider_id != "custom"))

    def _provider_changed(self, provider_label):
        self._render_auth_mode(PROVIDER_LABELS[provider_label], populate_server=True)

    def _render_auth_mode(self, provider_id, populate_server=False):
        definition = PROVIDERS[provider_id]
        self.server.configure(state="normal")
        self.port.configure(state="normal")
        if populate_server and definition.imap_server:
            self.server.delete(0, "end")
            self.server.insert(0, definition.imap_server)
        if provider_id in OAUTH_PROVIDER_IDS:
            self.password_frame.pack_forget()
            self.oauth_button.pack(anchor="w", padx=14, pady=(0, 8))
            self.connection_info.configure(
                text=(
                    "Die Anmeldung erfolgt direkt beim Anbieter im Standardbrowser. Sorterino "
                    "erhält niemals dein Passwort. Die notwendige IMAP-Berechtigung kann technisch "
                    "das gesamte Postfach lesen. Sorterino liest nur neue Nachrichten und Anhänge, "
                    "verändert keine Mail-Markierungen und versendet oder löscht nichts."
                )
            )
            self.oauth_button.configure(text=f"Mit {definition.label} verbinden")
        else:
            self.oauth_button.pack_forget()
            self.password_frame.pack(fill="x", padx=24, pady=(4, 0), before=self.advanced)
            self.connection_info.configure(
                text=(
                    "Verwende ein nur für Sorterino erzeugtes App-Passwort – niemals dein "
                    "normales Kontopasswort. Es wird im Windows-Anmeldeinformationsspeicher geschützt."
                )
            )
            if provider_id == "apple":
                self.apple_help.pack(anchor="w", pady=(8, 2))
            else:
                self.apple_help.pack_forget()
        locked = "disabled" if provider_id != "custom" else "normal"
        self.server.configure(state=locked)
        self.port.configure(state=locked)
        self.status.configure(text=_credential_status(self.account, self.config))

    def _values(self):
        provider_id = PROVIDER_LABELS[self.provider.get()]
        return {
            "label": self.label.get().strip(),
            "enabled": bool(self.enabled.get()),
            "provider": provider_id,
            "auth_method": auth_method_for_provider(provider_id),
            "imap_server": self.server.get().strip(),
            "imap_port": int(self.port.get().strip() or 993),
            "username": self.username.get().strip(),
            "mailbox": self.mailbox.get().strip() or "INBOX",
            "initial_lookback_days": LOOKBACK_OPTIONS.get(self.initial_lookback.get(), 30),
        }

    def _persist(self):
        previous_username = str((self.account or {}).get("username") or "").strip().casefold()
        account = self.service.save_email_account(
            self.profile_id, self._values(), self.account["id"] if self.account else None
        )
        self.account = account
        password = self.password.get().strip()
        if account.get("auth_method") == "oauth2":
            if previous_username and previous_username != account.get("username", "").strip().casefold():
                if account.get("provider") == "microsoft":
                    delete_microsoft_token_cache(self.config, account["id"])
                else:
                    delete_refresh_token(account["id"])
        else:
            username_changed = (
                previous_username
                and previous_username != account.get("username", "").strip().casefold()
            )
            if password:
                store_password(account["id"], password)
            elif username_changed:
                delete_password_credential(account["id"])
        return account

    def _save(self):
        try:
            account = self._persist()
            if not self.on_saved or not self.on_saved(self.profile_id):
                self.finish()
        except Exception as exc:
            messagebox.showerror("Postfach konnte nicht gespeichert werden", str(exc), parent=self)

    def _set_busy(self, busy, text=None):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.oauth_button.configure(state=state)
        self.test_button.configure(state=state)
        if text:
            self.status.configure(text=text)

    def _run_async(
        self, operation, success_text, on_success=None,
        busy_text="Sichere Verbindung wird hergestellt …",
    ):
        if self._busy:
            return
        self._set_busy(True, busy_text)

        results = queue.Queue(maxsize=1)

        def worker():
            try:
                operation_result = operation()
            except Exception as exc:
                error = exc if isinstance(exc, MailAuthenticationError) else MailAuthenticationError(
                    "Die Verbindung konnte nicht sicher hergestellt werden."
                )
                results.put((False, str(error)))
            else:
                results.put((True, operation_result))

        def poll():
            try:
                succeeded, result = results.get_nowait()
            except queue.Empty:
                if self.winfo_exists():
                    self.after(100, poll)
                return
            if succeeded:
                if on_success:
                    self._set_busy(False)
                    on_success(result)
                else:
                    self._finish_async_success(success_text)
            else:
                self._finish_async_error(result)

        threading.Thread(target=worker, name="SorterinoMailAuth", daemon=True).start()
        self.after(100, poll)

    def _finish_async_success(self, text):
        self._set_busy(False, text)
        messagebox.showinfo("Verbindung erfolgreich", text, parent=self)

    def _finish_async_error(self, text):
        self._set_busy(False, "Verbindung fehlgeschlagen")
        messagebox.showerror("Verbindung fehlgeschlagen", text, parent=self)

    def _connect_oauth(self):
        try:
            account = self._persist()
            oauth_client_config(self.config, account["provider"])
        except Exception as exc:
            messagebox.showerror("OAuth2 ist noch nicht eingerichtet", str(exc), parent=self)
            return

        def operation():
            grant = authorize_interactively(self.config, account["provider"])
            test_account_connection(account, grant.access_token)
            # Persist only after the token has authenticated the exact configured
            # mailbox; a wrong browser account must not appear as connected.
            if account["provider"] == "microsoft":
                store_microsoft_token_cache(self.config, account["id"], grant.token_cache)
            else:
                store_refresh_token(account["id"], grant.refresh_token)
            delete_password_credential(account["id"])

        self._run_async(operation, "Das Postfach ist sicher verbunden.")

    def _test(self):
        try:
            account = self._persist()
        except Exception as exc:
            messagebox.showerror("Angaben prüfen", str(exc), parent=self)
            return

        entered_password = self.password.get().strip()

        def operation():
            if account.get("auth_method") == "oauth2":
                credential = refresh_access_token(self.config, account)
            else:
                credential = entered_password or load_password(account["id"])
            test_account_connection(account, credential)

        self._run_async(operation, "Sorterino kann sicher auf das Postfach zugreifen.")

    def _remove(self):
        if not messagebox.askyesno(
            "Postfach entfernen",
            "Dieses Postfach aus Sorterino entfernen und alle lokal gespeicherten Zugangsdaten löschen?",
            parent=self,
        ):
            return
        account = dict(self.account)

        def operation():
            revoked = revoke_remote_access(account)
            delete_account_credentials(account["id"], self.config)
            self.service.remove_email_account(account["id"])
            return revoked

        def finished(revoked):
            provider = normalize_provider(account.get("provider"))
            if provider == "google" and revoked:
                note = "Der Google-Zugriff und alle lokalen Zugangsdaten wurden widerrufen."
            elif provider == "google":
                note = (
                    "Die lokalen Zugangsdaten wurden gelöscht. Der Google-Zugriff konnte nicht "
                    "online bestätigt werden; prüfe ihn zusätzlich in deinem Google-Konto."
                )
            else:
                note = (
                    "Die lokalen Zugangsdaten wurden gelöscht. Widerrufe den Zugriff beziehungsweise "
                    "das App-Passwort bei Bedarf zusätzlich im Konto des Anbieters."
                )
            messagebox.showinfo("Postfach entfernt", note, parent=self)
            self.finish()

        self._run_async(
            operation,
            "Postfach entfernt.",
            on_success=finished,
            busy_text="Zugriff wird sicher getrennt …",
        )
