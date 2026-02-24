import logging
import os

from interfaces.logger_service import LoggerService


class FileLogger(LoggerService):

    def __init__(self, log_directory: str = "logs", log_file: str = "sorterino.log"):
        os.makedirs(log_directory, exist_ok=True)
        log_path = os.path.join(log_directory, log_file)

        self.logger = logging.getLogger("Sorterino")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log(self, message: str) -> None:
        self.logger.info(message)
