import sys
import json
from pathlib import Path

# -------------------------------------------------
# Projekt-Root bestimmen
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# -------------------------------------------------

from src.utils.path_helper import get_user_base_dir

from infrastructure.config.config_loader import Config
from infrastructure.config.rules_loader import RulesLoader
from infrastructure.config.structure_loader import StructureLoader
from infrastructure.config.formats_loader import FormatsLoader
from infrastructure.config.initialize_workspace import initialize_workspace

from infrastructure.io.folder_document_source import FolderDocumentSource
from infrastructure.ocr.tesseract_ocr import TesseractOCR
from infrastructure.logging.file_logger import FileLogger
from infrastructure.storage.filesystem_storage import FilesystemStorage

from usecases.document_pipeline import DocumentPipeline


# -------------------------------------------------
# CONFIG BOOTSTRAP (PORTABLE!)
# -------------------------------------------------

def load_or_create_config():
    base = get_user_base_dir()
    runtime = base / ".sorterino_runtime"

    runtime.mkdir(parents=True, exist_ok=True)

    config_path = runtime / "config.json"

    if not config_path.exists():
        default_config = {
            "user_path": str(base),
            "runtime_folder_name": ".sorterino_runtime",
            "input_folder_name": "Sorterino - Input",
            "manual_sort_folder_name": "Sorterino - Manuelle Sortierung",
            "poppler_path": "third_party/poppler-25.12.0/Library/bin",
            "tesseract_path": "third_party/Tesseract-OCR/tesseract.exe"
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

    return config_path


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main() -> None:

    # 🔥 WICHTIG: portable config laden
    config_path = load_or_create_config()
    config = Config(config_path)

    company_profile = config.raw.get("company_profile", {})

    if not config.user_path:
        raise ValueError("user_path ist nicht konfiguriert.")

    initialize_workspace(config)

    # 🔥 WICHTIG: BASE_DIR behalten für interne Dateien
    rules = RulesLoader(BASE_DIR / "rules.json").load_rules()
    structure = StructureLoader(BASE_DIR / "structure.json").load_structure()

    formats_config = FormatsLoader(
        BASE_DIR / "supported_formats.json"
    ).load()

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    source = FolderDocumentSource(config.incoming_root)

    logger = FileLogger(config.logs_root)

    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path),
        logger=logger
    )

    # STORAGE-KONTEXTE
    runtime_storage = FilesystemStorage(config.runtime_root)
    archive_storage = FilesystemStorage(config.user_path)

    pipeline = DocumentPipeline(
        sources=[source],
        ocr_service=ocr_service,
        runtime_storage=runtime_storage,
        archive_storage=archive_storage,
        logger=logger,
        rules=rules,
        company_profile=company_profile,
        supported_extensions=supported_extensions,
        unsupported_target=unsupported_target,
        structure=structure,
        manual_sort_target="manual_sort",
        error_target="error"
    )

    pipeline.run()


# -------------------------------------------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🔵 Ausführung manuell beendet.")