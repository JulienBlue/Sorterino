import shutil
import subprocess
from pathlib import Path
import json
import sys
import os


# CONFIG / BASE PATH
def get_base_path():
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent


# CONFIG / TEMPLATE
def load_template_config():
    template_path = get_base_path() / "assets" / "templates" / "template.config.json"

    if not template_path.exists():
        raise FileNotFoundError("template.config.json fehlt")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


# CONFIG / RUNTIME
def ensure_runtime_config(config):
    runtime_config_path = config.runtime_root / "config.json"

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


# WORKSPACE / INIT
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
        processed = runtime / "processed"

        # 🔧 ORDNER ERSTELLEN
        for folder in [runtime, incoming, logs, backup, error, manual, processed]:
            folder.mkdir(parents=True, exist_ok=True)

        print("[INIT] Ordnerstruktur sichergestellt")

        # 🔧 HIDDEN FLAG
        try:
            subprocess.run(f'attrib +h "{runtime}"', shell=True)
        except Exception as e:
            print(f"[WARN] Hidden-Flag konnte nicht gesetzt werden: {e}")

        # 🔧 TEMPLATE COPY
        template_dir = get_base_path() / "assets" / "templates"

        def copy_if_missing(src_name, dst_name):
            try:
                src = template_dir / src_name
                dst = runtime / dst_name

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

        # 🔧 CONFIG
        ensure_runtime_config(config)

        # 🔧 JUNCTIONS
        def create_junction(link_path: Path, target: Path):

            try:
                # sauber prüfen
                if link_path.exists() and link_path.is_dir():
                    print(f"[INIT] Link existiert bereits: {link_path}")
                    return True

                # Versuch Symlink
                try:
                    os.symlink(target, link_path, target_is_directory=True)
                    print(f"[INIT] Symlink erstellt: {link_path}")
                    return True
                except Exception:
                    print("[INIT] Symlink nicht erlaubt → nutze Junction")

                # Fallback Junction
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
                    print(f"[INIT] Junction erstellt: {link_path}")
                    return True

                print(f"[WARN] mklink fehlgeschlagen: {result.stderr.strip()}")
                return False

            except Exception as e:
                print(f"[ERROR] Junction-Erstellung fehlgeschlagen: {e}")
                return False

        input_link = user_path / "Sorterino - Input"
        manual_link = user_path / "Sorterino - Manuelle Sortierung"

        if not create_junction(input_link, incoming):
            print("[WARN] Junction für Input konnte nicht erstellt werden")

        if not create_junction(manual_link, manual):
            print("[WARN] Junction für manuelle Sortierung konnte nicht erstellt werden")

        print("[INIT] Workspace vollständig initialisiert")

    except Exception as e:
        print(f"[FATAL] Workspace Initialisierung fehlgeschlagen: {e}")
        raise