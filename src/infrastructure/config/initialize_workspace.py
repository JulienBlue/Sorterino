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

    # ----------------------------------------
    # MailDrop BAS dynamisch generieren
    # ----------------------------------------
    generate_maildrop_bas(config)

    # ----------------------------------------
    # Rückgabe für GUI (MailDrop Info)
    # ----------------------------------------
    return {
        "runtime_root": config.runtime_root,
        "incoming_root": config.incoming_root,
        "maildrop_path": config.incoming_root
    }


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


def generate_maildrop_bas(config):

    template_path = (
        config.project_root
        / "src"
        / "infrastructure"
        / "maildrop"
        / "maildrop_template.bas"
    )

    output_dir = config.project_root / "docs" / "maildrop"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "sorterino_maildrop.bas"

    # Falls kein Template existiert → nichts tun
    if not template_path.exists():
        return

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Incoming-Pfad korrekt für VBA escapen
    incoming_path = str(config.incoming_root)
    escaped_path = incoming_path.replace("\\", "\\\\") + "\\\\"

    content = content.replace(
        "{{INCOMING_PATH}}",
        escaped_path
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)