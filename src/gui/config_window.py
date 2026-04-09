import keyring
import json
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
        self.geometry("400x825")

        self.create_ui()
        self.after(0, self.load_values)

    
    # UI
    
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

        ctk.CTkLabel(self, text="Vorname").pack(pady=(10, 0))
        self.first_name_entry = ctk.CTkEntry(self, placeholder_text="Vorname")
        self.first_name_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Nachname").pack(pady=(10, 0))
        self.last_name_entry = ctk.CTkEntry(self, placeholder_text="Nachname")
        self.last_name_entry.pack(padx=20, fill="x")

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

        self.save_btn = ctk.CTkButton(self, text="Speichern", command=self.save_company_profile)
        self.save_btn.pack(pady=15)

        ctk.CTkButton(self, text="Regeln bearbeiten", command=self.edit_rules).pack(pady=5)
        ctk.CTkButton(self, text="Struktur bearbeiten", command=self.edit_structure).pack(pady=15)

        ctk.CTkButton(self, text="E-Mail Integration", command=self.open_mail_window).pack(pady=5)

    
    # LOAD
    
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
        person = company.get("person", {})

        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        safe_insert(self.company_entry, company.get("name"))
        safe_insert(self.first_name_entry, person.get("first_name"))
        safe_insert(self.last_name_entry, person.get("last_name"))
        safe_insert(self.keywords_entry, ", ".join(company.get("keywords", [])))
        safe_insert(self.street_entry, address.get("street"))
        safe_insert(self.zip_entry, address.get("zip"))
        safe_insert(self.city_entry, address.get("city"))
        safe_insert(self.email_entry, contact.get("email"))
        safe_insert(self.phone_entry, contact.get("phone"))
        safe_insert(self.iban_entry, financial.get("iban"))
        safe_insert(self.tax_entry, financial.get("tax_id"))

    
    # SAVE
    
    def save_company_profile(self):

        data = {
            "name": self.company_entry.get().strip(),
            "person": {
                "first_name": self.first_name_entry.get().strip(),
                "last_name": self.last_name_entry.get().strip()
            },
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

    
    # MAIL
    
    def open_mail_window(self):
        from src.gui.mail_window import MailWindow
        MailWindow(self, config=self.config)

    
    # REST
    
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

    def clear_mail_credentials_ui(self):
        try:
            keyring.delete_password("SorterinoMail", "email_user")
        except:
            pass

        try:
            keyring.delete_password("SorterinoMail", "email_pass")
        except:
            pass

        self.mail_user_entry.delete(0, "end")
        self.mail_pass_entry.delete(0, "end")

        messagebox.showinfo("Erfolg", "E-Mail Zugangsdaten wurden gelöscht")