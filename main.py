import sys
import tempfile
import os

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


LOCK_FILE = os.path.join(tempfile.gettempdir(), "sorterino.lock")


# --------------------------------------------------
# CONFIG LOADING
# --------------------------------------------------

def load_or_create_config():
    service = ConfigService()
    return service.config_path


# --------------------------------------------------
# PIPELINE (REUSABLE)
# --------------------------------------------------

def run_pipeline() -> None:

    config_path = load_or_create_config()
    print("CONFIG PATH:", config_path)

    config = Config(config_path)

    print("USER PATH:", config.user_path)
    print("INCOMING:", config.incoming_root)

    company_profile = config.raw.get("company_profile", {})

    initialize_workspace(config)

    rules = RulesLoader(config.rules_path).load_rules()
    structure = StructureLoader(config.structure_path).load_structure()
    formats_config = FormatsLoader(config.formats_path).load()

    errors = validate_config(
        rules=rules,
        structure=structure,
        company_profile=company_profile
    )

    if errors:
        raise ValueError(f"CONFIG ERROR: {errors}")

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    logger = FileLogger(config.logs_root)
    logger.log("🔵 Pipeline gestartet")

    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path),
        logger=logger
    )

    runtime_storage = FilesystemStorage(config.runtime_root)
    archive_storage = FilesystemStorage(config.user_path)

    source = FolderDocumentSource(config.incoming_root)

    documents = source.fetch_documents()
    print(f"DEBUG: {len(documents)} Dokumente gefunden")

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


# --------------------------------------------------
# CLI ENTRY (LOCK NUR HIER!)
# --------------------------------------------------

def main():
    if os.path.exists(LOCK_FILE):
        print("⚠️ Sorterino läuft bereits")
        return

    with open(LOCK_FILE, "w") as f:
        f.write("running")

    try:
        run_pipeline()
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


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