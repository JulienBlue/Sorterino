import os
import shutil


def backup_document(source_path: str, backup_folder: str) -> str:
    """
    Creates a backup copy of the file in the backup folder.
    Returns the backup path.
    """

    os.makedirs(backup_folder, exist_ok=True)

    original_filename = os.path.basename(source_path)
    name, ext = os.path.splitext(original_filename)

    backup_path = os.path.join(backup_folder, original_filename)

    # Falls Datei existiert → nummerieren
    if os.path.exists(backup_path):
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_backup_path = os.path.join(backup_folder, new_filename)

            if not os.path.exists(new_backup_path):
                backup_path = new_backup_path
                break

            counter += 1

    shutil.copy2(source_path, backup_path)

    return backup_path
