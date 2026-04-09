import sys
import tempfile
import os
import json

from src.config import Config
from src.initialize_workspace import initialize_workspace

from src.storage_utils import FolderDocumentSource, FilesystemStorage
from src.tesseract_ocr import TesseractOCR
from src.logger import FileLogger
from src.document_pipeline import DocumentPipeline
from src.mail_fetcher import fetch_attachments

_pipeline_running = False

LOCK_FILE = os.path.join(tempfile.gettempdir(), "sorterino.lock")


# CONFIG / LOAD
def load_config_safe():
    try:
        config = Config()

        if not config.user_path:
            return None

        return config

    except Exception as e:
        print(f"[ERROR] Config konnte nicht geladen werden: {e}")
        return None



# IO / JSON LOAD
def load_json_safe(path, fallback):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return fallback
    except Exception as e:
        print(f"[ERROR] JSON Laden fehlgeschlagen ({path}): {e}")
        return fallback



# PIPELINE / RUN
def run_pipeline() -> None:
    global _pipeline_running

    if _pipeline_running:
        print("[INFO] Pipeline läuft bereits")
        return

    _pipeline_running = True

    try:
        config = load_config_safe()

        if not config or not config.user_path:
            print("[WARN] Kein Speicherort gesetzt")
            return

        
        # INIT WORKSPACE
        
        initialize_workspace(config)

        rules_data = load_json_safe(config.rules_path, {})
        rules = rules_data.get("rules", [])

        logger = FileLogger(config.logs_root)

        
        # MAIL (IMMER ZUERST, GENAU 1x)
        
        try:
            fetch_attachments(config)
        except Exception as e:
            print(f"[MAIL ERROR] {e}")

        
        # OCR (OPTIONAL)
        
        ocr_service = None

        try:
            ocr_service = TesseractOCR(
                poppler_path=str(config.poppler_path),
                tesseract_path=str(config.tesseract_path),
                logger=logger
            )
            print("[OCR] Initialisiert")
        except Exception as e:
            print(f"[OCR WARNING] OCR deaktiviert: {e}")

        
        # PIPELINE SETUP
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

        # RUN
        try:
            pipeline.run()
        except Exception as e:
            print(f"[ERROR] Pipeline Lauf fehlgeschlagen: {e}")

    except Exception as e:
        print(f"[ERROR] Unerwarteter Fehler in run_pipeline: {e}")

    finally:
        _pipeline_running = False



# APP / MAIN
def main():
    if os.path.exists(LOCK_FILE):
        print("[WARN] Sorterino läuft bereits oder wurde nicht sauber beendet")
        try:
            os.remove(LOCK_FILE)
        except Exception as e:
            print(f"[ERROR] Lockfile konnte nicht entfernt werden: {e}")
            return

    try:
        with open(LOCK_FILE, "w") as f:
            f.write("running")

        run_pipeline()

    except Exception as e:
        print(f"[ERROR] Fehler in main(): {e}")

    finally:
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception as e:
                print(f"[ERROR] Lockfile Cleanup fehlgeschlagen: {e}")



# ENTRY / START
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[INFO] Programm durch Benutzer beendet")
    except Exception as e:
        print(f"[FATAL] Unhandled Exception: {e}")
        sys.exit(1)