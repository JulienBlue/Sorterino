from pathlib import Path
from datetime import datetime


class FileLogger:

    # CONFIG / INIT
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "sorterino.log"

    # LOGGING / WRITE
    def _write(self, level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}"

        print(line)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    # LOGGING / PUBLIC
    def info(self, message: str):
        print(message)

    def log(self, message: str):
        self._write("LOG", message)

    def warning(self, message: str):
        print(message)

    def error(self, message: str):
        self._write("ERROR", message)

    def debug(self, message: str):
        print(message)