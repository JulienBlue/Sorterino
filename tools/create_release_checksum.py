"""Create the checksum asset required by Sorterino's updater."""

from hashlib import sha256
from pathlib import Path
import sys


def create_checksum(installer: Path) -> Path:
    installer = Path(installer).resolve()
    if not installer.is_file() or installer.suffix.casefold() != ".exe":
        raise ValueError(f"Installer nicht gefunden: {installer}")
    digest = sha256()
    with open(installer, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = installer.with_name(f"{installer.name}.sha256")
    checksum.write_text(f"{digest.hexdigest()}  {installer.name}\n", encoding="ascii")
    return checksum


def main(argv=None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if len(arguments) != 1:
        print("Verwendung: python tools/create_release_checksum.py <Installer.exe>")
        return 2
    try:
        checksum = create_checksum(Path(arguments[0]))
    except (OSError, ValueError) as exc:
        print(f"Fehler: {exc}")
        return 1
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

