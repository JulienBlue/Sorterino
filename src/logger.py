from pathlib import Path
from datetime import datetime


class FileLogger:

    # CONFIG / INIT
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "sorterino.log"

    # LOGGING / FORMAT
    def _format(self, level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"

    # LOGGING / FILE WRITE
    def _write_file(self, line: str):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[ERROR] Logfile konnte nicht geschrieben werden: {e}")

    # LOGGING / PUBLIC

    # 📄 FILE ONLY
    def log(self, message: str):
        line = self._format("LOG", message)
        self._write_file(line)

    def error(self, message: str):
        line = self._format("ERROR", message)
        self._write_file(line)
        print(line)

    # 🖥 CONSOLE ONLY
    def info(self, message: str):
        print(self._format("INFO", message))

    def warning(self, message: str):
        print(self._format("WARNING", message))

    def debug(self, message: str):
        print(self._format("DEBUG", message))
