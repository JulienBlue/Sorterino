import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
import threading
import json

from src.infrastructure.config.config_loader import Config
from src.infrastructure.config.initialize_workspace import initialize_workspace

from src.usecases.document_pipeline import DocumentPipeline

from src.infrastructure.config.rules_loader import RulesLoader
from src.infrastructure.config.structure_loader import StructureLoader
from src.infrastructure.config.formats_loader import FormatsLoader

from src.infrastructure.io.folder_document_source import FolderDocumentSource
from src.infrastructure.ocr.tesseract_ocr import TesseractOCR
from src.infrastructure.logging.file_logger import FileLogger
from src.infrastructure.storage.filesystem_storage import FilesystemStorage

from src.utils.path_helper import get_user_base_dir, get_base_path


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Sorterino v0.4.0")
        self.geometry("600x550")

        self.config_path = get_user_base_dir() / "config.json"
        self.config_data = self.load_config()

        self.auto_running = False
        self.auto_job = None

        self.create_widgets()

        self.auto_var.set(self.config_data.get("auto_mode", False))
        self.autostart_var.set(self.config_data.get("autostart", False))

        if self.config_data.get("user_path"):
            self.path_label.configure(text=self.config_data["user_path"])

    # ---------------- CONFIG ----------------

    def load_config(self):
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2)

    # ---------------- UI ----------------

    def create_widgets(self):

        self.path_label = ctk.CTkLabel(self, text="Kein Pfad gewählt")
        self.path_label.pack(pady=10)

        self.select_btn = ctk.CTkButton(
            self,
            text="Ordner auswählen",
            command=self.select_folder
        )
        self.select_btn.pack(pady=5)

        self.init_btn = ctk.CTkButton(
            self,
            text="Workspace einrichten",
            command=self.init_workspace
        )
        self.init_btn.pack(pady=5)

        self.run_btn = ctk.CTkButton(
            self,
            text="Pipeline manuell starten",
            command=self.run_pipeline
        )
        self.run_btn.pack(pady=10)

        # 🔥 BUTTON BAR
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=5)

        self.settings_btn = ctk.CTkButton(
            self.button_frame,
            text="⚙ Einstellungen",
            command=self.open_settings
        )
        self.settings_btn.pack(side="left", padx=5)

        # ---------------- Auto ----------------

        self.auto_var = ctk.BooleanVar(value=False)

        self.auto_checkbox = ctk.CTkCheckBox(
            self,
            text="Automatische Überwachung",
            variable=self.auto_var,
            command=self.toggle_auto_mode
        )
        self.auto_checkbox.pack(pady=5)

        # ---------------- Autostart ----------------

        self.autostart_var = ctk.BooleanVar(value=False)

        self.autostart_checkbox = ctk.CTkCheckBox(
            self,
            text="Mit Windows starten",
            variable=self.autostart_var,
            command=self.toggle_autostart
        )
        self.autostart_checkbox.pack(pady=5)

        # ---------------- Log ----------------

        self.log_box = ctk.CTkTextbox(self, height=250)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------- SETTINGS ----------------

    def open_settings(self):
        from src.infrastructure.config.config_loader import Config
        from src.gui.settings_window import SettingsWindow

        config = Config(self.config_path)
        SettingsWindow(self, config)
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config_data["user_path"] = folder
            self.save_config()
            self.path_label.configure(text=folder)

    def toggle_auto_mode(self):
        self.config_data["auto_mode"] = self.auto_var.get()
        self.save_config()

    def toggle_autostart(self):
        self.config_data["autostart"] = self.autostart_var.get()
        self.save_config()

    # ---------------- WORKSPACE ----------------

    def init_workspace(self):
        config = Config(self.config_path)
        result = initialize_workspace(config)

        self.log(f"Runtime: {result['runtime_root']}")
        self.log(f"Incoming: {result['incoming_root']}")

    # ---------------- PIPELINE ----------------

    def run_pipeline(self):

        self.run_btn.configure(state="disabled")

        def task():
            try:
                config = Config(self.config_path)

                rules = RulesLoader(config.rules_path).load_rules()
                structure = StructureLoader(config.structure_path).load_structure()
                formats = FormatsLoader(config.formats_path).load()

                source = FolderDocumentSource(config.incoming_root)
                logger = FileLogger(config.logs_root)

                ocr = TesseractOCR(
                    poppler_path=str(config.poppler_path),
                    tesseract_path=str(config.tesseract_path),
                    logger=logger
                )

                runtime_storage = FilesystemStorage(config.runtime_root)
                archive_storage = FilesystemStorage(config.user_path)

                pipeline = DocumentPipeline(
                    sources=[source],
                    ocr_service=ocr,
                    runtime_storage=runtime_storage,
                    archive_storage=archive_storage,
                    logger=logger,
                    rules=rules,
                    company_profile=config.company_profile,
                    supported_extensions=set(formats["supported_extensions"]),
                    unsupported_target=formats["unsupported_target"],
                    structure=structure,
                    manual_sort_target="manual_sort",
                    error_target="error"
                )

                self.log("Starte Pipeline...")
                pipeline.run()
                self.log("Fertig.")

            except Exception as e:
                self.log(f"Fehler: {e}")

            finally:
                self.run_btn.configure(state="normal")

        threading.Thread(target=task, daemon=True).start()

    # ---------------- LOG ----------------

    def log(self, message):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")