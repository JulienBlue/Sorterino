import os
from typing import List

from src.utils.path_helper import get_base_path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFile


# Große Bilder erlauben
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

base_path = get_base_path()

from src.utils.path_helper import get_base_path
import os
import pytesseract


class TesseractOCR:

    def __init__(
        self,
        poppler_path: str,
        tesseract_path: str,
        logger
    ):

        self.logger = logger

        base_path = get_base_path()

        # ----------------------------------------
        # 🔥 Tesseract EXE (IMMER aus third_party laden)
        # ----------------------------------------

        tesseract_exe = base_path / "third_party" / "Tesseract-OCR" / "tesseract.exe"

        if not tesseract_exe.exists():
            raise FileNotFoundError(
                f"Tesseract nicht gefunden unter: {tesseract_exe}"
            )

        pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)

        # ----------------------------------------
        # 🔥 Tessdata FIX
        # ----------------------------------------

        tessdata_path = base_path / "tessdata"

        if not tessdata_path.exists():
            # Fallback: innerhalb third_party
            tessdata_path = base_path / "third_party" / "Tesseract-OCR" / "tessdata"

        if not tessdata_path.exists():
            raise FileNotFoundError(
                f"Tessdata nicht gefunden unter: {tessdata_path}"
            )

        os.environ["TESSDATA_PREFIX"] = str(tessdata_path)

        self.logger.log(f"Tesseract Path: {tesseract_exe}")
        self.logger.log(f"Tessdata Path: {tessdata_path}")

        # ----------------------------------------
        # Poppler
        # ----------------------------------------

        self.poppler_path = poppler_path
        self.language = "deu"

    # =====================================================
    # Öffentlich
    # =====================================================

    def extract_text(self, file_path: str) -> str:

        if not os.path.exists(file_path):
            self.logger.error(f"OCR Fehler: Datei existiert nicht: {file_path}")
            return ""

        try:
            if file_path.lower().endswith(".pdf"):
                text = self._extract_from_pdf(file_path)
            else:
                text = self._extract_from_image(file_path)

            if not text or not text.strip():
                self.logger.warning("⚠️ Kein OCR-Text gefunden")
                return ""

            return text

        except Exception as e:
            self.logger.error(f"OCR Fehler bei {file_path}: {e}")
            return ""

    # =====================================================
    # PDF OCR
    # =====================================================

    def _extract_from_pdf(self, file_path: str) -> str:

        text_output: List[str] = []

        try:
            images = convert_from_path(
                file_path,
                poppler_path=self.poppler_path,
                dpi=300
            )
        except Exception as e:
            self.logger.error(f"PDF-Konvertierungsfehler bei {file_path}: {e}")
            return ""

        for index, img in enumerate(images):
            try:
                img.thumbnail((3500, 3500))

                text = pytesseract.image_to_string(
                    img,
                    lang=self.language
                )

                if text and text.strip():
                    text_output.append(text)

            except Exception as e:
                self.logger.warning(
                    f"OCR Seitenfehler bei {file_path} "
                    f"(Seite {index + 1}): {e}"
                )
                continue

        return "\n".join(text_output)

    # =====================================================
    # Image OCR
    # =====================================================

    def _extract_from_image(self, file_path: str) -> str:

        try:
            with Image.open(file_path) as img:

                img.thumbnail((3500, 3500))

                text = pytesseract.image_to_string(
                    img,
                    lang=self.language
                )

                return text or ""

        except Exception as e:
            self.logger.error(f"OCR Bildfehler bei {file_path}: {e}")
            return ""