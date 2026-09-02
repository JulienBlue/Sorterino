import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional


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
        lines.append(f"Sorterino Daily Report - {report['date']}")
        lines.append("")
        lines.append("Zusammenfassung")
        lines.append(f"- Gesamt: {report['summary']['total']}")
        lines.append(f"- Erfolgreich: {report['summary']['success']}")
        lines.append(f"- Manuell: {report['summary']['manual']}")
        lines.append(f"- Fehler: {report['summary']['error']}")
        lines.append("")
        lines.append("Details")
        for item in report["items"]:
            lines.append(
                f"{item['status'].upper():8} | "
                f"{item['original_name']} -> {item['final_name']} | "
                f"{item['target_folder']} | "
                f"{item.get('reason', '-')}"
            )
        return "\n".join(lines)

    def generate_daily_report(self, day: Optional[date] = None) -> Path:
        day = day or date.today()
        events = self._load_events_for_date(day)

        summary = {
            "total": len(events),
            "success": sum(1 for e in events if e.get("status") == "success"),
            "manual": sum(1 for e in events if e.get("status") == "manual"),
            "error": sum(1 for e in events if e.get("status") == "error"),
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

    def get_last_report_date(self) -> Optional[str]:
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_report_date")
        except Exception:
            return None

    def set_last_report_date(self, day: date) -> None:
        data = {"last_report_date": day.isoformat()}
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
