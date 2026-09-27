from datetime import date
import os
import queue
import subprocess
import sys
import threading
from tkinter import messagebox

import customtkinter as ctk

from src.gui.appearance import (
    APPEARANCE_LABELS,
    CONTROL_HOVER,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    appearance_label,
)
from src.profile_service import ProfileService, ProfileValidationError
from src.reporting import DailyReportManager
from src.report_mailer import PROVIDER_SMTP, deliver_daily_report, normalize_recipients
from src.mail_auth import store_password
from src.maintenance import cleanup_rebuildable_state
from src.updates import UpdateError, UpdateService, launch_installer_after_exit
from src.version import APP_VERSION, LATEST_CHANGELOG


SETTINGS_CATEGORIES = (
    ("general", "Allgemein", "Darstellung Autostart Taskleiste Fenster Hintergrund"),
    ("automation", "Automatisierung", "automatisch Verarbeitung Eingang Warteschlange Hintergrund"),
    ("reports", "Berichte", "Tagesbericht Daily Report Uhrzeit E-Mail Empfänger Absender Versand"),
    ("storage", "Speicherorte", "Dokumentenspeicher Eingang Ordner Profile Archiv Backup"),
    ("recognition", "Dokumente und Erkennung", "OCR PDF Word DOCX DOC ODT RTF TXT Pages JPG PNG TIFF WebP HEIC EML MSG"),
    ("email", "E-Mail-Import", "Postfach Mail OAuth IMAP Zeitraum Import Profile"),
    ("data", "Daten und Sicherheit", "Datenbank AppData Datenschutz Zugangsdaten Sicherung"),
    ("advanced", "Erweitert", "Protokoll Logs technische Konfiguration JSON Diagnose"),
    ("about", "Über Sorterino", "Version Hilfe Informationen Update Aktualisierung Beta Stabil"),
)


def matching_settings_category(query):
    """Return the first settings category matching a human search phrase."""
    words = [word.casefold() for word in str(query or "").split() if word.strip()]
    if not words:
        return None
    for key, label, keywords in SETTINGS_CATEGORIES:
        haystack = f"{label} {keywords}".casefold()
        if all(word in haystack for word in words):
            return key
    return None


