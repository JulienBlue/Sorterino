import sys
import ctypes
import tkinter as tk
from tkinter import messagebox
import traceback

MUTEX_NAME = "SorterinoSingletonMutex"


# SYSTEM / SINGLETON
def _check_singleton():
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)

        if ctypes.windll.kernel32.GetLastError() == 183:
            try:
                hwnd = ctypes.windll.user32.FindWindowW(None, "Sorterino")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 5)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as e:
                print(f"[WARN] Fenster konnte nicht in den Vordergrund gebracht werden: {e}")

            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("Sorterino", "Sorterino läuft bereits!")
                root.destroy()
            except Exception as e:
                print(f"[ERROR] MessageBox fehlgeschlagen: {e}")

            sys.exit(0)

        return mutex

    except Exception as e:
        print(f"[ERROR] Singleton-Check fehlgeschlagen: {e}")
        return None


# WINDOW / FOCUS
def bring_to_front(app):
    try:
        app.update_idletasks()
        app.deiconify()

        hwnd = app.winfo_id()

        try:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        app.lift()
        app.focus_force()

        app.attributes("-topmost", True)
        app.after(200, lambda: app.attributes("-topmost", False))

    except Exception as e:
        print(f"[ERROR] Fenster konnte nicht fokussiert werden: {e}")


# GUI / SETTINGS
def run_settings():
    try:
        import customtkinter as ctk
        from src.config import Config
        from src.gui.main_window import MainWindow
        from src.gui.appearance import apply_appearance

        config = Config()
        apply_appearance(config.get("appearance_mode", "system"))
        root = ctk.CTk()
        root.withdraw()

        app = MainWindow(master=root, config=config)
        app.show_page("settings")
        app.after(100, lambda: bring_to_front(app))

        root.mainloop()

    except Exception as e:
        print(f"[ERROR] Settings GUI fehlgeschlagen: {e}")
        print(traceback.format_exc())


# GUI / LOGS
def run_logs():
    try:
        import customtkinter as ctk
        from src.config import Config
        from src.gui.log_window import LogWindow
        from src.gui.main_window import MainWindow
        from src.gui.appearance import apply_appearance

        config = Config()
        apply_appearance(config.get("appearance_mode", "system"))
        root = ctk.CTk()
        root.withdraw()

        app = MainWindow(master=root, config=config)
        app.open_view(lambda parent: LogWindow(parent), "settings")
        app.after(100, lambda: bring_to_front(app))

        root.mainloop()

    except Exception as e:
        print(f"[ERROR] Log GUI fehlgeschlagen: {e}")
        print(traceback.format_exc())


# APP / MAIN
def main():
    try:
        from src.gui.tray import TrayApp

        tray = TrayApp()
        tray.run()

    except Exception as e:
        print(f"[ERROR] TrayApp Fehler: {e}")
        print(traceback.format_exc())


# ENTRY / START
if __name__ == "__main__":
    _mutex = _check_singleton()

    try:
        if "--settings" in sys.argv:
            run_settings()
        elif "--logs" in sys.argv:
            run_logs()
        else:
            main()

    except Exception as e:
        print(f"[FATAL] Unhandled Exception: {e}")
        print(traceback.format_exc())
        sys.exit(1)
