"""Central list of document formats accepted by Sorterino."""

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".heic", ".heif"
}
WORD_EXTENSIONS = {".docx", ".docm", ".doc"}
TEXT_DOCUMENT_EXTENSIONS = {".odt", ".rtf", ".txt"}
PAGES_EXTENSIONS = {".pages"}
EMAIL_EXTENSIONS = {".eml", ".msg"}

SUPPORTED_EXTENSIONS = (
    PDF_EXTENSIONS
    | IMAGE_EXTENSIONS
    | WORD_EXTENSIONS
    | TEXT_DOCUMENT_EXTENSIONS
    | PAGES_EXTENSIONS
    | EMAIL_EXTENSIONS
)


def file_dialog_patterns(extensions):
    return " ".join(f"*{extension}" for extension in sorted(extensions))


def is_ignored_source_name(filename):
    """Ignore transient editor locks and Windows metadata, never real documents."""
    name = str(filename or "")
    folded = name.casefold()
    return (
        name.startswith("~$")
        or folded.startswith(".~lock.")
        or folded in {"thumbs.db", "desktop.ini"}
        or folded.endswith((".tmp", ".part", ".crdownload"))
    )
