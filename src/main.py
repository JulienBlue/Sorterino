import os
from pathlib import Path

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
# Projekt-Root bestimmen (für rules.json etc.)
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:

    # ----------------------------------------
    # 1. Konfiguration laden
    # ----------------------------------------
    config_path = BASE_DIR / "config.json"
    config = Config(config_path)

    if not config.user_path:
        raise ValueError("user_path ist nicht konfiguriert.")

    # ----------------------------------------
    # 2. Workspace initialisieren
    # ----------------------------------------
    initialize_workspace(config)

    # ----------------------------------------
    # 3. Rules laden
    # ----------------------------------------
    rules_path = BASE_DIR / "rules.json"
    rules_loader = RulesLoader(rules_path)
    rules = rules_loader.load_rules()

    # ----------------------------------------
    # 4. Struktur laden
    # ----------------------------------------
    structure_path = BASE_DIR / "structure.json"
    structure_loader = StructureLoader(structure_path)
    structure = structure_loader.load_structure()

    # ----------------------------------------
    # 5. Formate laden
    # ----------------------------------------
    formats_path = BASE_DIR / "supported_formats.json"
    formats_loader = FormatsLoader(formats_path)
    formats_config = formats_loader.load()

    supported_extensions = set(formats_config["supported_extensions"])
    unsupported_target = formats_config["unsupported_target"]

    # ----------------------------------------
    # 6. Infrastruktur erstellen
    # ----------------------------------------

    # Dokumentquelle: Runtime Incoming
    source = FolderDocumentSource(config.runtime_root)

    # OCR Service mit relativen Third-Party-Pfaden
    ocr_service = TesseractOCR(
        poppler_path=str(config.poppler_path),
        tesseract_path=str(config.tesseract_path)
    )

    logger = FileLogger()

    # Storage-Ziel: Sorterino Business Root
    storage_service = FilesystemStorage(config.sorterino_root)

    # ----------------------------------------
    # 7. Pipeline zusammensetzen
    # ----------------------------------------
    pipeline = DocumentPipeline(
        sources=[source],
        ocr_service=ocr_service,
        storage_service=storage_service,
        logger=logger,
        rules=rules,
        supported_extensions=supported_extensions,
        unsupported_target=unsupported_target,
        structure=structure
    )

    # ----------------------------------------
    # 8. Pipeline starten
    # ----------------------------------------
    pipeline.run()

    # ----------------------------------------
    # 9. Debug-Ausgabe
    # ----------------------------------------
    print("User Path:", config.user_path)
    print("Sorterino Root:", config.sorterino_root)
    print("Runtime Root:", config.runtime_root)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Ausführung manuell beendet.")