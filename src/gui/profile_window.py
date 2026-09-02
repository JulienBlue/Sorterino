from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime

import customtkinter as ctk

from src.profile_service import ProfileService, ProfileValidationError
from src.gui.embedded import EmbeddedPage
from src.gui.appearance import (
    CONTROL_BG,
    CONTROL_BUTTON,
    CONTROL_HOVER,
    DANGER_BG,
    DANGER_TEXT,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
)
from src.person_age import is_minor_from_birth_date
from src.gui.profile_deletion import (
    confirm_permanent_delete as _confirm_permanent_delete,
    delete_archive_paths as _delete_archive_paths,
    delete_confirmation_message as _delete_confirmation_message,
    delete_mail_credentials as _delete_mail_passwords,
    person_archive_paths as _person_archive_paths,
    profile_archive_paths as _profile_archive_paths,
)
from src.profile_labels import (
    FAMILY_ROLES,
    GENDER_LABELS,
    GENDER_VALUES,
    ORGANIZATION_POSITIONS,
    PARTNER_RELATIONSHIP_LABELS,
    PARTNER_RELATIONSHIP_TYPES,
    all_people_assigned_message as _all_people_assigned_message,
    available_people_for_profile as _available_people_for_profile,
    family_profiles_for_person as _family_profiles_for_person,
    membership_label as _membership_label,
    profile_saved_message as _profile_saved_message,
    split_csv as _split_csv,
)


