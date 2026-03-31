import winreg
import sys
from pathlib import Path

APP_NAME = "Sorterino"

class AutostartService:

    def get_exe_path(self):
        if getattr(sys, 'frozen', False):
            return sys.executable
        return str(Path(sys.argv[0]).resolve())

    def enable(self):
        exe_path = self.get_exe_path()

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )

        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)

    def disable(self):
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