from pathlib import Path
import subprocess


def initialize_workspace(config):

    # ----------------------------------------
    # Runtime Root erstellen
    # ----------------------------------------
    config.runtime_root.mkdir(parents=True, exist_ok=True)

    # Runtime verstecken (Windows)
    try:
        subprocess.run(
            ["attrib", "+h", str(config.runtime_root)],
            shell=True
        )
    except Exception:
        pass

    # ----------------------------------------
    # Runtime-Unterordner erstellen
    # ----------------------------------------
    runtime_folders = [
        config.incoming_root,
        config.manual_sort_root,
        config.processed_root,
        config.error_root,
        config.logs_root,
        config.temp_root
    ]

    for folder in runtime_folders:
        folder.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------
    # Sichtbare Junctions im user_path
    # ----------------------------------------
    create_junction(
        config.user_path / config.visible_input_name,
        config.incoming_root
    )

    create_junction(
        config.user_path / config.visible_manual_sort_name,
        config.manual_sort_root
    )


def create_junction(link_path: Path, target_path: Path):

    if link_path.exists():
        return

    subprocess.run(
        [
            "cmd", "/c", "mklink", "/J",
            str(link_path),
            str(target_path)
        ],
        check=True
    )