import os
import re
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from src.manual_filing import ManualFilingService
from src.profile_service import ProfileService, ProfileValidationError
from src.profile_matcher import ProfileMatcher
from src.gui.embedded import EmbeddedPage
from src.gui.appearance import CONTROL_BUTTON, PRIMARY_TEXT, SECONDARY_TEXT
from src.manual_review_suggestions import (
    ManualReviewSuggestionStore,
    best_destination_label,
    likely_general_information_attachment,
    person_id_from_filename,
    suggested_year,
    tentative_destination,
)


def available_years(current_year=None):
    year = int(current_year or datetime.now().year)
    return [str(value) for value in range(year, 1949, -1)]


class PlaceholderComboBox(ctk.CTkComboBox):
    """Editable CTkComboBox with a real, focus-clearing placeholder."""

    def __init__(self, master, placeholder_text, **kwargs):
        self._placeholder_text = placeholder_text
        self._placeholder_visible = False
        self._compact_popup = None
        super().__init__(master, **kwargs)
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._restore_placeholder)
        self.set("")

    def _resolved_color(self, colors):
        return self._apply_appearance_mode(colors)

    def _show_placeholder(self):
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder_text)
        self._entry.configure(fg=self._resolved_color(SECONDARY_TEXT))
        self._placeholder_visible = True

    def _clear_placeholder(self, _event=None):
        if self._placeholder_visible:
            self._entry.delete(0, "end")
            self._entry.configure(fg=self._resolved_color(PRIMARY_TEXT))
            self._placeholder_visible = False

    def _restore_placeholder(self, _event=None):
        if not super().get().strip():
            self._show_placeholder()

    def _dropdown_callback(self, value):
        self._placeholder_visible = False
        self._entry.configure(fg=self._resolved_color(PRIMARY_TEXT))
        super()._dropdown_callback(value)

    def set(self, value):
        if str(value or ""):
            self._placeholder_visible = False
            self._entry.configure(fg=self._resolved_color(PRIMARY_TEXT))
            super().set(value)
        else:
            self._show_placeholder()

    def get(self):
        return "" if self._placeholder_visible else super().get()

    def _open_dropdown_menu(self):
        if self._compact_popup and self._compact_popup.winfo_exists():
            self._close_compact_popup()
            return
        popup_width = 170
        row_height = 32
        popup_height = row_height * 7 + 12
        x = self.winfo_rootx() + self.winfo_width() - popup_width
        below = self.winfo_rooty() + self.winfo_height() + 2
        y = below if below + popup_height <= self.winfo_screenheight() else self.winfo_rooty() - popup_height - 2

        popup = ctk.CTkToplevel(self)
        self._compact_popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.geometry(f"{popup_width}x{popup_height}+{max(0, x)}+{max(0, y)}")
        popup.transient(self.winfo_toplevel())
        scroll = ctk.CTkScrollableFrame(popup, corner_radius=6)
        scroll.pack(fill="both", expand=True)
        for value in self._values:
            ctk.CTkButton(
                scroll,
                text=value,
                height=row_height,
                anchor="w",
                fg_color="transparent",
                hover_color=CONTROL_BUTTON,
                text_color=PRIMARY_TEXT,
                command=lambda selected=value: self._select_compact_value(selected),
            ).pack(fill="x")
        popup.bind("<Escape>", lambda _event: self._close_compact_popup())
        popup.bind("<FocusOut>", lambda _event: popup.after(50, self._close_if_focus_left_popup))
        popup.protocol("WM_DELETE_WINDOW", self._close_compact_popup)
        popup.deiconify()
        popup.lift()
        popup.focus_force()

    def _close_if_focus_left_popup(self):
        popup = self._compact_popup
        if not popup or not popup.winfo_exists():
            return
        focused = popup.focus_get()
        if focused is None or not str(focused).startswith(str(popup)):
            self._close_compact_popup()

    def _select_compact_value(self, value):
        self.set(value)
        if self._command is not None:
            self._command(value)
        self._close_compact_popup()

    def _close_compact_popup(self):
        popup = self._compact_popup
        self._compact_popup = None
        if popup and popup.winfo_exists():
            popup.destroy()

    def destroy(self):
        self._close_compact_popup()
        super().destroy()


