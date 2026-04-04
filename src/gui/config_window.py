import threading
import json
import tkinter as tk
from tkinter import Toplevel, Text, Button, END, messagebox

import customtkinter as ctk

from src.gui.storage_window import StorageWindow
from src.config.config_loader import Config
from src.config.config_service import ConfigService
from src.autostart_service import AutostartService


class ConfigWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master=None, config=None, on_change=None):
        super().__init__(master)

        self.on_change = on_change

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        if config:
            self.config_service = config
        else:
            self.config_service = ConfigService()

        self.autostart_service = AutostartService()

        self.title("Konfiguration")
        self.geometry("400x650")

        self._pipeline_running = False
        self._auto_thread = None

        self.create_ui()
        self.load_values()

    # UI / BUILD
    def create_ui(self):

        self.storage_btn = ctk.CTkButton(
            self,
            text="Speicherort",
            command=self.open_storage
        )
        self.storage_btn.pack(pady=10)

        self.auto_mode_checkbox = ctk.CTkCheckBox(
            self,
            text="Automatikmodus",
            command=self.toggle_auto_mode
        )
        self.auto_mode_checkbox.pack(pady=5)

        self.autostart_checkbox = ctk.CTkCheckBox(
            self,
            text="Autostart",
            command=self.toggle_autostart
        )
        self.autostart_checkbox.pack(pady=5)

        self.company_label = ctk.CTkLabel(self, text="Firmenname")
        self.company_label.pack(pady=(15, 0))

        self.company_entry = ctk.CTkEntry(self)
        self.company_entry.pack(padx=20, fill="x")

        self.keywords_label = ctk.CTkLabel(self, text="Keywords (Komma getrennt)")
        self.keywords_label.pack(pady=(10, 0))

        self.keywords_entry = ctk.CTkEntry(self)
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

        self.tax_entry = ctk.CTkEntry(self, placeholder_text="Steuer-ID")
        self.tax_entry.pack(padx=20, fill="x")

        self.rules_btn = ctk.CTkButton(
            self,
            text="Regeln bearbeiten",
            command=self.edit_rules
        )
        self.rules_btn.pack(pady=5)

        self.structure_btn = ctk.CTkButton(
            self,
            text="Struktur bearbeiten",
            command=self.edit_structure
        )
        self.structure_btn.pack(pady=5)

        self.save_btn = ctk.CTkButton(
            self,
            text="Firmenprofil speichern",
            command=self.save_company_profile
        )
        self.save_btn.pack(pady=15)

    # CONFIG / LOAD
    def load_values(self):
        if self.config_service.get("auto_mode"):
            self.auto_mode_checkbox.select()

        if self.config_service.get("autostart"):
            self.autostart_checkbox.select()

        company = self.config_service.get("company_profile") or {}

        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        name = company.get("name", "")
        if name:
            self.company_entry.delete(0, "end")
            self.company_entry.insert(0, name)

        keywords = ", ".join(company.get("keywords", []))
        if keywords:
            self.keywords_entry.delete(0, "end")
            self.keywords_entry.insert(0, keywords)

        street = address.get("street", "")
        if street:
            self.street_entry.delete(0, "end")
            self.street_entry.insert(0, street)

        zip_code = address.get("zip", "")
        if zip_code:
            self.zip_entry.delete(0, "end")
            self.zip_entry.insert(0, zip_code)

        city = address.get("city", "")
        if city:
            self.city_entry.delete(0, "end")
            self.city_entry.insert(0, city)

        email = contact.get("email", "")
        if email:
            self.email_entry.delete(0, "end")
            self.email_entry.insert(0, email)

        phone = contact.get("phone", "")
        if phone:
            self.phone_entry.delete(0, "end")
            self.phone_entry.insert(0, phone)

        iban = financial.get("iban", "")
        if iban:
            self.iban_entry.delete(0, "end")
            self.iban_entry.insert(0, iban)

        tax = financial.get("tax_id", "")
        if tax:
            self.tax_entry.delete(0, "end")
            self.tax_entry.insert(0, tax)

    # CONFIG / SAVE
    def save_company_profile(self):
        name = self.company_entry.get().strip()
        keywords = [k.strip().lower() for k in self.keywords_entry.get().split(",") if k.strip()]

        data = {
            "name": name,
            "keywords": keywords,
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

        self.config_service.set("company_profile", data)

    # CONFIG / AUTO MODE
    def toggle_auto_mode(self):
        value = self.auto_mode_checkbox.get() == 1
        self.config_service.set("auto_mode", value)

        if value:
            from main import run_pipeline

            def _auto_loop():
                import time

                while self.config_service.get("auto_mode"):

                    if self._pipeline_running:
                        time.sleep(1)
                        continue

                    self._pipeline_running = True

                    try:
                        run_pipeline()
                    except Exception:
                        time.sleep(10)
                    finally:
                        self._pipeline_running = False

                    time.sleep(5)

            if self._auto_thread is None or not self._auto_thread.is_alive():
                self._auto_thread = threading.Thread(target=_auto_loop, daemon=True)
                self._auto_thread.start()

        if self.on_change:
            self.on_change()

    # CONFIG / AUTOSTART
    def toggle_autostart(self):
        value = self.autostart_checkbox.get() == 1
        self.config_service.set("autostart", value)

        if value:
            self.autostart_service.enable()
        else:
            self.autostart_service.disable()

    # UI / STORAGE
    def open_storage(self):
        StorageWindow(
            self,
            config=self.config_service,
            on_change=self.on_change
        )

    # CONFIG / RULES
    def edit_rules(self):
        from pathlib import Path

        user_path = self.config_service.get("user_path")

        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        runtime = Path(user_path) / ".sorterino_runtime"
        file_path = runtime / "rules.json"

        self._open_json_editor("Regeln bearbeiten", file_path)

    # CONFIG / STRUCTURE
    def edit_structure(self):
        from pathlib import Path

        user_path = self.config_service.get("user_path")

        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        runtime = Path(user_path) / ".sorterino_runtime"
        file_path = runtime / "structure.json"

        self._open_json_editor("Struktur bearbeiten", file_path)

    # UI / JSON EDITOR
    def _open_json_editor(self, title, file_path):

        window = Toplevel(self)
        window.title(title)
        window.geometry("700x600")

        text = Text(window, wrap="none")
        text.pack(expand=True, fill="both")

        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.dumps(json.load(f), indent=2)
            else:
                content = "{}"
        except Exception as e:
            content = f"Fehler beim Laden\n{e}"

        text.insert("1.0", content)

        def save():
            try:
                data = json.loads(text.get("1.0", END))

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                messagebox.showinfo("Erfolg", "Gespeichert")
                window.destroy()

            except Exception as e:
                messagebox.showerror("Fehler", f"Ungültiges JSON\n{e}")

        Button(window, text="Speichern", command=save).pack(pady=10)