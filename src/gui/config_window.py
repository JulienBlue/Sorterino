import threading
import json
import tkinter as tk
from tkinter import Toplevel, Text, Button, END, messagebox

import customtkinter as ctk

from src.gui.storage_window import StorageWindow
from src.config import Config
from src.autostart_service import AutostartService


class ConfigWindow(ctk.CTkToplevel):

    # CONFIG / INIT
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
        self.geometry("400x650")

        self.create_ui()
        self.after(0, self.load_values)

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

        self.company_entry = ctk.CTkEntry(self, placeholder_text="Firmenname")
        self.company_entry.pack(padx=20, fill="x")

        self.keywords_label = ctk.CTkLabel(self, text="Keywords (Komma getrennt)")
        self.keywords_label.pack(pady=(10, 0))

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
        self.config = Config()

        if self.config.get("auto_mode"):
            self.auto_mode_checkbox.select()

        if self.config.get("autostart"):
            self.autostart_checkbox.select()

        company = self.config.get("company_profile") or {}

        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        value = company.get("name")
        if value:
            self.company_entry.insert(0, value)

        value = ", ".join(company.get("keywords", []))
        if value:
            self.keywords_entry.insert(0, value)

        value = address.get("street")
        if value:
            self.street_entry.insert(0, value)

        value = address.get("zip")
        if value:
            self.zip_entry.insert(0, value)

        value = address.get("city")
        if value:
            self.city_entry.insert(0, value)

        value = contact.get("email")
        if value:
            self.email_entry.insert(0, value)

        value = contact.get("phone")
        if value:
            self.phone_entry.insert(0, value)

        value = financial.get("iban")
        if value:
            self.iban_entry.insert(0, value)

        value = financial.get("tax_id")
        if value:
            self.tax_entry.insert(0, value)

    # CONFIG / SAVE
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
        self.config = Config()

        if self.on_change:
            self.on_change()

    # CONFIG / AUTO MODE
    def toggle_auto_mode(self):
        value = self.auto_mode_checkbox.get() == 1
        self.config.set("auto_mode", value)

        self.config = Config()

        if value:
            from main import run_pipeline

            def _auto_loop():
                import time

                while True:
                    config = Config()

                    if not config.get("auto_mode"):
                        break

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
        self.config.set("autostart", value)

        self.config = Config()

        if value:
            self.autostart_service.enable()
        else:
            self.autostart_service.disable()

    # UI / STORAGE
    def open_storage(self):
        StorageWindow(
            self,
            config=self.config,
            on_change=self.on_change
        )

    # CONFIG / RULES
    def edit_rules(self):
        from pathlib import Path

        user_path = self.config.get("user_path")

        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        runtime = Path(user_path) / ".sorterino_runtime"
        file_path = runtime / "rules.json"

        self._open_json_editor("Regeln bearbeiten", file_path)

    # CONFIG / STRUCTURE
    def edit_structure(self):
        from pathlib import Path

        user_path = self.config.get("user_path")

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