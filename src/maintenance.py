"""Narrow, auditable cleanup of rebuildable local application state."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.document_registry import DocumentRegistry


def _inside(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
        raise ValueError(f"Unsicheres Bereinigungsziel: {resolved}")
    return resolved


def cleanup_rebuildable_state(config) -> list[Path]:
    """Remove only state that Sorterino can recreate without losing user data.

    Profiles, people, presets, settings, OAuth client registration, credentials
    and documents deliberately remain untouched. Processing, duplicate, report
    and mail-import state start fresh on the next launch.
    """

    app_root = Path(config.app_root).resolve()
    targets = (
        Path(config.logs_root),
        app_root / "updates",
        Path(config.state_root),
    )
    validated_targets = [_inside(candidate, app_root) for candidate in targets]

    # Do not delete the database file. A newly-created registry deliberately
    # bootstraps itself from legacy indexes and existing backups, which would
    # immediately restore the duplicate history the user just cleared. Clear
    # the records transactionally and retain the bootstrap-complete marker.
    registry = DocumentRegistry(config)
    registry.clear_document_history()
    with registry.database.transaction() as connection:
        connection.execute("DELETE FROM report_deliveries")
        connection.execute("DELETE FROM report_runs")

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
