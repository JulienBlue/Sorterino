from abc import ABC, abstractmethod
from typing import List
from domain.document import Document


class DocumentSource(ABC):

    @abstractmethod
    def fetch_documents(self) -> List[Document]:
        """Returns a list of documents to process."""
        pass