class ManualReviewWindow(EmbeddedPage):
    help_context = "manual_review"
    NEW_DESTINATION = "＋ Neuen Unterordner anlegen …"
    def __init__(self, master, config, document_path, on_filed=None):
        super().__init__(master)
        self.config = config
        self.document_path = Path(document_path)
        self.on_filed = on_filed
        self.profiles = ProfileService(config)
        self.filing = ManualFilingService(config, self.profiles)
        self.profile_items = self.profiles.list_profiles()
        self.person_map = {}
        self.destination_map = {}
        self._last_destination = None
        self.invoice_context = False
        self.invoice_usage = None
        self.tax_receipt = None
        self._name_before_original = None
        self.suggestion_store = ManualReviewSuggestionStore(config)
        self.suggestion = self.suggestion_store.load(self.document_path)
        filename_suggestion = self._filename_suggestion()
        if not self.suggestion:
            self.suggestion = filename_suggestion
        else:
            for key, value in filename_suggestion.items():
                self.suggestion.setdefault(key, value)
            stored_category = self.suggestion.get("category")
            debeka_termination = (
                filename_suggestion.get("category") == "Versicherungen"
                and "debeka" in self.document_path.name.casefold()
            )
            if stored_category in (None, "", "MANUELL") or debeka_termination:
                for key in ("category", "document_type", "destination_parts"):
                    if filename_suggestion.get(key):
                        self.suggestion[key] = filename_suggestion[key]
        self._build()

    def _filename_suggestion(self):
        suggestion = {"year": suggested_year({}, self.document_path.name)}
        filename_words = re.sub(r"[_\-]+", " ", self.document_path.name).casefold()
        if re.search(r"\b(?:rechnung|invoice|kassenbon)\b", filename_words):
            is_receipt = "kassenbon" in filename_words
            suggestion.update({
                "review_kind": "invoice_context",
                "document_label": "Kassenbon" if is_receipt else "Rechnung",
                "invoice_usage": "private",
                "tax_relevant": False,
                "category": "Anschaffungen und Garantien",
                "document_type": "Kassenbons" if is_receipt else "Kaufbelege",
                "destination_parts": [
                    "Anschaffungen und Garantien",
                    "Kassenbons" if is_receipt else "Kaufbelege",
                ],
            })
        settings = self.config.raw.get("profile_system", {}) or {}
        assignment = ProfileMatcher(
            self.profiles,
            settings.get("minimum_assignment_confidence", 0.8),
        ).match_document("", self.document_path.name)
        if assignment:
            suggestion["profile_id"] = assignment.profile_id
            suggestion["person_ids"] = assignment.person_ids
        tentative = tentative_destination(filename=self.document_path.name)
        if tentative and "destination_parts" not in suggestion:
            suggestion["category"], suggestion["document_type"] = tentative
            suggestion["destination_parts"] = list(tentative)
        if likely_general_information_attachment(filename=self.document_path.name):
            suggestion.update({
                "review_kind": "general_information_attachment",
                "review_notice": (
                    "Wahrscheinlich allgemeine Bedingungen – Verwerfen prüfen"
                ),
            })
        return {key: value for key, value in suggestion.items() if value not in (None, "", [])}

    def _build(self):
        self.scroll_content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.scroll_content.pack(fill="both", expand=True)
        content = self.scroll_content

        ctk.CTkLabel(content, text="Dokument zuordnen", font=("Arial", 20, "bold")).pack(anchor="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(content, text=self.document_path.name, wraplength=560).pack(anchor="w", padx=24, pady=(0, 12))
        ctk.CTkButton(content, text="Dokument öffnen", command=lambda: os.startfile(self.document_path)).pack(anchor="w", padx=24, pady=(0, 14))

        self._label("Dokumentname")
        self.name_entry = ctk.CTkEntry(content)
        self.name_entry.pack(fill="x", padx=24)
        self.name_entry.insert(0, self.document_path.stem)
        suggested_name = str(self.suggestion.get("suggested_name") or "").strip()
        if suggested_name:
            suggested_stem = Path(suggested_name).stem
            if suggested_stem:
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, suggested_stem)
        self.original_name_checkbox = ctk.CTkCheckBox(
            content,
            text="Originalnamen verwenden",
            command=self._toggle_original_name,
        )
        self.original_name_checkbox.pack(anchor="w", padx=24, pady=(8, 0))
        ctk.CTkLabel(
            content,
            text=f"Die Dateiendung {self.document_path.suffix} bleibt erhalten.",
            text_color=SECONDARY_TEXT,
        ).pack(anchor="w", padx=24, pady=(3, 0))

        if not self.profile_items:
            ctk.CTkLabel(
                content,
                text="Für die strukturierte Ablage muss zuerst ein Profil angelegt werden.",
            ).pack(pady=(24, 10))
            self._build_external_filing()
            self._build_discard_action()
            return
        if self.suggestion:
            ctk.CTkLabel(
                content,
                text="Vorschlag von Sorterino – bitte die vorausgefüllten Angaben prüfen.",
                text_color=SECONDARY_TEXT,
            ).pack(anchor="w", padx=24, pady=(12, 0))
        if self.suggestion.get("review_kind") == "general_information_attachment":
            self._build_general_information_notice()
        if self.suggestion.get("review_kind") == "exact_duplicate":
            self._build_duplicate_notice()
        if self.suggestion.get("review_kind") == "same_import_duplicate":
            self._build_duplicate_notice()
        if self.suggestion.get("review_kind") == "invoice_context":
            self._build_invoice_context()
        self._label("Profil")
        self.profile_menu = ctk.CTkOptionMenu(
            content,
            values=[p["display_name"] for p in self.profile_items],
            command=lambda _value: self._profile_changed(),
        )
        self.profile_menu.pack(fill="x", padx=24)
        self._label("Betroffene Person (optional)")
        self.person_menu = ctk.CTkOptionMenu(
            content,
            values=["Gemeinsame Dokumente"],
            command=lambda _value: self._person_changed(),
        )
        self.person_menu.pack(fill="x", padx=24)
        self._label("Ablage")
        self.destination_menu = ctk.CTkOptionMenu(
            content,
            values=["Kein Ablageziel verfügbar"],
            command=self._destination_changed,
        )
        self.destination_menu.pack(fill="x", padx=24)

        self._label("Jahr")
        years = available_years()
        self.year_menu = PlaceholderComboBox(
            content,
            values=years,
            placeholder_text="Kein Jahresordner",
        )
        self.year_menu.pack(fill="x", padx=24)
        self.year_menu.set("")

        ctk.CTkButton(content, text="Dokument strukturiert ablegen", command=self.file_document).pack(pady=(26, 14))
        self._build_external_filing()
        self._build_discard_action()
        self._apply_suggestion()

    def _build_general_information_notice(self):
        frame = ctk.CTkFrame(
            self.scroll_content,
            fg_color=("#fff4dd", "#4a3518"),
            border_width=1,
            border_color=("#b87800", "#d79a25"),
        )
        frame.pack(fill="x", padx=24, pady=(14, 2))
        ctk.CTkLabel(
            frame,
            text=self.suggestion.get(
                "review_notice",
                "Wahrscheinlich allgemeine Bedingungen – Verwerfen prüfen",
            ),
            font=("Arial", 14, "bold"),
            text_color=("#5c3900", "#ffd88a"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Sorterino hat vermutlich allgemeine Bedingungen, Datenschutz- oder "
                "Informationsseiten erkannt. Solche Unterlagen lassen sich meist erneut "
                "beim Anbieter abrufen. Du kannst sie unten verwerfen oder wie gewohnt "
                "in deiner Ordnerstruktur aufbewahren."
            ),
            justify="left",
            wraplength=650,
            text_color=("#5c3900", "#ffe7b8"),
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _build_duplicate_notice(self):
        frame = ctk.CTkFrame(
            self.scroll_content,
            fg_color=("#fff4dd", "#4a3518"),
            border_width=1,
            border_color=("#b87800", "#d79a25"),
        )
        frame.pack(fill="x", padx=24, pady=(14, 2))
        ctk.CTkLabel(
            frame,
            text=self.suggestion.get(
                "review_notice", "Bytegleiches Duplikat erkannt"
            ),
            font=("Arial", 14, "bold"),
            text_color=("#5c3900", "#ffd88a"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        duplicate_of = self.suggestion.get("duplicate_of", "")
        selected_import_name = self.suggestion.get("selected_import_name", "")
        if selected_import_name:
            explanation = (
                "Mehrere bytegleiche Dateien waren gleichzeitig im Eingang. Sorterino "
                f"hat „{selected_import_name}“ wegen des aussagekräftigeren Dateinamens "
                "als Hauptdatei ausgewählt und nur diese analysiert."
            )
        elif self.suggestion.get("duplicate_available") is False:
            explanation = (
                "Der Dateiinhalt wurde bereits früher von Sorterino verarbeitet. "
                "Die damals gespeicherte Datei ist momentan jedoch nicht auffindbar."
            )
        else:
            explanation = (
                "Der Dateiinhalt ist bereits vollständig vorhanden. Sorterino hat "
                "diese Kopie nicht erneut analysiert oder automatisch gelöscht."
            )
        ctk.CTkLabel(
            frame,
            text=(
                explanation
                + (f"\nBekannter Speicherort: {duplicate_of}" if duplicate_of else "")
            ),
            justify="left",
            wraplength=650,
            text_color=("#5c3900", "#ffe7b8"),
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _build_invoice_context(self):
        self.invoice_context = True
        document_label = self.suggestion.get("document_label")
        question = (
            "Wie wird dieser Kassenbon verwendet?"
            if document_label == "Kassenbon"
            else "Wie wird diese Rechnung verwendet?"
        )
        frame = ctk.CTkFrame(
            self.scroll_content,
            fg_color="transparent",
            border_width=1,
            border_color=CONTROL_BUTTON,
        )
        frame.pack(fill="x", padx=24, pady=(14, 2))
        ctk.CTkLabel(
            frame,
            text=question,
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Ein privater Kauf bleibt bei der ausgewählten Familie oder Person. „Für eigenes "
                "Unternehmen“ ist ausschließlich für echte Firmenausgaben gedacht. Ob ein privater "
                "Beleg steuerlich absetzbar ist, wird darunter getrennt ausgewählt."
            ),
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=620,
        ).pack(anchor="w", padx=16, pady=(0, 10))
        self.invoice_usage = ctk.CTkSegmentedButton(
            frame,
            values=["Privater Kauf", "Für eigenes Unternehmen", "Noch unklar"],
            command=self._invoice_usage_changed,
        )
        self.invoice_usage.pack(fill="x", padx=16, pady=(0, 10))
        self.tax_receipt = ctk.CTkCheckBox(
            frame,
            text="Privat steuerlich absetzbar – als Steuerbeleg ablegen",
            command=self._tax_receipt_changed,
        )
        self.tax_receipt.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            frame,
            text="Der Beleg landet dann im gewählten Steuerjahr unter „02 Belege / Sonstige Belege“.",
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=620,
        ).pack(anchor="w", padx=42, pady=(0, 14))

    def _build_external_filing(self):
        frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent", border_width=1, border_color=CONTROL_BUTTON)
        frame.pack(fill="x", padx=24, pady=(8, 24))
        ctk.CTkLabel(
            frame,
            text="Außerhalb der Sorterino-Struktur ablegen",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=("Wähle ausnahmsweise einen beliebigen Ordner. Profil, Person, "
                  "Ablageziel und Jahr werden dabei nicht verwendet."),
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            frame,
            text="Anderen Speicherort auswählen",
            command=self.file_document_outside_structure,
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _toggle_original_name(self):
        if self.original_name_checkbox.get():
            self._name_before_original = self.name_entry.get().strip()
            self.name_entry.configure(state="normal")
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, self.document_path.stem)
            self.name_entry.configure(state="disabled")
            return
        self.name_entry.configure(state="normal")
        restored = self._name_before_original or self.document_path.stem
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, restored)

    def _build_discard_action(self):
        frame = ctk.CTkFrame(
            self.scroll_content,
            fg_color="transparent",
            border_width=1,
            border_color=CONTROL_BUTTON,
        )
        frame.pack(fill="x", padx=24, pady=(0, 28))
        ctk.CTkLabel(
            frame,
            text="Dokument nicht aufbewahren",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Für unerwünschte Anhänge wie allgemeine Geschäftsbedingungen oder Werbung. "
                "Dabei wird nur dieses Dokument aus ‚Zu prüfen‘ gelöscht."
            ),
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=16, pady=(0, 10))
        ctk.CTkButton(
            frame,
            text="Dokument verwerfen",
            fg_color="transparent",
            text_color=("#8a1f1f", "#ff8a8a"),
            border_width=1,
            command=self.discard_document,
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _label(self, text):
        ctk.CTkLabel(self.scroll_content, text=text).pack(anchor="w", padx=24, pady=(12, 3))

    def _selected_profile(self):
        name = self.profile_menu.get()
        return next(profile for profile in self.profile_items if profile["display_name"] == name)

    def _profile_changed(self, preferred_person_id=None, preferred_destination=None):
        profile = self._selected_profile()
        members = self.profiles.profile_members(profile["id"])
        self.person_map = {person["display_name"]: person["id"] for person, _membership in members}
        person_values = ["Gemeinsame Dokumente / Profil"] + list(self.person_map)
        self.person_menu.configure(values=person_values)
        self.person_menu.set(person_values[0])
        if preferred_person_id:
            selected = next((name for name, person_id in self.person_map.items() if person_id == preferred_person_id), None)
            if selected:
                self.person_menu.set(selected)
        self._person_changed(preferred_destination)

    def _person_changed(self, preferred_destination=None):
        profile = self._selected_profile()
        person_id = self.person_map.get(self.person_menu.get())
        destinations = self.filing.destinations(profile["id"], person_id)
        self.destination_map = {" › ".join(path.parts): path for path in destinations}
        values = [*self.destination_map, self.NEW_DESTINATION] if self.destination_map else ["Kein Ablageziel verfügbar"]
        self.destination_menu.configure(values=values)
        self.destination_menu.set(values[0])
        if preferred_destination in self.destination_map:
            self.destination_menu.set(preferred_destination)
        self._last_destination = values[0] if self.destination_map else None
        if self.destination_menu.get() in self.destination_map:
            self._last_destination = self.destination_menu.get()

    def _apply_suggestion(self):
        profile_id = self.suggestion.get("profile_id")
        profile = next((item for item in self.profile_items if item.get("id") == profile_id), None)
        if profile:
            self.profile_menu.set(profile["display_name"])
        person_ids = self.suggestion.get("person_ids") or []
        preferred_person = person_ids[0] if len(person_ids) == 1 else None
        if not preferred_person:
            preferred_person = person_id_from_filename(
                self.profiles.profile_members(self._selected_profile()["id"]),
                self.document_path.name,
            )
        self._profile_changed(preferred_person_id=preferred_person)
        destination = best_destination_label(self.destination_map, self.suggestion)
        if destination:
            self.destination_menu.set(destination)
            self._last_destination = destination
        year = str(self.suggestion.get("year") or "")
        if year in available_years():
            self.year_menu.set(year)
        if self.invoice_context:
            usage = {
                "private": "Privater Kauf",
                "business": "Für eigenes Unternehmen",
                "unclear": "Noch unklar",
            }.get(self.suggestion.get("invoice_usage"), "Privater Kauf")
            self.invoice_usage.set(usage)
            if self.suggestion.get("tax_relevant"):
                self.tax_receipt.select()
            self._invoice_usage_changed(usage, quiet=True)

    def _select_destination(self, parts):
        wanted = tuple(parts)
        selected = next(
            (label for label, path in self.destination_map.items() if path.parts == wanted),
            None,
        )
        if selected:
            self.destination_menu.set(selected)
            self._last_destination = selected
        return bool(selected)

    def _invoice_usage_changed(self, selected, quiet=False):
        if not self.invoice_context or not hasattr(self, "profile_menu"):
            return
        if selected == "Für eigenes Unternehmen":
            organizations = [p for p in self.profile_items if p.get("type") == "organization"]
            if not organizations:
                self.invoice_usage.set("Noch unklar")
                if not quiet:
                    messagebox.showinfo(
                        "Kein Firmenprofil vorhanden",
                        "Lege zuerst ein Firmenprofil an oder wähle „Privater Kauf“.",
                        parent=self,
                    )
                return
            current = self._selected_profile()
            target = current if current.get("type") == "organization" else organizations[0]
            self.profile_menu.set(target["display_name"])
            self._profile_changed()
            self._select_destination(("Buchhaltung", "Eingangsrechnungen"))
            self.tax_receipt.deselect()
            self.tax_receipt.configure(state="disabled")
            return

        self.tax_receipt.configure(state="normal" if selected == "Privater Kauf" else "disabled")
        if selected != "Privater Kauf":
            self.tax_receipt.deselect()
            return
        private_profiles = [p for p in self.profile_items if p.get("type") != "organization"]
        preferred_id = self.suggestion.get("profile_id")
        target = next((p for p in private_profiles if p.get("id") == preferred_id), None)
        if target is None and private_profiles:
            target = private_profiles[0]
        if target:
            self.profile_menu.set(target["display_name"])
            person_ids = self.suggestion.get("person_ids") or []
            self._profile_changed(preferred_person_id=person_ids[0] if len(person_ids) == 1 else None)
            self._select_destination(self._private_purchase_destination())
        if self.tax_receipt.get():
            self._tax_receipt_changed()

    def _tax_receipt_changed(self):
        if not self.invoice_context or not self.tax_receipt.get():
            if self.invoice_context and self.invoice_usage.get() == "Privater Kauf":
                self._select_destination(self._private_purchase_destination())
            return
        if not self.year_menu.get().strip():
            suggested = str(self.suggestion.get("year") or "")
            if suggested in available_years():
                self.year_menu.set(suggested)

    def _private_purchase_destination(self):
        if self.suggestion.get("document_label") == "Kassenbon":
            return "Anschaffungen und Garantien", "Kassenbons"
        return "Anschaffungen und Garantien", "Kaufbelege"

    def _destination_changed(self, selected):
        if selected != self.NEW_DESTINATION:
            if selected in self.destination_map:
                self._last_destination = selected
            return
        parent_label = self._last_destination
        if not parent_label or parent_label not in self.destination_map:
            self.destination_menu.set(next(iter(self.destination_map), "Kein Ablageziel verfügbar"))
            return
        value = simpledialog.askstring(
            "Neuen Unterordner anlegen",
            f'Unterhalb von „{parent_label}“ einen neuen Ordner anlegen.\n\n'
            "Für mehrere Ebenen verwende einen Schrägstrich, z. B. Fortbildungen/Zertifikate:",
            parent=self,
        )
        if value is None:
            self.destination_menu.set(parent_label)
            return
        try:
            parts = self.filing._folder_parts(value)
            preview = self.destination_map[parent_label].joinpath(*parts)
            if not messagebox.askyesno(
                "Ablageziel hinzufügen",
                f"Dieses Ablageziel wird künftig in diesem Kontext angeboten:\n\n{preview}\n\nJetzt hinzufügen?",
                parent=self,
            ):
                self.destination_menu.set(parent_label)
                return
            profile = self._selected_profile()
            person_id = self.person_map.get(self.person_menu.get())
            target = self.filing.add_destination(
                profile["id"], self.destination_map[parent_label], value, person_id
            )
            self._person_changed()
            target_label = str(target)
            if target_label in self.destination_map:
                self.destination_menu.set(target_label)
                self._last_destination = target_label
        except (OSError, ProfileValidationError) as exc:
            self.destination_menu.set(parent_label)
            messagebox.showerror("Ablageziel nicht angelegt", str(exc), parent=self)

    def file_document(self):
        if not self.destination_map:
            messagebox.showwarning("Keine Ablage", "Für dieses Profil ist keine Ablagestruktur verfügbar.", parent=self)
            return
        profile = self._selected_profile()
        person_id = self.person_map.get(self.person_menu.get())
        destination = self.destination_map[self.destination_menu.get()]
        tax_receipt = False
        if self.invoice_context:
            usage = self.invoice_usage.get()
            if usage == "Noch unklar":
                messagebox.showwarning(
                    "Verwendung noch unklar",
                    "Bitte entscheide, ob es ein privater Kauf oder eine Ausgabe für ein eigenes Unternehmen ist.",
                    parent=self,
                )
                return
            if usage == "Für eigenes Unternehmen" and profile.get("type") != "organization":
                messagebox.showwarning(
                    "Firmenprofil auswählen",
                    "Für eine geschäftliche Rechnung muss ein Firmenprofil ausgewählt sein.",
                    parent=self,
                )
                return
            if usage == "Privater Kauf" and profile.get("type") == "organization":
                messagebox.showwarning(
                    "Privates Profil auswählen",
                    "Für eine private Rechnung muss eine Familie oder Privatperson ausgewählt sein.",
                    parent=self,
                )
                return
            tax_receipt = usage == "Privater Kauf" and bool(self.tax_receipt.get())
        try:
            selected_year = self.year_menu.get().strip()
            final = self.filing.file_document(
                self.document_path,
                profile["id"],
                destination,
                person_id,
                year=selected_year or None,
                new_name=self.name_entry.get(),
                tax_receipt=tax_receipt,
            )
            self._filing_succeeded(final)
        except (OSError, ProfileValidationError) as exc:
            messagebox.showerror("Ablage fehlgeschlagen", str(exc), parent=self)

    def file_document_outside_structure(self):
        destination = filedialog.askdirectory(
            parent=self,
            title="Speicherort für Dokument auswählen",
        )
        if not destination:
            return
        try:
            profile_id = None
            if self.profile_items and hasattr(self, "profile_menu"):
                profile_id = self._selected_profile().get("id")
            final = self.filing.file_document_outside_structure(
                self.document_path,
                destination,
                new_name=self.name_entry.get(),
                profile_id=profile_id,
            )
            self._filing_succeeded(final)
        except (OSError, ProfileValidationError) as exc:
            messagebox.showerror("Ablage fehlgeschlagen", str(exc), parent=self)

    def discard_document(self):
        if not messagebox.askyesno(
            "Dokument endgültig verwerfen",
            f"Soll dieses Dokument wirklich endgültig gelöscht werden?\n\n{self.document_path.name}",
            icon="warning",
            parent=self,
        ):
            return
        try:
            self.filing.discard_document(self.document_path)
            self.suggestion_store.remove(self.document_path)
        except (OSError, ProfileValidationError) as exc:
            messagebox.showerror("Dokument nicht gelöscht", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Dokument verworfen",
            "Das Dokument wurde aus ‚Zu prüfen‘ gelöscht.",
            parent=self,
        )
        if self.on_filed:
            self.on_filed()
        self.finish()

    def _filing_succeeded(self, final):
        self.suggestion_store.remove(self.document_path)
        backup = self.filing.last_backup_path
        details = f"Das Dokument wurde abgelegt:\n{final}"
        if backup:
            details += f"\n\nOriginal-Backup:\n{backup}"
        messagebox.showinfo("Abgelegt", details, parent=self)
        if self.on_filed:
            self.on_filed()
        self.finish()
