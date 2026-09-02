import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 1


class SorterinoDatabase:
    """Small, versioned SQLite database for technical application state."""

    def __init__(self, config):
        app_root = Path(
            getattr(
                config,
                "app_root",
                getattr(config, "state_root", getattr(config, "logs_root", ".")),
            )
        )
        self.path = Path(getattr(config, "database_path", app_root / "sorterino.db"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def read(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self):
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    sha256 TEXT NOT NULL UNIQUE,
                    byte_size INTEGER NOT NULL,
                    original_name TEXT,
                    status TEXT NOT NULL DEFAULT 'known',
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS document_locations (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    location_type TEXT NOT NULL,
                    path TEXT NOT NULL COLLATE NOCASE,
                    is_present INTEGER NOT NULL DEFAULT 1,
                    byte_size INTEGER,
                    mtime_ns INTEGER,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(document_id, location_type, path)
                );

                CREATE TABLE IF NOT EXISTS document_assignments (
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    profile_id TEXT,
                    person_id TEXT,
                    assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(document_id, profile_id, person_id)
                );

                CREATE TABLE IF NOT EXISTS document_metadata (
                    document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
                    category TEXT,
                    document_type TEXT,
                    document_date TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS processing_events (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
                    event_type TEXT NOT NULL,
                    status TEXT,
                    reason TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS registry_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS legacy_imports (
                    source_path TEXT PRIMARY KEY COLLATE NOCASE,
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_document_locations_path
                    ON document_locations(path);
                CREATE INDEX IF NOT EXISTS idx_processing_events_document
                    ON processing_events(document_id, created_at);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
                (SCHEMA_VERSION,),
            )

    def integrity_check(self):
        with self.read() as connection:
            return connection.execute("PRAGMA quick_check").fetchone()[0]

    @staticmethod
    def json_value(value):
        return json.dumps(value or {}, ensure_ascii=False, default=str)
