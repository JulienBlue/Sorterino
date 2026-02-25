import sys
from pathlib import Path

# -------------------------------------------------
# Projekt-Root bestimmen
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
SRC_PATH = BASE_DIR / "src"

# src dem Python-Path hinzufügen
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# -------------------------------------------------
# Jetzt dürfen wir src-Module importieren
# -------------------------------------------------

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



def main() -> None:

    # 1. Konfiguration
    config_path = BASE_DIR / "config.json"
    config = Config(config_path)

    if not config.user_path:
        raise ValueError("user_path ist nicht konfiguriert.")

    # 2. Workspace
    initialize_workspace(config)

    # 3. Rules
    rules = RulesLoader(BASE_DIR / "rules.json").load_rules()

    # 4. Struktur
    structure = StructureLoader(BASE_DIR / "structure.json").load_structure()

    # 5. Formate
    formats_config = FormatsLoader(
        BASE_DIR / "supported_formats.json"
    ).load()

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    # 6. Infrastruktur

    # EINZIGE Quelle: incoming
    source = FolderDocumentSource(config.incoming_root)

    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path)
    )

    logger = FileLogger()

    storage_service = FilesystemStorage(config.user_path)

    # 7. Pipeline
    pipeline = DocumentPipeline(
        sources=[source],
        ocr_service=ocr_service,
        storage_service=storage_service,
        logger=logger,
        rules=rules,
        supported_extensions=supported_extensions,
        unsupported_target=unsupported_target,
        structure=structure,
        manual_sort_target=config.manual_sort_root
    )

    # 8. Start
    pipeline.run()

# Debug
    # print("User Path:", config.user_path)
    # print("Runtime Root:", config.runtime_root)
    # print("Incoming Root:", config.incoming_root)
    # print("Manual Sort Root:", config.manual_sort_root)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Ausführung manuell beendet.")