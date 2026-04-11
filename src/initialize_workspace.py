import shutil
import subprocess
from pathlib import Path
import json
import sys
import os

def get_base_path():
    if getattr(sys, "frozen", False):
        exe_root = Path(sys.executable).parent
        internal = exe_root / "_internal"
        return internal if internal.exists() else exe_root
    else:
        return Path(__file__).resolve().parent.parent

def load_template_config():
    template_path = get_base_path() / "assets" / "templates" / "template.config.json"

    if not template_path.exists():
        raise FileNotFoundError("template.config.json fehlt")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def ensure_runtime_config(config):
    runtime_config_path = config.config_path

    if runtime_config_path.exists():
        print("[INIT] Runtime config existiert bereits")
        return

    try:
        default_config = load_template_config()

        with open(runtime_config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

        print("[INIT] Runtime config erstellt")

    except Exception as e:
        print(f"[WARN] Runtime config konnte nicht erstellt werden: {e}")

def initialize_workspace(config):
    print("[INIT] Starte Workspace Initialisierung")

    try:
        runtime = config.runtime_root
        user_path = Path(config.user_path)

        incoming = runtime / "incoming"
        logs = runtime / "logs"
        backup = runtime / "backup"
        error = runtime / "error"
        manual = runtime / "manual_sort"

        # 🔧 ORDNER ERSTELLEN
        for folder in [runtime, incoming, logs, backup, error, manual]:
            folder.mkdir(parents=True, exist_ok=True)

        print("[INIT] Ordnerstruktur sichergestellt")

        # Runtime-Ordner bleibt sichtbar (kein Hidden-Flag)

        template_dir = get_base_path() / "assets" / "templates"
        config_dir = config.config_root

        def copy_if_missing(src_name, dst_name):
            try:
                src = template_dir / src_name
                dst = config_dir / dst_name

                if not src.exists():
                    print(f"[WARN] Template fehlt: {src_name}")
                    return

                if not dst.exists():
                    shutil.copy(src, dst)
                    print(f"[INIT] Template kopiert: {dst_name}")
                else:
                    print(f"[INIT] Template existiert bereits: {dst_name}")

            except Exception as e:
                print(f"[WARN] Fehler beim Kopieren von {src_name}: {e}")

        copy_if_missing("template.rules.json", "rules.json")
        copy_if_missing("template.structure.json", "structure.json")
        ensure_runtime_config(config)

        def create_junction(link_path: Path, target: Path):
            try:
                if link_path.exists() and link_path.is_dir():
                    print(f"[INIT] Link existiert bereits: {link_path}")
                    return True

                try:
                    os.symlink(target, link_path, target_is_directory=True)
                    print(f"[INIT] Symlink erstellt: {link_path}")
                    return True
                except Exception:
                    print("[INIT] Symlink nicht erlaubt → nutze Junction")

                command = f'cmd /c mklink /J "{link_path}" "{target}"'

                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
                )

                if result.returncode == 0:
                    print(f"[INIT] Verknüpfung erstellt: {link_path}")
                    return True

                print(f"[WARN] mklink fehlgeschlagen: {result.stderr.strip()}")
                return False

            except Exception as e:
                print(f"[ERROR] Verknüpfung-Erstellung fehlgeschlagen: {e}")
                return False

        input_link = user_path / "Sorterino - Input"
        manual_link = user_path / "Sorterino - Manuelle Sortierung"

        if not create_junction(input_link, incoming):
            print("[WARN] Verknüpfung für Input konnte nicht erstellt werden")

        if not create_junction(manual_link, manual):
            print("[WARN] Verknüpfung für manuelle Sortierung konnte nicht erstellt werden")

        print("[INIT] Workspace vollständig initialisiert")

    except Exception as e:
        print(f"[FATAL] Workspace Initialisierung fehlgeschlagen: {e}")
        raise
