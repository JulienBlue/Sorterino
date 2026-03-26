import shutil
from pathlib import Path

from src.utils.path_helper import get_base_path


def initialize_workspace(config):

    runtime = config.runtime_root
    incoming = config.incoming_root
    logs = config.logs_root

    runtime.mkdir(parents=True, exist_ok=True)
    incoming.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    base_path = get_base_path()

    def copy_if_missing(filename):
        src = base_path / filename
        dst = runtime / filename

        if src.exists() and not dst.exists():
            shutil.copy(src, dst)

    # 🔥 Default configs reinziehen
    copy_if_missing("rules.json")
    copy_if_missing("structure.json")
    copy_if_missing("supported_formats.json")

    return {
        "runtime_root": runtime,
        "incoming_root": incoming
    }