import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from src.database import SorterinoDatabase


@dataclass(frozen=True)
class DuplicateMatch:
    document_id: int
    sha256: str
    status: str
    path: Path | None
    file_present: bool


class DocumentRegistry:
    """Durable history of processed documents, independent of backup retention."""

    def __init__(self, config):
        self.database = SorterinoDatabase(config)

    @staticmethod
    def hash_file(path, chunk_size=1024 * 1024):
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def find_exact(self, source_path, digest=None):
        source = Path(source_path)
        digest = digest or self.hash_file(source)
        with self.database.read() as connection:
            document = connection.execute(
                "SELECT id, sha256, status FROM documents WHERE sha256 = ?",
                (digest,),
            ).fetchone()
            if not document:
                return digest, None
            locations = connection.execute(
                """
                SELECT path FROM document_locations
                WHERE document_id = ?
                ORDER BY CASE location_type WHEN 'archive' THEN 0 WHEN 'backup' THEN 1 ELSE 2 END,
                         last_verified_at DESC
                """,
                (document["id"],),
            ).fetchall()

        source_key = str(source.resolve()).casefold()
        fallback = None
        for row in locations:
            candidate = Path(row["path"])
            if str(candidate.resolve()).casefold() == source_key:
                continue
            fallback = fallback or candidate
            if candidate.is_file():
                return digest, DuplicateMatch(
                    document["id"], digest, document["status"], candidate, True
                )
        return digest, DuplicateMatch(
            document["id"], digest, document["status"], fallback, False
        )

    def register_document(
        self,
        path,
        *,
        digest=None,
        status="processed",
        location_type=None,
        original_name=None,
        profile_id=None,
        person_ids=None,
        metadata=None,
    ):
        path = Path(path)
        digest = digest or self.hash_file(path)
        size = path.stat().st_size
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO documents(sha256, byte_size, original_name, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sha256) DO UPDATE SET
                    byte_size = excluded.byte_size,
                    original_name = COALESCE(documents.original_name, excluded.original_name),
                    status = CASE
                        WHEN documents.status = 'processed' OR excluded.status = 'processed'
                        THEN 'processed'
                        ELSE excluded.status
                    END,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (digest, size, original_name or path.name, status),
            )
            document_id = connection.execute(
                "SELECT id FROM documents WHERE sha256 = ?", (digest,)
            ).fetchone()["id"]
            if location_type:
                connection.execute(
                    """
                    INSERT INTO document_locations(
                        document_id, location_type, path, is_present, byte_size, mtime_ns
                    ) VALUES (?, ?, ?, 1, ?, ?)
                    ON CONFLICT(document_id, location_type, path) DO UPDATE SET
                        is_present = 1,
                        byte_size = excluded.byte_size,
                        mtime_ns = excluded.mtime_ns,
                        last_verified_at = CURRENT_TIMESTAMP
                    """,
                    (
                        document_id, location_type, str(path.resolve()),
                        path.stat().st_size, path.stat().st_mtime_ns,
                    ),
                )
            if profile_id or person_ids:
                ids = list(person_ids or []) or [None]
                for person_id in ids:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO document_assignments(document_id, profile_id, person_id)
                        VALUES (?, ?, ?)
                        """,
                        (document_id, profile_id, person_id),
                    )
            if metadata:
                connection.execute(
                    """
                    INSERT INTO document_metadata(
                        document_id, category, document_type, document_date, metadata_json
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(document_id) DO UPDATE SET
                        category = excluded.category,
                        document_type = excluded.document_type,
                        document_date = excluded.document_date,
                        metadata_json = excluded.metadata_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        document_id,
                        metadata.get("category"),
                        metadata.get("document_type"),
                        metadata.get("date"),
                        json.dumps(metadata, ensure_ascii=False, default=str),
                    ),
                )
        return document_id

    def add_location(self, document_id, path, location_type):
        path = Path(path)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO document_locations(
                    document_id, location_type, path, is_present, byte_size, mtime_ns
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, location_type, path) DO UPDATE SET
                    is_present = excluded.is_present,
                    byte_size = excluded.byte_size,
                    mtime_ns = excluded.mtime_ns,
                    last_verified_at = CURRENT_TIMESTAMP
                """,
                (
                    document_id, location_type, str(path.resolve()), int(path.is_file()),
                    path.stat().st_size if path.is_file() else None,
                    path.stat().st_mtime_ns if path.is_file() else None,
                ),
            )

    def location_is_current(self, path):
        path = Path(path)
        try:
            stat = path.stat()
        except OSError:
            return False
        with self.database.read() as connection:
            row = connection.execute(
                """
                SELECT byte_size, mtime_ns FROM document_locations
                WHERE path = ? AND is_present = 1
                ORDER BY last_verified_at DESC LIMIT 1
                """,
                (str(path.resolve()),),
            ).fetchone()
        return bool(
            row
            and row["byte_size"] == stat.st_size
            and row["mtime_ns"] == stat.st_mtime_ns
        )

    def mark_location_missing(self, document_id, path):
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE document_locations
                SET is_present = 0, last_verified_at = CURRENT_TIMESTAMP
                WHERE document_id = ? AND path = ?
                """,
                (document_id, str(Path(path).resolve())),
            )

    def record_event(self, document_id, event_type, status=None, reason=None, details=None):
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO processing_events(document_id, event_type, status, reason, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    event_type,
                    status,
                    reason,
                    json.dumps(details or {}, ensure_ascii=False, default=str),
                ),
            )

    def get_state(self, key, default=None):
        with self.database.read() as connection:
            row = connection.execute(
                "SELECT value FROM registry_state WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_state(self, key, value):
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO registry_state(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, str(value)),
            )

    def statistics(self):
        with self.database.read() as connection:
            documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            locations = connection.execute(
                "SELECT COUNT(*) FROM document_locations"
            ).fetchone()[0]
            events = connection.execute("SELECT COUNT(*) FROM processing_events").fetchone()[0]
        return {"documents": documents, "locations": locations, "events": events}

    def clear_document_history(self):
        """Clear technical document history without touching files or user settings."""
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM processing_events")
            connection.execute("DELETE FROM documents")
            connection.execute(
                """
                INSERT INTO registry_state(key, value) VALUES ('backup_bootstrap_complete', '1')
                ON CONFLICT(key) DO UPDATE SET value = '1', updated_at = CURRENT_TIMESTAMP
                """
            )

    def scan_directory(self, root, location_type="archive"):
        from src.document_formats import SUPPORTED_EXTENSIONS

        root = Path(root)
        imported = 0
        failed = 0
        if not root.is_dir():
            return {"imported": 0, "failed": 0}
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                self.register_document(
                    path, status="processed", location_type=location_type
                )
                imported += 1
            except OSError:
                failed += 1
        return {"imported": imported, "failed": failed}

    def import_legacy_index(self, index_path):
        index_path = Path(index_path)
        source_key = str(index_path.resolve())
        with self.database.read() as connection:
            if connection.execute(
                "SELECT 1 FROM legacy_imports WHERE source_path = ?", (source_key,)
            ).fetchone():
                return 0
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return 0
        imported = 0
        for entry in (payload.get("files") or {}).values():
            digest = entry.get("sha256")
            path = entry.get("path")
            size = entry.get("size")
            if not digest or not path or size is None:
                continue
            candidate = Path(path)
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO documents(sha256, byte_size, original_name, status)
                    VALUES (?, ?, ?, 'processed')
                    ON CONFLICT(sha256) DO NOTHING
                    """,
                    (digest, int(size), candidate.name),
                )
                document_id = connection.execute(
                    "SELECT id FROM documents WHERE sha256 = ?", (digest,)
                ).fetchone()["id"]
                connection.execute(
                    """
                    INSERT INTO document_locations(
                        document_id, location_type, path, is_present, byte_size, mtime_ns
                    ) VALUES (?, 'backup', ?, ?, ?, ?)
                    ON CONFLICT(document_id, location_type, path) DO UPDATE SET
                        is_present = excluded.is_present,
                        byte_size = excluded.byte_size,
                        mtime_ns = excluded.mtime_ns,
                        last_verified_at = CURRENT_TIMESTAMP
                    """,
                    (
                        document_id, str(candidate.resolve()), int(candidate.is_file()),
                        candidate.stat().st_size if candidate.is_file() else int(size),
                        candidate.stat().st_mtime_ns if candidate.is_file() else None,
                    ),
                )
            imported += 1
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO legacy_imports(source_path) VALUES (?)",
                (source_key,),
            )
        return imported
