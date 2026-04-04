import customtkinter as ctk
import threading
import os

from src.config.config_loader import Config
from main import run_pipeline


class MainWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master, pipeline, logger, config):
        super().__init__(master)

        self.pipeline = pipeline
        self.logger = logger
        self.config = config

        self.title("Sorterino")
        self.geometry("400x650")

        try:
            self._build_ui()
        except Exception:
            pass

        self.bind("<FocusIn>", lambda e: self._refresh_ui())

    # UI / BUILD
    def _build_ui(self):

        ctk.CTkLabel(
            self,
            text="Sorterino",
            font=("Arial", 22, "bold")
        ).pack(pady=(20, 10))

        auto_mode = False
        user_path = "Nicht gesetzt"

        try:
            auto_mode = self.config.get("auto_mode") or False
            user_path = self.config.get("user_path") or "Nicht gesetzt"
        except Exception:
            pass

        mode_text = "Automatik AN" if auto_mode else "Automatik AUS"

        self.mode_label = ctk.CTkLabel(self, text=mode_text)
        self.mode_label.pack(pady=5)

        self.path_label = ctk.CTkLabel(
            self,
            text=f"Speicherort\n{user_path}",
            wraplength=380,
            justify="center"
        )
        self.path_label.pack(pady=10)

        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(pady=10, padx=20, fill="x")

        self.manual_btn = ctk.CTkButton(
            actions_frame,
            text="Manueller Start",
            command=self._run_pipeline
        )
        self.manual_btn.pack(pady=5, fill="x")

        if auto_mode:
            self.manual_btn.configure(state="disabled")

        ctk.CTkButton(
            actions_frame,
            text="Logs anzeigen",
            command=self._open_logs
        ).pack(pady=5, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Einstellungen",
            command=self._open_settings
        ).pack(pady=5, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Speicherort öffnen",
            command=self._open_storage
        ).pack(pady=5, fill="x")

    # PIPELINE / RUN
    def _run_pipeline(self):

        def _run():
            try:
                run_pipeline()
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    # UI / LOGS
    def _open_logs(self):
        from src.gui.log_window import LogWindow
        LogWindow(self)

    # UI / SETTINGS
    def _open_settings(self):
        from src.gui.config_window import ConfigWindow
        ConfigWindow(self, config=self.config, on_change=self._refresh_ui)

    # UI / STORAGE
    def _open_storage(self):
        try:
            path = self.config.get("user_path")

            if path and os.path.exists(path):
                os.startfile(path)
        except Exception:
            pass

    # UI / REFRESH
    def _refresh_ui(self):

        try:
            auto_mode = self.config.get("auto_mode") or False
            user_path = self.config.get("user_path") or "Nicht gesetzt"
        except Exception:
            auto_mode = False
            user_path = "Nicht gesetzt"

        mode_text = "Automatik AN" if auto_mode else "Automatik AUS"

        if hasattr(self, "mode_label"):
            self.mode_label.configure(text=mode_text)

        if hasattr(self, "path_label"):
            self.path_label.configure(
                text=f"Speicherort\n{user_path}"
            )

        if hasattr(self, "manual_btn"):
            if auto_mode:
                self.manual_btn.configure(state="disabled")
            else:
                self.manual_btn.configure(state="normal")