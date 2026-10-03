import json
from datetime import datetime, date
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Optional


STATUS_LABELS = {
    "success": "Automatisch abgelegt",
    "manual": "Prüfung erforderlich",
    "error": "Nicht verarbeitet",
    "duplicate": "Bereits vorhanden",
    "discarded": "Verworfen",
}

REASON_LABELS = {
    "unsupported_format": "Das Dateiformat wird nicht unterstützt.",
    "exact_duplicate": "Das Dokument ist bereits vorhanden.",
    "extraction_error": "Der Dokumenttext konnte nicht gelesen werden.",
    "extraction_needs_review": "Der Dokumentinhalt muss geprüft werden.",
    "ocr_empty": "Es wurde kein lesbarer Text erkannt.",
    "profile_conflict": "Postfach und Dokumentinhalt passen nicht eindeutig zusammen.",
    "profile_unresolved": "Das passende Profil konnte nicht eindeutig erkannt werden.",
    "profile_person_unresolved": "Die betreffende Person konnte nicht eindeutig erkannt werden.",
    "classify_none": "Die Dokumentart konnte nicht sicher erkannt werden.",
    "classification_low_confidence": "Die Dokumentart wurde nur unsicher erkannt.",
    "invoice_context_review": "Die Zuordnung der Rechnung muss geprüft werden.",
    "missing_required_data": "Wichtige Angaben für die automatische Ablage fehlen.",
    "path_error": "Der vorgesehene Ablageort ist nicht erreichbar.",
    "ok": "",
}


def user_status(item):
    return STATUS_LABELS.get(item.get("status"), "Hinweis")


def user_reason(item):
    reason = str(item.get("reason") or "").strip()
    return REASON_LABELS.get(reason, reason if "_" not in reason else "Das Dokument muss geprüft werden.")


def user_target(item, max_parts=3):
    raw = str(item.get("target_folder") or "").strip()
    if not raw:
        return "Ablageort nicht angegeben"
    path = PureWindowsPath(raw) if "\\" in raw or ":" in raw else Path(raw)
    parts = [part for part in path.parts if part not in {path.anchor, path.root, path.drive}]
    return " › ".join(parts[-max_parts:]) if parts else raw


class DailyReportManager:
    def __init__(self, logs_root: Path):
        self.logs_root = Path(logs_root)
        self.logs_root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.logs_root / "daily_events.jsonl"
        self.reports_dir = self.logs_root / "daily_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.logs_root / "report_state.json"

    def record_event(self, event: dict) -> None:
        payload = dict(event)
        payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))

        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _load_events_for_date(self, day: date) -> list:
        if not self.events_path.exists():
            return []

        day_str = day.isoformat()
        events = []
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                ts = evt.get("timestamp", "")
                if ts.startswith(day_str):
                    events.append(evt)
        return events

    def _format_txt(self, report: dict) -> str:
        lines = []
        lines.append(f"Sorterino Tagesbericht – {report['date']}")
        lines.append("")
        lines.append("Zusammenfassung")
        lines.append(f"- Gesamt: {report['summary']['total']}")
        lines.append(f"- Erfolgreich: {report['summary']['success']}")
        lines.append(f"- Prüfung erforderlich: {report['summary']['manual']}")
        lines.append(f"- Fehler: {report['summary']['error']}")
        successes = [item for item in report["items"] if item.get("status") == "success"]
        attention = [item for item in report["items"] if item.get("status") in {"manual", "error"}]
        if successes:
            lines.extend(("", "Automatisch abgelegt"))
            for item in successes:
                name = item.get("final_name") or item.get("original_name") or "Dokument"
                lines.append(f"- {name} -> {user_target(item)}")
        if attention:
            lines.extend(("", "Handlungsbedarf"))
            for item in attention:
                name = item.get("final_name") or item.get("original_name") or "Dokument"
                lines.append(f"- {name}: {user_reason(item)}")
        return "\n".join(lines)

    def generate_daily_report(self, day: Optional[date] = None) -> Path:
        day = day or date.today()
        events = self._load_events_for_date(day)

        summary = {
            "total": len(events),
            "success": sum(1 for e in events if e.get("status") == "success"),
            "manual": sum(1 for e in events if e.get("status") == "manual"),
            "error": sum(1 for e in events if e.get("status") == "error"),
            "duplicate": sum(1 for e in events if e.get("status") == "duplicate"),
            "discarded": sum(1 for e in events if e.get("status") == "discarded"),
        }

        report = {
            "date": day.isoformat(),
            "summary": summary,
            "items": [
                {
                    "timestamp": e.get("timestamp"),
                    "status": e.get("status"),
                    "reason": e.get("reason"),
                    "original_name": e.get("original_name"),
                    "final_name": e.get("final_name"),
                    "target_folder": e.get("target_folder"),
                    "profile_id": e.get("profile_id"),
                    "person_ids": e.get("person_ids", []),
                }
                for e in events
            ],
        }

        json_path = self.reports_dir / f"{day.isoformat()}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        txt_path = self.logs_root / f"daily_report_{day.isoformat()}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self._format_txt(report))

        return json_path

    def load_report(self, day: Optional[date] = None) -> dict:
        day = day or date.today()
        path = self.reports_dir / f"{day.isoformat()}.json"
        if not path.exists():
            self.generate_daily_report(day)
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def get_last_report_date(self) -> Optional[str]:
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_report_date")
        except Exception:
            return None

    def get_latest_report_date(self) -> Optional[str]:
        """Return the newest generated report date, independent of scheduling state."""
        try:
            candidates = sorted(self.reports_dir.glob("????-??-??.json"), reverse=True)
        except OSError:
            return None
        return candidates[0].stem if candidates else None

    def set_last_report_date(self, day: date) -> None:
        data = {"last_report_date": day.isoformat()}
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
