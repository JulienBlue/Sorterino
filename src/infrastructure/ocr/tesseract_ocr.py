import os
from typing import List

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFile


# Große Bilder erlauben
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True


class TesseractOCR:

    def __init__(self, poppler_path: str, tesseract_path: str):

        # ----------------------------------------
        # Tesseract setzen (aus Config)
        # ----------------------------------------
        if not os.path.exists(tesseract_path):
            raise FileNotFoundError(
                f"Tesseract nicht gefunden unter: {tesseract_path}"
            )

        pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Tessdata-Verzeichnis automatisch ableiten
        tessdata_path = os.path.join(
            os.path.dirname(tesseract_path),
            "tessdata"
        )

        if not os.path.exists(tessdata_path):
            raise FileNotFoundError(
                f"Tessdata nicht gefunden unter: {tessdata_path}"
            )

        os.environ["TESSDATA_PREFIX"] = tessdata_path

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
            print(f"OCR Fehler: Datei existiert nicht: {file_path}")
            return ""

        try:
            if file_path.lower().endswith(".pdf"):
                text = self._extract_from_pdf(file_path)
            else:
                text = self._extract_from_image(file_path)

            if not text or not text.strip():
                print("   ⚠️ Kein OCR-Text gefunden")
                return ""

            return text

        except Exception as e:
            print(f"OCR Fehler bei {file_path}: {e}")
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
            print(f"PDF-Konvertierungsfehler bei {file_path}: {e}")
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
                print(
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
            print(f"OCR Bildfehler bei {file_path}: {e}")
            return ""