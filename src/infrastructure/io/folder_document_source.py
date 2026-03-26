import os
from typing import List
from pathlib import Path

from src.domain.document import Document
from src.interfaces.document_source import DocumentSource


class FolderDocumentSource(DocumentSource):

    def __init__(self, root_path: Path):
        # Erwartet z.B. config.incoming_root
        self.root_path = Path(root_path)

        # Falls Ordner noch nicht existiert (Safety)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def fetch_documents(self) -> List[Document]:

        documents: List[Document] = []

        for root, _, files in os.walk(self.root_path):

            # Hidden folders ignorieren (.sorterino_runtime intern etc.)
            if os.path.basename(root).startswith("."):
                continue

            for file_name in files:

                # Hidden files ignorieren (.DS_Store etc.)
                if file_name.startswith("."):
                    continue

                full_path = os.path.join(root, file_name)

                # Nur echte Dateien
                if not os.path.isfile(full_path):
                    continue

                # Nur Dateien mit Extension
                _, ext = os.path.splitext(file_name)
                if not ext:
                    continue

                documents.append(
                    Document(source_path=full_path)
                )

        return documents