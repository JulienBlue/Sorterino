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
        self.geometry("420x450")

        self.create_ui()
        self.after(0, self.load_values)

    
    # UI
    
    def create_ui(self):

        self.storage_btn = ctk.CTkButton(self, text="Speicherort", command=self.open_storage)
        self.storage_btn.pack(pady=8)

        self.auto_mode_checkbox = ctk.CTkCheckBox(self, text="Automatikmodus", command=self.toggle_auto_mode)
        self.auto_mode_checkbox.pack(pady=6)

        self.autostart_checkbox = ctk.CTkCheckBox(self, text="Autostart", command=self.toggle_autostart)
        self.autostart_checkbox.pack(pady=6)

        ctk.CTkButton(self, text="Persönliche Daten", command=self.open_user_window).pack(pady=8)

        ctk.CTkButton(self, text="Regeln bearbeiten", command=self.edit_rules).pack(pady=6)
        ctk.CTkButton(self, text="Struktur bearbeiten", command=self.edit_structure).pack(pady=10)

        ctk.CTkButton(self, text="E-Mail Integration", command=self.open_mail_window).pack(pady=8)


    
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

        _ = safe_insert  # Platzhalter, Felder werden im User-Fenster geladen

    
    # SAVE
    
    def open_user_window(self):
        from src.gui.user_window import UserWindow
        UserWindow(self, config=self.config)


    
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
        user_path = self.config.get("user_path")
        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        self._open_json_editor("Regeln bearbeiten", self.config.rules_path)

    def edit_structure(self):
        user_path = self.config.get("user_path")
        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        self._open_json_editor("Struktur bearbeiten", self.config.structure_path)

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
