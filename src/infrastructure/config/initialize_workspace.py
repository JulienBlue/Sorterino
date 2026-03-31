import shutil
import subprocess
from pathlib import Path

from src.utils.path_helper import get_base_path


def initialize_workspace(config):

    runtime = config.runtime_root
    incoming = config.incoming_root
    logs = config.logs_root
    backup = runtime / "backup"
    error = runtime / "error"
    manual = runtime / "manual_sort"
    processed = runtime / "processed"

    user_path = Path(config.user_path)

    print("INIT WORKSPACE:")
    print("User Path:", user_path)
    print("Runtime:", runtime)

    for folder in [runtime, incoming, logs, backup, error, manual, processed]:
        folder.mkdir(parents=True, exist_ok=True)

    def set_hidden(path: Path):
        try:
            subprocess.run(["attrib", "+h", str(path)], shell=True)
        except Exception as e:
            print("⚠️ Hidden Flag Fehler:", e)

    set_hidden(runtime)

    base_path = get_base_path()

    def copy_if_missing(filename):
        src = base_path / filename
        dst = runtime / filename

        if src.exists() and not dst.exists():
            shutil.copy(src, dst)

    copy_if_missing("rules.json")
    copy_if_missing("structure.json")
    copy_if_missing("supported_formats.json")

    def create_junction(link_path: Path, target: Path):
        try:
            if link_path.exists():
                if link_path.is_dir():
                    import shutil
                    shutil.rmtree(link_path)
                else:
                    link_path.unlink()

            command = f'mklink /J "{link_path}" "{target}"'

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )

            print("CMD:", command)
            print("RETURN:", result.returncode)
            print("STDERR:", result.stderr)

            if result.returncode != 0:
                return False

            return True

        except Exception as e:
            print("EXCEPTION:", e)
            return False
        
    input_link = user_path / "Sorterino - Input"
    manual_link = user_path / "Sorterino - Manuelle Sortierung"

    input_ok = create_junction(input_link, incoming)
    manual_ok = create_junction(manual_link, manual)