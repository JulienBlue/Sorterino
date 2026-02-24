from enum import Enum

class DocumentStatus(Enum):
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    CLASSIFIED = "CLASSIFIED"
    RENAMED = "RENAMED"
    STORED = "STORED"
    ERROR = "ERROR"
