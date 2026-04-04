import threading

import pystray
from PIL import Image, ImageDraw
from pathlib import Path
import customtkinter as ctk
import sys
import ctypes

from src.config.config_service import ConfigService
from src.gui.main_window import MainWindow

BASE_DIR = Path(__file__).resolve().parents[2]
ICON_PATH = BASE_DIR / "assets" / "icons" / "default_icon_128.ico"


class TrayApp:

    # CONFIG / INIT
    def __init__(self):
        self.config = ConfigService()

        self.window = None
        self._root = None

        menu = pystray.Menu(
            pystray.MenuItem("Öffnen", self.open_main_window),
            pystray.MenuItem("Beenden", self.exit_app),
        )
        self.icon = pystray.Icon("Sorterino", self.create_icon(), "Sorterino", menu)

    # UI / MAIN WINDOW
    def open_main_window(self, icon=None, item=None):

        def _open():
            try:
                if self.window and self.window.winfo_exists():
                    self._bring_to_front(self.window)
                    self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
                    return

                self.window = MainWindow(
                    master=self._root,
                    pipeline=None,
                    logger=None,
                    config=self.config
                )

                self._bring_to_front(self.window)
                self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

            except Exception:
                pass

        if self._root:
            self._root.after(0, _open)

    # SYSTEM / ICON
    def create_icon(self):
        if ICON_PATH.exists():
            return Image.open(ICON_PATH)

        img = Image.new("RGB", (64, 64), color="gray")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "S", fill="white")
        return img

    # WINDOW / FOCUS
    def _bring_to_front(self, app):
        app.update_idletasks()
        app.deiconify()

        hwnd = app.winfo_id()

        ctypes.windll.user32.ShowWindow(hwnd, 5)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

        app.lift()
        app.focus_force()

        app.attributes("-topmost", True)
        app.after(200, lambda: app.attributes("-topmost", False))

    # WINDOW / CLOSE
    def _on_window_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    # STORAGE / CALLBACK
    def _on_storage_set(self):
        if self.window and self.window.winfo_exists():
            self._bring_to_front(self.window)

    # APP / RUN
    def run(self):
        self._root = ctk.CTk()
        self._root.withdraw()

        self._root.after(0, self.open_main_window)

        if not self.config.get("user_path"):

            from src.gui.storage_window import StorageWindow

            def _open_setup():
                StorageWindow(
                    master=self._root,
                    config=self.config,
                    on_change=self._on_storage_set
                )

            self._root.after(200, _open_setup)

        threading.Thread(target=self.icon.run, daemon=True).start()
        self._root.mainloop()

    # APP / EXIT
    def exit_app(self, icon=None, item=None):
        try:
            self.icon.stop()
        except Exception:
            pass

        try:
            if self._root:
                self._root.destroy()
        except Exception:
            pass

        sys.exit(0)