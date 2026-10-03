import sys
import tempfile
import os
import json
import threading
from pathlib import Path

from src.config import Config
from src.initialize_workspace import initialize_workspace

from src.storage_utils import FileDocumentSource, FolderDocumentSource, FilesystemStorage
from src.tesseract_ocr import TesseractOCR
from src.document_text_extractor import DocumentTextExtractor
from src.logger import FileLogger
from src.document_pipeline import DocumentPipeline
from src.mail_fetcher import fetch_attachments
from src.profile_service import ProfileService, ProfileValidationError
from src.manual_review_suggestions import ManualReviewSuggestionStore

_pipeline_running = False
_pipeline_lock = threading.Lock()
_pipeline_stop_requested = threading.Event()

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


def _load_profile_service(config, logger):
    settings = config.get("profile_system") or {}
    try:
        service = ProfileService(config)
        if not service.list_profiles():
            return None

        # Existing profiles are the source of truth.  Older or partially
        # written settings may still say that the profile system is disabled;
        # silently honoring that flag would archive documents without their
        # profile/person prefix.
        if not settings.get("enabled"):
            repaired_settings = dict(settings)
            repaired_settings["enabled"] = True
            try:
                config.set("profile_system", repaired_settings)
                logger.info("Profilverwaltung automatisch aktiviert")
            except OSError as exc:
                logger.warning(
                    "Profilverwaltung konnte nicht dauerhaft aktiviert werden: "
                    f"{exc}"
                )
        return service
    except ProfileValidationError as exc:
        logger.warning(f"Profilverwaltung deaktiviert: {exc}")
        return None



# PIPELINE / RUN
def run_pipeline(document_path=None, *, force_reprocess=False) -> None:
    global _pipeline_running

    if not _pipeline_lock.acquire(blocking=False):
        print("[INFO] Pipeline läuft bereits")
        return

    _pipeline_running = True
    _pipeline_stop_requested.clear()

    try:
        config = load_config_safe()

        if not config or not config.user_path:
            print("[WARN] Kein Speicherort gesetzt")
            return

        
        # INIT WORKSPACE
        
        initialize_workspace(config)

        rules_data = load_json_safe(config.rules_path, {})

        logger = FileLogger(
            config.logs_root,
            developer_mode=config.get("developer_mode", False),
        )
        profile_service = _load_profile_service(config, logger)

        
        # MAIL (IMMER ZUERST, GENAU 1x)
        
        if document_path is None:
            try:
                fetch_attachments(config, profile_service, logger=logger)
            except Exception as e:
                logger.error(f"[MAIL] Abruf fehlgeschlagen: {e}")

        
        # OCR (OPTIONAL)
        
        ocr_service = None

        try:
            ocr_service = TesseractOCR(
                poppler_path=str(config.poppler_path),
                tesseract_path=str(config.tesseract_path),
                logger=logger
            )
            logger.info("[OCR] Initialisiert")
        except Exception as e:
            logger.warning(f"[OCR] OCR deaktiviert: {e}")

        document_extractor = DocumentTextExtractor(ocr_service, logger)

        
        # PIPELINE SETUP
        runtime_storage = FilesystemStorage(config.runtime_root)
        archive_storage = FilesystemStorage(config.user_path)

        if document_path is None:
            source = FolderDocumentSource(config.incoming_root)
        else:
            selected = Path(document_path).resolve()
            allowed_root = Path(
                config.manual_root if force_reprocess else config.incoming_root
            ).resolve()
            try:
                selected.relative_to(allowed_root)
            except ValueError:
                logger.warning(
                    "Einzeldokument liegt nicht im erlaubten Verarbeitungsordner"
                )
                return
            if force_reprocess:
                suggestions = ManualReviewSuggestionStore(config)
                suggestion = suggestions.load(selected)
                if suggestion.get("review_kind") not in {
                    "exact_duplicate", "same_import_duplicate"
                }:
                    logger.warning(
                        "Erneute Analyse abgelehnt: Dokument ist nicht als Duplikat markiert"
                    )
                    return
            source = FileDocumentSource(selected)

        pipeline = DocumentPipeline(
            config=config,
            sources=[source],
            ocr_service=document_extractor,
            runtime_storage=runtime_storage,
            archive_storage=archive_storage,
            logger=logger,
            rules=rules_data,
            structure=load_json_safe(config.structure_path, {}),
            profile_service=profile_service,
            stop_requested=_pipeline_stop_requested.is_set,
            allow_exact_duplicate=force_reprocess,
        )

        # RUN
        try:
            pipeline.run()
            if force_reprocess and not selected.exists():
                suggestions.remove(selected)
        except Exception as e:
            logger.error(f"Pipeline Lauf fehlgeschlagen: {e}")

    except Exception as e:
        print(f"[ERROR] Unerwarteter Fehler in run_pipeline: {e}")

    finally:
        _pipeline_running = False
        _pipeline_lock.release()


def is_pipeline_running() -> bool:
    return _pipeline_running


def request_pipeline_stop() -> bool:
    """Request a cooperative stop at the next safe pipeline checkpoint."""
    if not _pipeline_running:
        return False
    _pipeline_stop_requested.set()
    return True



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
