from pathlib import Path
from datetime import datetime

from interfaces.logger_service import LoggerService

import logging

class FileLogger(LoggerService):

    def __init__(self, log_directory: Path):

        log_directory = Path(log_directory)
        log_directory.mkdir(parents=True, exist_ok=True)

        # 🔥 Heutiges Datum
        today_str = datetime.now().strftime("%Y-%m-%d")

        log_filename = f"sorterino_logs_{today_str}.log"
        log_path = log_directory / log_filename

        self.logger = logging.getLogger("Sorterino")
        self.logger.setLevel(logging.INFO)

        # Verhindert doppelte Handler bei mehrfacher Initialisierung
        if not self.logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )

            # Datei-Handler
            file_handler = logging.FileHandler(
                filename=str(log_path),
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)

            # CLI-Handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def log(self, message: str) -> None:
        self.logger.info(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)