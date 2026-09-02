import json
from pathlib import Path
from tkinter import END, filedialog, messagebox

import customtkinter as ctk

from src.config import Config
from src.gui.embedded import EmbeddedPage
from src.document_registry import DocumentRegistry
from src.constants import BACKUP_DIRECTORY_NAME


class ConfigWindow(EmbeddedPage):
    """Expert tools. Everyday settings live in the main window."""

    help_context = "advanced"

    def __init__(self, master=None, config=None, on_change=None):
        super().__init__(master)
        self.on_change = on_change
        self.config = config if config else Config()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Erweiterte Einstellungen",
            font=("Arial", 20, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkLabel(
            self,
            text=(
                "Diese Werkzeuge sind für Diagnose und individuelle Sonderfälle. "
                "Ungültige Änderungen können die automatische Sortierung verhindern."
            ),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        actions = ctk.CTkScrollableFrame(self)
        actions.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self._button(actions, "Programmeinstellungen als JSON bearbeiten", self.config.settings_path)
        labels = {
            "family": "Familie", "person": "Privatperson",
            "child": "Kind", "organization": "Organisation",
        }
        for preset, label in labels.items():
            preset_root = self.config.presets_root / preset
            self._button(actions, f"Regelvorlage {label}", preset_root / "rules.json")
            self._button(actions, f"Strukturvorlage {label}", preset_root / "structure.json")
        ctk.CTkButton(
            actions,
            text="Dokumentregister verwalten",
            command=self._open_document_registry,
        ).pack(fill="x", padx=18, pady=(24, 8))

    def _button(self, parent, label, path):
        ctk.CTkButton(
            parent,
            text=label,
            command=lambda: self._open_json_editor(label, path),
        ).pack(fill="x", padx=18, pady=8)

    def _open_json_editor(self, title, file_path):
        if not file_path:
            messagebox.showerror("Nicht verfügbar", "Bitte zuerst einen Speicherort einrichten.", parent=self)
            return
        self.open_page(
            lambda parent: JsonEditorPage(parent, title, file_path, self.config, self.on_change),
            "settings",
        )

    def _open_document_registry(self):
        self.open_page(
            lambda parent: DocumentRegistryPage(parent, self.config),
            "settings",
        )


class DocumentRegistryPage(EmbeddedPage):
    help_context = "advanced"

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config
        self.registry = DocumentRegistry(config)
        ctk.CTkLabel(
            self, text="Dokumentregister", font=("Arial", 20, "bold")
        ).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkLabel(
            self,
            text=(
                "Die lokale SQLite-Datenbank speichert Hashwerte, bekannte Speicherorte "
                "und die technische Verarbeitungshistorie. Dokumentinhalte und OCR-Volltexte "
                "werden nicht in der Datenbank gespeichert."
            ),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))
        self.status = ctk.CTkLabel(self, text="", justify="left")
        self.status.pack(anchor="w", padx=24, pady=(0, 16))
        self._refresh_status()
        ctk.CTkButton(
            self,
            text="Datenbank prüfen",
            command=self._check_database,
        ).pack(anchor="w", padx=24, pady=6)
        ctk.CTkButton(
            self,
            text="Register aus einem Ordner ergänzen",
            command=self._rebuild_from_folder,
        ).pack(anchor="w", padx=24, pady=6)
        ctk.CTkLabel(
            self,
            text=(
                "Der kontrollierte Neustart löscht ausschließlich Hashwerte, bekannte Pfade "
                "und Verarbeitungseinträge. Profile, Einstellungen, E-Mail-Verknüpfungen "
                "und sämtliche Dokumentdateien bleiben erhalten."
            ),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkButton(
            self,
            text="Dokumenthistorie kontrolliert zurücksetzen",
            fg_color="transparent",
            border_width=1,
            text_color=("#8A2C2C", "#FFB5B5"),
            command=self._reset_history,
        ).pack(anchor="w", padx=24, pady=6)

    def _refresh_status(self):
        stats = self.registry.statistics()
        self.status.configure(
            text=(
                f"Datenbank: {self.registry.database.path}\n"
                f"Dokumente: {stats['documents']} · Speicherorte: {stats['locations']} "
                f"· Ereignisse: {stats['events']}"
            )
        )

    def _check_database(self):
        result = self.registry.database.integrity_check()
        if result == "ok":
            messagebox.showinfo(
                "Datenbank geprüft", "Die SQLite-Datenbank ist konsistent.", parent=self
            )
        else:
            messagebox.showerror(
                "Datenbankfehler", f"SQLite meldet: {result}", parent=self
            )

    def _rebuild_from_folder(self):
        selected = filedialog.askdirectory(parent=self, title="Dokumentordner auswählen")
        if not selected:
            return
        root = Path(selected)
        location_type = (
            "backup" if root.name.casefold() == BACKUP_DIRECTORY_NAME.casefold()
            else "archive"
        )
        result = self.registry.scan_directory(root, location_type)
        self._refresh_status()
        messagebox.showinfo(
            "Register ergänzt",
            f"{result['imported']} Dateien wurden erfasst.\n"
            f"{result['failed']} Dateien konnten nicht gelesen werden.",
            parent=self,
        )

    def _reset_history(self):
        from main import is_pipeline_running

        if is_pipeline_running():
            messagebox.showinfo(
                "Verarbeitung läuft",
                "Warte bitte, bis die aktuelle Dokumentverarbeitung abgeschlossen ist.",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "Dokumenthistorie zurücksetzen",
            "Wirklich nur die technische Dokumenthistorie zurücksetzen?\n\n"
            "Es werden keine Dokumente, Profile oder Zugangsdaten gelöscht.",
            parent=self,
        ):
            return
        verification = ctk.CTkInputDialog(
            text="Gib zur Bestätigung NEUSTART ein:",
            title="Zurücksetzen bestätigen",
        ).get_input()
        if verification != "NEUSTART":
            messagebox.showinfo(
                "Nicht zurückgesetzt", "Die Bestätigung war nicht korrekt.", parent=self
            )
            return
        self.registry.clear_document_history()
        self._refresh_status()
        messagebox.showinfo(
            "Dokumenthistorie zurückgesetzt",
            "Die Datenbank ist bereit für einen neuen Dokumentdurchlauf.",
            parent=self,
        )


class JsonEditorPage(EmbeddedPage):
    help_context = "json_editor"
    def __init__(self, master, title, file_path, config, on_change=None):
        super().__init__(master)
        self.file_path = file_path
        self.config = config
        self.on_change = on_change
        ctk.CTkLabel(self, text=title, font=("Arial", 20, "bold")).pack(anchor="w", padx=24, pady=(20, 8))
        self.text = ctk.CTkTextbox(self)
        self.text.pack(expand=True, fill="both", padx=24, pady=(0, 10))
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                content = json.dumps(json.load(handle), indent=2, ensure_ascii=False)
        except Exception as exc:
            messagebox.showerror("Datei konnte nicht geöffnet werden", str(exc), parent=self)
            return
        self.text.insert("1.0", content)
        ctk.CTkButton(self, text="Speichern", command=self.save).pack(pady=(0, 18))

    def save(self):
        try:
            data = json.loads(self.text.get("1.0", END))
            self.config._write_json(self.file_path, data)
            handled = bool(self.on_change and self.on_change())
            if not handled:
                messagebox.showinfo("Gespeichert", "Die Änderungen wurden gespeichert.", parent=self)
                self.finish()
        except Exception as exc:
            messagebox.showerror("Ungültige Konfiguration", str(exc), parent=self)
