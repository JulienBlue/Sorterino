import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.logger import FileLogger


class _LegacyConsole(io.StringIO):
    encoding = "cp1252"

    def write(self, value):
        value.encode(self.encoding)
        return super().write(value)


class FileLoggerTests(unittest.TestCase):
    def test_unsupported_console_character_does_not_break_logging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            console = _LegacyConsole()
            logger = FileLogger(Path(temp_dir))

            with patch("sys.stdout", console):
                logger.debug("PDF → Bild")

            self.assertIn("PDF ? Bild", console.getvalue())
            self.assertIn(
                "PDF → Bild",
                (Path(temp_dir) / "sorterino.log").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
