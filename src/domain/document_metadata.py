from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class DocumentMetadata:
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    category: Optional[str] = None
    document_type: Optional[str] = None

    invoice_number: Optional[str] = None

    # Kontextdaten wie Firma, Bank, Zeitraum etc.
    contexts: Dict[str, str] = field(default_factory=dict)