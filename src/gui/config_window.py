import threading
import json
import imaplib
from tkinter import Toplevel, Text, Button, END, messagebox

import customtkinter as ctk

from src.gui.storage_window import StorageWindow
from src.config import Config
from src.autostart_service import AutostartService

import keyring


class ConfigWindow(ctk.CTkToplevel):

    def __init__(self, master=None, config=None, on_change=None):
        super().__init__(master)

        self.on_change = on_change
        self.config = config if config else Config()

        self.autostart_service = AutostartService()

        self._pipeline_running = False
        self._auto_thread = None

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.title("Konfiguration")
        self.geometry("400x875")

        self.create_ui()
        self.after(0, self.load_values)

    # =========================
    # UI
    # =========================
    def create_ui(self):

        self.storage_btn = ctk.CTkButton(self, text="Speicherort", command=self.open_storage)
        self.storage_btn.pack(pady=10)

        self.auto_mode_checkbox = ctk.CTkCheckBox(self, text="Automatikmodus", command=self.toggle_auto_mode)
        self.auto_mode_checkbox.pack(pady=5)

        self.autostart_checkbox = ctk.CTkCheckBox(self, text="Autostart", command=self.toggle_autostart)
        self.autostart_checkbox.pack(pady=5)

        ctk.CTkLabel(self, text="Firmenname").pack(pady=(15, 0))
        self.company_entry = ctk.CTkEntry(self, placeholder_text="Firmenname")
        self.company_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Keywords (Komma getrennt)").pack(pady=(10, 0))
        self.keywords_entry = ctk.CTkEntry(self, placeholder_text="Keywords")
        self.keywords_entry.pack(padx=20, fill="x")

        self.street_entry = ctk.CTkEntry(self, placeholder_text="Straße")
        self.street_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.zip_entry = ctk.CTkEntry(self, placeholder_text="PLZ")
        self.zip_entry.pack(padx=20, fill="x")

        self.city_entry = ctk.CTkEntry(self, placeholder_text="Stadt")
        self.city_entry.pack(padx=20, fill="x")

        self.email_entry = ctk.CTkEntry(self, placeholder_text="E-Mail")
        self.email_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.phone_entry = ctk.CTkEntry(self, placeholder_text="Telefon")
        self.phone_entry.pack(padx=20, fill="x")

        self.iban_entry = ctk.CTkEntry(self, placeholder_text="IBAN")
        self.iban_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.tax_entry = ctk.CTkEntry(self, placeholder_text="USt.-ID")
        self.tax_entry.pack(padx=20, fill="x")

        ctk.CTkButton(self, text="Regeln bearbeiten", command=self.edit_rules).pack(pady=5)
        ctk.CTkButton(self, text="Struktur bearbeiten", command=self.edit_structure).pack(pady=5)

        # =========================
        # MAIL
        # =========================
        ctk.CTkLabel(self, text="E-Mail Integration").pack(pady=(20, 0))

        self.mail_enabled = ctk.CTkCheckBox(self, text="E-Mail Abruf aktiv")
        self.mail_enabled.pack(pady=5)

        self.mail_provider = ctk.CTkOptionMenu(
            self,
            values=[
                "Benutzerdefiniert",
                "Gmail",
                "Outlook / Hotmail",
                "GMX",
                "Web.de",
                "IONOS",
                "iCloud"
            ],
            command=self.on_provider_change
        )
        self.mail_provider.pack(padx=20, pady=(5, 0), fill="x")

        self.mail_server_entry = ctk.CTkEntry(self, placeholder_text="IMAP Server")
        self.mail_server_entry.pack(padx=20, fill="x")

        self.mail_user_entry = ctk.CTkEntry(self, placeholder_text="E-Mail Adresse")
        self.mail_user_entry.pack(padx=20, fill="x")

        self.mail_pass_entry = ctk.CTkEntry(self, placeholder_text="App-Passwort", show="*")
        self.mail_pass_entry.pack(padx=20, fill="x")

        self.mail_test_btn = ctk.CTkButton(
            self,
            text="Verbindung testen",
            command=self.test_mail_connection
        )
        self.mail_test_btn.pack(pady=10)

        self.save_btn = ctk.CTkButton(self, text="Speichern", command=self.save_company_profile)
        self.save_btn.pack(pady=15)

    # =========================
    # LOAD
    # =========================
    def load_values(self):

        def safe_insert(entry, value):
            if value:
                entry.insert(0, value)

        self.config = Config()

        if self.config.get("auto_mode"):
            self.auto_mode_checkbox.select()

        if self.config.get("autostart"):
            self.autostart_checkbox.select()

        company = self.config.get("company_profile") or {}

        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        safe_insert(self.company_entry, company.get("name"))
        safe_insert(self.keywords_entry, ", ".join(company.get("keywords", [])))
        safe_insert(self.street_entry, address.get("street"))
        safe_insert(self.zip_entry, address.get("zip"))
        safe_insert(self.city_entry, address.get("city"))
        safe_insert(self.email_entry, contact.get("email"))
        safe_insert(self.phone_entry, contact.get("phone"))
        safe_insert(self.iban_entry, financial.get("iban"))
        safe_insert(self.tax_entry, financial.get("tax_id"))

        email_cfg = self.config.get("email") or {}

        if email_cfg.get("enabled"):
            self.mail_enabled.select()

        server = email_cfg.get("imap_server")

        provider_map = {
            "imap.gmail.com": "Gmail",
            "imap-mail.outlook.com": "Outlook / Hotmail",
            "imap.gmx.net": "GMX",
            "imap.web.de": "Web.de",
            "imap.ionos.de": "IONOS",
            "imap.mail.me.com": "iCloud"
        }

        if server:
            self.mail_server_entry.insert(0, server)
            self.mail_provider.set(provider_map.get(server, "Benutzerdefiniert"))
        else:
            self.mail_provider.set("Benutzerdefiniert")

        user = keyring.get_password("SorterinoMail", "email_user")
        if user:
            self.mail_user_entry.insert(0, user)

    # =========================
    # SAVE
    # =========================
    def save_company_profile(self):

        data = {
            "name": self.company_entry.get().strip(),
            "keywords": [k.strip().lower() for k in self.keywords_entry.get().split(",") if k.strip()],
            "address": {
                "street": self.street_entry.get().strip(),
                "zip": self.zip_entry.get().strip(),
                "city": self.city_entry.get().strip()
            },
            "contact": {
                "email": self.email_entry.get().strip(),
                "phone": self.phone_entry.get().strip()
            },
            "financial": {
                "iban": self.iban_entry.get().strip(),
                "tax_id": self.tax_entry.get().strip()
            }
        }

        self.config.set("company_profile", data)

        email_data = {
            "enabled": self.mail_enabled.get() == 1,
            "imap_server": self.mail_server_entry.get().strip()
        }

        self.config.set("email", email_data)

        user = self.mail_user_entry.get().strip()
        password = self.mail_pass_entry.get().strip()

        if user and password:
            keyring.set_password("SorterinoMail", "email_user", user)
            keyring.set_password("SorterinoMail", "email_pass", password)

        self.mail_pass_entry.delete(0, "end")

        if self.on_change:
            self.on_change()

    # =========================
    # MAIL
    # =========================
    def on_provider_change(self, choice):
        mapping = {
            "Gmail": "imap.gmail.com",
            "Outlook / Hotmail": "imap-mail.outlook.com",
            "GMX": "imap.gmx.net",
            "Web.de": "imap.web.de",
            "IONOS": "imap.ionos.de",
            "iCloud": "imap.mail.me.com"
        }

        if choice in mapping:
            self.mail_server_entry.delete(0, "end")
            self.mail_server_entry.insert(0, mapping[choice])

    def test_mail_connection(self):

        server = self.mail_server_entry.get().strip()
        user = self.mail_user_entry.get().strip()
        password = self.mail_pass_entry.get().strip()

        # 🔥 fallback aus keyring
        if not password:
            password = keyring.get_password("SorterinoMail", "email_pass")

        if not server or not user or not password:
            messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen")
            return

        try:
            mail = imaplib.IMAP4_SSL(server)
            mail.login(user, password)
            mail.logout()

            messagebox.showinfo("Erfolg", "Verbindung erfolgreich!")

        except Exception as e:
            messagebox.showerror("Fehler", f"Verbindung fehlgeschlagen:\n{e}")

    # =========================
    # REST
    # =========================
    def toggle_auto_mode(self):
        value = self.auto_mode_checkbox.get() == 1
        self.config.set("auto_mode", value)

        if value:
            print("[AUTO] aktiviert")
        else:
            print("[AUTO] deaktiviert")

    def toggle_autostart(self):
        value = self.autostart_checkbox.get() == 1
        self.config.set("autostart", value)

        if value:
            self.autostart_service.enable()
        else:
            self.autostart_service.disable()

    def open_storage(self):
        StorageWindow(self, config=self.config, on_change=self.on_change)

    def edit_rules(self):
        from pathlib import Path

        user_path = self.config.get("user_path")
        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        self._open_json_editor("Regeln bearbeiten", Path(user_path) / ".sorterino_runtime" / "rules.json")

    def edit_structure(self):
        from pathlib import Path

        user_path = self.config.get("user_path")
        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        self._open_json_editor("Struktur bearbeiten", Path(user_path) / ".sorterino_runtime" / "structure.json")

    def _open_json_editor(self, title, file_path):

        window = Toplevel(self)
        window.title(title)
        window.geometry("700x600")

        text = Text(window)
        text.pack(expand=True, fill="both")

        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.dumps(json.load(f), indent=2)
            else:
                content = "{}"
        except Exception as e:
            content = str(e)

        text.insert("1.0", content)

        def save():
            try:
                data = json.loads(text.get("1.0", END))
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                messagebox.showinfo("Erfolg", "Gespeichert")
                window.destroy()
            except Exception as e:
                messagebox.showerror("Fehler", str(e))

        Button(window, text="Speichern", command=save).pack(pady=10)