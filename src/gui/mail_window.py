import customtkinter as ctk
from tkinter import messagebox
import imaplib
import keyring

from src.config import Config


class MailWindow(ctk.CTkToplevel):

    def __init__(self, master=None, config=None):
        super().__init__(master)

        self.config = config if config else Config()

        self.title("E-Mail Integration")
        self.geometry("420x450")

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.create_ui()
        self.load_values()

    
    # UI
    
    def create_ui(self):

        ctk.CTkLabel(self, text="E-Mail Integration").pack(pady=(16, 8))

        self.mail_enabled = ctk.CTkCheckBox(self, text="E-Mail Abruf aktiv")
        self.mail_enabled.pack(pady=6)

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
        self.mail_provider.pack(padx=20, pady=(6, 0), fill="x")

        self.mail_server_entry = ctk.CTkEntry(self, placeholder_text="IMAP Server")
        self.mail_server_entry.pack(padx=20, pady=(6, 0), fill="x")

        self.mail_user_entry = ctk.CTkEntry(self, placeholder_text="E-Mail Adresse")
        self.mail_user_entry.pack(padx=20, pady=(6, 0), fill="x")

        self.mail_pass_entry = ctk.CTkEntry(self, placeholder_text="App-Passwort", show="*")
        self.mail_pass_entry.pack(padx=20, pady=(6, 0), fill="x")

        ctk.CTkButton(self, text="Verbindung testen", command=self.test_mail_connection).pack(pady=12)

        ctk.CTkButton(self, text="Zugangsdaten löschen", command=self.clear_credentials).pack(pady=6)

        ctk.CTkButton(self, text="Speichern", command=self.save).pack(pady=12)

    
    # LOAD
    
    def load_values(self):

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
        if user and email_cfg.get("enabled"):
            self.mail_user_entry.insert(0, user)

    
    # SAVE
    
    def save(self):

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

        messagebox.showinfo("Erfolg", "Gespeichert")
        self.destroy()

    
    # HELPERS
    
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
            messagebox.showerror("Fehler", f"{e}")

    def clear_credentials(self):
        try:
            keyring.delete_password("SorterinoMail", "email_user")
            keyring.delete_password("SorterinoMail", "email_pass")
        except:
            pass

        self.mail_user_entry.delete(0, "end")
        self.mail_pass_entry.delete(0, "end")

        messagebox.showinfo("Erfolg", "Zugangsdaten gelöscht")
