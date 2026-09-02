import io
import tempfile
import unittest
import zipfile
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.document_formats import SUPPORTED_EXTENSIONS
from src.document_text_extractor import (
    DocumentNeedsReview,
    DocumentTextExtractor,
)
from src.tesseract_ocr import TesseractOCR


class _Logger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class _OCR:
    def __init__(self, text="Gescannter Inhalt"):
        self.text = text
        self.calls = []

    def extract_text(self, path):
        path = Path(path)
        self.calls.append((path.suffix.casefold(), path.read_bytes()))
        return self.text


def _zip(path, members):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


class DocumentTextExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ocr = _OCR()
        self.extractor = DocumentTextExtractor(self.ocr, _Logger())

    def tearDown(self):
        self.temp.cleanup()

    def test_priority_one_extensions_are_centralized(self):
        self.assertTrue({
            ".docx", ".docm", ".doc", ".odt", ".rtf", ".txt", ".pages",
            ".eml", ".msg", ".tif", ".tiff", ".webp", ".heic", ".heif",
        }.issubset(SUPPORTED_EXTENSIONS))

    def test_extracts_docx_body_headers_and_core_properties(self):
        path = self.root / "Schreiben.docx"
        _zip(path, {
            "word/document.xml": (
                '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Arbeitsvertrag</w:t>'
                '</w:r></w:p><w:p><w:r><w:t>Beispiel GmbH</w:t></w:r></w:p></w:body></w:document>'
            ),
            "word/header1.xml": (
                '<w:hdr xmlns:w="urn:w"><w:p><w:r><w:t>Julien Blue Hirte</w:t></w:r></w:p></w:hdr>'
            ),
            "docProps/core.xml": (
                '<cp:coreProperties xmlns:cp="urn:cp"><cp:title>Vertrag 2026</cp:title>'
                '<cp:creator>Personalabteilung</cp:creator></cp:coreProperties>'
            ),
        })

        text = self.extractor.extract_text(path)

        self.assertIn("Arbeitsvertrag", text)
        self.assertIn("Beispiel GmbH", text)
        self.assertIn("Julien Blue Hirte", text)
        self.assertIn("Vertrag 2026", text)

    def test_docx_with_only_scan_uses_embedded_image_ocr(self):
        path = self.root / "Scan.docx"
        _zip(path, {
            "word/document.xml": '<w:document xmlns:w="urn:w"><w:body/></w:document>',
            "word/media/image1.png": b"x" * 2048,
        })

        self.assertIn("Gescannter Inhalt", self.extractor.extract_text(path))
        self.assertEqual(self.ocr.calls[0][0], ".png")

    def test_extracts_odt_rtf_and_common_text_encodings(self):
        odt = self.root / "Brief.odt"
        _zip(odt, {
            "content.xml": (
                '<office:document-content xmlns:office="urn:o" xmlns:text="urn:t">'
                '<office:body><office:text><text:p>Mahnung</text:p>'
                '<text:p>Stadt Köln</text:p></office:text></office:body></office:document-content>'
            ),
        })
        rtf = self.root / "Notiz.rtf"
        rtf.write_bytes(r"{\rtf1\ansi Bewerbung f\'fcr Pflegeberaterin\par Sabine Hirte}".encode("ascii"))
        cp1252 = self.root / "Notiz.txt"
        cp1252.write_bytes("Kündigung für Köln".encode("cp1252"))
        utf16 = self.root / "Unicode.txt"
        utf16.write_bytes("Führungszeugnis".encode("utf-16"))

        self.assertIn("Mahnung", self.extractor.extract_text(odt))
        self.assertIn("für Pflegeberaterin", self.extractor.extract_text(rtf))
        self.assertEqual(self.extractor.extract_text(cp1252), "Kündigung für Köln")
        self.assertEqual(self.extractor.extract_text(utf16), "Führungszeugnis")

    def test_pages_uses_embedded_preview_without_changing_original(self):
        path = self.root / "Brief.pages"
        preview = b"%PDF-preview"
        _zip(path, {"QuickLook/Preview.pdf": preview, "Index/Document.iwa": b"binary"})
        original = path.read_bytes()

        text = self.extractor.extract_text(path)

        self.assertEqual(text, "Gescannter Inhalt")
        self.assertEqual(self.ocr.calls[0], (".pdf", preview))
        self.assertEqual(path.read_bytes(), original)

    def test_pages_without_preview_goes_to_manual_review(self):
        path = self.root / "Ohne Vorschau.pages"
        _zip(path, {"Index/Document.iwa": b"binary"})

        with self.assertRaisesRegex(DocumentNeedsReview, "keine auswertbare"):
            self.extractor.extract_text(path)

    def test_protected_odt_goes_to_manual_review(self):
        path = self.root / "Geschützt.odt"
        _zip(path, {
            "META-INF/manifest.xml": "<manifest><encryption-data/></manifest>",
            "content.xml": b"encrypted",
        })

        with self.assertRaisesRegex(DocumentNeedsReview, "passwortgeschützt"):
            self.extractor.extract_text(path)

    def test_old_doc_without_libreoffice_goes_to_manual_review(self):
        path = self.root / "Alt.doc"
        path.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"old-word")

        with patch.object(DocumentTextExtractor, "_find_soffice", return_value=None):
            with self.assertRaisesRegex(DocumentNeedsReview, "LibreOffice"):
                self.extractor.extract_text(path)

    def test_eml_extracts_headers_html_and_supported_attachment(self):
        message = EmailMessage()
        message["From"] = "rechnung@example.test"
        message["To"] = "sabine@example.test"
        message["Date"] = "Mon, 10 Aug 2026 10:00:00 +0200"
        message["Subject"] = "Rechnung August"
        message.set_content("Bitte beachten Sie den Anhang.")
        message.add_attachment(
            "Rechnungsnummer 4711\nGesamtbetrag 25,00 EUR".encode("utf-8"),
            maintype="text", subtype="plain", filename="Rechnung.txt",
        )
        path = self.root / "Nachricht.eml"
        path.write_bytes(message.as_bytes())

        text = self.extractor.extract_text(path)

        self.assertIn("Von: rechnung@example.test", text)
        self.assertIn("Betreff: Rechnung August", text)
        self.assertIn("Anhänge: Rechnung.txt", text)
        self.assertIn("Rechnungsnummer 4711", text)

    def test_msg_reads_mapi_text_fields_and_attachment_names(self):
        class FakeOle:
            values = {
                ("__substg1.0_0C1A001F",): "Beispiel GmbH".encode("utf-16-le"),
                ("__substg1.0_0E04001F",): "Sabine Hirte".encode("utf-16-le"),
                ("__substg1.0_0037001F",): "Versicherungsvertrag".encode("utf-16-le"),
                ("__substg1.0_1000001F",): "Ihre Vertragsnummer 123".encode("utf-16-le"),
                ("__attach_version1.0_#00000000", "__substg1.0_3707001F"):
                    "Anlage.txt".encode("utf-16-le"),
                ("__attach_version1.0_#00000000", "__substg1.0_37010102"):
                    b"Text aus dem Anhang",
            }

            def listdir(self, streams=True, storages=False):
                return [list(key) for key in self.values]

            def openstream(self, location):
                return io.BytesIO(self.values[tuple(location)])

            def close(self):
                pass

        path = self.root / "Nachricht.msg"
        path.write_bytes(b"fake-msg")
        with patch("olefile.OleFileIO", return_value=FakeOle()):
            text = self.extractor.extract_text(path)

        self.assertIn("Von: Beispiel GmbH", text)
        self.assertIn("Betreff: Versicherungsvertrag", text)
        self.assertIn("Anhänge: Anlage.txt", text)
        self.assertIn("Text aus dem Anhang", text)

    def test_multiframe_tiff_is_fully_ocr_processed(self):
        path = self.root / "Mehrseitig.tiff"
        first = Image.new("RGB", (20, 20), "white")
        second = Image.new("RGB", (20, 20), "black")
        first.save(path, save_all=True, append_images=[second])
        service = TesseractOCR.__new__(TesseractOCR)
        service.logger = _Logger()
        service.language = "deu+eng+fra"

        with patch("src.tesseract_ocr.pytesseract.image_to_string", side_effect=["Seite 1", "Seite 2"]):
            text = service._extract_from_image(str(path))

        self.assertIn("Seite 1", text)
        self.assertIn("Seite 2", text)

    def test_heic_is_opened_through_pillow_plugin(self):
        from pillow_heif import from_pillow

        path = self.root / "Scan.heic"
        source = Image.new("RGB", (20, 20), "white")
        from_pillow(source).save(path)
        service = TesseractOCR.__new__(TesseractOCR)
        service.logger = _Logger()
        service.language = "deu+eng+fra"

        with patch("src.tesseract_ocr.pytesseract.image_to_string", return_value="HEIC Text"):
            text = service._extract_from_image(str(path))

        self.assertEqual(text, "HEIC Text")


if __name__ == "__main__":
    unittest.main()
