import customtkinter as ctk
import threading
import os

from src.config import Config
from main import run_pipeline


class MainWindow(ctk.CTkToplevel):
    def __init__(self, master, config):
        super().__init__(master)

        self.config = config
        self._thread_running = False

        self.title("Sorterino")
        self.geometry("420x450")

        try:
            self._build_ui()
        except Exception as e:
            print(f"[ERROR] UI Build fehlgeschlagen: {e}")

        self.bind("<FocusIn>", lambda e: self._refresh_ui())

    def _load_config(self):
        self.config = Config()
        return (
            self.config.get("auto_mode") or False,
            self.config.get("user_path") or "Nicht gesetzt"
        )

    def _apply_ui_state(self, auto_mode, user_path):
        mode_text = "Automatik AN" if auto_mode else "Automatik AUS"

        if hasattr(self, "mode_label"):
            self.mode_label.configure(text=mode_text)

        if hasattr(self, "path_label"):
            self.path_label.configure(text=f"Speicherort\n{user_path}")

        if hasattr(self, "manual_btn"):
            state = "disabled" if auto_mode or self._thread_running else "normal"
            self.manual_btn.configure(state=state)

    def _build_ui(self):
        auto_mode, user_path = self._load_config()

        ctk.CTkLabel(
            self,
            text="Sorterino",
            font=("Arial", 22, "bold")
        ).pack(pady=(24, 12))

        self.mode_label = ctk.CTkLabel(self, text="")
        self.mode_label.pack(pady=8)

        self.path_label = ctk.CTkLabel(
            self,
            text="",
            wraplength=380,
            justify="center"
        )
        self.path_label.pack(pady=12)

        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(pady=12, padx=20, fill="x")

        self.manual_btn = ctk.CTkButton(
            actions_frame,
            text="Manueller Start",
            command=self._run_pipeline
        )
        self.manual_btn.pack(pady=6, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Daily-Report",
            command=self._open_daily_report
        ).pack(pady=6, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Logs anzeigen",
            command=self._open_logs
        ).pack(pady=6, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Einstellungen",
            command=self._open_settings
        ).pack(pady=6, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Speicherort öffnen",
            command=self._open_storage
        ).pack(pady=6, fill="x")

        self._apply_ui_state(auto_mode, user_path)

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

    def _open_daily_report(self):
        try:
            from src.gui.daily_report_window import DailyReportWindow
            DailyReportWindow(self, config=self.config)
        except Exception as e:
            print(f"[ERROR] Daily-Report Window konnte nicht geöffnet werden: {e}")

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
            _, path = self._load_config()

            if path and os.path.exists(path):
                os.startfile(path)
            else:
                print("[WARN] Speicherort existiert nicht")
        except Exception as e:
            print(f"[ERROR] Speicherort konnte nicht geöffnet werden: {e}")

    # UI / REFRESH
    def _refresh_ui(self):
        try:
            auto_mode, user_path = self._load_config()
        except Exception as e:
            print(f"[WARN] UI Refresh Fehler: {e}")
            auto_mode = False
            user_path = "Nicht gesetzt"

        self._apply_ui_state(auto_mode, user_path)
