import json
from pathlib import Path
import shutil

from src.initialize_workspace import get_base_path


class Config:

    # CONFIG / INIT
    def __init__(self):
        self.raw = {}

        self.base_config_path = Path.home() / ".sorterino_config.json"

        self._ensure_base_config()

        base = self._read_json(self.base_config_path)
        self.user_path = base.get("user_path")

        if not self.user_path:
            self._set_empty_defaults()
            return

        self.user_path = Path(self.user_path)

        self.runtime_root = self.user_path / ".sorterino_runtime"
        self.runtime_root.mkdir(parents=True, exist_ok=True)

        self.config_path = self.runtime_root / "config.json"

        if not self.config_path.exists():
            self._create_default_runtime_config()

        self.raw = self._read_json(self.config_path)

        # PATHS
        self.logs_root = self.runtime_root / "logs"
        self.incoming_root = self.runtime_root / "incoming"
        self.rules_path = self.runtime_root / "rules.json"
        self.structure_path = self.runtime_root / "structure.json"

        # OCR
        self._init_ocr()

    # CONFIG / GET
    def get(self, key, default=None):

        if key == "user_path":
            return str(self.user_path) if self.user_path else None

        return self.raw.get(key, default)

    # CONFIG / SET
    def set(self, key, value):
        if key == "user_path":
            base = self._read_json(self.base_config_path)
            base["user_path"] = str(value)
            self._write_json(self.base_config_path, base)

            self.__init__()
            return

        self.raw[key] = value
        self._write_json(self.config_path, self.raw)

    # =========================
    # OCR INIT (FIXED 🔥)
    # =========================
    def _init_ocr(self):
        project_root = get_base_path()

        internal_base = project_root / "_internal"
        base = internal_base if internal_base.exists() else project_root

        ocr = self.raw.get("ocr", {})

        # =========================
        # TESSERACT
        # =========================
        custom_tess = ocr.get("tesseract_path")

        if custom_tess:
            self.tesseract_path = (project_root / custom_tess).resolve()
        else:
            system = shutil.which("tesseract")

            if system:
                self.tesseract_path = Path(system)
            else:
                self.tesseract_path = (
                    base / "third_party" / "tesseract" / "tesseract.exe"
                ).resolve()

        # =========================
        # POPPLER
        # =========================
        custom_poppler = ocr.get("poppler_path")

        if custom_poppler:
            self.poppler_path = (project_root / custom_poppler).resolve()
        else:
            self.poppler_path = (
                base / "third_party" / "poppler" / "Library" / "bin"
            ).resolve()

    # CONFIG / DEFAULT RUNTIME
    def _create_default_runtime_config(self):
        template = get_base_path() / "assets" / "templates" / "template.config.json"

        if not template.exists():
            raise FileNotFoundError("template.config.json fehlt")

        data = self._read_json(template)
        self._write_json(self.config_path, data)

    # CONFIG / BASE
    def _ensure_base_config(self):
        if not self.base_config_path.exists():
            template = get_base_path() / "assets" / "templates" / "template.config.json"
            data = self._read_json(template)
            self._write_json(self.base_config_path, data)

    # IO
    def _read_json(self, path):
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # EMPTY DEFAULTS
    def _set_empty_defaults(self):
        self.user_path = None
        self.runtime_root = None
        self.logs_root = None
        self.incoming_root = None
        self.rules_path = None
        self.structure_path = None