import winreg
import sys
import os

# CONFIG / KONSTANTEN
APP_NAME = "Sorterino"


class AutostartService:

    # PFAD / EXE
    def get_exe_path(self):
        return os.path.abspath(sys.argv[0])

    # AUTOSTART / AKTIVIEREN
    def enable(self):
        exe_path = self.get_exe_path()

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)

        except Exception:
            pass

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
            except FileNotFoundError:
                pass

            winreg.CloseKey(key)

        except Exception:
            pass