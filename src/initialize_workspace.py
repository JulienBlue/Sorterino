import shutil
import subprocess
from pathlib import Path
import json
import sys


# CONFIG / TEMPLATE
def load_template_config():
    project_root = Path(__file__).resolve().parent.parent
    template_dir = project_root / "assets" / "templates"
    template_path = template_dir / "template.config.json"

    if not template_path.exists():
        raise FileNotFoundError("template.config.json fehlt fehlt")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


# WORKSPACE / INIT
def initialize_workspace(config):

    runtime = config.runtime_root
    incoming = runtime / "incoming"
    logs = runtime / "logs"
    backup = runtime / "backup"
    error = runtime / "error"
    manual = runtime / "manual_sort"
    processed = runtime / "processed"

    user_path = Path(config.user_path)

    for folder in [runtime, incoming, logs, backup, error, manual, processed]:
        folder.mkdir(parents=True, exist_ok=True)

    # SYSTEM / HIDDEN
    def set_hidden(path: Path):
        try:
            subprocess.run(["attrib", "+h", str(path)], shell=True)
        except Exception:
            pass

    set_hidden(runtime)

    # TEMPLATE / COPY
    base_path = Path(__file__).resolve().parent.parent
    template_dir = base_path / "assets" / "templates"

    def copy_if_missing(src_name, dst_name):
        src = template_dir / src_name
        dst = runtime / dst_name

        if src.exists() and not dst.exists():
            shutil.copy(src, dst)

    copy_if_missing("template.rules.json", "rules.json")
    copy_if_missing("template.structure.json", "structure.json")

    # CONFIG / RUNTIME
    ensure_runtime_config(config)

    # LINKS / JUNCTIONS
    def create_junction(link_path: Path, target: Path):
        try:
            if link_path.exists():
                try:
                    if link_path.is_symlink():
                        link_path.unlink()
                    elif link_path.is_dir():
                        import os
                        os.rmdir(link_path)
                    else:
                        link_path.unlink()
                except Exception:
                    pass

            command = f'mklink /J "{link_path}" "{target}"'

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            return result.returncode == 0

        except Exception:
            return False

    input_link = user_path / "Sorterino - Input"
    manual_link = user_path / "Sorterino - Manuelle Sortierung"

    create_junction(input_link, incoming)
    create_junction(manual_link, manual)


# CONFIG / RUNTIME
def ensure_runtime_config(config):

    runtime_config_path = config.runtime_root / "config.json"

    default_config = load_template_config()

    if not runtime_config_path.exists():
        with open(runtime_config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        return

    try:
        with open(runtime_config_path, "r", encoding="utf-8") as f:
            current = json.load(f)
    except Exception:
        current = {}

    def deep_merge(base, override):
        result = dict(base)

        for key, value in override.items():
            if isinstance(value, dict) and key in result:
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    merged = deep_merge(default_config, current)

    with open(runtime_config_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)


# CONFIG / BASE PATH
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]