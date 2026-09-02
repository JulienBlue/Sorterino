import tempfile
import unittest
from pathlib import Path

from src.document_import import import_documents
from src.storage_utils import FileDocumentSource, FolderDocumentSource, discard_file_within


class DocumentImportTests(unittest.TestCase):
    def test_single_file_source_returns_only_selected_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected = root / "selected.pdf"
            selected.write_bytes(b"pdf")
            (root / "other.pdf").write_bytes(b"pdf")

            documents = FileDocumentSource(selected).fetch_documents()

            self.assertEqual([item.source_path for item in documents], [selected])

    def test_discard_file_is_restricted_to_selected_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incoming = root / "incoming"
            incoming.mkdir()
            discarded = incoming / "agb.pdf"
            discarded.write_bytes(b"pdf")
            outside = root / "keep.pdf"
            outside.write_bytes(b"pdf")

            self.assertEqual(discard_file_within(discarded, incoming), discarded.resolve())
            self.assertFalse(discarded.exists())
            with self.assertRaises(ValueError):
                discard_file_within(outside, incoming)
            self.assertTrue(outside.exists())

    def test_copies_supported_documents_without_removing_originals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "Brief.pdf"
            source.parent.mkdir()
            source.write_bytes(b"pdf")

            imported, skipped = import_documents([source], root / "incoming")

            self.assertEqual(skipped, [])
            self.assertTrue(source.exists())
            self.assertEqual(imported[0].read_bytes(), b"pdf")

    def test_keeps_existing_files_and_skips_unsupported_formats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "Scan.jpg"
            source.parent.mkdir()
            source.write_bytes(b"new")
            incoming = root / "incoming"
            incoming.mkdir()
            (incoming / "Scan.jpg").write_bytes(b"existing")
            supported_text = root / "source" / "Notiz.txt"
            supported_text.write_text("text", encoding="utf-8")
            unsupported = root / "source" / "Archiv.zip"
            unsupported.write_bytes(b"zip")

            imported, skipped = import_documents(
                [source, supported_text, unsupported], incoming
            )

            self.assertEqual((incoming / "Scan.jpg").read_bytes(), b"existing")
            self.assertEqual(imported[0].name, "Scan (1).jpg")
            self.assertEqual(imported[1].name, "Notiz.txt")
            self.assertEqual(skipped, [unsupported])

    def test_office_lock_files_are_not_seen_as_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            incoming = Path(temp_dir)
            (incoming / "~$Brief.docx").write_bytes(b"lock")
            (incoming / ".~lock.Brief.odt#").write_bytes(b"lock")
            (incoming / "Brief.docx").write_bytes(b"document")

            documents = FolderDocumentSource(incoming).fetch_documents()

            self.assertEqual([document.filename for document in documents], ["Brief.docx"])


if __name__ == "__main__":
    unittest.main()
