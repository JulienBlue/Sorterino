from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from .enums import DocumentStatus
from .classification import Classification
from .document_metadata import DocumentMetadata


@dataclass
class Document:
    source_path: str
    id: str = field(default_factory=lambda: str(uuid4()))
    extracted_text: Optional[str] = None
    classification: Optional[Classification] = None
    metadata: Optional[DocumentMetadata] = None
    target_path: Optional[str] = None
    status: DocumentStatus = DocumentStatus.NEW

    def mark_analyzed(self, text: str) -> None:
        if self.status != DocumentStatus.NEW:
            raise ValueError("Document can only be analyzed from NEW state.")

        if not text:
            raise ValueError("Extracted text cannot be empty.")

        self.extracted_text = text
        self.status = DocumentStatus.ANALYZED

    def mark_classified(self, classification: Classification) -> None:
        if self.status != DocumentStatus.ANALYZED:
            raise ValueError("Document must be analyzed before classification.")

        self.classification = classification
        self.status = DocumentStatus.CLASSIFIED

    def set_metadata(self, metadata: DocumentMetadata) -> None:
        self.metadata = metadata

    def mark_stored(self, target_path: str) -> None:
        if self.status != DocumentStatus.CLASSIFIED:
            raise ValueError("Document must be classified before storing.")

        if not target_path:
            raise ValueError("Target path cannot be empty.")

        self.target_path = target_path
        self.status = DocumentStatus.STORED
