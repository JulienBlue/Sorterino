import customtkinter as ctk
from src.gui.storage_window import StorageWindow
from src.infrastructure.config.config_service import ConfigService
from src.infrastructure.system.autostart_service import AutostartService


class ConfigWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.config_service = ConfigService()
        self.autostart_service = AutostartService()

        self.title("Konfiguration")
        self.geometry("320x300")

        self.create_ui()
        self.load_values()

    def create_ui(self):

        self.storage_btn = ctk.CTkButton(
            self,
            text="Speicherort",
            command=self.open_storage
        )
        self.storage_btn.pack(pady=10)

        self.auto_mode_checkbox = ctk.CTkCheckBox(
            self,
            text="Automatikmodus",
            command=self.toggle_auto_mode
        )
        self.auto_mode_checkbox.pack(pady=10)

        self.autostart_checkbox = ctk.CTkCheckBox(
            self,
            text="Autostart",
            command=self.toggle_autostart
        )
        self.autostart_checkbox.pack(pady=10)

    def load_values(self):
        if self.config_service.get("auto_mode"):
            self.auto_mode_checkbox.select()

        if self.config_service.get("autostart"):
            self.autostart_checkbox.select()

    def toggle_auto_mode(self):
        value = self.auto_mode_checkbox.get() == 1
        self.config_service.set("auto_mode", value)

    def toggle_autostart(self):
        value = self.autostart_checkbox.get() == 1

        self.config_service.set("autostart", value)

        if value:
            self.autostart_service.enable()
        else:
            self.autostart_service.disable()

    def open_storage(self):
        StorageWindow(self)