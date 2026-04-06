import os
from typing import List
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True


class TesseractOCR:

    # CONFIG / INIT
    def __init__(
        self,
        poppler_path: str,
        tesseract_path: str,
        logger
    ):
        self.logger = logger

        # OCR / TESSERACT
        tesseract_exe = Path(tesseract_path).resolve()

        if not tesseract_exe.exists():
            raise FileNotFoundError(
                f"Tesseract nicht gefunden unter {tesseract_exe}"
            )

        pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)

        tessdata_path = tesseract_exe.parent / "tessdata"

        if not tessdata_path.exists():
            raise FileNotFoundError(
                f"Tessdata nicht gefunden unter {tessdata_path}"
            )

        os.environ["TESSDATA_PREFIX"] = str(tessdata_path)

        self.logger.info(f"Tesseract Path {tesseract_exe}")
        self.logger.info(f"Tessdata Path {tessdata_path}")

        # OCR / POPPLER
        poppler_path = Path(poppler_path).resolve()

        if not poppler_path.exists():
            raise FileNotFoundError(
                f"Poppler nicht gefunden unter {poppler_path}"
            )

        self.poppler_path = str(poppler_path)

        self.logger.info(f"Poppler Path {self.poppler_path}")

        # OCR / SETTINGS
        self.language = "deu+eng+fra"

    # OCR / ENTRY
    def extract_text(self, file_path: str) -> str:

        if not file_path:
            self.logger.error("OCR Fehler: file_path ist None oder leer")
            return ""

        file_path_str = str(file_path)

        if not os.path.exists(file_path_str):
            self.logger.error(f"OCR Fehler Datei existiert nicht {file_path_str}")
            return ""

        try:
            if file_path_str.lower().endswith(".pdf"):
                return self._extract_from_pdf(file_path_str)
            else:
                return self._extract_from_image(file_path_str)

        except Exception as e:
            self.logger.error(f"OCR Fehler bei {file_path_str} {e}")
            return ""

    # OCR / PDF
    def _extract_from_pdf(self, file_path: str) -> str:

        self.logger.debug(f"PDF → Image conversion startet: {file_path}")

        try:
            images = convert_from_path(
                file_path,
                poppler_path=self.poppler_path,
                dpi=300
            )
        except Exception as e:
            self.logger.error(f"PDF Konvertierungsfehler bei {file_path} {e}")
            return ""

        self.logger.debug(f"Anzahl Bilder: {len(images)}")

        if not images:
            self.logger.warning("Keine Bilder aus PDF erzeugt")
            return ""

        text_output: List[str] = []

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
                    f"OCR Seitenfehler bei {file_path} Seite {index + 1} {e}"
                )
                continue

        final_text = "\n".join(text_output)

        if not final_text.strip():
            self.logger.warning("Kein OCR Text aus PDF extrahiert")

        return final_text

    # OCR / IMAGE
    def _extract_from_image(self, file_path: str) -> str:

        self.logger.debug(f"OCR Image Verarbeitung: {file_path}")

        try:
            with Image.open(file_path) as img:

                img.thumbnail((3500, 3500))

                text = pytesseract.image_to_string(
                    img,
                    lang=self.language
                )

                if not text or not text.strip():
                    self.logger.warning("Kein OCR Text aus Bild extrahiert")
                    return ""

                return text

        except Exception as e:
            self.logger.error(f"OCR Bildfehler bei {file_path} {e}")
            return ""