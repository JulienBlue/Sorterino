import sys
from src.gui.tray import TrayApp


def run_settings():
    from src.gui.config_window import ConfigWindow

    app = ConfigWindow()

    app.after(0, lambda: (
        app.lift(),
        app.focus_force(),
        app.attributes("-topmost", True),
        app.after(200, lambda: app.attributes("-topmost", False))
    ))

    app.mainloop()


def run_logs():
    from src.gui.log_window import LogWindow

    app = LogWindow()

    app.after(0, lambda: (
        app.lift(),
        app.focus_force(),
        app.attributes("-topmost", True),
        app.after(200, lambda: app.attributes("-topmost", False))
    ))

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