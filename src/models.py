from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

class DocumentStatus:
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    CLASSIFIED = "CLASSIFIED"
    STORED = "STORED"
    ERROR = "ERROR"


@dataclass
class Classification:
    category: str
    confidence: float
    document_type: Optional[str] = None


@dataclass
class DocumentMetadata:
    category: Optional[str]
    document_type: Optional[str]
    invoice_date: Optional[str] = None


@dataclass
class Document:
    source_path: str

    extracted_text: Optional[str] = None
    classification: Optional[Classification] = None
    metadata: Optional[DocumentMetadata] = None
    extracted_data: dict = field(default_factory=dict)

    target_path: Optional[str] = None
    status: str = DocumentStatus.NEW

    @property
    def filename(self) -> str:
        return Path(self.source_path).name
    
    def mark_analyzed(self, text: str):
        self.extracted_text = text
        self.status = DocumentStatus.ANALYZED

    def mark_classified(self, classification: Classification):
        self.classification = classification
        self.status = DocumentStatus.CLASSIFIED

    def mark_stored(self, path: str):
        self.target_path = path
        self.status = DocumentStatus.STORED
