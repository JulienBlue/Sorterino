import json
import os
import subprocess
import sys
from pathlib import Path


def hidden_subprocess_kwargs():
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}


def get_base_path():
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).parent
        internal = executable_root / "_internal"
        return internal if internal.exists() else executable_root
    return Path(__file__).resolve().parent.parent


def load_template_config():
    path = get_base_path() / "assets" / "templates" / "template.config.json"
    if not path.exists():
        raise FileNotFoundError("template.config.json fehlt")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_runtime_config(config):
    return config.settings_path


def initialize_workspace(config):
    """Ensure application state directories; document archives remain separate."""
    for folder in (
        config.app_root, config.runtime_root, config.incoming_root, config.logs_root,
        config.backup_root, config.manual_root, config.error_root, config.state_root,
        config.profiles_root, config.persons_root, config.presets_root,
    ):
        Path(folder).mkdir(parents=True, exist_ok=True)
