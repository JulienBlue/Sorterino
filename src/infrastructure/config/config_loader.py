import json
from pathlib import Path


class Config:

    def __init__(self, config_path: Path):

        self.config_path = config_path

        # --------------------------------------------------
        # CONFIG LADEN / ERSTELLEN
        # --------------------------------------------------

        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.raw = json.load(f)

        # --------------------------------------------------
        # USER PATH (PFLICHT)
        # --------------------------------------------------

        user_path_value = self.raw.get("user_path")

        if not user_path_value:
            raise ValueError("Kein user_path gesetzt! Bitte Speicherort konfigurieren.")

        self.user_path = Path(user_path_value)

        # --------------------------------------------------
        # RUNTIME PATHS
        # --------------------------------------------------

        self.runtime_folder_name = ".sorterino_runtime"

        self.runtime_root = self.user_path / self.runtime_folder_name
        self.logs_root = self.runtime_root / "logs"
        self.incoming_root = self.runtime_root / "incoming"

        # --------------------------------------------------
        # 🔥 THIRD PARTY (HARDCODED)
        # --------------------------------------------------

        project_root = Path(__file__).resolve().parents[3]

        self.tesseract_path = (
            project_root / "third_party" / "tesseract" / "tesseract.exe"
        ).resolve()

        self.poppler_path = (
            project_root / "third_party" / "poppler" / "Library" / "bin"
        ).resolve()

        # --------------------------------------------------
        # COMPANY PROFILE
        # --------------------------------------------------

        self.company_profile = self.raw.get("company_profile") or {
            "name": "",
            "keywords": []
        }

        # --------------------------------------------------
        # CONFIG FILE PATHS (RUNTIME)
        # --------------------------------------------------

        self.rules_path = self.runtime_root / "rules.json"
        self.structure_path = self.runtime_root / "structure.json"
        self.formats_path = self.runtime_root / "supported_formats.json"

    # --------------------------------------------------
    # DEFAULT CONFIG
    # --------------------------------------------------

    def _create_default_config(self):

        default = {
            "user_path": str(Path.home()),
            "auto_mode": False,
            "autostart": False,
            "company_profile": {
                "name": "",
                "keywords": []
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)