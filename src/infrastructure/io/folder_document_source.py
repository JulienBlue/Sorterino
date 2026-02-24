import os
from typing import List

from domain.document import Document
from interfaces.document_source import DocumentSource


class FolderDocumentSource(DocumentSource):

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.input_path = os.path.join(workspace_path, "Input")
        os.makedirs(self.input_path, exist_ok=True)

    def fetch_documents(self) -> List[Document]:
        documents = []

        for root, _, files in os.walk(self.input_path):

            # Hidden folders ignorieren
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

                documents.append(Document(source_path=full_path))

        return documents