import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from src.infrastructure.config.config_service import ConfigService
from src.infrastructure.config.initialize_workspace import initialize_workspace
from src.infrastructure.config.config_loader import Config


class StorageWindow(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.config_service = ConfigService()

        self.title("Speicherort")
        self.geometry("400x260")

        self.create_ui()
        self.load_path()

    def create_ui(self):

        self.select_btn = ctk.CTkButton(
            self,
            text="Speicherort auswählen",
            command=self.select_path
        )
        self.select_btn.pack(pady=10)

        self.path_box = ctk.CTkTextbox(self, height=100)
        self.path_box.pack(padx=10, pady=10, fill="both")

        self.init_runtime_btn = ctk.CTkButton(
            self,
            text="Runtime initialisieren",
            command=self.initialize_runtime
        )
        self.init_runtime_btn.pack(pady=10)

    def load_path(self):
        path = self.config_service.get("user_path")

        if path:
            self.path_box.insert("0.0", path)

    def select_path(self):
        path = filedialog.askdirectory()

        if path:
            self.path_box.delete("0.0", "end")
            self.path_box.insert("0.0", path)

            self.config_service.set("user_path", path)

    def initialize_runtime(self):

        user_path = self.config_service.get("user_path")

        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt!")
            return

        user_path = Path(user_path)

        # 🔥 WICHTIG: persistente Speicherung
        self.config_service.set("user_path", str(user_path))

        config = Config(self.config_service.config_path)

        # 🔥 WICHTIG: user_path erzwingen
        config.raw["user_path"] = str(user_path)
        config.user_path = user_path

        # 🔥 CRITICAL: Runtime neu berechnen
        config.runtime_root = user_path / ".sorterino_runtime"
        config.incoming_root = config.runtime_root / "incoming"
        config.logs_root = config.runtime_root / "logs"

        result = initialize_workspace(config)

        print("DEBUG RESULT:", result)

        messagebox.showinfo(
            "Sorterino",
            f"Runtime erstellt unter:\n{user_path}"
        )