import customtkinter as ctk
import os
from main import run_pipeline


class MainWindow(ctk.CTkToplevel):

    def __init__(self, master, pipeline, logger, config):
        super().__init__(master)

        self.pipeline = pipeline
        self.logger = logger
        self.config = config

        self.title("Sorterino")
        self.geometry("420x520")

        try:
            self._build_ui()
        except Exception as e:
            print("❌ UI BUILD ERROR:", e)

        self.bind("<FocusIn>", lambda e: self._refresh_ui())

    # --------------------------------------------------

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
        except Exception as e:
            print("❌ CONFIG ERROR:", e)

        mode_text = "🟢 Automatik: AN" if auto_mode else "⚪ Automatik: AUS"

        self.mode_label = ctk.CTkLabel(self, text=mode_text)
        self.mode_label.pack(pady=5)

        ctk.CTkLabel(
            self,
            text=f"📂 Speicherort:\n{user_path}",
            wraplength=380,
            justify="center"
        ).pack(pady=10)

        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(pady=10, padx=20, fill="x")

        # 🔥 IMMER anzeigen, ggf. disabled
        self.manual_btn = ctk.CTkButton(
            actions_frame,
            text="▶ Manueller Start",
            command=self._run_pipeline
        )
        self.manual_btn.pack(pady=5, fill="x")

        if auto_mode:
            self.manual_btn.configure(state="disabled")

        ctk.CTkButton(
            actions_frame,
            text="📜 Logs anzeigen",
            command=self._open_logs
        ).pack(pady=5, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="⚙ Einstellungen",
            command=self._open_settings
        ).pack(pady=5, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="📂 Speicherort öffnen",
            command=self._open_storage
        ).pack(pady=5, fill="x")


    # --------------------------------------------------

    def _run_pipeline(self):
        import threading

        def _run():
            try:
                print("▶ Pipeline START (manuell)")
                run_pipeline()
            except Exception as e:
                print("❌ Pipeline ERROR:", e)

        threading.Thread(target=_run, daemon=True).start()

    def _open_logs(self):
        from src.gui.log_window import LogWindow
        LogWindow(self)

    def _open_settings(self):
        from src.gui.config_window import ConfigWindow
        ConfigWindow(self, on_change=self._refresh_ui)

    def _open_storage(self):
        try:
            path = self.config.get("user_path")

            if path and os.path.exists(path):
                os.startfile(path)
        except Exception as e:
            print("❌ STORAGE ERROR:", e)

    def _refresh_ui(self):

        try:
            auto_mode = self.config.get("auto_mode") or False
        except Exception:
            auto_mode = False

        # 🔥 Label aktualisieren
        mode_text = "🟢 Automatik: AN" if auto_mode else "⚪ Automatik: AUS"
        if hasattr(self, "mode_label"):
            self.mode_label.configure(text=mode_text)

        # 🔥 Button aktualisieren
        if hasattr(self, "manual_btn"):
            if auto_mode:
                self.manual_btn.configure(state="disabled")
            else:
                self.manual_btn.configure(state="normal")