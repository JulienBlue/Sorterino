import shutil
from pathlib import Path

from src.document_formats import SUPPORTED_EXTENSIONS, is_ignored_source_name


def import_documents(paths, incoming_folder):
    target_root = Path(incoming_folder)
    target_root.mkdir(parents=True, exist_ok=True)
    imported = []
    skipped = []

    for value in paths:
        source = Path(value)
        if (
            not source.is_file()
            or is_ignored_source_name(source.name)
            or source.suffix.casefold() not in SUPPORTED_EXTENSIONS
        ):
            skipped.append(source)
            continue
        target = target_root / source.name
        counter = 1
        while target.exists():
            target = target_root / f"{source.stem} ({counter}){source.suffix}"
            counter += 1
        shutil.copy2(source, target)
        imported.append(target)

    return imported, skipped
