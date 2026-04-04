import json
from pathlib import Path
import shutil
import sys


class Config:

    # CONFIG / INIT
    def __init__(self, config_path: Path):

        self.config_path = config_path

        # CONFIG / LADEN
        if not self.config_path.exists():
            self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

                if not content:
                    raise ValueError("Empty config file")

                self.raw = json.loads(content)

        except Exception:
            self._create_default_config()

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.raw = json.load(f)

        # CONFIG / USER PATH
        user_path_value = self.raw.get("user_path")

        if not user_path_value:
            self.user_path = None
            return

        self.user_path = Path(user_path_value)

        # CONFIG / RUNTIME
        self.runtime_folder_name = ".sorterino_runtime"

        self.runtime_root = self.user_path / self.runtime_folder_name
        self.logs_root = self.runtime_root / "logs"
        self.incoming_root = self.runtime_root / "incoming"

        # CONFIG / OCR
        project_root = Path(__file__).resolve().parents[2]

        ocr_config = self.raw.get("ocr", {})

        custom_tesseract = ocr_config.get("tesseract_path")

        if custom_tesseract:
            self.tesseract_path = Path(custom_tesseract)

        else:
            system_tesseract = shutil.which("tesseract")

            if system_tesseract:
                self.tesseract_path = Path(system_tesseract)
            else:
                self.tesseract_path = (
                    project_root / "third_party" / "tesseract" / "tesseract.exe"
                ).resolve()

        custom_poppler = ocr_config.get("poppler_path")

        if custom_poppler:
            self.poppler_path = Path(custom_poppler)

        else:
            self.poppler_path = (
                project_root / "third_party" / "poppler" / "Library" / "bin"
            ).resolve()

        # CONFIG / COMPANY
        self.company_profile = self.raw.get("company_profile") or {}

        # CONFIG / PATHS
        self.rules_path = self.runtime_root / "rules.json"
        self.structure_path = self.runtime_root / "structure.json"

    # CONFIG / DEFAULT
    def _create_default_config(self):

        project_root = Path(__file__).resolve().parents[2]
        template_dir = project_root / "assets" / "templates"
        default_path = template_dir / "template.config.json"

        if not default_path.exists():
            raise FileNotFoundError("template.config.json fehlt fehlt")

        with open(default_path, "r", encoding="utf-8") as f:
            default = json.load(f)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)