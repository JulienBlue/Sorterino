import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Liefert den Pfad zur EXE bzw. zum Projekt (für read-only Ressourcen)
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_user_base_dir() -> Path:
    """
    Liefert den persistenten User-Ordner
    """
    return Path.home()