import json
from pathlib import Path

from src.utils.path_helper import get_user_base_dir

CONFIG_PATH = Path.home() / ".sorterino_runtime" / "config.json"

DEFAULT_CONFIG = {
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


class ConfigService:

    def __init__(self):
        self.config_path = CONFIG_PATH
        self.config = self.load()

    def load(self):
        if not self.config_path.exists():
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, config=None):
        if config:
            self.config = config

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        self.save()