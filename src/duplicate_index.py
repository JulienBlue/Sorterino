from pathlib import Path

from src.document_registry import DocumentRegistry


class ExactDuplicateIndex:
    """Compatibility facade backed by Sorterino's durable SQLite registry."""

    def __init__(self, config, backup_root, logger=None):
        self.backup_root = Path(backup_root)
        self.logger = logger
        self.registry = DocumentRegistry(config)
        state_root = Path(
            getattr(config, "state_root", getattr(config, "logs_root", "."))
        )
        self.registry.import_legacy_index(state_root / "duplicate-index.json")
        if self.registry.get_state("backup_bootstrap_complete") != "1":
            if self.refresh() == 0:
                self.registry.set_state("backup_bootstrap_complete", "1")

    @staticmethod
    def hash_file(path, chunk_size=1024 * 1024):
        return DocumentRegistry.hash_file(path, chunk_size)

    def refresh(self):
        """Add new or changed backups; historical records are never discarded."""
        if not self.backup_root.exists():
            return 0
        failed = 0
        for path in self.backup_root.rglob("*"):
            if not path.is_file() or self.registry.location_is_current(path):
                continue
            try:
                self.registry.register_document(
                    path,
                    status="processed",
                    location_type="backup",
                )
            except OSError as exc:
                failed += 1
                if self.logger:
                    self.logger.warning(
                        f"Duplikatregister konnte {path.name} nicht lesen: {exc}"
                    )
        return failed

    def find(self, source_path):
        return self.registry.find_exact(source_path)

    def register(self, path, digest=None, location_type="backup", **details):
        return self.registry.register_document(
            path,
            digest=digest,
            status=details.pop("status", "processed"),
            location_type=location_type,
            **details,
        )
