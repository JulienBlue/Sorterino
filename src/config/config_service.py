import json
from pathlib import Path


class ConfigService:

    # CONFIG / INIT
    def __init__(self):
        self.base_config_path = Path.home() / ".sorterino_config.json"
        self._ensure_base_config()

    # CONFIG / DEFAULT
    def _load_root_default(self):
        project_root = Path(__file__).resolve().parents[2]
        template_dir = project_root / "assets" / "templates"
        default_path = template_dir / "template.config.json"

        if not default_path.exists():
            raise FileNotFoundError("template.config.json fehlt fehlt")

        return self._read_json(default_path)

    # IO / WRITE
    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # IO / READ
    def _read_json(self, path):
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # CONFIG / BASE
    def _ensure_base_config(self):
        if not self.base_config_path.exists():
            default = self._load_root_default()
            self._write_json(self.base_config_path, default)

    # CONFIG / PATH
    @property
    def config_path(self):
        base = self._read_json(self.base_config_path)
        user_path = base.get("user_path")

        if not user_path:
            return self.base_config_path

        runtime_path = Path(user_path) / ".sorterino_runtime"
        runtime_path.mkdir(parents=True, exist_ok=True)

        return runtime_path / "config.json"

    # CONFIG / GET
    def get(self, key):
        data = self._read_json(self.config_path)
        return data.get(key)

    # CONFIG / SET
    def set(self, key, value):
        if key == "user_path":
            base = self._read_json(self.base_config_path)
            base["user_path"] = value
            self._write_json(self.base_config_path, base)

        data = self._read_json(self.config_path)
        data[key] = value

        self._write_json(self.config_path, data)