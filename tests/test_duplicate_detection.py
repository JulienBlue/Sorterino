import tempfile
import unittest
from pathlib import Path

from src.document_pipeline import DocumentPipeline
from src.duplicate_index import ExactDuplicateIndex
from src.manual_review_suggestions import ManualReviewSuggestionStore
from src.models import Document, DocumentStatus
from src.profile_service import ProfileService
from src.storage_utils import FilesystemStorage
from src.storage_utils import FolderDocumentSource
from tests.test_profile_service import FakeConfig


class NullLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class FailingExtractor:
    def extract_text(self, _path):
        raise AssertionError("Duplikate dürfen nicht bis zur Texterkennung gelangen")


class CountingEmptyExtractor:
    def __init__(self):
        self.paths = []

    def extract_text(self, path):
        self.paths.append(Path(path))
        return ""


class StopDuringExtraction:
    def __init__(self, stop_event):
        self.stop_event = stop_event

    def extract_text(self, _path):
        self.stop_event.set()
        return "would normally continue"


class ExactDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = FakeConfig(self.root)
        self.config.state_root = self.root / "state"
        self.backup_root = self.root / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def test_finds_byte_identical_file_with_different_name(self):
        known = self.backup_root / "original.pdf"
        known.parent.mkdir(parents=True)
        known.write_bytes(b"same bytes")
        candidate = self.root / "copy.pdf"
        candidate.write_bytes(b"same bytes")

        _digest, duplicate = ExactDuplicateIndex(
            self.config, self.backup_root
        ).find(candidate)

        self.assertEqual(duplicate.path, known)
        self.assertTrue(duplicate.file_present)

    def test_different_content_is_not_a_duplicate(self):
        known = self.backup_root / "original.pdf"
        known.parent.mkdir(parents=True)
        known.write_bytes(b"first")
        candidate = self.root / "copy.pdf"
        candidate.write_bytes(b"second")

        _digest, duplicate = ExactDuplicateIndex(
            self.config, self.backup_root
        ).find(candidate)

        self.assertIsNone(duplicate)

    def test_pipeline_stops_duplicate_before_text_extraction(self):
        service = ProfileService(self.config)
        backup_root = service.resolve_backup_directory()
        known = backup_root / "Familie Hirte" / "original.pdf"
        known.parent.mkdir(parents=True)
        known.write_bytes(b"already archived")
        incoming = self.root / "incoming" / "copy.pdf"
        incoming.parent.mkdir()
        incoming.write_bytes(b"already archived")
        runtime = self.root / "runtime"
        pipeline = DocumentPipeline(
            config=self.config,
            sources=[],
            ocr_service=FailingExtractor(),
            runtime_storage=FilesystemStorage(runtime),
            archive_storage=FilesystemStorage(self.root / "archive"),
            logger=NullLogger(),
            rules={},
            structure={},
            profile_service=service,
        )
        document = Document(str(incoming))

        pipeline._process(document)

        reviewed = runtime / "manual_sort" / "copy.pdf"
        self.assertEqual(document.status, DocumentStatus.STORED)
        self.assertTrue(reviewed.exists())
        suggestion = ManualReviewSuggestionStore(self.config).load(reviewed)
        self.assertEqual(suggestion["review_kind"], "exact_duplicate")
        self.assertEqual(Path(suggestion["duplicate_of"]), known)

    def test_deleted_backup_remains_known_as_historical_duplicate(self):
        known = self.backup_root / "original.pdf"
        known.parent.mkdir(parents=True)
        known.write_bytes(b"remember these bytes")
        index = ExactDuplicateIndex(self.config, self.backup_root)
        known.unlink()
        candidate = self.root / "copy.pdf"
        candidate.write_bytes(b"remember these bytes")

        _digest, duplicate = ExactDuplicateIndex(
            self.config, self.backup_root
        ).find(candidate)

        self.assertIsNotNone(duplicate)
        self.assertFalse(duplicate.file_present)

    def test_same_import_selects_meaningful_name_and_extracts_only_once(self):
        incoming = self.root / "incoming"
        incoming.mkdir()
        generic = incoming / "IMG_1042.jpg"
        meaningful = incoming / "Warmwasserschaden Badezimmer.jpg"
        generic.write_bytes(b"identical photo bytes")
        meaningful.write_bytes(b"identical photo bytes")
        extractor = CountingEmptyExtractor()
        runtime = self.root / "runtime"
        pipeline = DocumentPipeline(
            config=self.config,
            sources=[FolderDocumentSource(incoming)],
            ocr_service=extractor,
            runtime_storage=FilesystemStorage(runtime),
            archive_storage=FilesystemStorage(self.root / "archive"),
            logger=NullLogger(),
            rules={},
            structure={},
            profile_service=None,
        )

        pipeline.run()

        self.assertEqual(
            [path.name for path in extractor.paths],
            ["Warmwasserschaden Badezimmer.jpg"],
        )
        duplicate = runtime / "manual_sort" / "IMG_1042.jpg"
        suggestion = ManualReviewSuggestionStore(self.config).load(duplicate)
        self.assertEqual(suggestion["review_kind"], "same_import_duplicate")
        self.assertEqual(
            suggestion["selected_import_name"],
            "Warmwasserschaden Badezimmer.jpg",
        )

    def test_cooperative_stop_leaves_current_document_in_incoming(self):
        import threading

        incoming = self.root / "incoming"
        incoming.mkdir()
        document_path = incoming / "large-scan.pdf"
        document_path.write_bytes(b"not previously known")
        stop_event = threading.Event()
        runtime = self.root / "runtime"
        pipeline = DocumentPipeline(
            config=self.config,
            sources=[FolderDocumentSource(incoming)],
            ocr_service=StopDuringExtraction(stop_event),
            runtime_storage=FilesystemStorage(runtime),
            archive_storage=FilesystemStorage(self.root / "archive"),
            logger=NullLogger(),
            rules={},
            structure={},
            profile_service=None,
            stop_requested=stop_event.is_set,
        )

        pipeline.run()

        self.assertTrue(document_path.exists())
        self.assertFalse((runtime / "manual_sort" / document_path.name).exists())
