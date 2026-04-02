import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
from pathlib import Path
import customtkinter as ctk

import subprocess
import sys

from src.infrastructure.config.config_service import ConfigService

BASE_DIR = Path(__file__).resolve().parents[2]
ICON_PATH = BASE_DIR / "assets" / "icons" / "default_icon_128.ico"

root = ctk.CTk()
root.withdraw()  # versteckt Hauptfenster

class TrayApp:

    def __init__(self):
        self.config_service = ConfigService()
        self.is_running = False

        self.icon = pystray.Icon(
            "Sorterino",
            self.create_icon(),
            "Sorterino (Inaktiv)",
            menu=self.build_menu()
        )

    def create_icon(self):
        try:
            if ICON_PATH.exists():
                return Image.open(ICON_PATH)
        except Exception as e:
            print(f"⚠️ Icon Fehler: {e}")

        img = Image.new("RGB", (64, 64), color="gray")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "S", fill="white")
        return img

    def update_icon(self):
        base = self.create_icon().resize((64, 64)).convert("RGBA")

        overlay = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        color = "green" if self.is_running else "gray"
        draw.ellipse((45, 45, 60, 60), fill=color)

        self.icon.icon = Image.alpha_composite(base, overlay)
        self.icon.title = f"Sorterino ({'Aktiv' if self.is_running else 'Inaktiv'})"

    def build_menu(self):
        return pystray.Menu(
            item(self.get_start_label, self.toggle_pipeline),
            item("Logs anzeigen", self.open_logs_window),
            item("Einstellungen", self.open_settings),
            item("Beenden", self.exit_app)
        )

    def get_start_label(self, item):
        return "Stoppen" if self.is_running else "Starten"

    def toggle_pipeline(self, icon, item):
        self.is_running = not self.is_running

        if self.is_running:
            threading.Thread(target=self.run_pipeline, daemon=True).start()

        self.update_icon()
        self.icon.menu = self.build_menu()

    def run_pipeline(self):
        import time

        while self.is_running:
            try:
                from main import main
                print("🔄 Pipeline läuft...")
                main()
            except Exception as e:
                print("❌ Pipeline Fehler:", e)

            time.sleep(5)  # Intervall (5 Sekunden)

    def open_logs_window(self, icon, item):
        import subprocess
        import sys

        subprocess.Popen([sys.executable, "-m", "src.gui.app", "--logs"])

    def open_settings(self, icon, item):
        import subprocess
        import sys

        subprocess.Popen([sys.executable, "-m", "src.gui.app", "--settings"])

    def exit_app(self, icon, item):
        self.icon.stop()

    def run(self):
        if self.config_service.get("auto_mode"):
            self.is_running = True
            threading.Thread(target=self.run_pipeline, daemon=True).start()

        self.update_icon()
        self.icon.run()