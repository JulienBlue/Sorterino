import pystray
from PIL import Image, ImageDraw
from pathlib import Path
import customtkinter as ctk

from src.infrastructure.config.config_service import ConfigService
from src.gui.main_window import MainWindow

BASE_DIR = Path(__file__).resolve().parents[2]
ICON_PATH = BASE_DIR / "assets" / "icons" / "default_icon_128.ico"

root = ctk.CTk()
root.withdraw()


class TrayApp:

    def __init__(self):
        self.config_service = ConfigService()
        self.window = None

        self.icon = pystray.Icon(
            "Sorterino",
            self.create_icon(),
            "Sorterino",
            menu=pystray.Menu(
                pystray.MenuItem("Öffnen", self.open_main_window, default=True),
                pystray.MenuItem("Beenden", self.exit_app)
            )
        )

    # --------------------------------------------------

    def open_main_window(self, icon=None, item=None):

        def _open():
            try:
                if self.window and self.window.winfo_exists():
                    self._bring_to_front(self.window)
                    self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
                    return

                self.window = MainWindow(
                    master=root,
                    pipeline=None,
                    logger=None,
                    config=self.config_service
                )

                self._bring_to_front(self.window)

            except Exception as e:
                print("❌ GUI ERROR:", e)

        root.after(0, _open)

    # --------------------------------------------------

    def create_icon(self):
        try:
            if ICON_PATH.exists():
                return Image.open(ICON_PATH)
        except Exception:
            pass

        img = Image.new("RGB", (64, 64), color="gray")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "S", fill="white")
        return img

    # --------------------------------------------------

    def _bring_to_front(self, app):
        import ctypes

        app.update_idletasks()
        app.deiconify()

        hwnd = app.winfo_id()

        ctypes.windll.user32.ShowWindow(hwnd, 5)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

        app.lift()
        app.focus_force()

        app.attributes("-topmost", True)
        app.after(200, lambda: app.attributes("-topmost", False))


    def _on_window_close(self):
        if self.window:
            self.window.destroy()
            self.window = None



    def run(self):

        # 🔥 Tray in separatem Thread
        import threading
        threading.Thread(target=self.icon.run, daemon=True).start()

        # 🔥 GUI starten
        root.after(0, self.open_main_window)

        root.mainloop()

    # --------------------------------------------------

    def exit_app(self, icon=None, item=None):
        try:
            icon.stop()
        except Exception:
            pass

        try:
            root.destroy()
        except Exception:
            pass

        import sys
        sys.exit(0)