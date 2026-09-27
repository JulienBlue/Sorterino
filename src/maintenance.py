"""Narrow, auditable cleanup of rebuildable local application state."""

from __future__ import annotations

import shutil
from pathlib import Path


def _inside(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
        raise ValueError(f"Unsicheres Bereinigungsziel: {resolved}")
    return resolved


def cleanup_rebuildable_state(config) -> list[Path]:
    """Remove only state that Sorterino can recreate without losing user data.

    Profiles, people, presets, settings, OAuth client registration, credentials,
    documents and the mail import cursor deliberately remain untouched. The
    processing database is reset, so its duplicate and report history starts
    fresh on the next launch.
    """

    app_root = Path(config.app_root).resolve()
    targets = (
        Path(config.logs_root),
        app_root / "updates",
        Path(config.state_root) / "manual-review",
        Path(config.database_path),
        Path(f"{config.database_path}-wal"),
        Path(f"{config.database_path}-shm"),
    )
    validated_targets = [_inside(candidate, app_root) for candidate in targets]
    removed: list[Path] = []
    for target in validated_targets:
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(target)
        elif target.exists():
            target.unlink()
            removed.append(target)

    # Atomic-write leftovers contain no authoritative settings and are safe to
    # discard. Limit the pattern to Sorterino's root; never recurse or glob a
    # user-selected document directory.
    for candidate in app_root.glob(".*.tmp"):
        target = _inside(candidate, app_root)
        if target.is_file():
            target.unlink()
            removed.append(target)
    return removed
