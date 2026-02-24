from abc import ABC, abstractmethod


class StorageService(ABC):

    @abstractmethod
    def store(
        self,
        source_path: str,
        target_directory: str,
        new_name: str
    ) -> str:
        """
        Stores the document and returns the final target path.
        """
        pass