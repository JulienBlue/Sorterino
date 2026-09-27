"""Human-readable activity report view."""

import customtkinter as ctk

from src.gui.appearance import SECONDARY_TEXT
from src.gui.embedded import EmbeddedPage
from src.reporting import DailyReportManager


STATUS_LABELS = {
    "success": "Erfolgreich abgelegt",
    "manual": "Prüfung erforderlich",
    "error": "Fehler",
    "duplicate": "Duplikat",
    "discarded": "Verworfen",
}


class ActivityReportPage(EmbeddedPage):
    help_context = "settings"

    def __init__(self, master, config, report_date=None):
        super().__init__(master)
        reporter = DailyReportManager(config.logs_root)
        report_date = report_date or reporter.get_latest_report_date()
        ctk.CTkLabel(self, text="Aktivitätsbericht", font=("Arial", 24, "bold")).pack(
            anchor="w", padx=20, pady=(18, 2)
        )
        if not report_date:
            ctk.CTkLabel(self, text="Noch kein Bericht vorhanden.").pack(anchor="w", padx=20, pady=20)
            return
        from datetime import date
        report = reporter.load_report(date.fromisoformat(report_date))
        ctk.CTkLabel(self, text=report_date, text_color=SECONDARY_TEXT).pack(anchor="w", padx=20)
        summary = report.get("summary", {})
        summary_row = ctk.CTkFrame(self, fg_color="transparent")
        summary_row.pack(fill="x", padx=14, pady=14)
        for label, key in (
            ("Gesamt", "total"), ("Erfolgreich", "success"),
            ("Zu prüfen", "manual"), ("Fehler", "error"),
        ):
            card = ctk.CTkFrame(summary_row, border_width=1, border_color=("gray78", "gray31"))
            card.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkLabel(card, text=str(summary.get(key, 0)), font=("Arial", 25, "bold")).pack(pady=(13, 0))
            ctk.CTkLabel(card, text=label, text_color=SECONDARY_TEXT).pack(pady=(0, 13))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        items = list(report.get("items", []))
        items.sort(key=lambda item: {"manual": 0, "error": 1, "success": 2}.get(item.get("status"), 3))
        for item in items:
            row = ctk.CTkFrame(body, border_width=1, border_color=("gray78", "gray31"))
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(
                row, text=STATUS_LABELS.get(item.get("status"), item.get("status") or "Aktivität"),
                font=("Arial", 14, "bold"),
            ).pack(anchor="w", padx=14, pady=(10, 2))
            name = item.get("final_name") or item.get("original_name") or "Dokument"
            ctk.CTkLabel(row, text=name, anchor="w").pack(anchor="w", padx=14)
            detail = item.get("reason") or item.get("target_folder") or ""
            if detail:
                ctk.CTkLabel(row, text=str(detail), text_color=SECONDARY_TEXT, wraplength=760, justify="left").pack(anchor="w", padx=14, pady=(2, 10))

