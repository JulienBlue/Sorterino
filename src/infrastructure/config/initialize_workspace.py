def initialize_workspace(config):

    # ----------------------------------------
    # 1. Sorterino Root erstellen
    # ----------------------------------------
    config.sorterino_root.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------
    # 2. Runtime Root erstellen
    # ----------------------------------------
    config.runtime_root.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------
    # 3. Runtime-Unterordner
    # ----------------------------------------
    runtime_folders = [
        config.incoming_root,
        config.manual_incoming_root,
        config.mail_drop_root,
        config.temp_root,
        config.attachments_root,
        config.processed_root,
        config.error_root,
        config.logs_root,
    ]

    for folder in runtime_folders:
        folder.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------
    # 4. Junctions im user_path
    # ----------------------------------------

    # Input → manual incoming
    create_junction(
        config.user_path / config.input_folder_name,
        config.manual_incoming_root
    )

    # Manuelle Sortierung → manual incoming
    create_junction(
        config.user_path / config.manual_sort_folder_name,
        config.manual_incoming_root
    )

    # Backup → processed root
    create_junction(
        config.user_path / config.backup_folder_name,
        config.processed_root
    )