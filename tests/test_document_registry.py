import json
import tempfile
import unittest
from pathlib import Path

from src.document_registry import DocumentRegistry
from tests.test_profile_service import FakeConfig


class DocumentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = FakeConfig(self.root)
        self.config.state_root = self.root / "state"

    def tearDown(self):
        self.temp.cleanup()

    def test_hash_survives_deleted_backup(self):
        registry = DocumentRegistry(self.config)
        backup = self.root / "backup.pdf"
        backup.write_bytes(b"persistent identity")
        digest = registry.hash_file(backup)
        registry.register_document(
            backup, digest=digest, location_type="backup", status="processed"
        )
        backup.unlink()
        candidate = self.root / "candidate.pdf"
        candidate.write_bytes(b"persistent identity")

        _digest, match = DocumentRegistry(self.config).find_exact(candidate)

        self.assertIsNotNone(match)
        self.assertFalse(match.file_present)
        self.assertEqual(match.status, "processed")

    def test_registers_backup_archive_assignment_and_metadata(self):
        registry = DocumentRegistry(self.config)
        backup = self.root / "backup.pdf"
        archive = self.root / "archive.pdf"
        backup.write_bytes(b"document")
        archive.write_bytes(b"document")
        document_id = registry.register_document(
            backup,
            location_type="backup",
            profile_id="family_1",
            person_ids=["person_1"],
            metadata={
                "category": "Versicherungen",
                "document_type": "Policen",
                "date": "2026-08-12",
            },
        )
        registry.add_location(document_id, archive, "archive")

        self.assertEqual(registry.statistics()["documents"], 1)
        self.assertEqual(registry.statistics()["locations"], 2)
        self.assertEqual(registry.database.integrity_check(), "ok")

    def test_imports_legacy_json_only_once(self):
        registry = DocumentRegistry(self.config)
        legacy = self.config.state_root / "duplicate-index.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            json.dumps({
                "files": {
                    "x": {
                        "sha256": "a" * 64,
                        "path": str(self.root / "missing.pdf"),
                        "size": 42,
                    }
                }
            }),
            encoding="utf-8",
        )

        self.assertEqual(registry.import_legacy_index(legacy), 1)
        self.assertEqual(registry.import_legacy_index(legacy), 0)
        self.assertEqual(registry.statistics()["documents"], 1)

    def test_controlled_reset_keeps_database_but_clears_history(self):
        registry = DocumentRegistry(self.config)
        document = self.root / "document.pdf"
        document.write_bytes(b"reset me")
        document_id = registry.register_document(document, location_type="archive")
        registry.record_event(document_id, "processed", status="success")

        registry.clear_document_history()

        self.assertEqual(
            registry.statistics(), {"documents": 0, "locations": 0, "events": 0}
        )
        self.assertEqual(registry.get_state("backup_bootstrap_complete"), "1")
        self.assertTrue(registry.database.path.exists())
