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

    def _cli_and_log(self, cli_msg, log_msg=None):
        self.logger.log(log_msg or cli_msg)

    # --------------------------------------------------

    def run(self):

        self._cli_and_log("\n🔵 SORTERINO PIPELINE START",
                          "Pipeline started")

        for source in self.sources:
            documents = source.fetch_documents()

            if not documents:
                self._cli_and_log("⚠️ Keine Dokumente gefunden.",
                                  "No documents found")
                continue

            for document in documents:
                try:
                    self._process_document(document)
                except Exception as e:
                    self._cli_and_log(f"❌ Fehler: {e}",
                                      f"Error processing document {document.id}: {e}")
                    self.logger.error(str(e))

        self._cli_and_log("\n🟢 PIPELINE BEENDET",
                          "Pipeline finished")

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
            self.logger.error(f"Manual sort failed: {e}")

            final_path = self.runtime_storage.store(
                document.source_path,
                self.error_target,
                original_name
            )

            self._cli_and_log(
                f"🚨 → In ERROR verschoben: {final_path}",
                f"Moved to ERROR: {final_path}"
            )

        self._cli_and_log(
            f"📂 → MANUELLE SORTIERUNG ({reason})",
            f"Manual sort triggered: {reason}"
        )

    # --------------------------------------------------

    def _process_document(self, document):

        self._cli_and_log(
            f"\n📄 Datei: {document.source_path}",
            f"Processing document: {document.source_path}"
        )

        ext = os.path.splitext(document.source_path)[1].lower()

        self._cli_and_log(
            f"🔎 Dateityp: {ext}",
            f"File extension: {ext}"
        )

        # Backup
        original_name = os.path.basename(document.source_path)

        processed_path = self.runtime_storage.copy(
            document.source_path,
            "processed",
            original_name
        )

        self.logger.log(f"Original backed up to: {processed_path}")

        # Unsupported
        if ext not in self.supported_extensions:

            self._cli_and_log(
                "⚠️ Nicht unterstütztes Format",
                "Unsupported file format"
            )

            self.runtime_storage.store(
                document.source_path,
                self.unsupported_target,
                original_name
            )

            return

        # OCR
        self._cli_and_log("🟡 OCR starte...",
                          "OCR started")

        text = self.ocr_service.extract_text(document.source_path)

        if not text.strip():
            self._cli_and_log("❌ Kein OCR-Text erkannt",
                              "OCR failed: No text extracted")
            self._move_to_manual_sort(document, "Kein OCR-Text")
            return

        self._cli_and_log("✅ OCR erfolgreich",
                          f"OCR success | Length: {len(text)}")

        document.mark_analyzed(text)

        # Klassifikation
        self._cli_and_log("🟡 Klassifikation starte...",
                        f"Text Preview: {text[:200]}")

        classification = classify_document(
            document,
            self.rules,
            self.company_profile,
            logger=self.logger
        )

        if not classification or not classification.category:
            self._cli_and_log("❌ Keine Kategorie erkannt",
                              "Classification failed")
            self._move_to_manual_sort(document, "Keine Kategorie")
            return

        self._cli_and_log(
            f"✅ Kategorie erkannt: {classification.category}",
            f"Category: {classification.category} | Confidence: {classification.confidence}"
        )

        document.mark_classified(classification)
        

        # --------------------------------------------------
        # MANUELLE KATEGORIE → Runtime manual_sort
        # --------------------------------------------------

        if classification.category.lower() in ["manuell", "unknown"]:
            self._move_to_manual_sort(
                document,
                f"Kategorie Manuell | Confidence: {classification.confidence}"
            )
            return
        
        # Rename
        self._cli_and_log("🟡 Neuer Dateiname generieren...",
                          "Generating new filename")

        new_name = rename_document(document)

        self.logger.log(f"New filename: {new_name}")

        # Zielpfad
        target_directory = self.path_resolver.resolve(
            document.metadata
        )

        if not target_directory:
            self._cli_and_log("❌ Kein Zielordner bestimmbar",
                              "Target directory not resolvable")
            self._move_to_manual_sort(document, "Kein Zielpfad")
            return

        self.logger.log(f"Target directory: {target_directory}")

        # Archivieren
        try:
            final_path = self.archive_storage.store(
                document.source_path,
                target_directory,
                new_name
            )

        except Exception as e:
            self._cli_and_log(f"❌ Archivierungsfehler: {e}",
                              f"Archive failed: {e}")

            self.runtime_storage.store(
                document.source_path,
                self.error_target,
                original_name
            )

            self.logger.error(f"Archive failed: {e}")
            return

        self._cli_and_log(
            f"✅ Gespeichert unter: {final_path}",
            f"Archived successfully to: {final_path}"
        )
        self.logger.log("-" * 70)