import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from src.config.config_service import ConfigService
from src.initialize_workspace import initialize_workspace
from src.config.config_loader import Config


class StorageWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master, config=None, on_change=None):
        super().__init__(master)

        self.config_service = config if config else ConfigService()
        self.on_change = on_change

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.grab_set()

        self.title("Speicherort")
        self.geometry("400x650")

        self.create_ui()
        self.load_path()

    # UI / BUILD
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

    # CONFIG / LOAD
    def load_path(self):
        path = self.config_service.get("user_path")

        if path:
            self.path_box.insert("0.0", path)

    # CONFIG / SELECT
    def select_path(self):
        path = filedialog.askdirectory()

        if path:
            self.path_box.delete("0.0", "end")
            self.path_box.insert("0.0", path)

            self.config_service.set("user_path", path)

            if self.on_change:
                self.after(100, self.on_change)

            self.destroy()

    # RUNTIME / INIT
    def initialize_runtime(self):

        user_path = self.config_service.get("user_path")

        if not user_path:
            messagebox.showerror("Fehler", "Kein Speicherort gesetzt")
            return

        user_path = Path(user_path)

        self.config_service.set("user_path", str(user_path))

        config = Config(self.config_service.config_path)

        initialize_workspace(config)

        messagebox.showinfo(
            "Sorterino",
            f"Runtime erstellt unter\n{user_path}"
        )

        if self.on_change:
            self.after(100, self.on_change)

        self.destroy()