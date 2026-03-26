import json
from pathlib import Path


class Config:

    def __init__(self, config_path: Path):

        self.config_path = config_path

        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.raw = json.load(f)

        # 🔥 FIX: user_path robust laden
        user_path_value = self.raw.get("user_path")

        if not user_path_value:
            user_path_value = str(Path.home())

        self.user_path = Path(user_path_value)

        self.runtime_folder_name = ".sorterino_runtime"

        self.runtime_root = self.user_path / self.runtime_folder_name
        self.logs_root = self.runtime_root / "logs"
        self.incoming_root = self.runtime_root / "incoming"

        self.poppler_path = Path(self.raw.get("poppler_path", ""))
        self.tesseract_path = Path(self.raw.get("tesseract_path", ""))

        self.company_profile = self.raw.get("company_profile") or {
            "name": "",
            "keywords": []
        }

        self.rules_path = self.runtime_root / "rules.json"
        self.structure_path = self.runtime_root / "structure.json"
        self.formats_path = self.runtime_root / "supported_formats.json"

    def _create_default_config(self):

        default = {
            "user_path": str(Path.home()),
            "auto_mode": False,
            "autostart": False,
            "company_profile": {
                "name": "",
                "keywords": []
            },
            "poppler_path": "",
            "tesseract_path": ""
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)