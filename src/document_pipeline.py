import os
from pathlib import Path

from src.storage_utils import StoragePathBuilder
from src.document_analyzer import DocumentAnalyzer
from src.models import Document, DocumentStatus
from src.reporting import DailyReportManager


class DocumentPipeline:
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

    def _store_runtime(self, document, target, filename, log_label, event_status, reason):
        final = self.runtime.store(document.source_path, target, filename)
        self.logger.log(f"{log_label}: {filename}")
        self.reporter.record_event({
            "status": event_status,
            "reason": reason,
            "original_name": filename,
            "final_name": Path(final).name if final else filename,
            "target_folder": str(Path(final).parent) if final else str(target),
        })
        return final

    def _missing_required_data(self, document: Document):
        doc_type = (document.metadata.document_type or "") if document.metadata else ""
        data = document.extracted_data or {}

        if doc_type == "Ausgangsrechnungen":
            required = {
                "date": data.get("date"),
                "vendor": data.get("vendor"),
                "invoice_number": data.get("invoice_number"),
            }
        elif doc_type == "Eingangsrechnungen":
            required = {
                "date": data.get("date"),
                "vendor": data.get("vendor"),
            }
        else:
            return []

        return [key for key, value in required.items() if not value]

    def _process(self, document: Document):
        filename = os.path.basename(document.source_path)
        ext = os.path.splitext(filename)[1].lower()

        self.logger.log(f"IN: {filename}")
        self.logger.info(f"Verarbeite {document.source_path}")
        
        try:
            self.runtime.backup(document.source_path, "backup", filename)
            self.logger.debug(f"Backup erstellt: {filename}")
        except Exception as e:
            self.logger.warning(f"Backup fehlgeschlagen: {e}")

        if ext not in self.supported_extensions:
            self.logger.info(f"Unsupported Format {ext}")
            self._store_runtime(document, self.error_target, filename, "UNSUPPORTED", "error", "unsupported_format")
            document.status = DocumentStatus.ERROR
            return

        self.logger.debug("OCR läuft")
        if not self.ocr:
            self.logger.warning("OCR deaktiviert → direkt manuell")
            text = ""
        else:
            text = self.ocr.extract_text(document.source_path)

        if text is None:
            self.logger.error("OCR Fehler → Datei in Error")
            self._store_runtime(document, self.error_target, filename, "ERROR", "error", "ocr_error")
            document.status = DocumentStatus.ERROR
            return

        if not text or not text.strip():
            self.logger.info("Kein Text erkannt manuell")
            self._store_runtime(document, self.manual_sort_target, filename, "MANUAL", "manual", "ocr_empty")
            document.status = DocumentStatus.STORED
            return

        self.logger.debug(f"OCR Länge {len(text)} Zeichen")

        document.mark_analyzed(text)
        classification, metadata, extracted = self.analyzer.analyze(document)

        self.logger.info(
            f"Klassifikation {classification.category} "
            f"{classification.confidence:.2f}"
        )

        self.logger.debug(f"Extrahiert {extracted}")

        if not classification.category or classification.category == "MANUELL":
            self.logger.info("Nicht zuordenbar manuell")
            self._store_runtime(document, self.manual_sort_target, filename, "MANUAL", "manual", "classify_none")
            document.status = DocumentStatus.STORED
            return

        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = extracted

        missing_fields = self._missing_required_data(document)
        if missing_fields:
            self.logger.info(
                "Unvollständige Extraktion manuell "
                + ", ".join(missing_fields)
            )
            self._store_runtime(
                document,
                self.manual_sort_target,
                filename,
                "MANUAL",
                "manual",
                "missing_required_data",
            )
            document.status = DocumentStatus.STORED
            return

        try:
            target_path = self.path_builder.build(document)
        except Exception as e:
            self.logger.error(f"{filename} PATH ERROR {e}")
            self._store_runtime(document, self.error_target, filename, "ERROR", "error", "path_error")
            document.status = DocumentStatus.ERROR
            return

        self.logger.debug(f"Zielpfad {target_path}")

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
            self._store_runtime(document, self.error_target, filename, "ERROR", "error", "store_error")
            document.status = DocumentStatus.ERROR
