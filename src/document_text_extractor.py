"""Safe local text extraction for all document formats supported by Sorterino."""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from src.document_formats import IMAGE_EXTENSIONS, PDF_EXTENSIONS, SUPPORTED_EXTENSIONS


MAX_EXTRACTED_CHARS = 2_000_000
MAX_ARCHIVE_ENTRY_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 300 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000


class DocumentExtractionError(RuntimeError):
    """The document could not be read for technical reasons."""

    reason = "extraction_error"


class DocumentNeedsReview(DocumentExtractionError):
    """The source is valid, but its contents cannot be safely interpreted."""

    reason = "extraction_needs_review"


class _HTMLTextExtractor(HTMLParser):
    BLOCKS = {
        "address", "article", "aside", "blockquote", "br", "div", "footer",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "p", "section",
        "table", "td", "th", "tr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, _attrs):
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._ignored_depth:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def _local_name(tag):
    return str(tag).rsplit("}", 1)[-1]


def _normalized_text(value):
    value = str(value or "").replace("\x00", "")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()[:MAX_EXTRACTED_CHARS]


def _xml_to_text(payload, paragraph_tags=("p", "h")):
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise DocumentExtractionError("Die Dokumentstruktur ist beschädigt.") from exc
    parts = []
    paragraph_tags = set(paragraph_tags)

    def walk(element):
        name = _local_name(element.tag)
        if element.text:
            parts.append(element.text)
        if name in {"tab"}:
            parts.append("\t")
        elif name in {"br", "line-break"}:
            parts.append("\n")
        for child in element:
            walk(child)
        if element.tail:
            parts.append(element.tail)
        if name in paragraph_tags:
            parts.append("\n")

    walk(root)
    return _normalized_text("".join(parts))


def _checked_zip(path):
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        try:
            with Path(path).open("rb") as stream:
                signature = stream.read(8)
        except OSError:
            signature = b""
        if signature.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
            raise DocumentNeedsReview(
                "Das Dokument ist vermutlich passwortgeschützt oder verschlüsselt."
            ) from exc
        raise DocumentExtractionError("Der Dokumentcontainer ist beschädigt.") from exc
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        archive.close()
        raise DocumentExtractionError("Der Dokumentcontainer enthält ungewöhnlich viele Einträge.")
    total = sum(info.file_size for info in infos)
    if total > MAX_ARCHIVE_TOTAL_BYTES or any(
        info.file_size > MAX_ARCHIVE_ENTRY_BYTES for info in infos
    ):
        archive.close()
        raise DocumentExtractionError("Der entpackte Dokumentinhalt ist ungewöhnlich groß.")
    return archive


def _read_zip_member(archive, name):
    try:
        return archive.read(name)
    except KeyError as exc:
        raise DocumentExtractionError(f"Erforderlicher Dokumentinhalt fehlt: {name}") from exc


class DocumentTextExtractor:
    """Dispatch direct parsers and OCR without changing the source document."""

    def __init__(self, ocr_service, logger):
        self.ocr = ocr_service
        self.logger = logger

    def extract_text(self, file_path, _depth=0):
        path = Path(file_path)
        extension = path.suffix.casefold()
        try:
            if extension in PDF_EXTENSIONS | IMAGE_EXTENSIONS:
                return self._ocr(path)
            if extension in {".docx", ".docm"}:
                return self._extract_docx(path)
            if extension == ".doc":
                return self._extract_legacy_doc(path)
            if extension == ".odt":
                return self._extract_odt(path)
            if extension == ".rtf":
                return self._extract_rtf(path)
            if extension == ".txt":
                return self._extract_txt(path)
            if extension == ".pages":
                return self._extract_pages(path)
            if extension == ".eml":
                return self._extract_eml(path, _depth)
            if extension == ".msg":
                return self._extract_msg(path, _depth)
            raise DocumentExtractionError(f"Das Dateiformat {extension or '(ohne Endung)'} wird nicht unterstützt.")
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError(
                f"{path.name} konnte nicht sicher gelesen werden: {exc}"
            ) from exc

    def _ocr(self, path):
        if not self.ocr:
            raise DocumentNeedsReview("Für dieses Format ist die Texterkennung erforderlich.")
        text = self.ocr.extract_text(path)
        if text is None:
            raise DocumentExtractionError("Die Texterkennung ist fehlgeschlagen.")
        return _normalized_text(text)

    def _extract_docx(self, path):
        with _checked_zip(path) as archive:
            names = set(archive.namelist())
            candidates = ["word/document.xml"]
            candidates.extend(sorted(
                name for name in names
                if re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
                or name in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
            ))
            sections = []
            for name in candidates:
                if name in names:
                    sections.append(_xml_to_text(_read_zip_member(archive, name)))
            if "docProps/core.xml" in names:
                core = _xml_to_text(_read_zip_member(archive, "docProps/core.xml"), ())
                if core:
                    sections.insert(0, core)
            direct_text = _normalized_text("\n\n".join(filter(None, sections)))
            if len(direct_text) < 300:
                image_names = [
                    name for name in names
                    if name.startswith("word/media/")
                    and Path(name).suffix.casefold() in IMAGE_EXTENSIONS
                ]
                sections.extend(self._ocr_archive_images(archive, image_names))
            result = _normalized_text("\n\n".join(filter(None, sections)))
            if not result:
                raise DocumentExtractionError("Das Word-Dokument enthält keinen lesbaren Dokumenttext.")
            return result

    def _extract_odt(self, path):
        with _checked_zip(path) as archive:
            if "META-INF/manifest.xml" in archive.namelist() and b"encryption-data" in _read_zip_member(
                archive, "META-INF/manifest.xml"
            ):
                raise DocumentNeedsReview(
                    "Das ODT-Dokument ist passwortgeschützt und muss vor der Verarbeitung entsperrt werden."
                )
            sections = []
            if "meta.xml" in archive.namelist():
                sections.append(_xml_to_text(_read_zip_member(archive, "meta.xml"), ()))
            sections.append(_xml_to_text(_read_zip_member(archive, "content.xml")))
            direct_text = _normalized_text("\n\n".join(filter(None, sections)))
            if len(direct_text) < 300:
                image_names = [
                    name for name in archive.namelist()
                    if name.startswith("Pictures/")
                    and Path(name).suffix.casefold() in IMAGE_EXTENSIONS
                ]
                sections.extend(self._ocr_archive_images(archive, image_names))
            return _normalized_text("\n\n".join(filter(None, sections)))

    def _ocr_archive_images(self, archive, names):
        if not names or not self.ocr:
            return []
        text_output = []
        with tempfile.TemporaryDirectory(prefix="sorterino-office-images-") as temp_dir:
            for index, name in enumerate(names[:20]):
                payload = _read_zip_member(archive, name)
                if len(payload) < 1024:
                    continue
                image_path = Path(temp_dir) / f"image-{index}{Path(name).suffix.casefold()}"
                image_path.write_bytes(payload)
                try:
                    text = self._ocr(image_path)
                except DocumentExtractionError:
                    continue
                if text:
                    text_output.append(text)
        return text_output

    def _extract_legacy_doc(self, path):
        soffice = self._find_soffice()
        if not soffice:
            raise DocumentNeedsReview(
                "Alte Word-Dateien (.doc) benötigen LibreOffice. Speichere die Datei alternativ als .docx."
            )
        with tempfile.TemporaryDirectory(prefix="sorterino-doc-") as temp_dir:
            libreoffice_profile = (Path(temp_dir) / "libreoffice-profile").resolve().as_uri()
            command = [
                soffice, "--headless", "--safe-mode",
                f"-env:UserInstallation={libreoffice_profile}", "--convert-to", "docx",
                "--outdir", temp_dir, str(path),
            ]
            startupinfo = None
            creationflags = 0
            if hasattr(subprocess, "STARTUPINFO"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            converted = Path(temp_dir) / f"{path.stem}.docx"
            if result.returncode or not converted.exists():
                details = (result.stderr or result.stdout or "Konvertierung fehlgeschlagen").strip()
                raise DocumentNeedsReview(f"Die alte Word-Datei konnte nicht konvertiert werden: {details}")
            return self._extract_docx(converted)

    @staticmethod
    def _find_soffice():
        candidates = [
            shutil.which("soffice"),
            str(Path.home() / "AppData/Local/Programs/LibreOffice/program/soffice.exe"),
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        return next((value for value in candidates if value and Path(value).is_file()), None)

    @staticmethod
    def _extract_txt(path):
        payload = path.read_bytes()
        encodings = []
        if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
            encodings.append("utf-16")
        encodings.extend(("utf-8-sig", "cp1252"))
        for encoding in encodings:
            try:
                decoded = payload.decode(encoding)
            except UnicodeDecodeError:
                continue
            control_count = sum(
                character < " " and character not in "\t\r\n"
                for character in decoded
            )
            if "\x00" in decoded or control_count > max(4, len(decoded) // 50):
                continue
            return _normalized_text(decoded)
        raise DocumentExtractionError("Die Textkodierung konnte nicht erkannt werden.")

    @staticmethod
    def _extract_rtf(path):
        payload = path.read_bytes()
        raw = payload.decode("latin-1", errors="replace")
        if not raw.lstrip().startswith("{\\rtf"):
            raise DocumentExtractionError("Die Datei enthält kein gültiges RTF-Dokument.")
        return _normalized_text(_rtf_to_text(raw))

    def _extract_pages(self, path):
        try:
            archive_context = _checked_zip(path)
        except DocumentExtractionError as exc:
            raise DocumentNeedsReview(
                "Die Pages-Datei kann unter Windows nicht direkt gelesen werden. Exportiere sie bitte als PDF."
            ) from exc
        with archive_context as archive:
            names = archive.namelist()
            preferred = (
                "QuickLook/Preview.pdf", "preview.pdf", "Preview.pdf",
                "QuickLook/Preview.jpg", "QuickLook/Preview.jpeg",
                "QuickLook/Preview.png", "preview.jpg", "preview.png",
            )
            preview_name = next((name for name in preferred if name in names), None)
            if not preview_name:
                preview_name = next((
                    name for name in names
                    if Path(name).name.casefold().startswith("preview.")
                    and Path(name).suffix.casefold() in PDF_EXTENSIONS | IMAGE_EXTENSIONS
                ), None)
            if not preview_name:
                raise DocumentNeedsReview(
                    "Die Pages-Datei enthält keine auswertbare PDF- oder Bildvorschau. Exportiere sie bitte als PDF."
                )
            suffix = Path(preview_name).suffix.casefold()
            with tempfile.TemporaryDirectory(prefix="sorterino-pages-") as temp_dir:
                preview = Path(temp_dir) / f"preview{suffix}"
                preview.write_bytes(_read_zip_member(archive, preview_name))
                return self._ocr(preview)

    def _extract_eml(self, path, depth):
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        sections = []
        for label, header in (
            ("Von", "From"), ("An", "To"), ("Kopie", "Cc"),
            ("Datum", "Date"), ("Betreff", "Subject"),
        ):
            value = message.get(header)
            if value:
                sections.append(f"{label}: {value}")
        bodies = []
        attachments = []
        for part in message.walk() if message.is_multipart() else (message,):
            disposition = part.get_content_disposition()
            filename = part.get_filename()
            if disposition == "attachment" or filename:
                if filename:
                    attachments.append((str(filename), part.get_payload(decode=True) or b""))
                continue
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            try:
                value = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True) or b""
                value = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if content_type == "text/html":
                parser = _HTMLTextExtractor()
                parser.feed(str(value))
                value = parser.text()
            if value and str(value).strip():
                bodies.append(str(value))
        sections.extend(bodies)
        if attachments:
            sections.append("Anhänge: " + ", ".join(name for name, _payload in attachments))
            sections.extend(self._extract_attachment_texts(attachments, depth))
        return _normalized_text("\n".join(sections))

    def _extract_msg(self, path, depth):
        try:
            import olefile
        except ImportError as exc:
            raise DocumentNeedsReview(
                "Für Outlook-MSG-Dateien fehlt die lokale Komponente olefile."
            ) from exc
        try:
            archive = olefile.OleFileIO(str(path))
        except Exception as exc:
            raise DocumentExtractionError("Die Outlook-MSG-Datei ist beschädigt oder verschlüsselt.") from exc
        try:
            streams = archive.listdir(streams=True, storages=False)

            def stream_map(prefix=()):
                return {
                    parts[-1].casefold(): parts
                    for parts in streams
                    if tuple(parts[:-1]) == tuple(prefix)
                }

            root_streams = stream_map()

            def read_property(tag, property_type="001F", mapping=None):
                if mapping is None:
                    mapping = root_streams
                name = f"__substg1.0_{tag}{property_type}".casefold()
                location = mapping.get(name)
                if location is None and property_type == "001F":
                    location = mapping.get(f"__substg1.0_{tag}001E".casefold())
                    if location is not None:
                        return archive.openstream(location).read().rstrip(b"\x00").decode(
                            "cp1252", errors="replace"
                        )
                if location is None:
                    return None
                payload = archive.openstream(location).read()
                if property_type == "001F":
                    return payload.decode("utf-16-le", errors="replace").rstrip("\x00")
                return payload

            sections = []
            for label, tag in (
                ("Von", "0C1A"), ("An", "0E04"), ("Kopie", "0E03"),
                ("Betreff", "0037"),
            ):
                value = read_property(tag)
                if value:
                    sections.append(f"{label}: {value}")

            sent_time = read_property("0039", "0040")
            if sent_time and len(sent_time) >= 8:
                filetime = int.from_bytes(sent_time[:8], "little", signed=False)
                if filetime:
                    value = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
                        microseconds=filetime // 10
                    )
                    sections.insert(3 if len(sections) >= 3 else 0, f"Datum: {value.isoformat()}")

            body = read_property("1000")
            if body:
                sections.append(str(body))
            else:
                html_body = read_property("1013", "0102")
                if html_body:
                    html_body = html_body.decode("utf-8", errors="replace")
                else:
                    html_body = None
            if not body and html_body:
                parser = _HTMLTextExtractor()
                parser.feed(str(html_body))
                sections.append(parser.text())

            attachment_storages = sorted({
                parts[0] for parts in streams
                if parts and parts[0].casefold().startswith("__attach_version1.0_")
            })
            attachments = []
            for storage in attachment_storages:
                mapping = stream_map((storage,))
                filename = read_property("3707", mapping=mapping) or read_property(
                    "3704", mapping=mapping
                )
                if filename:
                    data_location = mapping.get("__substg1.0_37010102")
                    payload = archive.openstream(data_location).read() if data_location else b""
                    attachments.append((filename, payload))
            if attachments:
                sections.append("Anhänge: " + ", ".join(name for name, _payload in attachments))
                sections.extend(self._extract_attachment_texts(attachments, depth))
            return _normalized_text("\n".join(sections))
        finally:
            archive.close()

    def _extract_attachment_texts(self, attachments, depth):
        if depth >= 2:
            return []
        results = []
        with tempfile.TemporaryDirectory(prefix="sorterino-mail-attachments-") as temp_dir:
            for index, (filename, payload) in enumerate(attachments[:10]):
                suffix = Path(filename).suffix.casefold()
                if suffix not in SUPPORTED_EXTENSIONS or not payload or len(payload) > 50 * 1024 * 1024:
                    continue
                target = Path(temp_dir) / f"attachment-{index}{suffix}"
                target.write_bytes(payload)
                try:
                    text = self.extract_text(target, _depth=depth + 1)
                except DocumentExtractionError:
                    continue
                if text:
                    results.append(f"Inhalt von Anhang {Path(filename).name}:\n{text}")
        return results


def _rtf_to_text(raw):
    """Conservative RTF text reader; ignores binary and formatting destinations."""
    destinations = {
        "fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "header",
        "footer", "headerl", "headerr", "footerl", "footerr", "generator", "xmlnstbl",
        "datastore", "themedata", "colorschememapping", "latentstyles", "listtable",
        "listoverridetable", "rsidtbl",
    }
    stack = []
    ignored = False
    uc_skip = 1
    skip_chars = 0
    output = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "{":
            stack.append((ignored, uc_skip))
            index += 1
            continue
        if char == "}":
            if stack:
                ignored, uc_skip = stack.pop()
            index += 1
            continue
        if char != "\\":
            if not ignored and skip_chars == 0 and char not in "\r\n":
                output.append(char)
            elif skip_chars:
                skip_chars -= 1
            index += 1
            continue
        index += 1
        if index >= len(raw):
            break
        symbol = raw[index]
        if symbol in "\\{}":
            if not ignored and not skip_chars:
                output.append(symbol)
            elif skip_chars:
                skip_chars -= 1
            index += 1
            continue
        if symbol == "'" and index + 2 < len(raw):
            try:
                decoded = bytes([int(raw[index + 1:index + 3], 16)]).decode("cp1252")
            except ValueError:
                decoded = ""
            if not ignored and not skip_chars:
                output.append(decoded)
            elif skip_chars:
                skip_chars -= 1
            index += 3
            continue
        if symbol == "*":
            ignored = True
            index += 1
            continue
        match = re.match(r"([a-zA-Z]+)(-?\d+)? ?", raw[index:])
        if not match:
            index += 1
            continue
        word = match.group(1)
        parameter = int(match.group(2)) if match.group(2) else None
        index += len(match.group(0))
        if word in destinations:
            ignored = True
        elif word == "uc" and parameter is not None:
            uc_skip = max(0, parameter)
        elif word == "u" and parameter is not None:
            if not ignored:
                output.append(chr(parameter if parameter >= 0 else parameter + 65536))
            skip_chars = uc_skip
        elif not ignored and word in {"par", "line"}:
            output.append("\n")
        elif not ignored and word == "tab":
            output.append("\t")
        elif not ignored and word == "emdash":
            output.append("—")
        elif not ignored and word == "endash":
            output.append("–")
        elif not ignored and word == "bullet":
            output.append("•")
    return html.unescape("".join(output))
