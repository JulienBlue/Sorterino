from abc import ABC, abstractmethod


class OCRService(ABC):

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """
        Extracts text from a file and returns it as string.
        """
        pass