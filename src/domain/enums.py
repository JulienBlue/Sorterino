from enum import Enum

class DocumentStatus(Enum):
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    CLASSIFIED = "CLASSIFIED"
    STORED = "STORED"
    ERROR = "ERROR"
