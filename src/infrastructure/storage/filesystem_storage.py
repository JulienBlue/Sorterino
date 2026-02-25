from pathlib import Path
import shutil

from interfaces.storage_service import StorageService


class FilesystemStorage(StorageService):

    def __init__(self, base_path: Path):
        # base_path muss config.user_path sein
        self.base_path = Path(base_path)

    def store(
        self,
        source_path: str,
        target_directory: str,
        new_name: str
    ) -> str:
        """
        Speichert die Datei im Zielverzeichnis unter neuem Namen
        und gibt den finalen Pfad zurück.
        """

        source = Path(source_path)

        # Zielverzeichnis relativ zum base_path
        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name

        shutil.move(str(source), str(target_path))

        return str(target_path)