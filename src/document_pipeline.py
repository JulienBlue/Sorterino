import os
from pathlib import Path

from src.storage_utils import StoragePathBuilder
from src.document_analyzer import DocumentAnalyzer
from src.models import Document, DocumentStatus
from src.reporting import DailyReportManager


class DocumentPipeline:

    # CONFIG / INIT
    def __init__(
        self,
        config,
        sources,
        ocr_service,
        runtime_storage,
        archive_storage,
        logger,
        rules,
        structure
    ):
        self.sources = sources
        self.ocr = ocr_service
        self.runtime = runtime_storage
        self.archive = archive_storage
        self.logger = logger

        self.config = config

        self.analyzer = DocumentAnalyzer(
            rules,
            config.raw.get("company_profile", {}),
            logger
        )

        self.path_builder = StoragePathBuilder(structure or {})
        self.reporter = DailyReportManager(config.logs_root)

        self.supported_extensions = {".pdf", ".png", ".jpg", ".jpeg"}

        targets = config.raw.get("targets", {})
        self.manual_sort_target = targets.get("manual", "manual_sort")
        self.error_target = targets.get("error", "error")

    # PIPELINE / START
    def run(self):

        total = 0

        for source in self.sources:
            documents = list(source.fetch_documents())

            if not documents:
                self.logger.info("Keine neuen Dateien gefunden")
                continue

            for doc in documents:
                total += 1
                self._process(doc)

        else:
            self.logger.info(f"Pipeline fertig {total} Dokument(e) verarbeitet")

    # PIPELINE / PROCESS
    def _process(self, document: Document):

        filename = os.path.basename(document.source_path)
        ext = os.path.splitext(filename)[1].lower()

        self.logger.log(f"IN: {filename}")
        self.logger.info(f"Verarbeite {document.source_path}")

        # BACKUP
        
        try:
            self.runtime.backup(
                document.source_path,
                "backup",
                filename
            )
            self.logger.debug(f"Backup erstellt: {filename}")
        except Exception as e:
            self.logger.warning(f"Backup fehlgeschlagen: {e}")

        # FORMAT / CHECK
        if ext not in self.supported_extensions:
            self.logger.info(f"Unsupported Format {ext}")

            final = self.runtime.store(
                document.source_path,
                self.error_target,
                filename
            )

            self.logger.log(f"UNSUPPORTED: {filename}")
            self.reporter.record_event({
                "status": "error",
                "reason": "unsupported_format",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.error_target),
            })

            document.status = DocumentStatus.ERROR
            return

        # OCR / PROCESS
        self.logger.debug("OCR läuft")
        if not self.ocr:
            self.logger.warning("OCR deaktiviert → direkt manuell")
            text = ""
        else:
            text = self.ocr.extract_text(document.source_path)

        if text is None:
            self.logger.error("OCR Fehler → Datei in Error")

            final = self.runtime.store(
                document.source_path,
                self.error_target,
                filename
            )

            self.logger.log(f"ERROR: {filename}")
            self.reporter.record_event({
                "status": "error",
                "reason": "ocr_error",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.error_target),
            })

            document.status = DocumentStatus.ERROR
            return

        if not text or not text.strip():
            self.logger.info("Kein Text erkannt manuell")

            final = self.runtime.store(
                document.source_path,
                self.manual_sort_target,
                filename
            )

            self.logger.log(f"MANUAL: {filename}")
            self.reporter.record_event({
                "status": "manual",
                "reason": "ocr_empty",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.manual_sort_target),
            })

            document.status = DocumentStatus.STORED
            return

        self.logger.debug(f"OCR Länge {len(text)} Zeichen")

        document.mark_analyzed(text)

        # ANALYSE / LOGIK
        classification, metadata, extracted = self.analyzer.analyze(document)

        self.logger.info(
            f"Klassifikation {classification.category} "
            f"{classification.confidence:.2f}"
        )

        self.logger.debug(f"Extrahiert {extracted}")

        if not classification.category or classification.category == "MANUELL":
            self.logger.info("Nicht zuordenbar manuell")

            final = self.runtime.store(
                document.source_path,
                self.manual_sort_target,
                filename
            )

            self.logger.log(f"MANUAL: {filename}")
            self.reporter.record_event({
                "status": "manual",
                "reason": "classify_none",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.manual_sort_target),
            })

            document.status = DocumentStatus.STORED
            return

        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = extracted

        # STORAGE / PATH
        try:
            target_path = self.path_builder.build(document)
        except Exception as e:
            self.logger.error(f"{filename} PATH ERROR {e}")

            final = self.runtime.store(
                document.source_path,
                self.error_target,
                filename
            )

            self.reporter.record_event({
                "status": "error",
                "reason": "path_error",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.error_target),
            })

            document.status = DocumentStatus.ERROR
            return

        self.logger.debug(f"Zielpfad {target_path}")

        # STORAGE / SAVE
        try:
            final = self.archive.store(
                document.source_path,
                target_path.parent,
                target_path.name
            )

            self.logger.log(f"OUT: {filename} {final}")
            self.logger.debug(f"________________________________")

            self.reporter.record_event({
                "status": "success",
                "reason": "ok",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(target_path.parent),
            })

            document.mark_stored(str(final))

        except Exception as e:
            self.logger.error(f"{filename} {str(e)}")

            final = self.runtime.store(
                document.source_path,
                self.error_target,
                filename
            )

            self.reporter.record_event({
                "status": "error",
                "reason": "store_error",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(self.error_target),
            })

            document.status = DocumentStatus.ERROR
