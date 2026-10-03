"""Runtime facts that differ between classic and Microsoft Store installs."""

from __future__ import annotations

import ctypes
import os


APPMODEL_ERROR_NO_PACKAGE = 15700
ERROR_INSUFFICIENT_BUFFER = 122
STORE_PACKAGE_NAME = "JulienBlueHirte.Sorterino"


def package_full_name() -> str | None:
    """Return the package identity when running as MSIX, otherwise ``None``."""
    if os.name != "nt":
        return None
    try:
        get_name = ctypes.windll.kernel32.GetCurrentPackageFullName
        length = ctypes.c_uint32(0)
        result = get_name(ctypes.byref(length), None)
        if result == APPMODEL_ERROR_NO_PACKAGE:
            return None
        if result != ERROR_INSUFFICIENT_BUFFER or length.value <= 1:
            return None
        buffer = ctypes.create_unicode_buffer(length.value)
        result = get_name(ctypes.byref(length), buffer)
        return buffer.value if result == 0 and buffer.value else None
    except (AttributeError, OSError, ValueError):
        return None


def is_store_install() -> bool:
    """Whether this process has Sorterino's Microsoft Store identity."""
    full_name = package_full_name()
    return bool(full_name and full_name.startswith(f"{STORE_PACKAGE_NAME}_"))
