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


def load_or_create_config():
    service = ConfigService()
    return service.config_path


def main() -> None:

    config_path = load_or_create_config()
    config = Config(config_path)

    company_profile = config.raw.get("company_profile", {})

    if not config.user_path:
        raise ValueError("user_path ist nicht konfiguriert.")

    initialize_workspace(config)

    rules = RulesLoader(config.rules_path).load_rules()
    structure = StructureLoader(config.structure_path).load_structure()

    formats_config = FormatsLoader(config.formats_path).load()

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    source = FolderDocumentSource(config.incoming_root)
    logger = FileLogger(config.logs_root)

    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path),
        logger=logger
    )

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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🔵 Ausführung manuell beendet.")