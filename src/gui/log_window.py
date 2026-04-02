import customtkinter as ctk
from src.infrastructure.config.config_loader import Config
from src.infrastructure.config.config_service import ConfigService


class LogWindow(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.title("Logs")
        self.geometry("600x400")

        config = Config(ConfigService().config_path)
        self.log_dir = config.logs_root

        self.create_ui()
        self.update_logs()

    def create_ui(self):
        self.textbox = ctk.CTkTextbox(self)
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)

    def update_logs(self):
        latest_file = None

        if self.log_dir.exists():
            logs = sorted(self.log_dir.glob("*.log"), reverse=True)
            if logs:
                latest_file = logs[0]

        if latest_file:
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", content)

        self.after(2000, self.update_logs)