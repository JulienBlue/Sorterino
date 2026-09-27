"""Detached, terminal-style live view for Sorterino diagnostics."""

from pathlib import Path

import customtkinter as ctk

from src.config import Config


class DeveloperConsole(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sorterino Entwicklerkonsole")
        self.geometry("1080x620")
        self.minsize(720, 420)
        self.config_data = Config()
        self.log_path = Path(self.config_data.logs_root) / "sorterino.log"
        self._offset = 0

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            header, text="Sorterino Entwicklerkonsole", font=("Consolas", 18, "bold")
        ).pack(side="left")
        ctk.CTkButton(header, text="Leeren", width=90, command=self._clear).pack(side="right")

        self.output = ctk.CTkTextbox(
            self, font=("Consolas", 12), fg_color=("#111111", "#0B0D0F"),
            text_color=("#E6E6E6", "#E6E6E6"), wrap="none",
        )
        self.output.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._read_new_content(initial=True)

    def _clear(self):
        self.output.delete("0.0", "end")

    def _read_new_content(self, initial=False):
        try:
            size = self.log_path.stat().st_size
            if size < self._offset:
                self._offset = 0
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as handle:
                if initial and size > 250_000:
                    handle.seek(max(0, size - 250_000))
                else:
                    handle.seek(self._offset)
                content = handle.read()
                self._offset = handle.tell()
            if content:
                self.output.insert("end", content)
                self.output.see("end")
        except OSError:
            pass
        self.after(500, self._read_new_content)


def run_developer_console():
    DeveloperConsole().mainloop()
