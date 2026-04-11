import os
import customtkinter as ctk
from tkinter import messagebox

from src.config import Config
from src.reporting import DailyReportManager


class DailyReportWindow(ctk.CTkToplevel):

    def __init__(self, master=None, config=None):
        super().__init__(master)

        self.config = config if config else Config()

        self.title("Daily-Report")
        self.geometry("420x450")

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.create_ui()
        self.load_values()

    def create_ui(self):
        ctk.CTkLabel(self, text="Daily-Report Einstellungen").pack(pady=(16, 8))

        ctk.CTkLabel(self, text="Uhrzeit (HH:MM)").pack(pady=(10, 0))
        self.report_time_entry = ctk.CTkEntry(self, placeholder_text="18:00")
        self.report_time_entry.pack(padx=20, fill="x")

        ctk.CTkButton(self, text="Zeit speichern", command=self.save_report_time).pack(pady=12)
        ctk.CTkButton(self, text="Letzten Report öffnen", command=self.open_last_report).pack(pady=6)

    def load_values(self):
        value = self.config.get("daily_report_time") or "18:00"
        if value:
            self.report_time_entry.insert(0, value)

    def save_report_time(self):
        value = self.report_time_entry.get().strip() or "18:00"
        self.config.set("daily_report_time", value)
        messagebox.showinfo("Erfolg", "Report-Zeit gespeichert")

    def open_last_report(self):
        try:
            reporter = DailyReportManager(self.config.logs_root)
            last_date = reporter.get_last_report_date()
            if not last_date:
                messagebox.showinfo("Info", "Noch kein Daily-Report vorhanden")
                return

            report_path = self.config.logs_root / f"daily_report_{last_date}.txt"
            if report_path.exists():
                os.startfile(report_path)
                return

            messagebox.showinfo("Info", "Letzter Report wurde noch nicht gefunden")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
