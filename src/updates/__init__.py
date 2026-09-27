"""Safe update checks and downloads for official Sorterino releases."""

from src.updates.service import (
    UpdateCheckResult,
    UpdateError,
    UpdateRelease,
    UpdateService,
    launch_installer_after_exit,
)

__all__ = [
    "UpdateCheckResult",
    "UpdateError",
    "UpdateRelease",
    "UpdateService",
    "launch_installer_after_exit",
]

