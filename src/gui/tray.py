import threading
import os

import pystray
from PIL import Image, ImageDraw
from pathlib import Path
import customtkinter as ctk
import ctypes
from datetime import datetime, time as dt_time

from src.config import Config
from src.gui.main_window import MainWindow
from src.initialize_workspace import get_base_path
from src.reporting import DailyReportManager
from src.gui.appearance import apply_appearance

BASE_DIR = get_base_path()

ICON_PATH = BASE_DIR / "assets" / "icons" / "default_icon_128.ico"


class TrayApp:
    def __init__(self):
        self.config = Config()

        self._auto_thread = None

        self.window = None
        self._root = None

        menu = pystray.Menu(
            pystray.MenuItem("Öffnen", self.open_main_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Jetzt verarbeiten", self.process_documents),
            pystray.MenuItem("Dokumente hinzufügen", self.add_documents),
            pystray.MenuItem("Eingangsordner öffnen", self.open_incoming_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", self.exit_app),
        )
        self.icon = pystray.Icon("Sorterino", self.create_icon(), "Sorterino", menu)

    def open_main_window(self, icon=None, item=None):
        if self._root:
            self._root.after(0, self._open_main_window_now)

    def _open_main_window_now(self):
        try:
            self.config = Config()
            if self.window and self.window.winfo_exists():
                self.window.config = self.config
                self._bring_to_front(self.window)
                self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
                return self.window
            self.window = MainWindow(master=self._root, config=self.config)
            if not self.config.get("user_path"):
                self.window.show_page("settings")
            self._bring_to_front(self.window)
            self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
            return self.window
        except Exception as e:
            print(f"[ERROR] MainWindow konnte nicht geöffnet werden: {e}")
            return None

    def process_documents(self, icon=None, item=None):
        if not self._root:
            return

        def _start():
            window = self.window if self.window and self.window.winfo_exists() else None
            if window:
                window._run_pipeline()
                return
            from main import run_pipeline
            threading.Thread(target=run_pipeline, daemon=True).start()

        self._root.after(0, _start)

    def add_documents(self, icon=None, item=None):
        if self._root:
            def _add():
                window = self._open_main_window_now()
                if window:
                    window._add_documents()
            self._root.after(0, _add)

    def open_incoming_folder(self, icon=None, item=None):
        if not self._root:
            return

        def _open():
            config = Config()
            path = config.incoming_root
            if path and Path(path).exists():
                os.startfile(path)
            else:
                window = self._open_main_window_now()
                if window:
                    window.show_page("settings")

        self._root.after(0, _open)

    def create_icon(self):
        if ICON_PATH.exists():
            return Image.open(ICON_PATH)

        img = Image.new("RGB", (64, 64), color="gray")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "S", fill="white")
        return img

    def _bring_to_front(self, app):
        try:
            app.update_idletasks()
            app.deiconify()

            hwnd = app.winfo_id()

            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)

            app.lift()
            app.focus_force()

            app.attributes("-topmost", True)
            app.after(200, lambda: app.attributes("-topmost", False))
        except Exception as e:
            print(f"[WARN] Fenster konnte nicht fokussiert werden: {e}")

    def _on_window_close(self):
        if self.window:
            window = self.window

            def close_to_tray():
                if self.window is window:
                    self.window = None
                window.close_safely()

            window.request_close_to_tray(close_to_tray)

    def run(self):
        apply_appearance(self.config.get("appearance_mode", "system"))
        self._root = ctk.CTk()
        self._root.withdraw()

        self._root.after(0, self.open_main_window)

        threading.Thread(target=self._monitor_auto_mode, daemon=True).start()
        threading.Thread(target=self._monitor_daily_report, daemon=True).start()
        threading.Thread(target=self.icon.run, daemon=True).start()

        self._root.mainloop()

    def _auto_loop(self):
        import time
        from main import run_pipeline
        from src.config import Config

        print("[AUTO] Thread gestartet")

        while True:
            try:
                config = Config()

                if not config.get("auto_mode"):
                    print("[AUTO] beendet")
                    break

                print("[AUTO] Tick → starte Pipeline")

                run_pipeline()

            except Exception as e:
                print(f"[AUTO ERROR] {e}")

            time.sleep(10)

    def _monitor_auto_mode(self):
        import time
        from src.config import Config

        while True:
            try:
                config = Config()

                if config.get("auto_mode"):
                    if not self._auto_thread or not self._auto_thread.is_alive():
                        print("[AUTO] dynamisch gestartet")

                        self._auto_thread = threading.Thread(
                            target=self._auto_loop,
                            daemon=True
                        )
                        self._auto_thread.start()

            except Exception as e:
                print(f"[AUTO MONITOR ERROR] {e}")

            time.sleep(5)

    def _monitor_daily_report(self):
        import time

        while True:
            try:
                config = Config()
                if not config.logs_root:
                    time.sleep(60)
                    continue

                reporter = DailyReportManager(config.logs_root)

                now = datetime.now()
                raw_time = config.get("daily_report_time") or "18:00"
                try:
                    parts = raw_time.split(":")
                    report_time = dt_time(int(parts[0]), int(parts[1]))
                except Exception:
                    report_time = dt_time(18, 0)

                if now.time() >= report_time:
                    last_date = reporter.get_last_report_date()
                    today = now.date()

                    if last_date != today.isoformat():
                        reporter.generate_daily_report(today)
                        reporter.set_last_report_date(today)

            except Exception as e:
                print(f"[REPORT ERROR] {e}")

            time.sleep(60)

    def exit_app(self, icon=None, item=None):
        try:
            if self.window and self.window.winfo_exists():
                self.window.save_window_state()
        except Exception:
            pass

        try:
            self.icon.stop()
        except Exception:
            pass

        # pystray invokes menu callbacks on its own thread. Tk widgets must
        # only be destroyed by the Tk main thread, otherwise pending redraws
        # can address canvases that no longer exist.
        try:
            if self._root:
                self._root.after(0, self._shutdown_tk)
        except Exception:
            pass

    def _shutdown_tk(self):
        try:
            if self.window and self.window.winfo_exists():
                self.window.save_window_state()
            self.window = None
            self._root.quit()
            self._root.destroy()
        except Exception:
            pass