class SettingsPage(ctk.CTkFrame):
    """Searchable, category-based application settings."""

    def __init__(self, parent, owner):
        super().__init__(parent, fg_color="transparent")
        self.owner = owner
        self.config = owner.config
        self.active_category = "general"
        self.category_buttons = {}
        self.search_after = None
        self._update_queue = queue.Queue()
        self._update_release = None
        self._update_poll_after = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        navigation = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="transparent")
        navigation.grid(row=0, column=0, sticky="nsew", padx=(24, 10), pady=22)
        navigation.grid_propagate(False)
        ctk.CTkLabel(
            navigation, text="Einstellungen", font=("Arial", 23, "bold")
        ).pack(anchor="w", padx=8, pady=(4, 18))
        for key, label, _keywords in SETTINGS_CATEGORIES:
            button = ctk.CTkButton(
                navigation,
                text=label,
                height=38,
                anchor="w",
                fg_color="transparent",
                hover_color=CONTROL_HOVER,
                text_color=PRIMARY_TEXT,
                command=lambda selected=key: self.show_category(selected),
            )
            button.pack(fill="x", pady=2)
            self.category_buttons[key] = button

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 30), pady=22)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._search_changed)
        search = ctk.CTkEntry(
            right,
            textvariable=self.search_var,
            placeholder_text="In Einstellungen suchen",
            height=38,
        )
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.search_hint = ctk.CTkLabel(
            right, text="", text_color=SECONDARY_TEXT, anchor="w"
        )
        self.search_hint.grid(row=1, column=0, sticky="ew")
        self.body = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        self.body._scrollbar.configure(width=10)
        self.show_category(self.active_category)

    def _search_changed(self, *_args):
        if self.search_after:
            self.after_cancel(self.search_after)
        self.search_after = self.after(180, self._apply_search)

    def _apply_search(self):
        self.search_after = None
        query = self.search_var.get().strip()
        if not query:
            self.search_hint.configure(text="")
            return
        category = matching_settings_category(query)
        if category:
            label = next(item[1] for item in SETTINGS_CATEGORIES if item[0] == category)
            self.search_hint.configure(text=f"Passender Bereich: {label}")
            self.show_category(category)
        else:
            self.search_hint.configure(text="Keine passende Einstellung gefunden.")

    def show_category(self, category):
        if category not in {item[0] for item in SETTINGS_CATEGORIES}:
            category = "general"
        self.active_category = category
        for key, button in self.category_buttons.items():
            button.configure(
                fg_color=self.owner.SIDEBAR_ACTIVE if key == category else "transparent"
            )
        for child in self.body.winfo_children():
            child.destroy()
        builders = {
            "general": self._build_general,
            "automation": self._build_automation,
            "reports": self._build_reports,
            "storage": self._build_storage,
            "recognition": self._build_recognition,
            "email": self._build_email,
            "data": self._build_data,
            "advanced": self._build_advanced,
            "about": self._build_about,
        }
        builders[category]()

    def _heading(self, title, subtitle):
        ctk.CTkLabel(self.body, text=title, font=("Arial", 24, "bold")).pack(
            anchor="w", padx=4, pady=(2, 3)
        )
        ctk.CTkLabel(
            self.body,
            text=subtitle,
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=720,
        ).pack(anchor="w", padx=4, pady=(0, 16))

    def _card(self, title, description=""):
        card = ctk.CTkFrame(
            self.body,
            border_width=1,
            border_color=("gray78", "gray31"),
        )
        card.pack(fill="x", padx=4, pady=(0, 14))
        ctk.CTkLabel(card, text=title, font=("Arial", 17, "bold")).pack(
            anchor="w", padx=18, pady=(16, 2)
        )
        if description:
            ctk.CTkLabel(
                card,
                text=description,
                text_color=SECONDARY_TEXT,
                justify="left",
                wraplength=690,
            ).pack(anchor="w", padx=18, pady=(0, 10))
        return card

    @staticmethod
    def _actions(card):
        frame = ctk.CTkFrame(card, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=(5, 16))
        return frame

    @staticmethod
    def _status_row(card, label, value, ready=True):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(row, text=label).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            text_color=("#2E7D32", "#81C784") if ready else ("#9A6700", "#F0B429"),
        ).pack(side="right")

    def _build_general(self):
        self._heading("Allgemein", "Darstellung und Verhalten der Anwendung")
        card = self._card("Erscheinungsbild")
        row = self._actions(card)
        ctk.CTkLabel(row, text="Darstellung").pack(side="left")
        self.owner.appearance_menu = ctk.CTkOptionMenu(
            row,
            values=list(APPEARANCE_LABELS),
            command=self.owner._change_appearance,
            width=170,
        )
        self.owner.appearance_menu.set(
            appearance_label(self.config.get("appearance_mode", "system"))
        )
        self.owner.appearance_menu.pack(side="right")

        card = self._card(
            "Windows und Taskleiste",
            "Lege fest, wie Sorterino beim Anmelden und Schließen reagiert.",
        )
        self.owner.autostart_switch = ctk.CTkSwitch(
            card,
            text="Sorterino mit Windows starten",
            command=self.owner._toggle_autostart,
        )
        self.owner.autostart_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("autostart"):
            self.owner.autostart_switch.select()
        notice = ctk.CTkSwitch(
            card,
            text="Hinweis beim Schließen in den Infobereich anzeigen",
            command=lambda: self.config.set(
                "hide_close_to_tray_notice", not bool(notice.get())
            ),
        )
        notice.pack(anchor="w", padx=18, pady=(8, 18))
        if not self.config.get("hide_close_to_tray_notice", False):
            notice.select()

    def _build_automation(self):
        self._heading(
            "Automatisierung",
            "Automatische Verarbeitung neuer Dokumente",
        )
        card = self._card(
            "Dokumentverarbeitung",
            "Neue Dokumente werden im Hintergrund erkannt und verarbeitet, solange Sorterino läuft.",
        )
        self.owner.auto_switch = ctk.CTkSwitch(
            card,
            text="Dokumente automatisch verarbeiten",
            command=self.owner._toggle_auto,
        )
        self.owner.auto_switch.pack(anchor="w", padx=18, pady=(8, 18))
        if self.config.get("auto_mode"):
            self.owner.auto_switch.select()

        card = self._card(
            "E-Mail-Abruf",
            "Verknüpfte Postfächer werden zusammen mit der automatischen Dokumentverarbeitung geprüft. Bereits gelesene Nachrichten bleiben über den gespeicherten Importstand berücksichtigt.",
        )
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def _build_reports(self):
        self._heading("Berichte", "Aktivitätsübersicht, Zeitplan und sicherer E-Mail-Versand")
        card = self._card(
            "Tagesbericht",
            "Erfasst erfolgreiche Ablagen, Prüfungen und Fehler. Ein verpasster Termin wird beim nächsten Programmstart nachgeholt.",
        )
        self.report_switch = ctk.CTkSwitch(
            card, text="Tagesbericht automatisch erstellen", command=self._toggle_daily_report
        )
        self.report_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("daily_report_enabled", True):
            self.report_switch.select()
        time_row = ctk.CTkFrame(card, fg_color="transparent")
        time_row.pack(fill="x", padx=18, pady=8)
        ctk.CTkLabel(time_row, text="Uhrzeit (HH:MM)").pack(side="left")
        self.report_time = ctk.CTkEntry(time_row, width=90)
        self.report_time.insert(0, self.config.get("daily_report_time") or "18:00")
        self.report_time.pack(side="right")
        self.report_time.bind("<Return>", lambda _event: self._save_report_time())
        self.report_time.bind("<FocusOut>", lambda _event: self._save_report_time(False))
        reporter = DailyReportManager(self.config.logs_root)
        last = reporter.get_latest_report_date() or "Noch kein Bericht erstellt"
        ctk.CTkLabel(card, text=f"Letzter Bericht: {last}", text_color=SECONDARY_TEXT).pack(
            anchor="w", padx=18, pady=(4, 2)
        )
        actions = self._actions(card)
        ctk.CTkButton(actions, text="Uhrzeit speichern", command=self._save_report_time).pack(side="left")
        ctk.CTkButton(actions, text="Jetzt erstellen", command=self._generate_report).pack(side="left", padx=8)
        latest_report = self.config.logs_root / f"daily_report_{last}.txt"
        if last != "Noch kein Bericht erstellt" and latest_report.exists():
            ctk.CTkButton(actions, text="Letzten Bericht anzeigen", command=self._open_activity_report).pack(side="left")
        ctk.CTkButton(
            actions, text="Berichtsordner öffnen", fg_color="transparent", border_width=1,
            text_color=PRIMARY_TEXT, hover_color=CONTROL_HOVER,
            command=lambda: self.owner._open_path(self.config.logs_root),
        ).pack(side="left", padx=(8, 0))

        card = self._card(
            "E-Mail-Versand",
            "Berichte werden je Empfänger einzeln und ausschließlich über TLS versendet. Zugangsdaten bleiben im Windows-Anmeldespeicher.",
        )
        self.report_email_switch = ctk.CTkSwitch(card, text="Tagesbericht per E-Mail versenden")
        self.report_email_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("daily_report_email_enabled", False):
            self.report_email_switch.select()
        ctk.CTkLabel(card, text="Empfänger (mit Komma, Semikolon oder Zeilenumbruch trennen)").pack(anchor="w", padx=18, pady=(8, 2))
        self.report_recipients = ctk.CTkEntry(card)
        self.report_recipients.insert(0, ", ".join(self.config.get("daily_report_recipients", [])))
        self.report_recipients.pack(fill="x", padx=18, pady=(0, 8))

        self._report_accounts = ProfileService(self.config).list_email_accounts()
        self._report_account_labels = {
            f"{account.get('label') or account.get('username')} · {account.get('username')}": account.get("id")
            for account in self._report_accounts
        }
        values = list(self._report_account_labels) or ["Kein Postfach eingerichtet"]
        ctk.CTkLabel(card, text="Absender aus verknüpften Postfächern").pack(anchor="w", padx=18, pady=(8, 2))
        self.report_sender_menu = ctk.CTkOptionMenu(card, values=values)
        selected_id = self.config.get("daily_report_sender_account_id", "")
        selected_label = next((label for label, account_id in self._report_account_labels.items() if account_id == selected_id), values[0])
        self.report_sender_menu.set(selected_label)
        self.report_sender_menu.pack(fill="x", padx=18, pady=(0, 8))

        self.report_content_menu = ctk.CTkOptionMenu(card, values=["Kompakt", "Standard"])
        self.report_content_menu.set("Standard" if self.config.get("daily_report_content_level") == "standard" else "Kompakt")
        self.report_content_menu.pack(anchor="w", padx=18, pady=8)
        self.report_activity_only = ctk.CTkSwitch(card, text="Nur senden, wenn Aktivitäten vorhanden sind")
        self.report_activity_only.pack(anchor="w", padx=18, pady=6)
        if self.config.get("daily_report_only_with_activity", True):
            self.report_activity_only.select()
        self.report_attention_only = ctk.CTkSwitch(card, text="Nur senden, wenn Handlungsbedarf besteht")
        self.report_attention_only.pack(anchor="w", padx=18, pady=6)
        if self.config.get("daily_report_only_with_attention", False):
            self.report_attention_only.select()
        actions = self._actions(card)
        ctk.CTkButton(actions, text="Versand speichern", command=self._save_report_delivery).pack(side="left")
        ctk.CTkButton(actions, text="Testbericht senden", command=self._send_test_report).pack(side="left", padx=8)

        card = self._card(
            "Eigenes Berichtskonto",
            "Optional kann ein separates SMTP-Konto nur für Berichte genutzt werden. Geeignet für Apple, GMX, WEB.DE, IONOS und eigene Mailserver.",
        )
        self.report_dedicated_switch = ctk.CTkSwitch(card, text="Separates Berichtskonto verwenden")
        self.report_dedicated_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("daily_report_sender_mode") == "dedicated":
            self.report_dedicated_switch.select()
        dedicated = dict(self.config.get("daily_report_sender") or {})
        provider_labels = {
            "Anderer Anbieter": "custom", "Apple / iCloud": "apple", "GMX": "gmx",
            "WEB.DE": "webde", "IONOS": "ionos",
        }
        self._report_provider_labels = provider_labels
        self.report_provider_menu = ctk.CTkOptionMenu(
            card, values=list(provider_labels), command=self._report_provider_changed
        )
        current_provider = dedicated.get("provider", "custom")
        self.report_provider_menu.set(next((label for label, value in provider_labels.items() if value == current_provider), "Anderer Anbieter"))
        self.report_provider_menu.pack(fill="x", padx=18, pady=5)
        self.report_dedicated_email = ctk.CTkEntry(card, placeholder_text="Absenderadresse")
        self.report_dedicated_email.insert(0, dedicated.get("email", ""))
        self.report_dedicated_email.pack(fill="x", padx=18, pady=5)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=5)
        self.report_smtp_server = ctk.CTkEntry(row, placeholder_text="SMTP-Server")
        self.report_smtp_server.insert(0, dedicated.get("smtp_server", ""))
        self.report_smtp_server.pack(side="left", fill="x", expand=True)
        self.report_smtp_port = ctk.CTkEntry(row, width=90, placeholder_text="Port")
        self.report_smtp_port.insert(0, str(dedicated.get("smtp_port", 587)))
        self.report_smtp_port.pack(side="left", padx=(8, 0))
        self.report_smtp_password = ctk.CTkEntry(card, placeholder_text="App-Passwort", show="•")
        self.report_smtp_password.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(card, text="Das Passwort wird nicht in der Einstellungsdatei gespeichert.", text_color=SECONDARY_TEXT).pack(anchor="w", padx=18, pady=(2, 8))

    def _save_report_delivery(self, show_confirmation=True):
        recipients = normalize_recipients(self.report_recipients.get())
        if self.report_email_switch.get() and not recipients:
            messagebox.showwarning("Empfänger fehlt", "Bitte gib mindestens eine gültige E-Mail-Adresse ein.", parent=self.owner)
            return False
        mode = "dedicated" if self.report_dedicated_switch.get() else "existing"
        account_id = self._report_account_labels.get(self.report_sender_menu.get(), "")
        if self.report_email_switch.get() and mode == "existing" and not account_id:
            messagebox.showwarning(
                "Absender fehlt",
                "Bitte verknüpfe ein Postfach oder richte ein separates Berichtskonto ein.",
                parent=self.owner,
            )
            return False
        try:
            port = int(self.report_smtp_port.get() or 587)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ungültiger Port", "Bitte gib einen gültigen SMTP-Port ein.", parent=self.owner)
            return False
        dedicated = {
            "id": "report_sender",
            "provider": self._report_provider_labels.get(self.report_provider_menu.get(), "custom"),
            "auth_method": "app_password",
            "email": self.report_dedicated_email.get().strip(),
            "username": self.report_dedicated_email.get().strip(),
            "smtp_server": self.report_smtp_server.get().strip(), "smtp_port": port,
        }
        if mode == "dedicated" and (not dedicated["email"] or not dedicated["smtp_server"]):
            messagebox.showwarning("Absender fehlt", "Bitte richte das separate Berichtskonto vollständig ein.", parent=self.owner)
            return False
        password = self.report_smtp_password.get().strip()
        if password:
            store_password("report_sender", password)
        self.config.set("daily_report_email_enabled", bool(self.report_email_switch.get()))
        self.config.set("daily_report_recipients", recipients)
        self.config.set("daily_report_sender_mode", mode)
        self.config.set("daily_report_sender_account_id", account_id)
        self.config.set("daily_report_sender", dedicated)
        self.config.set("daily_report_content_level", "standard" if self.report_content_menu.get() == "Standard" else "compact")
        self.config.set("daily_report_only_with_activity", bool(self.report_activity_only.get()))
        self.config.set("daily_report_only_with_attention", bool(self.report_attention_only.get()))
        if show_confirmation:
            self.owner._show_success_banner("Berichtsversand gespeichert.")
        return True

    def _report_provider_changed(self, label):
        provider = self._report_provider_labels.get(label, "custom")
        server, port = PROVIDER_SMTP.get(provider, ("", 587))
        if server:
            self.report_smtp_server.delete(0, "end")
            self.report_smtp_server.insert(0, server)
            self.report_smtp_port.delete(0, "end")
            self.report_smtp_port.insert(0, str(port))

    def _send_test_report(self):
        if not self._save_report_delivery(False):
            return
        self.owner._show_success_banner("Testbericht wird versendet …")
        def worker():
            try:
                result = deliver_daily_report(self.config, date.today(), force=True)
                message = f"Testbericht versendet: {result.get('sent', 0)} erfolgreich, {result.get('failed', 0)} fehlgeschlagen."
                self.after(0, lambda: self.owner._show_success_banner(message))
            except Exception as exc:
                self.after(0, lambda error=str(exc): messagebox.showerror("Versand fehlgeschlagen", error, parent=self.owner))
        threading.Thread(target=worker, daemon=True).start()

    def _toggle_daily_report(self):
        self.config.set("daily_report_enabled", bool(self.report_switch.get()))

    def _open_activity_report(self):
        from src.gui.report_window import ActivityReportPage
        self.owner.open_view(
            lambda parent: ActivityReportPage(parent, self.config),
            "settings",
        )

    def _save_report_time(self, show_confirmation=True):
        value = self.report_time.get().strip()
        try:
            hour, minute = (int(part) for part in value.split(":"))
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
        except (ValueError, TypeError):
            if show_confirmation:
                messagebox.showwarning(
                    "Ungültige Uhrzeit",
                    "Bitte gib die Uhrzeit im Format HH:MM ein, zum Beispiel 18:00.",
                    parent=self.owner,
                )
            return False
        normalized = f"{hour:02d}:{minute:02d}"
        self.report_time.delete(0, "end")
        self.report_time.insert(0, normalized)
        self.config.set("daily_report_time", normalized)
        if show_confirmation:
            self.owner._show_success_banner("Uhrzeit für den Tagesbericht gespeichert.")
        return True

    def _generate_report(self):
        try:
            reporter = DailyReportManager(self.config.logs_root)
            report_path = reporter.generate_daily_report(date.today())
        except OSError as exc:
            messagebox.showerror("Bericht nicht erstellt", str(exc), parent=self.owner)
            return
        self.owner._show_success_banner(f"Tagesbericht erstellt: {report_path.name}")
        self.show_category("automation")

    def _build_storage(self):
        self._heading("Speicherorte", "Eingang, Archive und profilspezifische Ablagen")
        card = self._card(
            "Standard-Dokumentenspeicher",
            str(self.config.get("user_path") or "Noch nicht eingerichtet"),
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Speicherort auswählen",
            command=self.owner._choose_global_storage,
        ).pack(side="left")
        card = self._card("Gemeinsamer Eingangsordner", str(self.config.incoming_root))
        actions = self._actions(card)
        ctk.CTkButton(
            actions, text="Ordner öffnen", command=self.owner._open_incoming
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Ordner ändern",
            command=self.owner._choose_incoming_storage,
        ).pack(side="left", padx=8)
        card = self._card(
            "Profile und Backups",
            "Eigene Speicherorte werden pro Profil gepflegt. Backups liegen zentral in „Sorterino - Backups“ und sind dort nach Profilen getrennt.",
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Profile verwalten",
            command=lambda: self.owner.show_page("profiles"),
        ).pack(side="left")

    def _build_recognition(self):
        self._heading(
            "Dokumente und Erkennung",
            "Unterstützte Dateitypen und Verfügbarkeit der Texterkennung",
        )
        tess_ready = bool(
            getattr(self.config, "tesseract_path", None)
            and self.config.tesseract_path.exists()
        )
        poppler_ready = bool(
            getattr(self.config, "poppler_path", None)
            and self.config.poppler_path.exists()
        )
        try:
            from pillow_heif import register_heif_opener as heif_opener
            heic_ready = bool(heif_opener)
        except ImportError:
            heic_ready = False
        card = self._card(
            "Dateiformate",
            "Nicht vollständig verfügbare Formate werden nicht still verworfen, sondern zur Prüfung zurückgegeben.",
        )
        states = (
            ("PDF-Dateien", "PDF und Scans", tess_ready and poppler_ready),
            ("Textdokumente", "Word, ODT, RTF, TXT und Pages", True),
            ("Bilddateien", "JPG, PNG, TIFF, WebP, HEIC und HEIF", tess_ready and heic_ready),
            ("E-Mail-Dateien", "EML und MSG", True),
        )
        for title, formats, ready in states:
            self._status_row(
                card,
                f"{title} · {formats}",
                "Bereit" if ready else "Teilweise verfügbar",
                ready,
            )
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def _build_email(self):
        self._heading("E-Mail-Import", "Verknüpfte Postfächer und Importregeln")
        try:
            accounts = ProfileService(self.config).list_email_accounts()
        except ProfileValidationError:
            accounts = []
        enabled = sum(1 for account in accounts if account.get("enabled", True))
        card = self._card(
            "Verknüpfte Postfächer",
            f"{len(accounts)} eingerichtet, davon {enabled} aktiv. Zugangstoken werden geschützt im Windows-Anmeldespeicher abgelegt.",
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Postfächer in Profilen verwalten",
            command=lambda: self.owner.show_page("profiles"),
        ).pack(side="left")
        card = self._card(
            "Importverhalten",
            "Zeitraum, Anbieter und Zielprofil werden je Postfach eingestellt. Bereits gelesene E-Mails werden über den gespeicherten Importstand zuverlässig berücksichtigt.",
        )
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def _build_data(self):
        self._heading("Daten und Sicherheit", "Lokale Programmdaten und geschützte Anmeldedaten")
        card = self._card(
            "Lokale Daten",
            "Sorterino speichert Einstellungen, Status, Datenbank und Protokolle lokal im Benutzerprofil.",
        )
        database_ready = self.config.database_path.exists()
        self._status_row(
            card,
            "Datenbank",
            "Bereit" if database_ready else "Wird bei Bedarf angelegt",
            True,
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Programmdaten öffnen",
            command=lambda: self.owner._open_path(self.config.app_root),
        ).pack(side="left")
        card = self._card(
            "Anmeldedaten",
            "OAuth-Tokens und Passwörter gehören nicht in die Einstellungsdatei. Sorterino nutzt dafür den geschützten Anmeldespeicher des Betriebssystems.",
        )
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def _build_advanced(self):
        self._heading("Erweitert", "Diagnose und technische Konfiguration")
        card = self._card(
            "Diagnose",
            "Das Protokoll hilft bei fehlgeschlagenen Importen und nicht erkannten Dokumenten.",
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions, text="Protokoll anzeigen", command=self.owner._open_logs
        ).pack(side="left")
        card = self._card(
            "Entwicklermodus",
            "Öffnet eine getrennte Live-Konsole mit Verarbeitungsschritten. Sie verändert weder Klassifikation noch Sicherheitsprüfungen.",
        )
        self.developer_switch = ctk.CTkSwitch(
            card, text="Entwicklermodus aktivieren", command=self._toggle_developer_mode
        )
        self.developer_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("developer_mode", False):
            self.developer_switch.select()
        self.developer_autostart_switch = ctk.CTkSwitch(
            card,
            text="Entwicklerkonsole beim Programmstart öffnen",
            command=lambda: self.config.set(
                "developer_console_autostart", bool(self.developer_autostart_switch.get())
            ),
        )
        self.developer_autostart_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("developer_console_autostart", True):
            self.developer_autostart_switch.select()
        actions = self._actions(card)
        ctk.CTkButton(
            actions, text="Entwicklerkonsole öffnen", command=self._open_developer_console
        ).pack(side="left")
        ctk.CTkButton(
            actions, text="Logordner öffnen", command=lambda: self.owner._open_path(self.config.logs_root)
        ).pack(side="left", padx=8)
        card = self._card(
            "Technische Konfiguration",
            "Direkter Zugriff auf Regeln und JSON-Einstellungen. Änderungen wirken unmittelbar und sind für erfahrene Nutzer gedacht.",
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Technische Konfiguration öffnen",
            command=self.owner._open_advanced_settings,
        ).pack(side="left")
        card = self._card(
            "Lokale Laufzeitdaten zurücksetzen",
            (
                "Entfernt Protokolle, Tagesberichte, heruntergeladene Updates, "
                "Prüfvorschläge, den E-Mail-Importstand sowie die technische "
                "Verarbeitungs- und Duplikathistorie. "
                "Profile, Personen, Einstellungen, Postfach-Zugangsdaten, OAuth-Clients, "
                "und Dokumente bleiben erhalten."
            ),
        )
        actions = self._actions(card)
        ctk.CTkButton(
            actions,
            text="Laufzeitdaten bereinigen",
            fg_color="#A33A3A",
            hover_color="#7F2D2D",
            command=self._cleanup_runtime_data,
        ).pack(side="left")

    def _toggle_developer_mode(self):
        enabled = bool(self.developer_switch.get())
        self.config.set("developer_mode", enabled)
        if enabled:
            self._open_developer_console()
            self.owner._show_success_banner("Entwicklermodus aktiviert.")
        else:
            self.owner._show_success_banner("Entwicklermodus deaktiviert.")

    def _open_developer_console(self):
        try:
            if getattr(sys, "frozen", False):
                command = [sys.executable, "--developer-console"]
            else:
                command = [sys.executable, "-m", "src.gui.app", "--developer-console"]
            subprocess.Popen(command, cwd=os.getcwd())
        except OSError as exc:
            messagebox.showerror("Konsole nicht geöffnet", str(exc), parent=self.owner)

    def _cleanup_runtime_data(self):
        confirmed = messagebox.askyesno(
            "Laufzeitdaten bereinigen",
            (
                "Sorterino entfernt jetzt:\n\n"
                "• Protokolle und Tagesberichte\n"
                "• heruntergeladene Update-Dateien\n"
                "• automatisch erzeugte Prüfvorschläge\n"
                "• den E-Mail-Importstand\n"
                "• Verarbeitungs-, Berichts- und Duplikathistorie\n\n"
                "Erhalten bleiben Profile, Personen, Einstellungen, OAuth-Clients, "
                "geschützte Zugangsdaten und sämtliche Dokumente. Beim nächsten Lauf "
                "werden E-Mails innerhalb des je Postfach eingestellten Zeitraums erneut geprüft.\n\n"
                "Sorterino wird danach beendet. Wirklich fortfahren?"
            ),
            parent=self.owner,
        )
        if not confirmed:
            return
        try:
            cleanup_rebuildable_state(self.config)
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Bereinigung fehlgeschlagen",
                f"Die Laufzeitdaten wurden nicht vollständig bereinigt:\n\n{exc}",
                parent=self.owner,
            )
            return
        messagebox.showinfo(
            "Bereinigung abgeschlossen",
            "Die Laufzeitdaten wurden bereinigt. Sorterino wird jetzt beendet und legt sie beim nächsten Start neu an.",
            parent=self.owner,
        )
        self.owner.exit_application()

    def _build_about(self):
        self._heading("Über Sorterino", "Programminformationen und Aktualisierungen")
        card = self._card(
            f"Sorterino v{APP_VERSION}",
            "Dokumente lokal erkennen, zuordnen und nachvollziehbar ablegen.",
        )
        ctk.CTkLabel(
            card,
            text="Letzte Änderungen",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=18, pady=(8, 3))
        ctk.CTkLabel(
            card,
            text=LATEST_CHANGELOG,
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=690,
        ).pack(anchor="w", padx=18, pady=(0, 16))

        card = self._card(
            "Softwareaktualisierung",
            "Sorterino prüft ausschließlich offizielle GitHub-Releases. Tesseract und Poppler werden nur zusammen mit einer getesteten Sorterino-Version aktualisiert.",
        )
        channel_row = ctk.CTkFrame(card, fg_color="transparent")
        channel_row.pack(fill="x", padx=18, pady=(4, 8))
        ctk.CTkLabel(channel_row, text="Updatekanal").pack(side="left")
        self.update_channel_menu = ctk.CTkOptionMenu(
            channel_row,
            values=["Beta", "Stabil"],
            width=150,
            command=self._set_update_channel,
        )
        self.update_channel_menu.set(
            "Stabil" if self.config.get("update_channel", "beta") == "stable" else "Beta"
        )
        self.update_channel_menu.pack(side="right")

        self.automatic_update_switch = ctk.CTkSwitch(
            card,
            text="Beim Programmstart nach Updates suchen",
            command=self._toggle_automatic_update_checks,
        )
        self.automatic_update_switch.pack(anchor="w", padx=18, pady=8)
        if self.config.get("automatic_update_checks", True):
            self.automatic_update_switch.select()

        self.update_status_label = ctk.CTkLabel(
            card,
            text=self._initial_update_status(),
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=690,
        )
        self.update_status_label.pack(anchor="w", padx=18, pady=(4, 6))
        self.update_notes_label = ctk.CTkLabel(
            card,
            text="",
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=690,
        )
        self.update_notes_label.pack(anchor="w", padx=18)
        actions = self._actions(card)
        self.update_button = ctk.CTkButton(
            actions,
            text="Nach Updates suchen",
            command=self._start_update_check,
        )
        self.update_button.pack(side="left")
        ctk.CTkLabel(
            card,
            text=(
                "Hinweis: Die kostenlose Beta ist noch nicht mit einer verifizierten "
                "Windows-Herausgebersignatur versehen. Downloads werden deshalb über "
                "GitHub und SHA-256 geprüft."
            ),
            text_color=("#9A6700", "#F0B429"),
            justify="left",
            wraplength=690,
        ).pack(anchor="w", padx=18, pady=(0, 16))

    def _initial_update_status(self):
        last_check = str(self.config.get("last_update_check", "") or "").strip()
        return f"Installiert: {APP_VERSION} · Zuletzt geprüft: {last_check or 'noch nie'}"

    def _set_update_channel(self, label):
        self.config.set("update_channel", "stable" if label == "Stabil" else "beta")
        self._update_release = None
        self.update_button.configure(text="Nach Updates suchen", command=self._start_update_check)

    def _toggle_automatic_update_checks(self):
        self.config.set("automatic_update_checks", bool(self.automatic_update_switch.get()))

    def _start_update_check(self):
        if getattr(self, "update_button", None):
            self.update_button.configure(state="disabled", text="Prüfe …")
            self.update_status_label.configure(text="GitHub-Releases werden geprüft …")
            self.update_notes_label.configure(text="")
        channel = self.config.get("update_channel", "beta")

        def worker():
            try:
                result = UpdateService().check(channel)
                self._update_queue.put(("checked", result))
            except Exception as exc:
                self._update_queue.put(("error", exc))

        threading.Thread(target=worker, name="SorterinoUpdateCheck", daemon=True).start()
        self._schedule_update_poll()

    def _schedule_update_poll(self):
        if self._update_poll_after is None:
            self._update_poll_after = self.after(100, self._poll_update_queue)

    def _poll_update_queue(self):
        self._update_poll_after = None
        handled = False
        while True:
            try:
                kind, payload = self._update_queue.get_nowait()
            except queue.Empty:
                break
            handled = True
            if kind == "checked":
                self._show_update_result(payload)
            elif kind == "progress":
                downloaded, total = payload
                percent = int(downloaded * 100 / total) if total else 0
                if self._update_widgets_exist():
                    self.update_status_label.configure(text=f"Installer wird heruntergeladen: {percent} %")
            elif kind == "downloaded":
                self._offer_install(payload)
            else:
                self._show_update_error(payload)
        if self._update_widgets_exist() and str(self.update_button.cget("state")) == "disabled":
            self._schedule_update_poll()

    def _update_widgets_exist(self):
        try:
            return bool(self.update_button.winfo_exists() and self.update_status_label.winfo_exists())
        except Exception:
            return False

    def _show_update_result(self, result):
        if not self._update_widgets_exist():
            return
        from datetime import datetime

        checked_at = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.config.set("last_update_check", checked_at)
        self.update_button.configure(state="normal")
        if not result.update_available:
            self._update_release = None
            self.update_status_label.configure(text=f"Sorterino {APP_VERSION} ist aktuell · geprüft {checked_at}")
            self.update_button.configure(text="Erneut prüfen", command=self._start_update_check)
            return
        release = result.release
        self._update_release = release
        size_mb = release.installer.size / (1024 * 1024)
        integrity = "SHA-256 verfügbar" if release.has_integrity_information else "Prüfsumme fehlt"
        self.update_status_label.configure(
            text=f"Version {release.version} verfügbar · {size_mb:.1f} MB · {integrity}"
        )
        notes = release.notes.strip()
        if len(notes) > 700:
            notes = notes[:697].rstrip() + "…"
        self.update_notes_label.configure(text=notes or "Für dieses Release wurden keine Hinweise hinterlegt.")
        self.update_button.configure(
            text="Herunterladen und installieren",
            command=self._start_update_download,
            state="normal" if release.has_integrity_information else "disabled",
        )

    def _start_update_download(self):
        release = self._update_release
        if release is None:
            return
        self.update_button.configure(state="disabled", text="Download läuft …")

        def progress(downloaded, total):
            self._update_queue.put(("progress", (downloaded, total)))

        def worker():
            try:
                path = UpdateService().download(release, self.config.app_root / "updates", progress)
                self._update_queue.put(("downloaded", path))
            except Exception as exc:
                self._update_queue.put(("error", exc))

        threading.Thread(target=worker, name="SorterinoUpdateDownload", daemon=True).start()
        self._schedule_update_poll()

    def _offer_install(self, installer_path):
        if not self._update_widgets_exist():
            return
        self.update_status_label.configure(text="Download und SHA-256-Prüfung abgeschlossen.")
        self.update_button.configure(state="normal", text="Installation starten")
        if not messagebox.askyesno(
            "Sorterino aktualisieren",
            (
                "Der Installer wurde vollständig geladen und seine SHA-256-Prüfsumme wurde geprüft.\n\n"
                "Diese kostenlose Beta besitzt noch keine verifizierte Windows-Herausgebersignatur. "
                "Windows kann deshalb eine SmartScreen-Warnung anzeigen.\n\n"
                "Sorterino jetzt beenden und den Installer starten?"
            ),
            parent=self.owner,
        ):
            return
        try:
            launch_installer_after_exit(installer_path, os.getpid())
            self.owner.exit_application()
        except Exception as exc:
            self._show_update_error(exc)

    def _show_update_error(self, exc):
        if not self._update_widgets_exist():
            return
        message = str(exc) if isinstance(exc, UpdateError) else "Das Update konnte nicht sicher verarbeitet werden."
        self.update_status_label.configure(text=message)
        self.update_button.configure(state="normal", text="Erneut versuchen", command=self._start_update_check)
        messagebox.showerror("Update fehlgeschlagen", message, parent=self.owner)