class DateEntry(ctk.CTkFrame):
    """Three-part numeric date input with normal native editing behavior."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.day = self._part("TT", 2, 56)
        ctk.CTkLabel(self, text=".", font=("Arial", 18, "bold"), width=12).pack(side="left", padx=2)
        self.month = self._part("MM", 2, 56)
        ctk.CTkLabel(self, text=".", font=("Arial", 18, "bold"), width=12).pack(side="left", padx=2)
        self.year = self._part("JJJJ", 4, 88)
        self.day.bind("<KeyRelease>", lambda event: self._advance(event, self.day, self.month, 2))
        self.month.bind("<KeyRelease>", lambda event: self._advance(event, self.month, self.year, 2))
        self.month.bind("<BackSpace>", lambda _event: self._back(self.month, self.day))
        self.year.bind("<BackSpace>", lambda _event: self._back(self.year, self.month))

    def _part(self, label, limit, width):
        validate = (self.register(lambda proposed, maximum=limit: proposed.isdigit() and len(proposed) <= maximum or proposed == ""), "%P")
        entry = ctk.CTkEntry(
            self,
            width=width,
            justify="center",
            placeholder_text=label,
            validate="key",
            validatecommand=validate,
        )
        entry.pack(side="left")
        return entry

    @staticmethod
    def _advance(event, current, following, limit):
        if event.keysym.isdigit() and len(current.get()) == limit:
            following.focus_set()
            following.select_range(0, "end")

    @staticmethod
    def _back(current, previous):
        if not current.get():
            previous.focus_set()
            previous.icursor("end")

    def set_date(self, value):
        raw = str(value or "").strip()
        for entry in (self.day, self.month, self.year):
            entry.delete(0, "end")
        if not raw:
            return
        parsed = None
        for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, date_format)
                break
            except ValueError:
                continue
        if parsed:
            values = parsed.strftime("%d.%m.%Y").split(".")
            for entry, part in zip((self.day, self.month, self.year), values):
                entry.insert(0, part)
            return
        digits = "".join(char for char in raw if char.isdigit())[:8]
        for entry, part in zip((self.day, self.month, self.year), (digits[:2], digits[2:4], digits[4:8])):
            entry.insert(0, part)

    def date_value(self):
        day, month, year = (entry.get().strip() for entry in (self.day, self.month, self.year))
        if not day and not month and not year:
            return ""
        if not day or not month or len(year) != 4:
            raise ValueError("Das Geburtsdatum muss vollständig im Format TT.MM.JJJJ eingegeben werden.")
        value = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
        try:
            datetime.strptime(value, "%d.%m.%Y")
        except ValueError as exc:
            raise ValueError("Das Geburtsdatum ist kein gültiges Datum im Format TT.MM.JJJJ.") from exc
        return value


class OrganizationPositionInput(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.menu = ctk.CTkOptionMenu(
            self,
            values=ORGANIZATION_POSITIONS,
            command=self._selection_changed,
        )
        self.menu.pack(fill="x")
        self.menu.set(ORGANIZATION_POSITIONS[0])
        self.custom = ctk.CTkEntry(self, placeholder_text="Eigene Funktion eingeben")

    def _selection_changed(self, value):
        if value == "Eigene Funktion …":
            self.custom.pack(fill="x", pady=(8, 0))
            self.custom.focus_set()
        else:
            self.custom.pack_forget()

    def get(self):
        selected = self.menu.get()
        if selected == "Eigene Funktion …":
            custom = self.custom.get().strip()
            if not custom:
                raise ProfileValidationError("Bitte gib die eigene Funktion in der Firma ein.")
            return custom
        return selected


class FamilyRoleInput(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.menu = ctk.CTkOptionMenu(self, values=list(FAMILY_ROLES), command=self._selection_changed)
        self.menu.pack(fill="x")
        self.menu.set("Elternteil")
        self.custom = ctk.CTkEntry(self, placeholder_text="Eigene Beziehung eingeben")

    def _selection_changed(self, value):
        if FAMILY_ROLES[value] is None:
            self.custom.pack(fill="x", pady=(8, 0))
            self.custom.focus_set()
        else:
            self.custom.pack_forget()

    def get(self):
        selected = self.menu.get()
        role = FAMILY_ROLES[selected]
        if role is None:
            role = self.custom.get().strip()
            if not role:
                raise ProfileValidationError("Bitte gib die eigene Beziehung zur Familie ein.")
        return role


class NewProfilePage(EmbeddedPage):
    help_context = "profile_new"
    def __init__(self, master, service, profile_type, on_saved=None):
        super().__init__(master)
        self.service = service
        self.profile_type = profile_type
        self.on_saved = on_saved
        is_family = profile_type == "family"
        title = "Familie anlegen" if is_family else "Firma oder Organisation anlegen"
        ctk.CTkLabel(self, text=title, font=("Arial", 22, "bold")).pack(anchor="w", padx=28, pady=(26, 8))
        ctk.CTkLabel(
            self,
            text="Schritt 2 von 2 · Grunddaten",
            text_color=SECONDARY_TEXT,
        ).pack(anchor="w", padx=28)
        ctk.CTkLabel(self, text="Name *").pack(anchor="w", padx=28, pady=(16, 4))
        self.name = ctk.CTkEntry(self, placeholder_text="Familienname" if is_family else "Firmen- oder Organisationsname")
        self.name.pack(fill="x", padx=28)
        ctk.CTkButton(self, text="Profil anlegen", command=self.save).pack(anchor="w", padx=28, pady=22)

    def save(self):
        name = self.name.get().strip()
        if not name:
            messagebox.showwarning("Angabe fehlt", "Bitte einen Namen eingeben.", parent=self)
            return
        try:
            if self.profile_type == "family":
                profile = self.service.create_family(name)
            else:
                profile = self.service.create_organization(name)
            if not self.on_saved or not self.on_saved(profile["id"]):
                self.finish()
        except ProfileValidationError as exc:
            messagebox.showerror("Profil konnte nicht angelegt werden", str(exc), parent=self)


class ProfileCreationWizard(EmbeddedPage):
    help_context = "profile_new"

    OPTIONS = (
        (
            "individual",
            "Person",
            "Für eine einzelne Person mit eigener privater Ablage. Bereits vorhandene Personendaten können übernommen werden.",
        ),
        (
            "family",
            "Familie",
            "Für gemeinsame Dokumente und persönliche Unterordner der Familienmitglieder, einschließlich Kindern.",
        ),
        (
            "organization",
            "Firma oder Organisation",
            "Für geschäftliche Dokumente, eigene Postfächer sowie Mitarbeiter und deren Positionen.",
        ),
    )

    def __init__(self, master, on_continue):
        super().__init__(master)
        self.on_continue = on_continue
        self.profile_type = ctk.StringVar(value="")
        ctk.CTkLabel(
            self,
            text="Neues Profil anlegen",
            font=("Arial", 24, "bold"),
        ).pack(anchor="w", padx=30, pady=(28, 5))
        ctk.CTkLabel(
            self,
            text="Schritt 1 von 2 · Was möchtest du verwalten?",
            text_color=SECONDARY_TEXT,
        ).pack(anchor="w", padx=30, pady=(0, 18))

        choices = ctk.CTkScrollableFrame(self, fg_color="transparent")
        choices.pack(fill="both", expand=True, padx=24)
        for value, title, description in self.OPTIONS:
            card = ctk.CTkFrame(choices, border_width=1, border_color=("gray78", "gray30"))
            card.pack(fill="x", pady=6)
            ctk.CTkRadioButton(
                card,
                text=title,
                variable=self.profile_type,
                value=value,
                font=("Arial", 16, "bold"),
            ).pack(anchor="w", padx=18, pady=(14, 4))
            ctk.CTkLabel(
                card,
                text=description,
                justify="left",
                wraplength=680,
            ).pack(anchor="w", padx=48, pady=(0, 14))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=30, pady=(12, 24))
        ctk.CTkButton(
            actions,
            text="Weiter",
            command=self.continue_creation,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Abbrechen",
            fg_color="transparent",
            border_width=1,
            text_color=PRIMARY_TEXT,
            command=self.finish,
        ).pack(side="left", padx=8)

    def continue_creation(self):
        selected = self.profile_type.get()
        if selected not in {value for value, _title, _description in self.OPTIONS}:
            messagebox.showwarning(
                "Profilart auswählen",
                "Bitte wähle aus, was für ein Profil angelegt werden soll.",
                parent=self,
            )
            return
        self.on_continue(selected)


class ProfileWindow(EmbeddedPage):
    help_context = "profiles"
    def __init__(self, master=None, config=None, selected_id=None):
        super().__init__(master)
        self.host_navigator = self.navigator
        self.config = config
        self.service = ProfileService(config)
        self.service.promote_unassigned_persons()
        self._build_ui()
        self.refresh(selected_id)

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Profile",
            font=("Arial", 25, "bold"),
        ).pack(anchor="w", padx=30, pady=(26, 2))
        ctk.CTkLabel(
            self,
            text="Personen, Familien und Firmen verwalten",
            text_color=SECONDARY_TEXT,
        ).pack(anchor="w", padx=30, pady=(0, 18))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        sidebar_column = ctk.CTkFrame(body, width=300, fg_color="transparent")
        sidebar_column.pack(side="left", fill="y", padx=10, pady=10)
        sidebar_column.pack_propagate(False)
        ctk.CTkButton(
            sidebar_column,
            text="Neues Profil anlegen",
            command=self.add_profile,
        ).pack(side="bottom", fill="x", pady=(8, 0))
        self.sidebar = ctk.CTkScrollableFrame(sidebar_column, label_text="Profile")
        self.sidebar.pack(side="top", fill="both", expand=True)
        self.detail = ctk.CTkScrollableFrame(body, label_text="Details")
        self.detail.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

    def refresh(self, selected_id=None):
        self.service.reload()
        for child in self.sidebar.winfo_children():
            child.destroy()
        profiles = self.service.list_profiles()
        if not profiles:
            ctk.CTkLabel(
                self.sidebar,
                text="Noch kein Profil angelegt.",
                wraplength=240,
            ).pack(pady=20)
            self._clear_detail()
            ctk.CTkLabel(
                self.detail,
                text="Lege eine Privatperson, Familie oder Firma an.",
                font=("Arial", 18, "bold"),
                wraplength=480,
            ).pack(anchor="w", pady=(18, 8))
            if self.service.legacy_migration_available():
                ctk.CTkLabel(
                    self.detail,
                    text="Es wurden Daten aus der bisherigen Version für Privatpersonen gefunden.",
                    wraplength=480,
                ).pack(anchor="w", pady=(18, 6))
                ctk.CTkButton(
                    self.detail,
                    text="Bisherige Daten als Profil übernehmen",
                    command=self._migrate_legacy,
                ).pack(anchor="w")
            return
        for profile in profiles:
            kind = {"family": "Familie", "organization": "Organisation", "individual": "Privatperson"}.get(profile["type"], "Profil")
            ctk.CTkButton(
                self.sidebar,
                text=f"{profile['display_name']}\n{kind}",
                command=lambda pid=profile["id"]: self.show_profile(pid),
            ).pack(fill="x", pady=4)
        self.show_profile(selected_id or profiles[0]["id"])

    def _clear_detail(self):
        for child in self.detail.winfo_children():
            child.destroy()

    def show_profile(self, profile_id):
        previous_detail = self.detail
        next_detail = ctk.CTkScrollableFrame(previous_detail.master, label_text='Details')
        self.detail = next_detail
        try:
            self._render_profile_detail(profile_id)
        except Exception:
            next_detail.destroy()
            self.detail = previous_detail
            raise
        next_detail.pack(side='left', fill='both', expand=True, padx=(0, 10), pady=10)
        next_detail.lift()
        previous_detail.destroy()

    def _render_profile_detail(self, profile_id):
        profile = self.service.get_profile(profile_id)
        if not profile:
            return
        kind = {"family": "Familie", "organization": "Firma / Organisation", "individual": "Privatperson"}.get(profile["type"], "Profil")
        ctk.CTkLabel(self.detail, text=profile["display_name"], font=("Arial", 20, "bold")).pack(anchor="w")
        routing = profile.get("routing", {}) or {}
        storage_label = (
            self.config.get("user_path")
            if routing.get("use_global_storage", True)
            else routing.get("storage_root", "")
        )
        ctk.CTkLabel(
            self.detail,
            text=f"Speicherort: {storage_label or 'nicht gesetzt'}",
            wraplength=540,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        buttons = ctk.CTkFrame(self.detail, fg_color="transparent")
        buttons.pack(fill="x", pady=(0, 12))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            buttons,
            text="Profil bearbeiten",
            command=lambda: self._open(ProfileEditDialog, self.service, profile_id, self._return_to_profiles),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(
            buttons,
            text="E-Mail-Postfächer",
            command=lambda: self._open_profile_mail(profile_id),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)
        if profile["type"] != "individual":
            member_name = "Familienmitglied" if profile["type"] == "family" else "Mitarbeiter"
            ctk.CTkButton(
                buttons,
                text="Vorhandene Person zuordnen",
                command=lambda: self._assign_existing_person(profile_id),
            ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
            ctk.CTkButton(
                buttons,
                text=("Neues Familienmitglied hinzufügen" if profile["type"] == "family" else "Neuen Mitarbeiter hinzufügen"),
                command=lambda: self._open(PersonDialog, self.service, self._return_to_profiles, profile_id),
            ).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)

        member_heading = {
            "family": "Familienmitglieder",
            "organization": "Mitarbeiter",
            "individual": "Personendaten",
        }.get(profile["type"], "Personen")
        ctk.CTkLabel(self.detail, text=member_heading, font=("Arial", 16, "bold")).pack(anchor="w", pady=(8, 4))
        members = self.service.profile_members(profile_id)
        if not members:
            empty_name = "Familienmitglieder" if profile["type"] == "family" else "Mitarbeiter"
            ctk.CTkLabel(self.detail, text=f"Diesem Profil sind noch keine {empty_name} zugeordnet.").pack(anchor="w")
        for person, membership in members:
            row = ctk.CTkFrame(self.detail)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=person["display_name"], font=("Arial", 14, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
            role = _membership_label(profile.get("type"), person, membership)
            ctk.CTkLabel(row, text=role).pack(anchor="w", padx=12, pady=(0, 8))
            ctk.CTkButton(
                row,
                text="Bearbeiten",
                width=90,
                command=lambda pid=person["id"], selected=profile_id: self._open(
                    PersonDialog,
                    self.service,
                    lambda *_: self._return_to_profiles(selected),
                    person_id=pid,
                ),
            ).pack(side="right", padx=8, pady=8)
            if profile.get("type") != "individual":
                role_name = role
                ctk.CTkButton(
                    row,
                    text="Entfernen",
                    width=90,
                    fg_color=DANGER_BG,
                    hover_color=("gray84", "gray27"),
                    border_width=1,
                    border_color=("gray72", "gray38"),
                    text_color=DANGER_TEXT,
                    command=lambda pid=person["id"], label=role_name: self._remove_member(profile_id, pid, label),
                ).pack(side="right", padx=(0, 2), pady=8)

        delete_area = ctk.CTkFrame(self.detail, fg_color="transparent")
        delete_area.pack(fill="x", pady=(28, 4))
        ctk.CTkButton(
            delete_area,
            text=f"{kind} löschen",
            height=34,
            fg_color=DANGER_BG,
            hover_color=("gray84", "gray27"),
            border_width=1,
            border_color=("gray72", "gray38"),
            text_color=DANGER_TEXT,
            command=lambda: self._delete_profile(profile_id),
        ).pack(side="right")

    def add_profile(self):
        self._open(ProfileCreationWizard, self._start_profile_creation)

    def _assign_existing_person(self, profile_id):
        profile = self.service.get_profile(profile_id)
        if not profile:
            return
        if not _available_people_for_profile(self.service, profile_id):
            messagebox.showinfo(
                "Keine weitere Person verfügbar",
                _all_people_assigned_message(profile.get("type")),
                parent=self,
            )
            return
        self._open(
            MembershipDialog,
            self.service,
            profile_id,
            self._return_to_profiles,
        )

    def _start_profile_creation(self, profile_type):
        if profile_type == "individual":
            self._open(IndividualDialog, self.service, self._return_to_profiles)
        elif profile_type in {"family", "organization"}:
            self._open(
                NewProfilePage,
                self.service,
                profile_type,
                self._edit_new_profile,
            )

    def _return_to_profiles(self, selected_id=None):
        if self.host_navigator and hasattr(self.host_navigator, "return_to_profiles"):
            profile = self.service.get_profile(selected_id) if selected_id else None
            self.host_navigator.return_to_profiles(selected_id, _profile_saved_message(profile))
            return True
        return False

    def _edit_new_profile(self, profile_id):
        self._open(
            ProfileEditDialog,
            self.service,
            profile_id,
            self._return_to_profiles,
        )
        return True

    def _delete_profile(self, profile_id):
        profile = self.service.get_profile(profile_id)
        if not profile:
            return
        kind = {"family": "die Familie", "organization": "die Firma", "individual": "die Privatperson"}.get(
            profile.get("type"), "das Profil"
        )
        label = f'{kind} „{profile["display_name"]}“'

        delete_person = profile.get("type") == "individual"
        family_profiles = (
            _family_profiles_for_person(self.service, profile.get("person_id"))
            if delete_person else []
        )
        if family_profiles:
            family_names = "\n".join(f'• {item["display_name"]}' for item in family_profiles)
            family_choice = messagebox.askyesnocancel(
                "Familienzuordnungen der Privatperson",
                f'Die Privatperson „{profile["display_name"]}“ gehört außerdem zu:\n\n'
                f"{family_names}\n\n"
                "Soll die Person auch aus diesen Familien entfernt und vollständig aus Sorterino gelöscht werden?\n\n"
                "Ja: Person und Familienzuordnungen vollständig löschen\n"
                "Nein: Nur das Privatpersonenprofil löschen; Person, Familienzuordnungen und Dokumente behalten\n"
                "Abbrechen: Nichts ändern",
                icon="warning",
                parent=self,
            )
            if family_choice is None:
                return
            delete_person = family_choice

        if family_profiles and not delete_person:
            warning = (
                "Die Person bleibt Mitglied in: "
                + ", ".join(item["display_name"] for item in family_profiles)
                + ". Ihre Personendaten und Dokumente bleiben erhalten."
            )
            if not _confirm_permanent_delete(self, label, "keep_files", warning):
                return
            try:
                account_ids = self.service.delete_profile(profile_id)
                _delete_mail_passwords(account_ids, self.service.config)
                self.refresh()
            except ProfileValidationError as exc:
                messagebox.showerror("Löschen fehlgeschlagen", str(exc), parent=self)
            return

        delete_files = messagebox.askyesnocancel(
            "Was soll gelöscht werden?",
            f"Sollen zusätzlich die eindeutig zugehörigen Dateiordner von {label} gelöscht werden?\n\n"
            "Ja: Konfiguration und Dateiordner löschen\n"
            "Nein: Nur Konfiguration löschen, alle Dokumente behalten\n"
            "Abbrechen: Nichts ändern",
            icon="warning",
            parent=self,
        )
        if delete_files is None:
            return
        employee_actions = {}
        employee_warning = ""
        if profile.get("type") == "organization":
            employees = [person for person, _membership in self.service.profile_members(profile_id)]
            choice = self._choose_employee_actions(profile, employees)
            if choice is None:
                return
            employee_actions = choice
            private_names = [
                person["display_name"] for person in employees
                if employee_actions.get(person["id"]) == "private"
            ]
            deleted_names = [
                person["display_name"] for person in employees
                if employee_actions.get(person["id"]) == "delete"
            ]
            parts = []
            if private_names:
                parts.append("Als Privatperson behalten: " + ", ".join(private_names))
            if deleted_names:
                parts.append(
                    "Vollständig aus Sorterino löschen – einschließlich anderer Profilzuordnungen: "
                    + ", ".join(deleted_names)
                )
            employee_warning = "\n".join(parts)
        archive_paths, skipped = _profile_archive_paths(self.service, profile) if delete_files else ([], [])
        if not _confirm_permanent_delete(
            self,
            label,
            "delete_files" if delete_files else "keep_files",
            employee_warning,
        ):
            return
        try:
            account_ids = []
            if profile.get("type") == "individual":
                account_ids.extend(self.service.delete_person(profile.get("person_id")))
            else:
                for person_id, action in employee_actions.items():
                    if action == "delete":
                        account_ids.extend(self.service.delete_person(person_id))
                account_ids.extend(self.service.delete_profile(profile_id))
                for person_id, action in employee_actions.items():
                    if action == "private" and self.service.get_person(person_id):
                        self.service.ensure_individual_profile(person_id)
            _delete_mail_passwords(account_ids, self.service.config)
            if delete_files:
                _delete_archive_paths(self, archive_paths)
                if skipped:
                    messagebox.showwarning(
                        "Gemeinsam genutzte Ordner behalten",
                        "Diese Ordner werden noch von einem anderen Profil verwendet und wurden nicht gelöscht:\n\n"
                        + "\n".join(str(path) for path in skipped),
                        parent=self,
                    )
            self.refresh()
        except ProfileValidationError as exc:
            messagebox.showerror("Löschen fehlgeschlagen", str(exc), parent=self)

    def _choose_employee_actions(self, profile, employees):
        if not employees:
            return {}
        choice = simpledialog.askstring(
            "Mitarbeiter beim Löschen der Firma",
            f'Was soll mit den {len(employees)} Mitarbeitern von „{profile["display_name"]}“ geschehen?\n\n'
            "PRIVAT = alle als sichtbare Privatpersonen behalten\n"
            "AUSWÄHLEN = für jede Person einzeln entscheiden\n"
            "ALLE LÖSCHEN = alle vollständig aus Sorterino löschen\n\n"
            "Gib eine der drei Angaben exakt ein:",
            parent=self,
        )
        if choice is None:
            return None
        normalized = choice.strip().upper()
        if normalized == "PRIVAT":
            return {person["id"]: "private" for person in employees}
        if normalized == "ALLE LÖSCHEN":
            if not messagebox.askyesno(
                "Alle Mitarbeiter vollständig löschen?",
                "Dadurch werden die Personen auch aus anderen Familien und Firmen sowie aus vorhandenen "
                "Privatpersonenprofilen entfernt. Dokumente bleiben entsprechend der separat gewählten "
                "Dateioption erhalten oder werden gelöscht. Wirklich fortfahren?",
                icon="warning",
                parent=self,
            ):
                return None
            return {person["id"]: "delete" for person in employees}
        if normalized == "AUSWÄHLEN":
            actions = {}
            for person in employees:
                delete_person = messagebox.askyesnocancel(
                    f'Mitarbeiter „{person["display_name"]}“',
                    "Ja: Person vollständig aus Sorterino und allen Profilen löschen\n"
                    "Nein: Als Privatperson behalten\n"
                    "Abbrechen: Gesamten Löschvorgang abbrechen",
                    icon="warning",
                    parent=self,
                )
                if delete_person is None:
                    return None
                actions[person["id"]] = "delete" if delete_person else "private"
            return actions
        messagebox.showwarning(
            "Ungültige Auswahl",
            "Die Eingabe muss exakt PRIVAT, AUSWÄHLEN oder ALLE LÖSCHEN lauten. Es wurde nichts gelöscht.",
            parent=self,
        )
        return None

    def _remove_member(self, profile_id, person_id, role_name):
        person = self.service.get_person(person_id)
        profile = self.service.get_profile(profile_id)
        if not person or not profile:
            return
        only_membership = messagebox.askyesnocancel(
            f"{role_name} entfernen",
            f'Wie soll „{person["display_name"]}“ entfernt werden?\n\n'
            f"Ja: Nur aus „{profile['display_name']}“ entfernen; Person und Dateien behalten\n"
            "Nein: Person vollständig aus Sorterino löschen\n"
            "Abbrechen: Nichts ändern",
            icon="warning",
            parent=self,
        )
        if only_membership is None:
            return
        if only_membership:
            label = f'die Zuordnung von „{person["display_name"]}“ zu „{profile["display_name"]}“'
            if not _confirm_permanent_delete(self, label, "membership_only"):
                return
            self.service.remove_membership(profile_id, person_id)
            self.refresh(profile_id)
            return

        delete_files = messagebox.askyesnocancel(
            "Dateien der Person",
            "Sollen zusätzlich eindeutig zugehörige persönliche Dateiordner gelöscht werden?\n\n"
            "Ja: Person, Zuordnungen und persönliche Ordner löschen\n"
            "Nein: Person und Zuordnungen löschen, Dokumente behalten\n"
            "Abbrechen: Nichts ändern",
            icon="warning",
            parent=self,
        )
        if delete_files is None:
            return
        archive_paths, skipped = _person_archive_paths(self.service, person_id) if delete_files else ([], [])
        if not _confirm_permanent_delete(
            self,
            f'die Person „{person["display_name"]}“ in allen Profilen',
            "delete_files" if delete_files else "keep_files",
        ):
            return
        account_ids = self.service.delete_person(person_id)
        _delete_mail_passwords(account_ids, self.service.config)
        if delete_files:
            _delete_archive_paths(self, archive_paths)
            if skipped:
                messagebox.showwarning(
                    "Gemeinsam genutzte Ordner behalten",
                    "Mehrdeutige oder gemeinsam genutzte Ordner wurden aus Sicherheitsgründen nicht gelöscht:\n\n"
                    + "\n".join(str(path) for path in skipped),
                    parent=self,
                )
        self.refresh(profile_id)

    def _open(self, page_class, *args, **kwargs):
        if self.host_navigator:
            self.host_navigator.open_view(
                lambda parent: page_class(parent, *args, **kwargs),
                "profiles",
            )

    def _migrate_legacy(self):
        if not messagebox.askyesno(
            "Daten übernehmen",
            "Die bisherigen persönlichen beziehungsweise Firmendaten werden in das neue Profilmodell kopiert. Die alten Daten bleiben als Rückfall erhalten.",
            parent=self,
        ):
            return
        try:
            self.service.migrate_legacy_company_profile()
            self.refresh()
        except ProfileValidationError as exc:
            messagebox.showerror("Übernahme fehlgeschlagen", str(exc), parent=self)

    def _open_profile_mail(self, profile_id):
        from src.gui.mail_window import ProfileMailAccountsWindow
        self._open(ProfileMailAccountsWindow, self.config, profile_id, self._return_to_profiles)

class PersonDialog(EmbeddedPage):
    help_context = "person"
    def __init__(self, master, service, on_saved, profile_id=None, person_id=None, return_person=False):
        super().__init__(master)
        self.service = service
        self.on_saved = on_saved
        self.profile_id = profile_id
        self.person = service.get_person(person_id) if person_id else None
        self.return_person = return_person
        self.entries = {}
        self._build()
        if self.person:
            self._load()

    def _field(self, parent, key, label):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=12, pady=(8, 2))
        entry = ctk.CTkEntry(parent)
        entry.pack(fill="x", padx=12)
        self.entries[key] = entry
        return entry

    def _build(self):
        ctk.CTkLabel(
            self,
            text="Person bearbeiten" if self.person else "Person hinzufügen",
            font=("Arial", 22, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 0))
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=16)
        base_tab = tabs.add("Stammdaten")
        ids_tab = tabs.add("Kennungen")
        base = ctk.CTkScrollableFrame(base_tab, fg_color="transparent")
        base.pack(fill="both", expand=True)
        ids = ctk.CTkScrollableFrame(ids_tab, fg_color="transparent")
        ids.pack(fill="both", expand=True)
        ctk.CTkLabel(
            base,
            text="* Pflichtfeld    ·    *** empfohlen für eine bessere Erkennung",
            text_color=SECONDARY_TEXT,
        ).pack(anchor="w", padx=12, pady=(6, 2))

        self._field(base, "first_name", "Vorname *")
        self._field(base, "second_first_name", "Zweiter Vorname")
        self._field(base, "last_name", "Nachname *")
        self._field(base, "birth_name", "Geburtsname")
        ctk.CTkLabel(base, text="Geschlecht").pack(anchor="w", padx=12, pady=(8, 2))
        self.gender = ctk.CTkOptionMenu(base, values=list(GENDER_VALUES))
        self.gender.pack(fill="x", padx=12)
        self.gender.set("Keine Angabe")
        ctk.CTkLabel(base, text="Geburtsdatum ***").pack(anchor="w", padx=12, pady=(8, 2))
        self.entries["date_of_birth"] = DateEntry(base)
        self.entries["date_of_birth"].pack(fill="x", padx=12)
        self._field(base, "place_of_birth", "Geburtsort")
        self._field(base, "street", "Straße")
        self._field(base, "house_number", "Hausnummer")
        self._field(base, "postal_code", "PLZ")
        self._field(base, "city", "Ort")
        self._field(base, "emails", "E-Mail-Adressen *** (Komma getrennt)")
        self._field(base, "phones", "Telefonnummern (Komma getrennt)")
        profile = self.service.get_profile(self.profile_id) if self.profile_id else None
        self.organization_position = None
        if profile and profile.get("type") == "organization" and not self.person:
            ctk.CTkLabel(base, text="Funktion in der Firma").pack(anchor="w", padx=12, pady=(14, 2))
            self.organization_position = OrganizationPositionInput(base)
            self.organization_position.pack(fill="x", padx=12)

        self._field(ids, "tax_id", "Steueridentifikationsnummer ***")
        self._field(ids, "tax_numbers", "Steuernummern (Komma getrennt)")
        self._field(ids, "health_insurer", "Krankenkasse")
        self._field(ids, "health_number", "Krankenversichertennummer ***")
        self._field(ids, "pension_number", "Renten-/Sozialversicherungsnummer")
        self._field(ids, "family_benefits", "Kindergeldnummer")
        self._field(ids, "student_numbers", "Schüler-/Matrikelnummern")
        self._field(ids, "ibans", "IBANs (Komma getrennt)")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(actions, text="Speichern", command=self.save).pack(side="right")
        if self.person:
            ctk.CTkButton(
                actions,
                text="Person löschen",
                fg_color=DANGER_BG,
                hover_color=("gray84", "gray27"),
                border_width=1,
                border_color=("gray72", "gray38"),
                text_color=DANGER_TEXT,
                command=self.delete_person,
            ).pack(side="left")

    def delete_person(self):
        label = f'die Person „{self.person["display_name"]}“'
        delete_files = messagebox.askyesnocancel(
            "Was soll gelöscht werden?",
            "Sollen zusätzlich eindeutig zugehörige persönliche Dateiordner gelöscht werden?\n\n"
            "Ja: Person und persönliche Ordner löschen\n"
            "Nein: Person löschen, alle Dokumente behalten\n"
            "Abbrechen: Nichts ändern",
            icon="warning",
            parent=self,
        )
        if delete_files is None:
            return
        archive_paths, skipped = _person_archive_paths(self.service, self.person["id"]) if delete_files else ([], [])
        if not _confirm_permanent_delete(self, label, "delete_files" if delete_files else "keep_files"):
            return
        try:
            account_ids = self.service.delete_person(self.person["id"])
            _delete_mail_passwords(account_ids, self.service.config)
            if delete_files:
                _delete_archive_paths(self, archive_paths)
                if skipped:
                    messagebox.showwarning(
                        "Gemeinsam genutzte Ordner behalten",
                        "Mehrdeutige oder gemeinsam genutzte Ordner wurden aus Sicherheitsgründen nicht gelöscht:\n\n"
                        + "\n".join(str(path) for path in skipped),
                        parent=self,
                    )
            if not self.on_saved(self.profile_id):
                self.finish()
        except ProfileValidationError as exc:
            messagebox.showerror("Löschen fehlgeschlagen", str(exc), parent=self)

    def _set(self, key, value):
        entry = self.entries[key]
        if isinstance(entry, DateEntry):
            entry.set_date(value)
            return
        entry.delete(0, "end")
        if isinstance(value, list):
            value = ", ".join(value)
        if value:
            entry.insert(0, value)

    def _load(self):
        name = self.person.get("name", {})
        personal = self.person.get("personal", {})
        identifiers = self.person.get("identifiers", {})
        contacts = self.person.get("contacts", {})
        address = self.person.get("address", {})
        self._set("first_name", name.get("first_name"))
        middle_names = list(name.get("middle_names", []))
        second_first_name = name.get("second_first_name") or (middle_names[0] if middle_names else "")
        self._set("second_first_name", second_first_name)
        self._set("last_name", name.get("last_name"))
        self._set("birth_name", name.get("birth_name"))
        gender = str(personal.get("gender") or "").casefold()
        self.gender.set(GENDER_LABELS.get(gender, "Keine Angabe"))
        self._set("date_of_birth", personal.get("date_of_birth"))
        self._set("place_of_birth", personal.get("place_of_birth"))
        for key in ["street", "house_number", "postal_code", "city"]:
            self._set(key, address.get(key))
        self._set("emails", [v.get("value", "") for v in contacts.get("emails", [])])
        self._set("phones", [v.get("value", "") for v in contacts.get("phones", [])])
        self._set("tax_id", identifiers.get("tax_identification_number"))
        self._set("tax_numbers", identifiers.get("tax_numbers", []))
        self._set("health_insurer", self.person.get("health", {}).get("health_insurer"))
        self._set("health_number", identifiers.get("health_insurance_number"))
        self._set(
            "pension_number",
            identifiers.get("pension_insurance_number") or identifiers.get("social_security_number"),
        )
        self._set("family_benefits", identifiers.get("family_benefits_number"))
        self._set("student_numbers", identifiers.get("student_or_pupil_numbers", []))
        self._set("ibans", identifiers.get("ibans", []))

    def save(self):
        first = self.entries["first_name"].get().strip()
        last = self.entries["last_name"].get().strip()
        second_first_name = self.entries["second_first_name"].get().strip()
        hidden_middle_names = list((self.person or {}).get("name", {}).get("middle_names", []))[1:]
        middle = ([second_first_name] if second_first_name else []) + hidden_middle_names
        try:
            date_of_birth = self.entries["date_of_birth"].date_value()
            is_minor = bool(is_minor_from_birth_date(date_of_birth))
            if self.person:
                display_name = " ".join([first, *middle, last])
                changes = {
                    "display_name": display_name,
                    "is_minor": is_minor,
                    "name": {
                        "first_name": first,
                        "second_first_name": second_first_name,
                        "middle_names": middle,
                        "last_name": last,
                        "birth_name": self.entries["birth_name"].get().strip(),
                        "previous_names": list(self.person.get("name", {}).get("previous_names", [])),
                    },
                    "personal": {
                        "gender": GENDER_VALUES.get(self.gender.get(), ""),
                        "date_of_birth": date_of_birth,
                        "place_of_birth": self.entries["place_of_birth"].get().strip(),
                    },
                    "contacts": {
                        "emails": [{"type": "private", "value": v} for v in _split_csv(self.entries["emails"].get())],
                        "phones": [{"type": "private", "value": v} for v in _split_csv(self.entries["phones"].get())],
                    },
                    "address": {key: self.entries[key].get().strip() for key in ["street", "house_number", "postal_code", "city"]},
                    "identifiers": self._identifiers(),
                    "health": {"health_insurer": self.entries["health_insurer"].get().strip()},
                    "matching": self._matching(first, last, middle),
                    "routing": {"archive_folder": display_name, "structure_template": "child" if is_minor else "adult"},
                }
                person = self.service.update_person(self.person["id"], changes)
            else:
                person = self.service.create_person(
                    first, last, middle, is_minor,
                    date_of_birth,
                    gender=GENDER_VALUES.get(self.gender.get(), ""),
                )
                self.service.update_person(person["id"], {
                    "name": {
                        "birth_name": self.entries["birth_name"].get().strip(),
                        "previous_names": [],
                    },
                    "personal": {"place_of_birth": self.entries["place_of_birth"].get().strip()},
                    "contacts": {
                        "emails": [{"type": "private", "value": v} for v in _split_csv(self.entries["emails"].get())],
                        "phones": [{"type": "private", "value": v} for v in _split_csv(self.entries["phones"].get())],
                    },
                    "address": {key: self.entries[key].get().strip() for key in ["street", "house_number", "postal_code", "city"]},
                    "identifiers": self._identifiers(),
                    "health": {"health_insurer": self.entries["health_insurer"].get().strip()},
                    "matching": self._matching(first, last, middle),
                })
            if self.profile_id:
                profile = self.service.get_profile(self.profile_id)
                role = (
                    "child"
                    if is_minor
                    else "parent" if profile and profile.get("type") == "family" else "employee"
                )
                position = self.organization_position.get() if self.organization_position else ""
                self.service.add_membership(
                    self.profile_id,
                    person["id"],
                    role=role,
                    position=position,
                )
            if not self.on_saved(person if self.return_person else self.profile_id):
                self.finish()
        except (ProfileValidationError, ValueError) as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc), parent=self)

    def _identifiers(self):
        return {
            "tax_identification_number": self.entries["tax_id"].get().strip(),
            "tax_numbers": _split_csv(self.entries["tax_numbers"].get()),
            "health_insurance_number": self.entries["health_number"].get().strip(),
            "pension_insurance_number": self.entries["pension_number"].get().strip(),
            "family_benefits_number": self.entries["family_benefits"].get().strip(),
            "student_or_pupil_numbers": _split_csv(self.entries["student_numbers"].get()),
            "ibans": _split_csv(self.entries["ibans"].get()),
        }

    def _matching(self, first_name, last_name, middle_names):
        matching = dict((self.person or {}).get("matching", {}))
        official_variants = [
            " ".join([first_name, *middle_names, last_name]).strip(),
            f"{first_name} {last_name}".strip(),
        ]
        matching["name_variants"] = list(dict.fromkeys(
            [value for value in official_variants if value]
        ))
        return matching


class MembershipDialog(EmbeddedPage):
    help_context = "membership"
    def __init__(self, master, service, profile_id, on_saved):
        super().__init__(master)
        self.service = service
        self.profile_id = profile_id
        self.on_saved = on_saved
        self.people = _available_people_for_profile(service, profile_id)
        self.profile = self.service.get_profile(profile_id) or {}
        ctk.CTkLabel(self, text="Person zuordnen", font=("Arial", 22, "bold")).pack(anchor="w", padx=20, pady=(20, 4))
        if not self.people:
            self.after(0, self._show_empty_state)
            return
        names = [p["display_name"] for p in self.people] or ["Keine Person vorhanden"]
        ctk.CTkLabel(self, text="Person").pack(anchor="w", padx=20, pady=(20, 4))
        self.person_menu = ctk.CTkOptionMenu(self, values=names)
        self.person_menu.pack(fill="x", padx=20)
        if self.profile.get("type") == "organization":
            ctk.CTkLabel(self, text="Funktion in der Firma").pack(anchor="w", padx=20, pady=(14, 4))
            self.position = OrganizationPositionInput(self)
            self.position.pack(fill="x", padx=20)
            self.role = None
            ctk.CTkLabel(self, text="Abteilung").pack(anchor="w", padx=20, pady=(14, 4))
            self.department = ctk.CTkEntry(self)
            self.department.pack(fill="x", padx=20)
        else:
            ctk.CTkLabel(self, text="Beziehung zur Familie").pack(anchor="w", padx=20, pady=(14, 4))
            self.role = FamilyRoleInput(self)
            self.role.pack(fill="x", padx=20)
            self.position = None
            self.department = None
        ctk.CTkButton(self, text="Zuordnen", command=self.save).pack(pady=22)

    def _show_empty_state(self):
        profile = self.service.get_profile(self.profile_id) or {}
        messagebox.showinfo(
            "Keine weitere Person verfügbar",
            _all_people_assigned_message(profile.get("type")),
            parent=self,
        )
        self.finish()

    def save(self):
        if not self.people:
            messagebox.showwarning("Keine Person", "Bitte zuerst eine Person anlegen.", parent=self)
            return
        selected = self.person_menu.get()
        person = next(p for p in self.people if p["display_name"] == selected)
        try:
            profile = self.service.get_profile(self.profile_id)
            role = self.role.get().strip() if self.role else "employee"
            position = self.position.get() if self.position else ""
            self.service.add_membership(
                self.profile_id,
                person["id"],
                role=role if profile["type"] == "family" else "employee",
                position=position,
                department=self.department.get().strip() if self.department else "",
            )
            if not self.on_saved(self.profile_id):
                self.finish()
        except ProfileValidationError as exc:
            messagebox.showerror("Zuordnung fehlgeschlagen", str(exc), parent=self)


class IndividualDialog(EmbeddedPage):
    help_context = "profile_new"
    def __init__(self, master, service, on_saved):
        super().__init__(master)
        self.service = service
        self.on_saved = on_saved
        self.people = service.list_persons()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=180, pady=(24, 0))
        ctk.CTkLabel(
            content,
            text="Neue Privatperson",
            font=("Arial", 22, "bold"),
        ).pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            content,
            text="Schritt 2 von 2 · Personendaten",
            text_color=SECONDARY_TEXT,
        ).pack(fill="x", pady=(0, 18))
        if self.people:
            ctk.CTkLabel(
                content,
                text="Ausgewählte Person verwenden",
                font=("Arial", 15, "bold"),
            ).pack(fill="x", pady=(4, 6))
            self.person_menu = ctk.CTkOptionMenu(
                content,
                values=[p["display_name"] for p in self.people],
                fg_color=CONTROL_BG,
                button_color=CONTROL_BUTTON,
                button_hover_color=CONTROL_HOVER,
                text_color=PRIMARY_TEXT,
                dropdown_fg_color=CONTROL_BG,
                dropdown_hover_color=CONTROL_HOVER,
                dropdown_text_color=PRIMARY_TEXT,
            )
            self.person_menu.pack(fill="x", pady=(0, 8))
            ctk.CTkButton(
                content,
                text="Auswahl verwenden",
                command=self.use_existing,
            ).pack(fill="x", pady=(0, 18))
            ctk.CTkLabel(
                content,
                text="oder",
                text_color=SECONDARY_TEXT,
            ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            content,
            text="Neue Person erfassen",
            command=self.create_new,
        ).pack(fill="x", pady=(0, 8))

    def use_existing(self):
        selected = self.person_menu.get()
        person = next(p for p in self.people if p["display_name"] == selected)
        try:
            profile = self.service.create_individual(person["id"])
            if not self.on_saved(profile["id"]):
                self.finish()
        except ProfileValidationError as exc:
            messagebox.showerror("Profil konnte nicht angelegt werden", str(exc), parent=self)

    def create_new(self):
        self.open_page(
            lambda parent: PersonDialog(parent, self.service, self._person_created_as_individual, return_person=True),
            "profiles",
        )

    def _person_created_as_individual(self, person):
        try:
            profile = self.service.create_individual(person["id"])
            return self.on_saved(profile["id"])
        except ProfileValidationError as exc:
            messagebox.showerror("Profil konnte nicht angelegt werden", str(exc))


class ProfileEditDialog(EmbeddedPage):
    help_context = "profile_edit"
    def __init__(self, master, service, profile_id, on_saved):
        super().__init__(master)
        self.service = service
        self.profile = service.get_profile(profile_id)
        self.on_saved = on_saved
        self.entries = {}
        titles = {
            "family": "Familie bearbeiten",
            "organization": "Organisation bearbeiten",
            "individual": "Privatperson bearbeiten",
        }
        self.page_title = titles.get(self.profile["type"], "Profil bearbeiten")
        ctk.CTkLabel(self, text=self.page_title, font=("Arial", 22, "bold")).pack(anchor="w", padx=20, pady=(18, 0))
        self._build()
        self._load()

    def _field(self, parent, key, label):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=12, pady=(7, 2))
        entry = ctk.CTkEntry(parent)
        entry.pack(fill="x", padx=12)
        self.entries[key] = entry

    def _build(self):
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=16)
        base_tab = tabs.add("Allgemein")
        contact_tab = tabs.add("Kontakt")
        identifiers_tab = tabs.add("Kennungen")
        relationship_tab = tabs.add("Beziehungen") if self.profile["type"] == "family" else None
        base = ctk.CTkScrollableFrame(base_tab, fg_color="transparent")
        base.pack(fill="both", expand=True)
        contact = ctk.CTkScrollableFrame(contact_tab, fg_color="transparent")
        contact.pack(fill="both", expand=True)
        identifiers = ctk.CTkScrollableFrame(identifiers_tab, fg_color="transparent")
        identifiers.pack(fill="both", expand=True)
        if relationship_tab is not None:
            relationships = ctk.CTkScrollableFrame(relationship_tab, fg_color="transparent")
            relationships.pack(fill="both", expand=True)
            self._build_partner_relationships(relationships)
        self._field(base, "display_name", "Anzeigename *")
        self._field(base, "archive_folder", "Archivordner *")
        ctk.CTkLabel(base, text="Speicherort").pack(anchor="w", padx=12, pady=(12, 4))
        self.storage_mode = ctk.StringVar(value="global")
        self.custom_storage_label = (
            "Dieser Ordner ist der Firmenordner"
            if self.profile["type"] == "organization"
            else "Dieser Ordner ist der Profilordner"
        )
        self.storage_mode_control = ctk.CTkSegmentedButton(
            base,
            values=["Globalen Speicherort verwenden", self.custom_storage_label],
            command=self._storage_mode_changed,
        )
        self.storage_mode_control.pack(fill="x", padx=12, pady=(0, 8))
        storage_row = ctk.CTkFrame(base, fg_color="transparent")
        storage_row.pack(fill="x", padx=12)
        self.storage_root = ctk.CTkEntry(storage_row, placeholder_text="Profilordner auswählen")
        self.storage_root.pack(side="left", fill="x", expand=True)
        self.storage_button = ctk.CTkButton(storage_row, text="Auswählen", width=90, command=self._choose_storage)
        self.storage_button.pack(side="left", padx=(6, 0))
        if self.profile["type"] == "organization":
            self._field(base, "legal_name", "Rechtlicher Name")
            self._field(base, "legal_form", "Rechtsform")
        self._field(contact, "street", "Straße")
        self._field(contact, "house_number", "Hausnummer")
        self._field(contact, "postal_code", "PLZ")
        self._field(contact, "city", "Ort")
        self._field(contact, "country", "Land")
        self._field(contact, "emails", "E-Mail-Adressen (Komma getrennt)")
        self._field(contact, "phones", "Telefonnummern (Komma getrennt)")
        if self.profile["type"] == "organization":
            ctk.CTkLabel(contact, text="Geschäftsführung", font=("Arial", 16, "bold")).pack(
                anchor="w", padx=12, pady=(18, 4)
            )
            self._field(contact, "director_first_name", "Vorname Geschäftsführer")
            self._field(contact, "director_second_name", "Zweiter Vorname Geschäftsführer")
            self._field(contact, "director_last_name", "Nachname Geschäftsführer")
        if self.profile["type"] == "family":
            self._field(identifiers, "tax_numbers", "Gemeinsame Steuernummern (Komma getrennt)")
            self._field(identifiers, "ibans", "Gemeinsame IBANs (Komma getrennt)")
        elif self.profile["type"] == "organization":
            self._field(identifiers, "register_number", "Handels-/Registernummer")
            self._field(identifiers, "tax_numbers", "Steuernummern")
            self._field(identifiers, "vat_id", "Umsatzsteuer-ID")
            self._field(identifiers, "employer_number", "Betriebsnummer")
            self._field(identifiers, "ibans", "Geschäftliche IBANs (Komma getrennt)")
        ctk.CTkButton(self, text="Speichern", command=self.save).pack(pady=(0, 16))

    def _build_partner_relationships(self, parent):
        members = [person for person, _membership in self.service.profile_members(self.profile["id"])]
        self.partner_people = {person["display_name"]: person["id"] for person in members}
        ctk.CTkLabel(
            parent,
            text="Ehe- und Lebenspartner verknüpfen",
            font=("Arial", 16, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            parent,
            text=("Die Beziehung bleibt bestehen, unabhängig vom Alter der Personen, und hilft "
                  "bei der Erkennung gemeinsamer Dokumente."),
            text_color=SECONDARY_TEXT,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=12, pady=(0, 12))
        if len(members) < 2:
            ctk.CTkLabel(
                parent,
                text="Füge der Familie mindestens zwei Personen hinzu, um sie zu verknüpfen.",
            ).pack(anchor="w", padx=12, pady=8)
            self.partner_first = self.partner_second = self.partner_type = None
            return
        names = list(self.partner_people)
        self.partner_first = ctk.CTkOptionMenu(parent, values=names)
        self.partner_first.pack(fill="x", padx=12, pady=(4, 8))
        self.partner_second = ctk.CTkOptionMenu(parent, values=names)
        self.partner_second.pack(fill="x", padx=12, pady=8)
        self.partner_second.set(names[1])
        self.partner_type = ctk.CTkOptionMenu(parent, values=list(PARTNER_RELATIONSHIP_TYPES))
        self.partner_type.pack(fill="x", padx=12, pady=8)
        existing = (self.profile.get("partner_relationships") or [None])[0]
        if existing:
            ids = existing.get("person_ids", [])
            names_by_id = {person_id: name for name, person_id in self.partner_people.items()}
            if len(ids) == 2 and all(person_id in names_by_id for person_id in ids):
                self.partner_first.set(names_by_id[ids[0]])
                self.partner_second.set(names_by_id[ids[1]])
            self.partner_type.set(PARTNER_RELATIONSHIP_LABELS.get(existing.get("type"), "Verheiratet"))
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(actions, text="Beziehung speichern", command=self._save_partner_relationship).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Beziehung entfernen",
            fg_color=CONTROL_BUTTON,
            hover_color=CONTROL_HOVER,
            text_color=PRIMARY_TEXT,
            command=self._remove_partner_relationship,
        ).pack(side="left", padx=8)

    def _selected_partner_ids(self):
        if not self.partner_first:
            raise ProfileValidationError("Es sind noch nicht genügend Familienmitglieder vorhanden.")
        return (
            self.partner_people[self.partner_first.get()],
            self.partner_people[self.partner_second.get()],
        )

    def _save_partner_relationship(self):
        try:
            first_id, second_id = self._selected_partner_ids()
            self.service.set_partner_relationship(
                self.profile["id"],
                first_id,
                second_id,
                PARTNER_RELATIONSHIP_TYPES[self.partner_type.get()],
            )
            messagebox.showinfo("Beziehung gespeichert", "Die Partnerbeziehung wurde gespeichert.", parent=self)
        except ProfileValidationError as exc:
            messagebox.showerror("Beziehung nicht gespeichert", str(exc), parent=self)

    def _remove_partner_relationship(self):
        try:
            first_id, second_id = self._selected_partner_ids()
            self.service.remove_partner_relationship(self.profile["id"], first_id, second_id)
            messagebox.showinfo("Beziehung entfernt", "Die ausgewählte Partnerbeziehung wurde entfernt.", parent=self)
        except ProfileValidationError as exc:
            messagebox.showerror("Beziehung nicht entfernt", str(exc), parent=self)

    def _set(self, key, value):
        if key not in self.entries:
            return
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if value:
            self.entries[key].insert(0, value)

    def _load(self):
        profile = self.profile
        self._set("display_name", profile.get("display_name"))
        self._set("archive_folder", profile.get("routing", {}).get("archive_folder"))
        routing = profile.get("routing", {}) or {}
        mode = "global" if routing.get("use_global_storage", True) else "custom"
        self.storage_mode.set(mode)
        self.storage_mode_control.set(
            "Globalen Speicherort verwenden" if mode == "global" else self.custom_storage_label
        )
        self.storage_root.insert(0, routing.get("storage_root", ""))
        self._toggle_storage()
        contacts = profile.get("contacts", {})
        self._set("emails", [v.get("value", "") for v in contacts.get("emails", [])])
        self._set("phones", [v.get("value", "") for v in contacts.get("phones", [])])
        address = (profile.get("address", {}) or {})
        for key in ["street", "house_number", "postal_code", "city", "country"]:
            self._set(key, address.get(key))
        if profile["type"] == "family":
            values = profile.get("household_identifiers", {})
            self._set("tax_numbers", values.get("tax_numbers", []))
            self._set("ibans", values.get("ibans", []))
        elif profile["type"] == "organization":
            name = profile.get("name", {})
            registration = profile.get("registration", {})
            self._set("legal_name", name.get("legal_name"))
            self._set("legal_form", name.get("legal_form"))
            mapping = {
                "register_number": "register_number",
                "tax_numbers": "tax_numbers", "vat_id": "vat_identification_number",
                "employer_number": "employer_number",
            }
            for field, key in mapping.items():
                self._set(field, registration.get(key))
            self._set("ibans", (profile.get("financial_identifiers", {}) or {}).get("ibans", []))
            director = (profile.get("management", {}) or {}).get("managing_director", {}) or {}
            self._set("director_first_name", director.get("first_name"))
            self._set("director_second_name", director.get("second_first_name"))
            self._set("director_last_name", director.get("last_name"))

    def save(self):
        display_name = self.entries["display_name"].get().strip()
        changes = {
            "display_name": display_name,
            "routing": {
                "use_global_storage": self.storage_mode.get() == "global",
                "storage_root": self.storage_root.get().strip(),
                "archive_folder": self.entries["archive_folder"].get().strip(),
            },
            "address": {key: self.entries[key].get().strip() for key in ["street", "house_number", "postal_code", "city", "country"]},
            "contacts": {
                "emails": [{"type": "general", "value": value} for value in _split_csv(self.entries["emails"].get())],
                "phones": [{"type": "general", "value": value} for value in _split_csv(self.entries["phones"].get())],
            },
        }
        if self.profile["type"] == "family":
            changes["household_identifiers"] = {
                "tax_numbers": _split_csv(self.entries["tax_numbers"].get()),
                "ibans": _split_csv(self.entries["ibans"].get()),
            }
        elif self.profile["type"] == "organization":
            changes.update({
                "name": {
                    "legal_name": self.entries["legal_name"].get().strip(),
                    "legal_form": self.entries["legal_form"].get().strip(),
                },
                "registration": {
                    "register_number": self.entries["register_number"].get().strip(),
                    "tax_numbers": _split_csv(self.entries["tax_numbers"].get()),
                    "vat_identification_number": self.entries["vat_id"].get().strip(),
                    "employer_number": self.entries["employer_number"].get().strip(),
                },
                "management": {
                    "managing_director": {
                        "first_name": self.entries["director_first_name"].get().strip(),
                        "second_first_name": self.entries["director_second_name"].get().strip(),
                        "last_name": self.entries["director_last_name"].get().strip(),
                    },
                },
                "financial_identifiers": {
                    "ibans": _split_csv(self.entries["ibans"].get()),
                },
            })
        try:
            self.service.update_profile(self.profile["id"], changes)
            if not self.on_saved(self.profile["id"]):
                self.finish()
        except ProfileValidationError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc), parent=self)

    def _toggle_storage(self):
        state = "disabled" if self.storage_mode.get() == "global" else "normal"
        self.storage_root.configure(state=state)
        self.storage_button.configure(state=state)

    def _storage_mode_changed(self, selection):
        self.storage_mode.set(
            "global" if selection == "Globalen Speicherort verwenden" else "custom"
        )
        self._toggle_storage()

    def _choose_storage(self):
        initial = self.storage_root.get().strip() or self.service.config.get("user_path") or ""
        selected = filedialog.askdirectory(parent=self, initialdir=initial or None)
        if not selected:
            return
        self.storage_mode.set("custom")
        self.storage_mode_control.set(self.custom_storage_label)
        self.storage_root.configure(state="normal")
        self.storage_root.delete(0, "end")
        self.storage_root.insert(0, selected)
