from datetime import datetime
from pathlib import Path
import json
import threading


class FileLogger:

    # CONFIG / INIT
    def __init__(self, log_dir: Path, *, developer_mode=False):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "sorterino.log"
        self.event_file = self.log_dir / "processing_events.jsonl"
        self.developer_mode = bool(developer_mode)
        self._lock = threading.RLock()

    # LOGGING / FORMAT
    def _format(self, level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"

    # LOGGING / FILE WRITE
    def _write_file(self, line: str):
        try:
            with self._lock:
                self._rotate_if_needed()
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            print(f"[ERROR] Logfile konnte nicht geschrieben werden: {e}")

    def _rotate_if_needed(self):
        try:
            if not self.log_file.exists() or self.log_file.stat().st_size < 5 * 1024 * 1024:
                return
            oldest = self.log_dir / "sorterino.log.5"
            if oldest.exists():
                oldest.unlink()
            for index in range(4, 0, -1):
                source = self.log_dir / f"sorterino.log.{index}"
                if source.exists():
                    source.replace(self.log_dir / f"sorterino.log.{index + 1}")
            self.log_file.replace(self.log_dir / "sorterino.log.1")
        except OSError:
            pass

    # LOGGING / PUBLIC

    # 📄 FILE ONLY
    def log(self, message: str):
        self._emit("LOG", message)

    def error(self, message: str):
        self._emit("ERROR", message)

    # 🖥 CONSOLE ONLY
    def info(self, message: str):
        self._emit("INFO", message)

    def warning(self, message: str):
        self._emit("WARNING", message)

    def debug(self, message: str):
        self._emit("DEBUG", message)

    def _emit(self, level: str, message: str):
        line = self._format(level, str(message))
        self._write_file(line)
        if self.developer_mode or level in {"ERROR", "WARNING"}:
            print(line)

    def processing_step(self, operation_id, step, message, **details):
        """Record one structured, secret-free processing step for diagnostics."""
        payload = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "operation_id": str(operation_id or "-"),
            "step": str(step),
            "message": str(message),
            "details": details,
        }
        try:
            with self._lock:
                with open(self.event_file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
        self.debug(f"[{payload['operation_id']}] [{step}] {message}")
