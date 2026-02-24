import os
import shutil
import time

from interfaces.storage_service import StorageService
from infrastructure.backup.backup_document import backup_document


class FilesystemStorage(StorageService):

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.archive_root = os.path.join(workspace_path, "Bürokratie")

        os.makedirs(self.archive_root, exist_ok=True)

    def store(
        self,
        source_path: str,
        target_directory: str,
        new_name: str
    ) -> str:

        # -----------------------------
        # Backup
        # -----------------------------
        backup_folder = os.path.join(self.workspace_path, "Backup")
        backup_document(source_path, backup_folder)

        # -----------------------------
        # Zielordner unter Bürokratie
        # -----------------------------
        target_folder_path = os.path.join(
            self.archive_root,
            target_directory
        )

        os.makedirs(target_folder_path, exist_ok=True)

        target_path = os.path.join(
            target_folder_path,
            new_name
        )

        shutil.move(source_path, target_path)

        # Kleine Pause für Windows/OneDrive
        time.sleep(0.1)

        # -----------------------------
        # Leere Input-Ordner bereinigen
        # -----------------------------
        self._cleanup_empty_dirs(os.path.dirname(source_path))

        return target_path

    def _cleanup_empty_dirs(self, path: str):
        input_root = os.path.join(self.workspace_path, "Input")

        while path.startswith(input_root):
            try:
                if os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)
                    path = os.path.dirname(path)
                else:
                    break
            except PermissionError:
                # Windows / OneDrive blockiert → einfach abbrechen
                break
