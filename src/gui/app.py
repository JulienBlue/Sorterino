import sys
import ctypes
import tkinter as tk
from tkinter import messagebox
import traceback

MUTEX_NAME = "SorterinoSingletonMutex"


def _argument_value(name):
    try:
        index = sys.argv.index(name)
        return sys.argv[index + 1]
    except (ValueError, IndexError):
        return None


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


def remove_mail_credentials_for_uninstall():
    """Non-interactive cleanup entry point used by the signed uninstaller."""
    from src.config import Config
    from src.mail_auth import delete_all_mail_credentials

    delete_all_mail_credentials(Config())


# ENTRY / START
if __name__ == "__main__":
    try:
        if "--developer-console" in sys.argv:
            from src.gui.developer_console import run_developer_console
            parent_pid = _argument_value("--parent-pid")
            run_developer_console(int(parent_pid) if parent_pid and parent_pid.isdigit() else None)
            sys.exit(0)

        if "--remove-mail-credentials" in sys.argv:
            remove_mail_credentials_for_uninstall()
            sys.exit(0)

        _mutex = _check_singleton()
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
