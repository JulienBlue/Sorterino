import winreg
import sys
import os

# CONFIG / KONSTANTEN
APP_NAME = "Sorterino"


class AutostartService:

    # PFAD / EXE
    def get_exe_path(self):
        try:
            # PyInstaller EXE
            if getattr(sys, "frozen", False):
                return sys.executable

            # Dev Mode
            return os.path.abspath(sys.argv[0])

        except Exception as e:
            print(f"[ERROR] EXE-Pfad konnte nicht ermittelt werden: {e}")
            return None

    # AUTOSTART / AKTIVIEREN
    def enable(self):
        exe_path = self.get_exe_path()

        if not exe_path:
            print("[ERROR] Kein gültiger EXE-Pfad für Autostart")
            return

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)

            print("[INFO] Autostart aktiviert")

        except Exception as e:
            print(f"[ERROR] Autostart konnte nicht aktiviert werden: {e}")

    # AUTOSTART / DEAKTIVIEREN
    def disable(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            try:
                winreg.DeleteValue(key, APP_NAME)
                print("[INFO] Autostart deaktiviert")
            except FileNotFoundError:
                print("[INFO] Autostart war nicht gesetzt")

            winreg.CloseKey(key)

        except Exception as e:
            print(f"[ERROR] Autostart konnte nicht deaktiviert werden: {e}")