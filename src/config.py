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

        # Runtime-Ordner (sichtbar, schöner Name)
        self.runtime_root = self.user_path / "Sorterino - Runtime"

        # Migration: alte Ordner -> neuer Name
        old_runtimes = [
            self.user_path / ".sorterino_runtime",
            self.user_path / "Sorterino-Runtime",
        ]
        for old_runtime in old_runtimes:
            if old_runtime.exists() and not self.runtime_root.exists():
                try:
                    shutil.move(str(old_runtime), str(self.runtime_root))
                except Exception as e:
                    print(f"[WARN] Runtime-Migration fehlgeschlagen: {e}")
        self.runtime_root.mkdir(parents=True, exist_ok=True)

        # Configs-Unterordner
        self.config_root = self.runtime_root / "configs"
        self.config_root.mkdir(parents=True, exist_ok=True)

        # Migration: alte Dateien im Runtime-Root -> configs
        def _move_if_exists(name: str):
            src = self.runtime_root / name
            dst = self.config_root / name
            if src.exists() and not dst.exists():
                try:
                    shutil.move(str(src), str(dst))
                except Exception as e:
                    print(f"[WARN] Konnte {name} nicht verschieben: {e}")

        _move_if_exists("config.json")
        _move_if_exists("rules.json")
        _move_if_exists("structure.json")

        self.config_path = self.config_root / "config.json"

        if not self.config_path.exists():
            self._create_default_runtime_config()

        self.raw = self._read_json(self.config_path)

        # PATHS
        self.logs_root = self.runtime_root / "logs"
        self.incoming_root = self.runtime_root / "incoming"
        self.rules_path = self.config_root / "rules.json"
        self.structure_path = self.config_root / "structure.json"

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

    
    # OCR INIT (FIXED 🔥)
    
    def _init_ocr(self):
        project_root = get_base_path()

        internal_base = project_root / "_internal"
        base = internal_base if internal_base.exists() else project_root

        ocr = self.raw.get("ocr", {})

        
        # TESSERACT
        
        custom_tess = ocr.get("tesseract_path")

        if custom_tess:
            path = Path(custom_tess)

            if not path.is_absolute():
                path = project_root / path

            self.tesseract_path = path.resolve()

        
        # POPPLER
        
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
