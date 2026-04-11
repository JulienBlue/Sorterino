import customtkinter as ctk
from tkinter import filedialog, messagebox

from src.initialize_workspace import initialize_workspace
from src.config import Config


class StorageWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master, config=None, on_change=None):
        super().__init__(master)

        self.config = config if config else Config()
        self.on_change = on_change

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.grab_set()

        self.title("Speicherort")
        self.geometry("420x450")

        self.create_ui()
        self.load_path()

    # UI / BUILD
    def create_ui(self):

        self.select_btn = ctk.CTkButton(
            self,
            text="Speicherort auswählen",
            command=self.select_path
        )
        self.select_btn.pack(pady=12)

        self.path_box = ctk.CTkTextbox(self, height=200)
        self.path_box.pack(padx=20, pady=12, fill="both")

    # CONFIG / LOAD
    def load_path(self):
        self.path_box.delete("0.0", "end")

        path = self.config.get("user_path")
        if path:
            self.path_box.insert("0.0", path)

    # CONFIG / SELECT + AUTO INIT
    def select_path(self):
        path = filedialog.askdirectory()

        if not path:
            return

        # UI sofort aktualisieren
        self.path_box.delete("0.0", "end")
        self.path_box.insert("0.0", path)

        try:
            self.config.set("user_path", path)

            self.config = Config()

            initialize_workspace(self.config)

        except Exception as e:
            messagebox.showerror(
                "Fehler",
                f"Initialisierung fehlgeschlagen:\n{e}"
            )
            return

        messagebox.showinfo(
            "Sorterino",
            f"Speicherort gesetzt & Runtime bereit:\n{path}"
        )

        if self.on_change:
            self.after(100, self.on_change)

        self.destroy()
