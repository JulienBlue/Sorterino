import json
from pathlib import Path

from src.utils.path_helper import get_base_path


class ConfigService:

    def __init__(self):
        # 🔹 Bootstrap Config (nur für user_path)
        self.base_config_path = Path.home() / ".sorterino_config.json"
        self._ensure_base_config()

    # --------------------------------------------------
    # BASIC IO
    # --------------------------------------------------

    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _read_json(self, path):
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # --------------------------------------------------
    # DEFAULT CONFIG (TEMPLATE)
    # --------------------------------------------------

    def _load_default_config(self):
        base_path = get_base_path()
        default_path = base_path / "config" / "default_config.json"

        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        print("⚠️ default_config.json nicht gefunden!")
        return {}

    # --------------------------------------------------
    # BASE CONFIG (BOOTSTRAP)
    # --------------------------------------------------

    def _ensure_base_config(self):
        if not self.base_config_path.exists():
            self._write_json(self.base_config_path, {})

    # --------------------------------------------------
    # RUNTIME CONFIG PATH (FIXED)
    # --------------------------------------------------

    @property
    def config_path(self):
        base = self._read_json(self.base_config_path)
        user_path = base.get("user_path")

        # 🔥 Wenn noch kein user_path → Base Config
        if not user_path:
            return self.base_config_path

        # 🔥 Runtime Config erzwingen
        runtime_path = Path(user_path) / ".sorterino_runtime"
        runtime_path.mkdir(parents=True, exist_ok=True)

        return runtime_path / "config.json"

    # --------------------------------------------------
    # ENSURE RUNTIME CONFIG EXISTS
    # --------------------------------------------------

    def _ensure_runtime_config(self):
        path = self.config_path

        # Wenn wir noch im Base-Mode sind → nichts tun
        if path == self.base_config_path:
            return

        if not path.exists():
            default_data = self._load_default_config()
            self._write_json(path, default_data)

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def get(self, key):
        self._ensure_runtime_config()

        data = self._read_json(self.config_path)
        return data.get(key)

    def set(self, key, value):

        # 🔥 WICHTIG: user_path zuerst in BASE speichern!
        if key == "user_path":
            base = self._read_json(self.base_config_path)
            base["user_path"] = value
            self._write_json(self.base_config_path, base)

        # 🔥 danach Runtime Config sicherstellen
        self._ensure_runtime_config()

        data = self._read_json(self.config_path)
        data[key] = value
        self._write_json(self.config_path, data)

    def get_all(self):
        self._ensure_runtime_config()
        return self._read_json(self.config_path)

    def reset(self):
        """Setzt Runtime Config auf Default zurück"""
        default_data = self._load_default_config()

        if self.config_path != self.base_config_path:
            self._write_json(self.config_path, default_data)
            print("♻️ Runtime Config zurückgesetzt")
        else:
            print("⚠️ Noch keine Runtime aktiv")