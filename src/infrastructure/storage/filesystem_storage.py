import shutil
from pathlib import Path


class FilesystemStorage:

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    # --------------------------------------------------
    # MOVE (mit Duplikatschutz)
    # --------------------------------------------------

    def store(self, source_path: str, target_directory: str, new_name: str) -> str:
        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name

        # 🔥 Duplikatschutz
        target_path = self._get_unique_path(target_path)

        shutil.move(str(source), str(target_path))

        return str(target_path)

    # --------------------------------------------------
    # COPY (mit Duplikatschutz)
    # --------------------------------------------------

    def copy(self, source_path: str, target_directory: str, new_name: str) -> str:
        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name

        target_path = self._get_unique_path(target_path)

        shutil.copy2(str(source), str(target_path))

        return str(target_path)

    # --------------------------------------------------
    # UNIQUE NAME GENERATOR
    # --------------------------------------------------

    def _get_unique_path(self, target_path: Path) -> Path:

        if not target_path.exists():
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        counter = 1

        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name

            if not new_path.exists():
                return new_path

            counter += 1