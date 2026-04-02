import sys
from src.gui.tray import TrayApp

def bring_to_front(app):
    import ctypes

    app.update_idletasks()
    app.deiconify()

    hwnd = app.winfo_id()

    # Fenster anzeigen
    ctypes.windll.user32.ShowWindow(hwnd, 5)

    # Fokus erzwingen
    ctypes.windll.user32.SetForegroundWindow(hwnd)

    # zusätzlicher Fallback
    app.lift()
    app.focus_force()

    app.attributes("-topmost", True)
    app.after(200, lambda: app.attributes("-topmost", False))

def run_settings():
    from src.gui.config_window import ConfigWindow

    app = ConfigWindow()

    app.after(100, lambda: bring_to_front(app))

    app.mainloop()


def run_logs():
    from src.gui.log_window import LogWindow

    app = LogWindow()

    app.after(100, lambda: bring_to_front(app))

    app.mainloop()


def main():
    tray = TrayApp()
    tray.run()


if __name__ == "__main__":
    if "--settings" in sys.argv:
        run_settings()
    elif "--logs" in sys.argv:
        run_logs()
    else:
        main()