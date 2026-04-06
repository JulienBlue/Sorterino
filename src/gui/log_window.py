import customtkinter as ctk
from tkinter import messagebox

from src.config import Config


class LogWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master=None):
        super().__init__(master)

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.title("Logs")
        self.geometry("1000x650")

        config = Config()

        if config.runtime_root is None:
            messagebox.showerror(
                "Fehler",
                "Kein Speicherort konfiguriert.\nBitte zuerst einen Speicherort setzen."
            )
            self.destroy()
            return

        self.log_dir = config.runtime_root / "logs"

        self._after_id = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.create_ui()
        self.update_logs()

    # UI / BUILD
    def create_ui(self):
        self.textbox = ctk.CTkTextbox(self)
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)

    # LOGS / UPDATE
    def update_logs(self):
        latest_file = None

        if self.log_dir.exists():
            logs = sorted(self.log_dir.glob("*.log"), reverse=True)
            if logs:
                latest_file = logs[0]

        if latest_file:
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    content = f.read()

                current_position = self.textbox.yview()

                self.textbox.delete("0.0", "end")
                self.textbox.insert("0.0", content)

                if current_position[1] == 1.0:
                    self.textbox.yview_moveto(1.0)
                else:
                    self.textbox.yview_moveto(current_position[0])

            except Exception:
                pass

        self._after_id = self.after(2000, self.update_logs)

    # WINDOW / CLOSE
    def _on_close(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

        self.destroy()