import customtkinter as ctk
import threading
import os

from src.config import Config
from main import run_pipeline


class MainWindow(ctk.CTkToplevel):

    # CONFIG / INIT
    def __init__(self, master, pipeline, logger, config):
        super().__init__(master)

        self.pipeline = pipeline
        self.logger = logger
        self.config = config
        self._thread_running = False

        self.title("Sorterino")
        self.geometry("400x650")

        try:
            self._build_ui()
        except Exception as e:
            print(f"[ERROR] UI Build fehlgeschlagen: {e}")

        self.bind("<FocusIn>", lambda e: self._refresh_ui())

    # UI / BUILD
    def _build_ui(self):

        # 🔥 immer aktuelle Config laden
        self.config = Config()

        ctk.CTkLabel(
            self,
            text="Sorterino",
            font=("Arial", 22, "bold")
        ).pack(pady=(20, 10))

        auto_mode = self.config.get("auto_mode") or False
        user_path = self.config.get("user_path") or "Nicht gesetzt"

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

        if self._thread_running:
            print("[INFO] Pipeline läuft bereits")
            return

        self._thread_running = True
        self.manual_btn.configure(state="disabled")

        def _run():
            try:
                run_pipeline()
            except Exception as e:
                print(f"[ERROR] Pipeline Fehler: {e}")
            finally:
                self._thread_running = False
                self.after(0, self._refresh_ui)

        threading.Thread(target=_run, daemon=True).start()

    # UI / LOGS
    def _open_logs(self):
        try:
            from src.gui.log_window import LogWindow
            LogWindow(self)
        except Exception as e:
            print(f"[ERROR] LogWindow konnte nicht geöffnet werden: {e}")

    # UI / SETTINGS
    def _open_settings(self):
        try:
            from src.gui.config_window import ConfigWindow
            ConfigWindow(self, config=self.config, on_change=self._refresh_ui)
        except Exception as e:
            print(f"[ERROR] Settings konnten nicht geöffnet werden: {e}")

    # UI / STORAGE
    def _open_storage(self):
        try:
            # 🔥 aktuelle Config laden
            self.config = Config()

            path = self.config.get("user_path")

            if path and os.path.exists(path):
                os.startfile(path)
            else:
                print("[WARN] Speicherort existiert nicht")
        except Exception as e:
            print(f"[ERROR] Speicherort konnte nicht geöffnet werden: {e}")

    # UI / REFRESH
    def _refresh_ui(self):

        try:
            # 🔥 NEU LADEN (entscheidend!)
            self.config = Config()

            auto_mode = self.config.get("auto_mode") or False
            user_path = self.config.get("user_path") or "Nicht gesetzt"

        except Exception as e:
            print(f"[WARN] UI Refresh Fehler: {e}")
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
            if auto_mode or self._thread_running:
                self.manual_btn.configure(state="disabled")
            else:
                self.manual_btn.configure(state="normal")