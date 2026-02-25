from pathlib import Path
import json


class Config:

    def __init__(self, config_path: Path):

        self.project_root = Path(__file__).resolve().parents[3]

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ----------------------------------------
        # Basis
        # ----------------------------------------
        self.user_path = Path(data["user_path"]).resolve()
        self.runtime_folder_name = data.get(
            "runtime_folder_name",
            ".sorterino_runtime"
        )

        # Sichtbare Junction-Namen
        self.visible_input_name = data["input_folder_name"]
        self.visible_manual_sort_name = data["manual_sort_folder_name"]

        # ----------------------------------------
        # Runtime Root
        # ----------------------------------------
        self.runtime_root = self.user_path / self.runtime_folder_name

        # ----------------------------------------
        # Runtime interne Struktur
        # ----------------------------------------
        self.incoming_folder_name = "incoming"
        self.manual_sort_folder_name = "manual_sort"
        self.processed_folder_name = "processed"
        self.error_folder_name = "error"
        self.logs_folder_name = "logs"
        self.temp_folder_name = "temp"
        self.attachments_folder_name = "attachments"

        # ----------------------------------------
        # Third-Party
        # ----------------------------------------
        self.poppler_path = self._resolve_project_path(
            data["poppler_path"]
        )
        self.tesseract_path = self._resolve_project_path(
            data["tesseract_path"]
        )

        # ----------------------------------------
        # Sonstiges
        # ----------------------------------------
        self.scan_interval_seconds = data["scan_interval_seconds"]
        self.identities = data.get("identities", [])

    def _resolve_project_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path.resolve()
        return (self.project_root / path).resolve()

    # ---------------- Runtime-Pfade ----------------

    @property
    def incoming_root(self) -> Path:
        return self.runtime_root / self.incoming_folder_name

    @property
    def manual_sort_root(self) -> Path:
        return self.runtime_root / self.manual_sort_folder_name

    @property
    def processed_root(self) -> Path:
        return self.runtime_root / self.processed_folder_name

    @property
    def error_root(self) -> Path:
        return self.runtime_root / self.error_folder_name

    @property
    def logs_root(self) -> Path:
        return self.runtime_root / self.logs_folder_name

    @property
    def temp_root(self) -> Path:
        return self.runtime_root / self.temp_folder_name

    @property
    def attachments_root(self) -> Path:
        return self.temp_root / self.attachments_folder_name