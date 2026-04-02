import os

from src.usecases.classify_document import classify_document
from src.usecases.rename_document import rename_document
from src.usecases.path_resolver import PathResolver


class DocumentPipeline:

    def __init__(
        self,
        sources,
        ocr_service,
        runtime_storage,
        archive_storage,
        logger,
        rules,
        company_profile,
        supported_extensions,
        unsupported_target,
        structure,
        manual_sort_target,
        error_target
    ):
        self.sources = sources
        self.ocr_service = ocr_service
        self.runtime_storage = runtime_storage
        self.archive_storage = archive_storage
        self.logger = logger
        self.rules = rules
        self.company_profile = company_profile
        self.supported_extensions = supported_extensions
        self.unsupported_target = unsupported_target
        self.path_resolver = PathResolver(structure)
        self.manual_sort_target = manual_sort_target
        self.error_target = error_target

    # --------------------------------------------------
    # LOGGING HELPER
    # --------------------------------------------------

    def _log_step(self, step, message):
        self.logger.log(f"[{step}] {message}")

    # --------------------------------------------------

    def run(self):

        self._log_step("PIPELINE", "START")

        for source in self.sources:
            documents = source.fetch_documents()

            if not documents:
                self._log_step("SOURCE", "No documents found")
                continue

            for document in documents:
                try:
                    self._process_document(document)
                except Exception as e:
                    self.logger.error(f"[FATAL] {document.id}: {e}")

        self._log_step("PIPELINE", "END")

    # --------------------------------------------------

    def _move_to_manual_sort(self, document, reason="Unbekannt"):

        original_name = os.path.basename(document.source_path)

        try:
            final_path = self.runtime_storage.store(
                document.source_path,
                self.manual_sort_target,
                original_name
            )

        except Exception as e:
            self.logger.error(f"[MANUAL_SORT_FAIL] {e}")

            final_path = self.runtime_storage.store(
                document.source_path,
                self.error_target,
                original_name
            )

            self._log_step("ERROR", f"Moved to ERROR: {final_path}")
            return

        self._log_step("MANUAL_SORT", f"{reason} → {final_path}")

    # --------------------------------------------------

    def _process_document(self, document):

        doc_id = os.path.basename(document.source_path)

        self._log_step("START", doc_id)

        ext = os.path.splitext(document.source_path)[1].lower()
        self._log_step("FILETYPE", ext)

        original_name = os.path.basename(document.source_path)

        # --------------------------------------------------
        # BACKUP
        # --------------------------------------------------

        processed_path = self.runtime_storage.copy(
            document.source_path,
            "processed",
            original_name
        )

        self._log_step("BACKUP", processed_path)

        # --------------------------------------------------
        # FORMAT CHECK
        # --------------------------------------------------

        if ext not in self.supported_extensions:

            self._log_step("UNSUPPORTED", ext)

            self.runtime_storage.store(
                document.source_path,
                self.unsupported_target,
                original_name
            )
            return

        # --------------------------------------------------
        # OCR
        # --------------------------------------------------

        self._log_step("OCR", "start")

        text = self.ocr_service.extract_text(document.source_path)

        if not text.strip():
            self._log_step("OCR_FAIL", "empty text")
            self._move_to_manual_sort(document, "Kein OCR-Text")
            return

        self._log_step("OCR_OK", f"len={len(text)}")

        document.mark_analyzed(text)

        # --------------------------------------------------
        # CLASSIFICATION
        # --------------------------------------------------

        self._log_step("CLASSIFY", "start")

        classification = classify_document(
            document,
            self.rules,
            self.company_profile,
            logger=self.logger
        )

        if not classification or not classification.category:
            self._log_step("CLASSIFY_FAIL", "no category")
            self._move_to_manual_sort(document, "Keine Kategorie")
            return

        self._log_step(
            "CLASSIFY_OK",
            f"{classification.category} ({classification.confidence})"
        )

        document.mark_classified(classification)

        # --------------------------------------------------
        # MANUAL CATEGORY
        # --------------------------------------------------

        if classification.category.lower() in ["manuell", "unknown"]:
            self._move_to_manual_sort(
                document,
                f"Manuell ({classification.confidence})"
            )
            return

        # --------------------------------------------------
        # RENAME
        # --------------------------------------------------

        self._log_step("RENAME", "start")

        new_name = rename_document(document)

        self._log_step("RENAME_OK", new_name)

        # --------------------------------------------------
        # PATH RESOLVE
        # --------------------------------------------------

        target_directory = self.path_resolver.resolve(
            document.metadata
        )

        if not target_directory:
            self._log_step("PATH_FAIL", "None")
            self._move_to_manual_sort(document, "Kein Zielpfad")
            return

        self._log_step("PATH_OK", target_directory)

        # --------------------------------------------------
        # STORE
        # --------------------------------------------------

        try:
            final_path = self.archive_storage.store(
                document.source_path,
                target_directory,
                new_name
            )

        except Exception as e:
            self._log_step("STORE_FAIL", str(e))

            self.runtime_storage.store(
                document.source_path,
                self.error_target,
                original_name
            )

            return

        self._log_step("STORE_OK", final_path)

        self._log_step("DONE", doc_id)
        self.logger.log("-" * 70)