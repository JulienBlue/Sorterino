import customtkinter as ctk
from tkinter import messagebox

from src.config import Config
from src.gui.embedded import EmbeddedPage


class LogWindow(EmbeddedPage):
    help_context = "logs"

    # CONFIG / INIT
    def __init__(self, master=None):
        super().__init__(master)

        config = Config()

        if config.runtime_root is None:
            messagebox.showerror(
                "Fehler",
                "Kein Speicherort konfiguriert.\nBitte zuerst einen Speicherort setzen."
            )
            return

        self.log_dir = config.runtime_root / "logs"

        self._after_id = None

        ctk.CTkLabel(self, text="Protokoll", font=("Arial", 22, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        self.create_ui()
        self.update_logs()

    # UI / BUILD
    def create_ui(self):
        self.textbox = ctk.CTkTextbox(self)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=12)

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

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        super().destroy()
