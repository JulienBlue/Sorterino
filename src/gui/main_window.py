import os
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.gui.view_state import (
    attention_tab,
    attention_title,
    clamp_window_geometry,
    live_status_decision,
    overview_summary,
    same_document_path,
)

from main import is_pipeline_running, request_pipeline_stop, run_pipeline
from src.config import Config
from src.initialize_workspace import initialize_workspace
from src.profile_service import ProfileService, ProfileValidationError
from src.initialize_workspace import get_base_path
from src.gui.appearance import (
    APPEARANCE_LABELS,
    CONTROL_HOVER,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    apply_appearance,
    appearance_label,
)
from src.document_import import import_documents
from src.document_formats import is_ignored_source_name
from src.storage_utils import FilesystemStorage, SourceFileBusyError, discard_file_within
from src.manual_review_suggestions import ManualReviewSuggestionStore
from src.manual_filing import ManualFilingService


class InitialStorageDialog(ctk.CTkToplevel):
    """Small first-run welcome shown before the shared workspace is configured."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.title("Willkommen bei Sorterino")
        self.geometry("520x300")
        self.resizable(False, False)
        self.transient(owner)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        icon_path = get_base_path() / "assets" / "icons" / "default_icon_128.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        card = ctk.CTkFrame(self, border_width=1, border_color=("gray78", "gray30"))
        card.pack(fill="both", expand=True, padx=22, pady=22)
        ctk.CTkLabel(
            card,
            text="Willkommen bei Sorterino",
            font=("Arial", 23, "bold"),
        ).pack(pady=(28, 10))
        ctk.CTkLabel(
            card,
            text=(
                "Wähle beim ersten Start bitte einen Standardspeicherort aus.\n"
                "Sorterino richtet dort den gemeinsamen Eingangsordner ein.\n"
                "Für einzelne Profile kannst du später eigene Speicherorte festlegen."
            ),
            justify="center",
            wraplength=430,
        ).pack(padx=24, pady=(0, 22))
        ctk.CTkButton(
            card,
            text="Standardspeicherort auswählen",
            height=42,
            command=self._choose,
        ).pack(padx=40, fill="x")
        ctk.CTkLabel(
            card,
            text="Es werden noch keine Dokumente verarbeitet.",
            text_color=SECONDARY_TEXT,
        ).pack(pady=(12, 20))
        self.after(50, self._activate)

    def _activate(self):
        self.grab_set()
        self.lift()
        self.focus_force()

    def _choose(self):
        if self.owner._choose_global_storage(required=True, dialog_parent=self):
            self.grab_release()
            self.destroy()


class CloseToTrayDialog(ctk.CTkToplevel):
    """One-time explanation shown before the main window moves to the tray."""

    def __init__(self, owner, on_confirm):
        super().__init__(owner)
        self.owner = owner
        self.on_confirm = on_confirm
        self.title("Sorterino läuft weiter")
        self.geometry("510x270")
        self.resizable(False, False)
        self.transient(owner)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Sorterino läuft im Hintergrund weiter",
            font=("Arial", 20, "bold"),
        ).grid(row=0, column=0, padx=28, pady=(28, 10), sticky="w")
        ctk.CTkLabel(
            self,
            text=(
                "Das Fenster wird geschlossen. Sorterino bleibt aktiv und ist über "
                "das Symbol im Infobereich der Windows-Taskleiste erreichbar.\n\n"
                "Über das Tray-Menü kannst du Sorterino später vollständig beenden."
            ),
            justify="left",
            wraplength=450,
        ).grid(row=1, column=0, padx=28, pady=(0, 14), sticky="w")
        self.hide_notice = ctk.CTkCheckBox(
            self,
            text="Diese Nachricht künftig nicht mehr anzeigen",
        )
        self.hide_notice.grid(row=2, column=0, padx=28, pady=(0, 18), sticky="w")
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, padx=28, pady=(0, 24), sticky="e")
        ctk.CTkButton(
            actions,
            text="Abbrechen",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=PRIMARY_TEXT,
            hover_color=CONTROL_HOVER,
            command=self._cancel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Im Hintergrund weiter",
            width=175,
            command=self._confirm,
        ).pack(side="left")
        self.after(20, self._activate)

    def _activate(self):
        self.grab_set()
        self.lift()
        self.focus_force()

    def _cancel(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _confirm(self):
        if self.hide_notice.get():
            try:
                self.owner.config.set("hide_close_to_tray_notice", True)
            except OSError as exc:
                messagebox.showerror(
                    "Einstellung nicht gespeichert",
                    f"Die Auswahl konnte nicht gespeichert werden:\n{exc}",
                    parent=self,
                )
                return
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        self.on_confirm()


class MainWindow(ctk.CTkToplevel):
    TEXT_COLOR = PRIMARY_TEXT
    SIDEBAR_COLOR = ("gray94", "gray13")
    SIDEBAR_HOVER = ("gray84", "gray24")
    SIDEBAR_ACTIVE = ("gray76", "gray30")
    NAV_ITEMS = [
        ("overview", "Übersicht"),
        ("documents", "Dokumente"),
        ("profiles", "Profile"),
        ("settings", "Einstellungen"),
    ]

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config
        apply_appearance(self.config.get("appearance_mode", "system"))
        self._thread_running = False
        self._single_document_queue = []
        self._active_single_document = None
        self._stop_requested = False
        self._active_page = "overview"
        self._back_stack = []
        self._forward_stack = []
        self._current_view = None
        self._active_content = None
        self._help_window = None
        self._success_banner = None
        self._success_banner_after = None
        self._initial_storage_prompted = False
        self._initial_storage_dialog = None
        self._close_to_tray_dialog = None
        self.run_button = None
        self._document_lists = {}
        self._overview_widgets = {}
        self._document_snapshot = None
        self._last_incoming_count = 0
        self._status_mode = None
        self._readiness_issues = []
        self._next_readiness_check = 0.0
        self._geometry_save_after = None
        self._last_normal_geometry = None
        self._restoring_geometry = True
        self._close_pending = False
        self.title("Sorterino")
        self.minsize(1080, 700)
        saved_geometry = self.config.get("window_geometry") or {}
        width, height, x, y = self._clamp_window_geometry(
            saved_geometry,
            self._virtual_screen_bounds(),
        )
        self._restored_geometry = (width, height, x, y)
        self.geometry(f"{width}x{height}{x:+d}{y:+d}")
        self._last_normal_geometry = self._restored_geometry
        icon_path = get_base_path() / "assets" / "icons" / "default_icon_128.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
        self._build_shell()
        self.bind("<Alt-Left>", lambda _event: self.go_back())
        self.bind("<Alt-Right>", lambda _event: self.go_forward())
        self.bind("<Configure>", self._window_geometry_changed, add="+")
        self.show_page("overview")
        self.after_idle(
            lambda: self._apply_restored_geometry(bool(saved_geometry.get("maximized")))
        )
        self.after(
            180,
            lambda: self._apply_restored_geometry(bool(saved_geometry.get("maximized"))),
        )
        self.after(300, self._finish_geometry_restore)
        self.after(200, self._ensure_initial_storage)
        self.after(750, self._poll_document_folders)

    def _virtual_screen_bounds(self):
        if os.name == "nt":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                return (
                    user32.GetSystemMetrics(76),
                    user32.GetSystemMetrics(77),
                    user32.GetSystemMetrics(78),
                    user32.GetSystemMetrics(79),
                )
            except Exception:
                pass
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _apply_restored_geometry(self, maximized=False):
        try:
            width, height, x, y = self._restored_geometry
            if self.state() == "zoomed":
                self.state("normal")
            self.geometry(f"{width}x{height}{x:+d}{y:+d}")
            self.update_idletasks()
            if maximized:
                self.state("zoomed")
        except Exception:
            pass

    def _finish_geometry_restore(self):
        self._restoring_geometry = False
        if self.state() == "normal":
            self._capture_normal_geometry()

    @staticmethod
    def _clamp_window_geometry(saved, bounds, default=(1280, 820), minimum=(1080, 700)):
        return clamp_window_geometry(saved, bounds, default, minimum)

    def _capture_normal_geometry(self):
        self._last_normal_geometry = (
            int(self.winfo_width()),
            int(self.winfo_height()),
            int(self.winfo_x()),
            int(self.winfo_y()),
        )

    def _window_geometry_changed(self, event=None):
        if event is not None and event.widget is not self:
            return
        try:
            if self._restoring_geometry or self.state() != "normal":
                return
            self._capture_normal_geometry()
            if self._geometry_save_after:
                self.after_cancel(self._geometry_save_after)
            self._geometry_save_after = self.after(500, self.save_window_state)
        except Exception:
            pass

    def save_window_state(self):
        self._geometry_save_after = None
        if self.state() == "normal" and not self._restoring_geometry:
            self._capture_normal_geometry()
        width, height, x, y = self._last_normal_geometry or self._restored_geometry
        self.config.set("window_geometry", {
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "maximized": self.state() == "zoomed",
        })

    def destroy(self):
        try:
            if self._geometry_save_after:
                self.after_cancel(self._geometry_save_after)
            self.save_window_state()
        except Exception:
            pass
        super().destroy()

    def close_safely(self):
        if self._close_pending:
            return
        self._close_pending = True
        try:
            if self._geometry_save_after:
                self.after_cancel(self._geometry_save_after)
                self._geometry_save_after = None
            self.save_window_state()
            self.withdraw()
            self.update_idletasks()
            self.after(80, self._finish_safe_close)
        except Exception:
            self._finish_safe_close()

    def request_close_to_tray(self, on_confirm):
        if self.config.get("hide_close_to_tray_notice", False):
            on_confirm()
            return
        if (
            self._close_to_tray_dialog
            and self._close_to_tray_dialog.winfo_exists()
        ):
            self._close_to_tray_dialog.lift()
            self._close_to_tray_dialog.focus_force()
            return
        self._close_to_tray_dialog = CloseToTrayDialog(self, on_confirm)

    def _finish_safe_close(self):
        try:
            super().destroy()
        except Exception:
            pass

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(
            self,
            width=190,
            corner_radius=0,
            fg_color=self.SIDEBAR_COLOR,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(
            self.sidebar,
            text="Sorterino",
            font=("Arial", 24, "bold"),
            text_color=self.TEXT_COLOR,
        ).pack(anchor="w", padx=22, pady=(24, 28))
        self.nav_buttons = {}
        for key, label in self.NAV_ITEMS:
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=42,
                anchor="w",
                fg_color="transparent",
                hover_color=self.SIDEBAR_HOVER,
                text_color=self.TEXT_COLOR,
                command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button
        sidebar_tools = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_tools.pack(side="bottom", fill="x", padx=12, pady=(8, 16))
        self.sidebar_run_button = ctk.CTkButton(
            sidebar_tools,
            text="Jetzt verarbeiten",
            anchor="w",
            command=self._run_pipeline,
        )
        self.sidebar_run_button.pack(fill="x", pady=3)
        ctk.CTkButton(
            sidebar_tools,
            text="Eingangsordner öffnen",
            anchor="w",
            fg_color="transparent",
            hover_color=self.SIDEBAR_HOVER,
            text_color=self.TEXT_COLOR,
            command=self._open_incoming,
        ).pack(fill="x", pady=3)
        ctk.CTkButton(
            sidebar_tools,
            text="Dokumente hinzufügen",
            anchor="w",
            fg_color="transparent",
            hover_color=self.SIDEBAR_HOVER,
            text_color=self.TEXT_COLOR,
            command=self._add_documents,
        ).pack(fill="x", pady=3)
        ctk.CTkFrame(sidebar_tools, height=1, fg_color=self.SIDEBAR_HOVER).pack(
            fill="x", pady=(9, 6)
        )
        ctk.CTkButton(
            sidebar_tools,
            text="Hilfe",
            anchor="w",
            fg_color="transparent",
            hover_color=self.SIDEBAR_HOVER,
            text_color=self.TEXT_COLOR,
            command=self._show_help,
        ).pack(fill="x", pady=3)
        workspace = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)
        history = ctk.CTkFrame(
            workspace,
            height=44,
            corner_radius=8,
            fg_color=("gray92", "gray18"),
        )
        history.grid(row=0, column=0, sticky="ew", padx=30, pady=(12, 0))
        self.back_button = ctk.CTkButton(
            history,
            text="←  Zurück",
            width=92,
            height=32,
            fg_color="transparent",
            hover_color=CONTROL_HOVER,
            text_color=PRIMARY_TEXT,
            border_width=1,
            border_color=("gray72", "gray38"),
            command=self.go_back,
        )
        self.back_button.pack(side="left", padx=(6, 4), pady=6)
        self.forward_button = ctk.CTkButton(
            history,
            text="Weiter  →",
            width=92,
            height=32,
            fg_color="transparent",
            hover_color=CONTROL_HOVER,
            text_color=PRIMARY_TEXT,
            border_width=1,
            border_color=("gray72", "gray38"),
            command=self.go_forward,
        )
        self.forward_button.pack(side="left")
        self.live_status = ctk.CTkFrame(history, fg_color="transparent")
        self.live_status.pack(side="right", padx=(12, 10), pady=6)
        self.live_status_label = ctk.CTkLabel(
            self.live_status,
            text="Status wird geprüft …",
            text_color=SECONDARY_TEXT,
        )
        self.live_status_label.pack(side="left", padx=(0, 10))
        self.live_status_label.bind("<Button-1>", lambda _event: self._show_help())
        self.live_progress = ctk.CTkProgressBar(self.live_status, width=150, height=8)
        self.live_progress.pack(side="left")
        self.live_progress.set(0)
        self.live_progress.bind("<Button-1>", lambda _event: self._show_help())
        self.stop_processing_button = ctk.CTkButton(
            self.live_status,
            text="Verarbeitung stoppen",
            width=145,
            height=28,
            fg_color="transparent",
            text_color=("#8A2C2C", "#FFB5B5"),
            hover_color=CONTROL_HOVER,
            border_width=1,
            command=self._stop_processing,
        )
        self.content = ctk.CTkFrame(workspace, corner_radius=0, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew")
        self._update_history_buttons()

    def show_page(self, page, add_history=True):
        if page == "profiles":
            self.show_profiles(add_history=add_history)
            return
        view = ("main", page)
        if add_history and self._current_view and self._current_view != view:
            self._back_stack.append(self._current_view)
            self._forward_stack.clear()
        self._render_view(view)

    def show_documents(self, tab="Neu", add_history=True):
        view = ("main", "documents", tab)
        if add_history and self._current_view and self._current_view != view:
            self._back_stack.append(self._current_view)
            self._forward_stack.clear()
        self._render_view(view)

    def show_profiles(self, selected_id=None, add_history=True):
        from src.gui.profile_window import ProfileWindow
        self.open_view(
            lambda parent: ProfileWindow(parent, config=Config(), selected_id=selected_id),
            "profiles",
            add_history=add_history,
        )

    def return_to_profiles(self, selected_id=None, message=None):
        """Finish a nested profile flow and return to one fresh profile overview."""
        while self._back_stack and len(self._back_stack[-1]) > 2 and self._back_stack[-1][2] == "profiles":
            self._back_stack.pop()
        self._forward_stack.clear()
        from src.gui.profile_window import ProfileWindow
        self._render_view((
            "custom",
            lambda parent: ProfileWindow(parent, config=Config(), selected_id=selected_id),
            "profiles",
        ))
        if message:
            self._show_success_banner(message)

    def _show_success_banner(self, message):
        if self._success_banner_after:
            try:
                self.after_cancel(self._success_banner_after)
            except Exception:
                pass
        if self._success_banner and self._success_banner.winfo_exists():
            self._success_banner.destroy()
        self._success_banner = ctk.CTkFrame(
            self.content,
            border_width=1,
            border_color=("#2e7d32", "#66bb6a"),
            fg_color=("gray98", "gray17"),
            corner_radius=8,
        )
        ctk.CTkLabel(
            self._success_banner,
            text=message,
            text_color=("#1b5e20", "#81c784"),
        ).pack(padx=18, pady=10)
        self._success_banner.place(relx=0.5, y=8, anchor="n")
        self._success_banner.lift()
        self._success_banner_after = self.after(5000, self._hide_success_banner)

    def _hide_success_banner(self):
        if self._success_banner and self._success_banner.winfo_exists():
            self._success_banner.destroy()
        self._success_banner = None
        self._success_banner_after = None

    def open_view(self, factory, nav_key=None, add_history=True):
        view = ("custom", factory, nav_key)
        if add_history and self._current_view:
            self._back_stack.append(self._current_view)
            self._forward_stack.clear()
        self._render_view(view)

    def _render_view(self, view):
        previous_view = self._current_view
        previous_content = self.content
        previous_active_content = self._active_content
        previous_active_page = self._active_page
        previous_run_button = self.run_button

        # Build the complete next page on an unmanaged surface. Tk cannot paint
        # this frame while its children are being packed, so users see one
        # atomic page swap instead of the individual construction steps.
        next_content = ctk.CTkFrame(
            previous_content.master,
            corner_radius=0,
            fg_color="transparent",
        )
        self.content = next_content
        self._current_view = view
        self._next_readiness_check = 0.0
        # The overview owns this button. Clear the reference before its page
        # widgets are destroyed so buttons on other pages cannot address a
        # stale CustomTkinter widget later.
        self.run_button = None
        try:
            if view[0] == "custom":
                self._active_page = view[2]
                frame = view[1](next_content)
                frame.pack(fill="both", expand=True)
                self._active_content = frame
            else:
                page = view[1]
                self._active_page = page
                self.config = Config()
                if page == "documents":
                    self._build_documents(view[2] if len(view) > 2 else "Neu")
                else:
                    {
                        "overview": self._build_overview,
                        "settings": self._build_settings,
                    }[page]()
                self._active_content = None
        except Exception:
            next_content.destroy()
            self.content = previous_content
            self._current_view = previous_view
            self._active_content = previous_active_content
            self._active_page = previous_active_page
            self.run_button = previous_run_button
            raise

        next_content.grid(row=1, column=0, sticky="nsew")
        next_content.lift()
        previous_content.destroy()
        for key, button in self.nav_buttons.items():
            button.configure(fg_color=self.SIDEBAR_ACTIVE if key == self._active_page else "transparent")
        self._update_history_buttons()

    def go_back(self):
        if self._back_stack:
            self._forward_stack.append(self._current_view)
            self._render_view(self._back_stack.pop())

    def go_forward(self):
        if self._forward_stack:
            self._back_stack.append(self._current_view)
            self._render_view(self._forward_stack.pop())

    def _update_history_buttons(self):
        if hasattr(self, "back_button"):
            self.back_button.configure(state="normal" if self._back_stack else "disabled")
            self.forward_button.configure(state="normal" if self._forward_stack else "disabled")

    def refresh(self):
        if self.winfo_exists():
            if self._current_view:
                self._render_view(self._current_view)

    def _page_header(self, title, subtitle=""):
        ctk.CTkLabel(self.content, text=title, font=("Arial", 25, "bold")).pack(anchor="w", padx=30, pady=(26, 2))
        if subtitle:
            ctk.CTkLabel(self.content, text=subtitle, text_color=SECONDARY_TEXT).pack(anchor="w", padx=30, pady=(0, 18))

    def _build_overview(self):
        self._page_header("Übersicht", "Alles Wichtige auf einen Blick")
        stats = self._document_stats()
        hero = ctk.CTkFrame(self.content)
        hero.pack(fill="x", padx=30, pady=(4, 14))
        title, subtitle, open_count = self._overview_summary(stats)
        title_label = ctk.CTkLabel(hero, text=title, font=("Arial", 19, "bold"))
        title_label.pack(anchor="w", padx=20, pady=(18, 4))
        subtitle_label = ctk.CTkLabel(hero, text=subtitle)
        subtitle_label.pack(anchor="w", padx=20)
        attention_tab = self._attention_tab(stats)
        attention_button = ctk.CTkButton(
            hero,
            text="Dokument ansehen" if open_count == 1 else "Dokumente ansehen",
            command=lambda tab=attention_tab: self.show_documents(tab),
        )
        attention_button.pack(anchor="w", padx=20, pady=18)

        self._overview_widgets = {
            "title": title_label,
            "subtitle": subtitle_label,
            "attention_button": attention_button,
            "counts": {},
        }

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=24)
        for label, value in [
            ("Neu im Eingang", stats["incoming"]),
            ("Zu prüfen", stats["manual"]),
            ("Fehler", stats["error"]),
            ("Profile", stats["profiles"]),
        ]:
            card = ctk.CTkFrame(cards)
            card.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            count_label = ctk.CTkLabel(card, text=str(value), font=("Arial", 28, "bold"))
            count_label.pack(pady=(16, 2))
            ctk.CTkLabel(card, text=label).pack(pady=(0, 16))
            self._overview_widgets["counts"][label] = count_label

    def _refresh_overview_stats(self):
        if self._active_page != "overview" or not self._overview_widgets:
            return
        stats = self._document_stats()
        title, subtitle, open_count = self._overview_summary(stats)
        attention_tab = self._attention_tab(stats)
        self._overview_widgets["title"].configure(text=title)
        self._overview_widgets["subtitle"].configure(text=subtitle)
        self._overview_widgets["attention_button"].configure(
            text="Dokument ansehen" if open_count == 1 else "Dokumente ansehen",
            command=lambda tab=attention_tab: self.show_documents(tab),
        )
        for label, value in (
            ("Neu im Eingang", stats["incoming"]),
            ("Zu prüfen", stats["manual"]),
            ("Fehler", stats["error"]),
            ("Profile", stats["profiles"]),
        ):
            self._overview_widgets["counts"][label].configure(text=str(value))

    def _refresh_changed_document_views(self):
        self._refresh_overview_stats()
        self._refresh_document_lists()

    @staticmethod
    def _overview_summary(stats):
        return overview_summary(stats)

    @staticmethod
    def _attention_title(count):
        return attention_title(count)

    @staticmethod
    def _attention_tab(stats):
        return attention_tab(stats)

    def _build_documents(self, initial_tab="Neu"):
        self._page_header("Dokumente", "Eingang, Prüfung und technische Probleme")
        tabs = ctk.CTkTabview(self.content)
        tabs.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self._document_tabs = tabs
        self._document_lists = {}
        for label, folder, empty_text in [
            ("Neu", self.config.incoming_root, "Keine neuen Dokumente."),
            ("Zu prüfen", self.config.manual_root, "Nichts zu prüfen."),
            ("Fehler", self.config.error_root, "Keine technischen Fehler."),
        ]:
            tab = tabs.add(label)
            if label == "Zu prüfen":
                actions = ctk.CTkFrame(tab, fg_color="transparent")
                actions.pack(fill="x", pady=(6, 0))
                ctk.CTkButton(
                    actions,
                    text="Alle verwerfen",
                    width=120,
                    fg_color="transparent",
                    text_color=("#8a1f1f", "#ff9b9b"),
                    hover_color=self.SIDEBAR_HOVER,
                    border_width=1,
                    command=self._discard_all_review_documents,
                ).pack(side="right", padx=4)
            frame = ctk.CTkScrollableFrame(tab)
            frame.pack(fill="both", expand=True, pady=(8, 0))
            self._document_lists[label] = (
                frame, folder, empty_text, label == "Zu prüfen", label == "Fehler"
            )
            self._populate_file_list(
                frame, folder, empty_text,
                review=(label == "Zu prüfen"), error=(label == "Fehler")
            )
        if initial_tab in {"Neu", "Zu prüfen", "Fehler"}:
            tabs.set(initial_tab)

    def _populate_file_list(self, frame, folder, empty_text, review=False, error=False):
        for child in frame.winfo_children():
            child.destroy()
        files = self._files(folder)
        if not files:
            ctk.CTkLabel(frame, text=empty_text).pack(pady=30)
            return
        mail_state = None
        suggestion_store = ManualReviewSuggestionStore(self.config) if review else None
        if not review and not error:
            try:
                from src.mail_fetcher import MailImportState
                mail_state = MailImportState(self.config)
            except (AttributeError, OSError):
                mail_state = None
        for path in files:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=3)
            name_area = ctk.CTkFrame(row, fg_color="transparent")
            name_area.pack(side="left", fill="x", expand=True, padx=12, pady=7)
            ctk.CTkLabel(name_area, text=path.name, anchor="w").pack(side="left")
            suggestion = suggestion_store.load(path) if suggestion_store else {}
            if suggestion.get("review_kind") in {
                "exact_duplicate", "same_import_duplicate"
            }:
                ctk.CTkLabel(
                    name_area,
                    text="Duplikat",
                    font=("Arial", 11, "bold"),
                    fg_color=("#FFF0D2", "#5A390D"),
                    text_color=("#704400", "#FFE0A3"),
                    corner_radius=6,
                ).pack(side="left", padx=(8, 0), ipady=2, ipadx=5)
            if mail_state and mail_state.file_info(path):
                ctk.CTkLabel(
                    name_area,
                    text="✉ E-Mail",
                    font=("Arial", 11, "bold"),
                    fg_color=("#DCEEFF", "#174A70"),
                    text_color=("#164E73", "#E6F4FF"),
                    corner_radius=6,
                ).pack(side="left", padx=(8, 0), ipady=2, ipadx=5)
            if review:
                ctk.CTkButton(
                    row,
                    text="🗑",
                    width=36,
                    height=28,
                    fg_color="transparent",
                    text_color=("#7A3030", "#FFB0B0"),
                    hover_color=self.SIDEBAR_HOVER,
                    border_width=1,
                    command=lambda p=path: self._discard_review_document(p),
                ).pack(side="right", padx=(0, 8), pady=6)
                ctk.CTkButton(
                    row,
                    text="Prüfen",
                    width=70,
                    command=lambda p=path: self._review_document(p),
                ).pack(side="right", padx=(8, 4), pady=6)
            elif error:
                ctk.CTkButton(
                    row, text="Erneut versuchen", width=120,
                    command=lambda p=path: self._retry_error_document(p)
                ).pack(side="right", padx=8, pady=6)
                ctk.CTkButton(
                    row, text="Öffnen", width=70,
                    command=lambda p=path: self._open_path(p)
                ).pack(side="right", padx=(0, 4), pady=6)
                ctk.CTkButton(
                    row, text="Aus Liste entfernen", width=130,
                    fg_color="transparent", text_color=self.TEXT_COLOR,
                    hover_color=self.SIDEBAR_HOVER,
                    command=lambda p=path: self._remove_error_document(p)
                ).pack(side="right", padx=(0, 4), pady=6)
            else:
                queue_position = self._single_queue_position(path)
                is_active = self._same_document_path(path, self._active_single_document)
                if is_active or queue_position:
                    marker = (
                        "Wird verarbeitet"
                        if is_active else f"Warteschlange · Platz {queue_position}"
                    )
                    ctk.CTkLabel(
                        name_area,
                        text=marker,
                        font=("Arial", 11, "bold"),
                        fg_color=("#DCEEFF", "#174A70"),
                        text_color=("#164E73", "#E6F4FF"),
                        corner_radius=6,
                    ).pack(side="left", padx=(8, 0), ipady=2, ipadx=5)
                if not is_active and not queue_position:
                    process_button = ctk.CTkButton(
                        row,
                        text="Verarbeiten",
                        width=95,
                    )
                    process_button.configure(
                        command=lambda p=path, button=process_button: self._run_single_document(p, button)
                    )
                    process_button.pack(side="right", padx=8, pady=6)
                ctk.CTkButton(
                    row,
                    text="Öffnen",
                    width=70,
                    fg_color="transparent",
                    text_color=self.TEXT_COLOR,
                    hover_color=self.SIDEBAR_HOVER,
                    command=lambda p=path: self._open_path(p),
                ).pack(side="right", padx=(0, 4), pady=6)
                discard_button = ctk.CTkButton(
                    row,
                    text="Verwerfen",
                    width=85,
                    fg_color="transparent",
                    text_color=("#8a1f1f", "#ff8a8a"),
                    hover_color=self.SIDEBAR_HOVER,
                    border_width=1,
                    command=lambda p=path: self._discard_incoming_document(p),
                )
                discard_button.pack(side="right", padx=(0, 4), pady=6)
                if is_active or queue_position:
                    discard_button.configure(state="disabled")

    @staticmethod
    def _same_document_path(first, second):
        return same_document_path(first, second)

    def _single_queue_position(self, path):
        for index, queued in enumerate(self._single_document_queue, start=1):
            if self._same_document_path(path, queued):
                return index
        return None

    def _processing_status_text(self):
        queued = len(self._single_document_queue)
        if self._active_single_document is not None:
            text = f"Verarbeite {Path(self._active_single_document).name}"
            return f"{text} · {queued} in Warteschlange" if queued else text
        if queued:
            return f"Verarbeitung läuft · {queued} in Warteschlange"
        return "Verarbeitung läuft …"

    def _discard_incoming_document(self, path):
        path = Path(path)
        if not messagebox.askyesno(
            "Dokument endgültig verwerfen",
            f"Soll dieses neue Dokument wirklich endgültig gelöscht werden?\n\n{path.name}",
            icon="warning",
            parent=self,
        ):
            return
        try:
            discard_file_within(path, self.config.incoming_root)
        except SourceFileBusyError:
            messagebox.showinfo(
                "Dokument ist geöffnet",
                "Schließe das Dokument im anderen Programm und versuche es danach erneut.",
                parent=self,
            )
            return
        except (OSError, ValueError) as exc:
            messagebox.showerror("Dokument nicht gelöscht", str(exc), parent=self)
            return
        self._document_snapshot = None
        self._refresh_document_lists()
        self._next_readiness_check = 0.0

    def _discard_all_review_documents(self):
        files = self._files(self.config.manual_root)
        if not files:
            messagebox.showinfo(
                "Nichts zu verwerfen",
                "Unter ‚Zu prüfen‘ befinden sich keine Dokumente.",
                parent=self,
            )
            return
        count = len(files)
        if not messagebox.askyesno(
            "Alle Dokumente verwerfen",
            f"Sollen wirklich alle {count} Dokumente aus ‚Zu prüfen‘ endgültig "
            "gelöscht werden?\n\nArchive, Backups und Dateien im Eingang bleiben erhalten.",
            icon="warning",
            parent=self,
        ):
            return

        filing = ManualFilingService(self.config, ProfileService(self.config))
        suggestions = ManualReviewSuggestionStore(self.config)
        discarded = 0
        failures = []
        for path in files:
            try:
                filing.discard_document(path)
                suggestions.remove(path)
                discarded += 1
            except (OSError, ProfileValidationError) as exc:
                failures.append(f"{path.name}: {exc}")

        self._document_snapshot = None
        self._refresh_document_lists()
        self._next_readiness_check = 0.0
        if failures:
            preview = "\n".join(failures[:5])
            more = f"\n… und {len(failures) - 5} weitere" if len(failures) > 5 else ""
            messagebox.showwarning(
                "Nicht alle Dokumente verworfen",
                f"{discarded} Dokumente wurden verworfen.\n"
                f"{len(failures)} konnten nicht gelöscht werden:\n\n{preview}{more}",
                parent=self,
            )
            return
        messagebox.showinfo(
            "Alles verworfen",
            f"Alle {discarded} Dokumente wurden aus ‚Zu prüfen‘ gelöscht.",
            parent=self,
        )

    def _discard_review_document(self, path):
        path = Path(path)
        if not messagebox.askyesno(
            "Dokument verwerfen",
            f"Soll dieses Dokument wirklich endgültig aus ‚Zu prüfen‘ gelöscht werden?\n\n"
            f"{path.name}",
            icon="warning",
            parent=self,
        ):
            return
        try:
            filing = ManualFilingService(self.config, ProfileService(self.config))
            filing.discard_document(path)
            ManualReviewSuggestionStore(self.config).remove(path)
        except SourceFileBusyError:
            messagebox.showinfo(
                "Dokument ist geöffnet",
                "Schließe das Dokument im anderen Programm und versuche es danach erneut.",
                parent=self,
            )
            return
        except (OSError, ProfileValidationError) as exc:
            messagebox.showerror("Dokument nicht verworfen", str(exc), parent=self)
            return
        self._document_snapshot = None
        self._refresh_document_lists()
        self._next_readiness_check = 0.0

    def _retry_error_document(self, path):
        try:
            FilesystemStorage.ensure_movable(path)
            FilesystemStorage(self.config.incoming_root).store(path, Path(), path.name)
        except SourceFileBusyError:
            messagebox.showinfo(
                "Dokument ist geöffnet",
                "Schließe das Dokument im anderen Programm und versuche es danach erneut.",
                parent=self,
            )
            return
        except OSError as exc:
            messagebox.showerror("Erneuter Versuch fehlgeschlagen", str(exc), parent=self)
            return
        self._document_snapshot = None
        self._refresh_document_lists()
        self._run_pipeline()

    def _remove_error_document(self, path):
        if not messagebox.askyesno(
            "Fehlerkopie entfernen",
            "Wurde das Dokument bereits erfolgreich im Archiv abgelegt?\n\n"
            "Dann kann diese Fehlerkopie dauerhaft gelöscht und aus der Liste entfernt werden.",
            parent=self,
        ):
            return
        try:
            path.unlink()
        except PermissionError:
            messagebox.showinfo(
                "Dokument ist geöffnet",
                "Schließe das Dokument im anderen Programm und versuche es danach erneut.",
                parent=self,
            )
            return
        except OSError as exc:
            messagebox.showerror("Fehlerkopie nicht entfernt", str(exc), parent=self)
            return
        self._document_snapshot = None
        self._refresh_document_lists()

    def _refresh_document_lists(self):
        if self._active_page != "documents":
            return
        for frame, folder, empty_text, review, error in self._document_lists.values():
            try:
                if frame.winfo_exists():
                    self._populate_file_list(frame, folder, empty_text, review, error)
            except Exception:
                return

    def _build_settings(self):
        self._page_header("Einstellungen", "Nur Einstellungen, die Sorterino als Programm betreffen")
        scroll = ctk.CTkScrollableFrame(self.content)
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self._settings_section(scroll, "Allgemein")
        appearance_row = ctk.CTkFrame(scroll, fg_color="transparent")
        appearance_row.pack(fill="x", padx=16, pady=(2, 10))
        ctk.CTkLabel(appearance_row, text="Darstellung").pack(side="left", padx=(0, 12))
        self.appearance_menu = ctk.CTkOptionMenu(
            appearance_row,
            values=list(APPEARANCE_LABELS),
            command=self._change_appearance,
        )
        self.appearance_menu.set(appearance_label(self.config.get("appearance_mode", "system")))
        self.appearance_menu.pack(side="left")
        self.auto_switch = ctk.CTkSwitch(scroll, text="Dokumente automatisch verarbeiten", command=self._toggle_auto)
        self.auto_switch.pack(anchor="w", padx=16, pady=6)
        if self.config.get("auto_mode"):
            self.auto_switch.select()
        self.autostart_switch = ctk.CTkSwitch(scroll, text="Sorterino mit Windows starten", command=self._toggle_autostart)
        self.autostart_switch.pack(anchor="w", padx=16, pady=6)
        if self.config.get("autostart"):
            self.autostart_switch.select()

        self._settings_section(scroll, "Dokumentquellen")
        ctk.CTkLabel(scroll, text=f"Standard-Dokumentenspeicher: {self.config.get('user_path') or 'nicht eingerichtet'}", wraplength=650, justify="left").pack(anchor="w", padx=16, pady=4)
        ctk.CTkButton(
            scroll,
            text="Standard-Speicherort auswählen",
            command=self._choose_global_storage,
        ).pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(
            scroll,
            text=f"Gemeinsamer Eingangsordner für alle Profile: {self.config.incoming_root}",
            wraplength=650,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(10, 4))
        incoming_actions = ctk.CTkFrame(scroll, fg_color="transparent")
        incoming_actions.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(incoming_actions, text="Eingangsordner öffnen", command=self._open_incoming).pack(side="left")
        ctk.CTkButton(
            incoming_actions,
            text="Eingangsordner ändern",
            command=self._choose_incoming_storage,
        ).pack(side="left", padx=8)
        ctk.CTkLabel(
            scroll,
            text="Neue E-Mail-Postfächer werden direkt im jeweiligen Profil eingerichtet.",
        ).pack(anchor="w", padx=16, pady=(8, 3))
        ctk.CTkButton(scroll, text="Zu den Profilen", command=lambda: self.show_page("profiles")).pack(anchor="w", padx=16, pady=4)

        self._settings_section(scroll, "Texterkennung")
        tess_ready = bool(getattr(self.config, "tesseract_path", None) and self.config.tesseract_path.exists())
        poppler_ready = bool(getattr(self.config, "poppler_path", None) and self.config.poppler_path.exists())
        ctk.CTkLabel(scroll, text=f"Texterkennung: {'Bereit' if tess_ready else 'Nicht verfügbar'}").pack(anchor="w", padx=16, pady=3)
        ctk.CTkLabel(scroll, text=f"PDF-Unterstützung: {'Bereit' if poppler_ready else 'Nicht verfügbar'}").pack(anchor="w", padx=16, pady=3)
        ctk.CTkLabel(scroll, text="Word, ODT, RTF, TXT und E-Mail-Dateien: Bereit").pack(anchor="w", padx=16, pady=3)
        try:
            from pillow_heif import register_heif_opener as _heif_opener
            heic_ready = bool(_heif_opener)
        except ImportError:
            heic_ready = False
        ctk.CTkLabel(
            scroll,
            text=f"HEIC/HEIF-Unterstützung: {'Bereit' if heic_ready else 'Nicht verfügbar'}",
        ).pack(anchor="w", padx=16, pady=3)
        from src.document_text_extractor import DocumentTextExtractor
        legacy_word_ready = bool(DocumentTextExtractor._find_soffice())
        ctk.CTkLabel(
            scroll,
            text=(
                "Alte Word-Dateien (.doc): Bereit"
                if legacy_word_ready
                else "Alte Word-Dateien (.doc): LibreOffice fehlt – DOCX empfohlen"
            ),
        ).pack(anchor="w", padx=16, pady=3)

        self._settings_section(scroll, "Erweitert")
        ctk.CTkButton(scroll, text="Technische Konfiguration", command=self._open_advanced_settings).pack(anchor="w", padx=16, pady=6)
        ctk.CTkButton(scroll, text="Protokoll anzeigen", command=self._open_logs).pack(anchor="w", padx=16, pady=6)

    @staticmethod
    def _settings_section(parent, text):
        ctk.CTkLabel(parent, text=text, font=("Arial", 17, "bold")).pack(anchor="w", padx=12, pady=(18, 6))

    def _document_stats(self):
        stats = {
            "incoming": len(self._files(self.config.incoming_root)),
            "manual": len(self._files(self.config.manual_root)),
            "error": len(self._files(self.config.error_root)),
            "profiles": 0,
        }
        try:
            if self.config.user_path:
                stats["profiles"] = len(ProfileService(self.config).list_profiles())
        except ProfileValidationError:
            pass
        return stats

    @staticmethod
    def _files(folder):
        if not folder:
            return []
        path = Path(folder)
        if not path.exists():
            return []
        return sorted(
            (
                item for item in path.rglob("*")
                if item.is_file() and not is_ignored_source_name(item.name)
            ),
            key=lambda p: p.name.casefold(),
        )

    def _folder_snapshot(self):
        result = []
        for folder in (self.config.incoming_root, self.config.manual_root, self.config.error_root):
            entries = []
            for path in self._files(folder):
                try:
                    stat = path.stat()
                    entries.append((str(path), stat.st_mtime_ns, stat.st_size))
                except OSError:
                    continue
            result.append(tuple(entries))
        return tuple(result)

    def _poll_document_folders(self):
        try:
            if not self.winfo_exists():
                return
            snapshot = self._folder_snapshot()
            incoming_count = len(snapshot[0])
            changed = self._document_snapshot is not None and snapshot != self._document_snapshot
            new_incoming = incoming_count > self._last_incoming_count
            self._document_snapshot = snapshot
            self._last_incoming_count = incoming_count
            running = self._thread_running or is_pipeline_running()
            if not running and self._stop_requested and not self._thread_running:
                self._stop_requested = False
                self.stop_processing_button.configure(state="normal")
            if not running and self._single_document_queue and self._active_single_document is None:
                self._start_next_single_document()
                running = self._thread_running or is_pipeline_running()
            if time.monotonic() >= self._next_readiness_check:
                try:
                    from src.gui.help_window import diagnose
                    _status, self._readiness_issues = diagnose(Config(), self._active_page)
                except Exception as exc:
                    self._readiness_issues = [f"Die Einsatzbereitschaft konnte nicht geprüft werden: {exc}"]
                self._next_readiness_check = time.monotonic() + 5.0
            status_text, status_mode = self._live_status_decision(
                running,
                incoming_count,
                len(snapshot[1]),
                len(snapshot[2]),
                self._readiness_issues,
                new_incoming,
            )
            if running and (
                self._single_document_queue or self._active_single_document is not None
            ):
                status_text = self._processing_status_text()
                status_mode = "running"
            self._set_live_status(status_text, status_mode)
            if changed:
                self._refresh_changed_document_views()
        finally:
            try:
                if self.winfo_exists():
                    self.after(1250, self._poll_document_folders)
            except Exception:
                pass

    @staticmethod
    def _live_status_decision(running, incoming, manual, errors, readiness_issues, new_incoming=False):
        return live_status_decision(
            running,
            incoming,
            manual,
            errors,
            readiness_issues,
            new_incoming,
        )

    def _set_live_status(self, text, mode):
        if mode == "running":
            if not self.stop_processing_button.winfo_manager():
                self.stop_processing_button.pack(side="left", padx=(12, 0))
        else:
            self.stop_processing_button.pack_forget()
        if self._status_mode == mode and self.live_status_label.cget("text") == text:
            return
        self._status_mode = mode
        self.live_status_label.configure(text=text)
        self.live_progress.stop()
        colors = {
            "ready": ("#2E7D32", "#66BB6A"),
            "incoming": ("#1565C0", "#64B5F6"),
            "attention": ("#9A6700", "#F0B429"),
            "configuration": ("#9A6700", "#F0B429"),
            "running": ("#1565C0", "#64B5F6"),
        }
        self.live_progress.configure(progress_color=colors.get(mode, colors["ready"]))
        if mode == "running":
            self.live_progress.configure(mode="indeterminate")
            self.live_progress.start()
        else:
            self.live_progress.configure(mode="determinate")
            self.live_progress.set({
                "ready": 1.0,
                "incoming": 0.55,
                "attention": 0.3,
                "configuration": 0.2,
            }.get(mode, 0))

    def _run_pipeline(self):
        if self._thread_running or is_pipeline_running():
            self._set_live_status("Verarbeitung läuft …", "running")
            return
        self._thread_running = True
        self._stop_requested = False
        self.stop_processing_button.configure(state="normal")
        self._set_live_status("Verarbeitung läuft …", "running")
        if self.sidebar_run_button.winfo_exists():
            self.sidebar_run_button.configure(
                state="disabled", text="Verarbeitung läuft …"
            )
        button = self.run_button
        if button is not None:
            try:
                if button.winfo_exists():
                    button.configure(state="disabled", text="Verarbeitung läuft …")
            except Exception:
                # Navigation may destroy the overview between the click and
                # this update. Processing itself must still start normally.
                self.run_button = None

        def worker():
            try:
                run_pipeline()
            finally:
                self.after(0, self._batch_pipeline_finished)

        threading.Thread(target=worker, daemon=True).start()

    def _batch_pipeline_finished(self):
        self._thread_running = False
        self._pipeline_finished()

    def _stop_processing(self):
        if not (self._thread_running or is_pipeline_running()):
            return
        self._stop_requested = True
        self._single_document_queue.clear()
        request_pipeline_stop()
        self.stop_processing_button.configure(state="disabled")
        self._set_live_status(
            "Stoppe sicher – aktuelle Datei bleibt im Eingang …", "running"
        )
        self._refresh_document_lists()

    def _run_single_document(self, path, button=None):
        path = Path(path)
        if not path.is_file():
            self._document_snapshot = None
            self._refresh_document_lists()
            return
        if self._same_document_path(path, self._active_single_document) or self._single_queue_position(path):
            self._set_live_status(self._processing_status_text(), "running")
            return
        self._single_document_queue.append(path)
        self._refresh_document_lists()
        self._set_live_status(self._processing_status_text(), "running")
        self._start_next_single_document()

    def _start_next_single_document(self):
        if self._stop_requested:
            return
        if self._thread_running or is_pipeline_running() or self._active_single_document is not None:
            return
        while self._single_document_queue:
            path = self._single_document_queue.pop(0)
            if path.is_file():
                break
        else:
            self._pipeline_finished()
            return
        self._active_single_document = path
        self._thread_running = True
        self._set_live_status(self._processing_status_text(), "running")
        if self.sidebar_run_button.winfo_exists():
            self.sidebar_run_button.configure(state="disabled", text="Verarbeitung läuft …")
        self._refresh_document_lists()

        def worker():
            try:
                run_pipeline(path)
            finally:
                self.after(0, self._single_document_finished)

        threading.Thread(target=worker, daemon=True).start()

    def _single_document_finished(self):
        self._thread_running = False
        self._active_single_document = None
        self._pipeline_finished()

    def _pipeline_finished(self):
        self._document_snapshot = None
        stopped = self._stop_requested
        if self._active_single_document is not None:
            self._refresh_document_lists()
            self._set_live_status(self._processing_status_text(), "running")
            return
        if not stopped and self._single_document_queue and self._active_single_document is None:
            self._refresh_document_lists()
            self._start_next_single_document()
            return
        if self.sidebar_run_button.winfo_exists():
            self.sidebar_run_button.configure(
                state="normal", text="Jetzt verarbeiten"
            )
        self.stop_processing_button.configure(state="normal")
        self._stop_requested = False
        self._next_readiness_check = 0.0
        if self._active_page == "overview":
            self.refresh()
        else:
            self._refresh_document_lists()
        self._set_live_status(
            "Verarbeitung gestoppt – Dateien bleiben im Eingang"
            if stopped else "Status wird geprüft …",
            "incoming" if stopped else "checking",
        )

    def _open_incoming(self):
        self._open_path(self.config.incoming_root)

    def _add_documents(self):
        from src.document_formats import (
            EMAIL_EXTENSIONS,
            IMAGE_EXTENSIONS,
            PAGES_EXTENSIONS,
            PDF_EXTENSIONS,
            SUPPORTED_EXTENSIONS,
            TEXT_DOCUMENT_EXTENSIONS,
            WORD_EXTENSIONS,
            file_dialog_patterns,
        )
        if not self.config.incoming_root:
            messagebox.showwarning(
                "Kein Eingangsordner",
                "Bitte richte zuerst einen Standard-Speicherort ein.",
                parent=self,
            )
            self.show_page("settings")
            return
        selected = filedialog.askopenfilenames(
            parent=self,
            title="Dokumente zu Sorterino hinzufügen",
            filetypes=[
                ("Unterstützte Dokumente", file_dialog_patterns(SUPPORTED_EXTENSIONS)),
                ("PDF-Dateien", file_dialog_patterns(PDF_EXTENSIONS)),
                ("Word und Text", file_dialog_patterns(WORD_EXTENSIONS | TEXT_DOCUMENT_EXTENSIONS)),
                ("Pages-Dateien", file_dialog_patterns(PAGES_EXTENSIONS)),
                ("E-Mail-Dateien", file_dialog_patterns(EMAIL_EXTENSIONS)),
                ("Bilddateien", file_dialog_patterns(IMAGE_EXTENSIONS)),
                ("Alle Dateien", "*.*"),
            ],
        )
        if not selected:
            return
        try:
            imported, skipped = import_documents(selected, self.config.incoming_root)
        except OSError as exc:
            messagebox.showerror(
                "Hinzufügen fehlgeschlagen", str(exc), parent=self
            )
            return
        if imported:
            count = len(imported)
            message = (
                "1 Dokument wurde zum Eingang hinzugefügt."
                if count == 1
                else f"{count} Dokumente wurden zum Eingang hinzugefügt."
            )
            if skipped:
                message += f" {len(skipped)} nicht unterstützte Datei(en) wurden übersprungen."
            self.refresh()
            self._show_success_banner(message)
        elif skipped:
            messagebox.showwarning(
                "Keine Dokumente hinzugefügt",
                "Die ausgewählten Dateien werden nicht unterstützt.",
                parent=self,
            )

    @staticmethod
    def _open_path(path):
        if path and Path(path).exists():
            os.startfile(path)
        else:
            messagebox.showwarning("Ordner nicht verfügbar", "Der Ordner wurde noch nicht eingerichtet.")

    def _review_document(self, path):
        from src.gui.manual_review_window import ManualReviewWindow
        self.open_view(lambda parent: ManualReviewWindow(parent, Config(), path), "documents")

    def _ensure_initial_storage(self):
        if self._initial_storage_prompted or self.config.get("user_path"):
            return
        self._initial_storage_prompted = True
        self._initial_storage_dialog = InitialStorageDialog(self)

    def _choose_global_storage(self, required=False, dialog_parent=None):
        current = self.config.get("user_path") or ""
        selected = filedialog.askdirectory(
            parent=dialog_parent or self,
            title=(
                "Zuerst Standard-Dokumentenspeicher für Sorterino auswählen"
                if required else "Standard-Dokumentenspeicher auswählen"
            ),
            initialdir=current or None,
        )
        if not selected or selected == current:
            return False
        try:
            self.config.set_standard_storage(selected)
            self.config = Config()
            initialize_workspace(self.config)
            if not required:
                messagebox.showinfo(
                    "Speicherort geändert",
                    "Der Sorterino-Arbeitsbereich wurde eingerichtet. Profile, die den allgemeinen Speicherort verwenden, nutzen ab jetzt diesen Ordner.",
                    parent=self,
                )
            self.show_page("settings")
            if required:
                self._show_success_banner("Willkommen! Sorterino wurde erfolgreich eingerichtet.")
            return True
        except Exception as exc:
            messagebox.showerror(
                "Speicherort konnte nicht eingerichtet werden",
                str(exc),
                parent=self,
            )
            return False

    def _choose_incoming_storage(self):
        selected = filedialog.askdirectory(
            parent=self,
            title="Gemeinsamen Eingangsordner auswählen",
            initialdir=str(self.config.incoming_root),
        )
        if not selected or Path(selected) == Path(self.config.incoming_root):
            return
        try:
            self.config.set_incoming_storage(selected)
            self.config = Config()
            self.show_page("settings")
        except Exception as exc:
            messagebox.showerror(
                "Eingangsordner konnte nicht eingerichtet werden",
                str(exc),
                parent=self,
            )

    def _open_advanced_settings(self):
        from src.gui.config_window import ConfigWindow
        self.open_view(lambda parent: ConfigWindow(parent, config=Config()), "settings")

    def _open_logs(self):
        from src.gui.log_window import LogWindow
        self.open_view(lambda parent: LogWindow(parent), "settings")

    def _toggle_auto(self):
        self.config.set("auto_mode", bool(self.auto_switch.get()))

    def _change_appearance(self, label):
        mode = apply_appearance(APPEARANCE_LABELS[label])
        self.config.set("appearance_mode", mode)

    def _toggle_autostart(self):
        from src.autostart_service import AutostartService
        enabled = bool(self.autostart_switch.get())
        self.config.set("autostart", enabled)
        service = AutostartService()
        service.enable() if enabled else service.disable()

    def _show_help(self):
        from src.gui.help_window import HelpWindow
        context = (
            getattr(self._active_content, "help_context", None)
            if self._active_content else self._active_page
        ) or "overview"
        if self._help_window and self._help_window.winfo_exists():
            self._help_window.destroy()
        self._help_window = HelpWindow(self, Config(), context)
