import sys
import ctypes
import tkinter as tk
from tkinter import messagebox

MUTEX_NAME = "SorterinoSingletonMutex"


# SYSTEM / SINGLETON
def _check_singleton():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)

    if ctypes.windll.kernel32.GetLastError() == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Sorterino")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Sorterino", "Sorterino läuft bereits!")
        root.destroy()

        sys.exit(0)

    return mutex


# WINDOW / FOCUS
def bring_to_front(app):
    app.update_idletasks()
    app.deiconify()

    hwnd = app.winfo_id()

    ctypes.windll.user32.ShowWindow(hwnd, 5)
    ctypes.windll.user32.SetForegroundWindow(hwnd)

    app.lift()
    app.focus_force()

    app.attributes("-topmost", True)
    app.after(200, lambda: app.attributes("-topmost", False))


# GUI / SETTINGS
def run_settings():
    import customtkinter as ctk
    from src.gui.config_window import ConfigWindow

    root = ctk.CTk()
    root.withdraw()

    app = ConfigWindow(master=root)
    app.after(100, lambda: bring_to_front(app))
    root.mainloop()


# GUI / LOGS
def run_logs():
    import customtkinter as ctk
    from src.gui.log_window import LogWindow

    root = ctk.CTk()
    root.withdraw()

    app = LogWindow(master=root)
    app.after(100, lambda: bring_to_front(app))
    root.mainloop()


# APP / MAIN
def main():
    from src.gui.tray import TrayApp
    tray = TrayApp()
    tray.run()


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

    except Exception:
        import traceback
        traceback.print_exc()
        input("CRASH ENTER drücken zum Schließen")