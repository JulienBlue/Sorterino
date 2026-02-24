from pathlib import Path
import json


class Config:

    def __init__(self, config_path: Path):

        self.project_root = Path(__file__).resolve().parents[3]

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # -------------------------------------------------
        # Basis
        # -------------------------------------------------
        self.user_path = Path(data["user_path"]).resolve()

        self.sorterino_folder_name = data["sorterino_folder_name"]
        self.runtime_folder_name = data["runtime_folder_name"]

        # -------------------------------------------------
        # Sichtbare Ordner (nur hier definiert!)
        # -------------------------------------------------
        self.input_folder_name = data["input_folder_name"]
        self.manual_sort_folder_name = data["manual_sort_folder_name"]
        self.backup_folder_name = data["backup_folder_name"]
        self.processing_folder_name = data["processing_folder_name"]

        # -------------------------------------------------
        # Abgeleitete Hauptpfade
        # -------------------------------------------------
        self.sorterino_root = self.user_path / self.sorterino_folder_name
        self.runtime_root = self.sorterino_root / self.runtime_folder_name

        # -------------------------------------------------
        # Runtime interne Struktur (nur hier definiert!)
        # -------------------------------------------------
        self.incoming_folder_name = "incoming"
        self.mail_drop_folder_name = "mail_drop"
        self.temp_folder_name = "temp"
        self.attachments_folder_name = "attachments"
        self.processed_folder_name = "processed"
        self.error_folder_name = "error"
        self.logs_folder_name = "logs"

        # -------------------------------------------------
        # Third-Party (relativ zum Projekt)
        # -------------------------------------------------
        self.poppler_path = self._resolve_project_path(
            data["poppler_path"]
        )

        self.tesseract_path = self._resolve_project_path(
            data["tesseract_path"]
        )

        # -------------------------------------------------
        # Sonstiges
        # -------------------------------------------------
        self.scan_interval_seconds = data["scan_interval_seconds"]
        self.identities = data.get("identities", [])

    # =====================================================
    # Projekt-relative Pfadauflösung
    # =====================================================

    def _resolve_project_path(self, path_str: str) -> Path:
        path = Path(path_str)

        if path.is_absolute():
            return path.resolve()

        return (self.project_root / path).resolve()

    # =====================================================
    # Abgeleitete Runtime-Pfade (nur hier gebaut!)
    # =====================================================

    @property
    def incoming_root(self) -> Path:
        return self.runtime_root / self.incoming_folder_name

    @property
    def manual_incoming_root(self) -> Path:
        return self.incoming_root / "manual"

    @property
    def mail_drop_root(self) -> Path:
        return self.incoming_root / self.mail_drop_folder_name

    @property
    def temp_root(self) -> Path:
        return self.runtime_root / self.temp_folder_name

    @property
    def attachments_root(self) -> Path:
        return self.temp_root / self.attachments_folder_name

    @property
    def processed_root(self) -> Path:
        return self.runtime_root / self.processed_folder_name

    @property
    def error_root(self) -> Path:
        return self.runtime_root / self.error_folder_name

    @property
    def logs_root(self) -> Path:
        return self.runtime_root / self.logs_folder_name