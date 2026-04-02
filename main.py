import sys

from src.infrastructure.config.config_loader import Config
from src.infrastructure.config.config_service import ConfigService
from src.infrastructure.config.rules_loader import RulesLoader
from src.infrastructure.config.structure_loader import StructureLoader
from src.infrastructure.config.formats_loader import FormatsLoader
from src.infrastructure.config.initialize_workspace import initialize_workspace

from src.infrastructure.io.folder_document_source import FolderDocumentSource
from src.infrastructure.ocr.tesseract_ocr import TesseractOCR
from src.infrastructure.logging.file_logger import FileLogger
from src.infrastructure.storage.filesystem_storage import FilesystemStorage

from src.usecases.document_pipeline import DocumentPipeline
from src.usecases.validate_config import validate_config


# --------------------------------------------------
# CONFIG LOADING
# --------------------------------------------------

def load_or_create_config():
    service = ConfigService()
    return service.config_path


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main() -> None:

    # --------------------------------------------------
    # CONFIG LOAD
    # --------------------------------------------------

    config_path = load_or_create_config()
    config = Config(config_path)

    company_profile = config.raw.get("company_profile", {})

    if not config.user_path:
        raise ValueError("user_path ist nicht konfiguriert.")

    initialize_workspace(config)

    # --------------------------------------------------
    # LOAD CONFIG FILES
    # --------------------------------------------------

    rules = RulesLoader(config.rules_path).load_rules()
    structure = StructureLoader(config.structure_path).load_structure()
    formats_config = FormatsLoader(config.formats_path).load()

    # --------------------------------------------------
    # 🔥 CONFIG VALIDATION (CRITICAL)
    # --------------------------------------------------

    errors = validate_config(
        rules=rules,
        structure=structure,
        company_profile=company_profile
    )

    if errors:
        print("\n❌ CONFIG ERROR:")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)

    # --------------------------------------------------
    # FORMATS
    # --------------------------------------------------

    if "supported_extensions" not in formats_config:
        raise ValueError("formats.json: supported_extensions fehlt")

    if "unsupported_target" not in formats_config:
        raise ValueError("formats.json: unsupported_target fehlt")

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    # --------------------------------------------------
    # LOGGER
    # --------------------------------------------------

    logger = FileLogger(config.logs_root)
    logger.log("🔵 Sorterino gestartet")

    # --------------------------------------------------
    # OCR SETUP CHECK
    # --------------------------------------------------

    if not config.tesseract_path:
        raise ValueError("Tesseract Pfad fehlt")

    if not config.poppler_path:
        logger.log("⚠️ Poppler nicht gesetzt (PDF könnte Probleme machen)")

    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path),
        logger=logger
    )

    # --------------------------------------------------
    # STORAGE
    # --------------------------------------------------

    runtime_storage = FilesystemStorage(config.runtime_root)
    archive_storage = FilesystemStorage(config.user_path)

    # --------------------------------------------------
    # SOURCE
    # --------------------------------------------------

    source = FolderDocumentSource(config.incoming_root)

    # --------------------------------------------------
    # PIPELINE
    # --------------------------------------------------

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

    # --------------------------------------------------
    # RUN
    # --------------------------------------------------

    pipeline.run()


# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🔵 Ausführung manuell beendet.")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)