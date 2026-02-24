import os

from usecases.classify_document import classify_document
from usecases.rename_document import rename_document
from usecases.path_resolver import PathResolver


class DocumentPipeline:

    def __init__(
        self,
        sources,
        ocr_service,
        storage_service,
        logger,
        rules,
        supported_extensions,
        unsupported_target,
        structure
    ):
        self.sources = sources
        self.ocr_service = ocr_service
        self.storage_service = storage_service
        self.logger = logger
        self.rules = rules
        self.supported_extensions = supported_extensions
        self.unsupported_target = unsupported_target

        self.path_resolver = PathResolver(structure)

    # --------------------------------------------------
    # RUN
    # --------------------------------------------------

    def run(self):

        print("🔵 Pipeline gestartet")

        for source in self.sources:
            documents = source.fetch_documents()

            for document in documents:
                try:
                    print(f"\n➡️ Verarbeite: {document.source_path}")
                    self._process_document(document)

                except Exception as e:
                    print(f"❌ Fehler: {e}")
                    self.logger.log(
                        f"Error processing document {document.id}: {e}"
                    )

        print("🟢 Pipeline beendet")

    # --------------------------------------------------
    # PROCESS DOCUMENT
    # --------------------------------------------------

    def _process_document(self, document):

        ext = os.path.splitext(document.source_path)[1].lower()

        # ------------------------------------------
        # Unsupported formats
        # ------------------------------------------

        if ext not in self.supported_extensions:
            print(f"⚠️ Nicht unterstützter Dateityp: {ext}")

            new_name = os.path.basename(document.source_path)

            self.storage_service.store(
                document.source_path,
                self.unsupported_target,
                new_name
            )
            return

        # ------------------------------------------
        # OCR
        # ------------------------------------------

        print("   🟡 OCR starte...")
        text = self.ocr_service.extract_text(document.source_path)
        print("   ✅ OCR fertig")

        # 🔥 WICHTIG: Kein Crash bei leerem Text
        if not text or not text.strip():
            print("   ⚠️ Kein OCR-Text gefunden → Manuelle Sortierung")
            text = ""

        document.mark_analyzed(text)

        # ------------------------------------------
        # Classification
        # ------------------------------------------

        print("   🟡 Klassifikation starte...")
        classification = classify_document(document, self.rules)
        print(f"   ✅ Kategorie: {classification.category}")

        document.mark_classified(classification)

        # ------------------------------------------
        # Rename
        # ------------------------------------------

        print("   🟡 Neuer Dateiname...")
        new_name = rename_document(document)
        print(f"   ✅ Neuer Name: {new_name}")

        # ------------------------------------------
        # Resolve path
        # ------------------------------------------

        print("   🟡 Zielpfad bestimmen...")
        target_directory = self.path_resolver.resolve(
            document.metadata
        )
        print(f"   ✅ Zielordner: {target_directory}")

        # ------------------------------------------
        # Store
        # ------------------------------------------

        print("   🟡 Datei speichern...")
        final_path = self.storage_service.store(
            document.source_path,
            target_directory,
            new_name
        )
        print(f"   ✅ Gespeichert unter: {final_path}")

        document.mark_stored(final_path)