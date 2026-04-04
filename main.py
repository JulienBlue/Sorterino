import sys
import tempfile
import os
import json

from src.config.config_loader import Config
from src.config.config_service import ConfigService
from src.initialize_workspace import initialize_workspace

from src.storage_utils import FolderDocumentSource, FilesystemStorage
from src.tesseract_ocr import TesseractOCR
from src.logger import FileLogger
from src.document_pipeline import DocumentPipeline

_pipeline_running = False

LOCK_FILE = os.path.join(tempfile.gettempdir(), "sorterino.lock")


# CONFIG / LOAD
def load_config_safe():
    service = ConfigService()
    path = service.config_path

    config = Config(path)

    if not config.user_path:
        return None

    return config


# IO / JSON LOAD
def load_json_safe(path, fallback):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return fallback
    except Exception:
        return fallback


# PIPELINE / RUN
def run_pipeline() -> None:
    global _pipeline_running

    if _pipeline_running:
        return

    _pipeline_running = True

    try:
        config = load_config_safe()

        if not config or not config.user_path:
            return

        initialize_workspace(config)

        rules_data = load_json_safe(config.rules_path, {})
        rules = rules_data.get("rules", [])

        logger = FileLogger(config.logs_root)
        if not hasattr(logger, "_init"):
            logger.info("Pipeline gestartet")
            logger._init = True

        try:
            ocr_service = TesseractOCR(
                poppler_path=str(config.poppler_path),
                tesseract_path=str(config.tesseract_path),
                logger=logger
            )
        except Exception:
            return

        runtime_storage = FilesystemStorage(config.runtime_root)
        archive_storage = FilesystemStorage(config.user_path)

        source = FolderDocumentSource(config.incoming_root)

        pipeline = DocumentPipeline(
            config=config,
            sources=[source],
            ocr_service=ocr_service,
            runtime_storage=runtime_storage,
            archive_storage=archive_storage,
            logger=logger,
            rules=rules,
            structure=load_json_safe(config.structure_path, {})
        )

        pipeline.run()

    except Exception:
        pass

    finally:
        _pipeline_running = False


# APP / MAIN
def main():
    if os.path.exists(LOCK_FILE):
        return

    with open(LOCK_FILE, "w") as f:
        f.write("running")

    try:
        run_pipeline()
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


# ENTRY / START
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        sys.exit(1)