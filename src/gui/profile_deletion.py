"""Safety-focused profile deletion dialogs and archive cleanup operations."""

from pathlib import Path
import shutil
from tkinter import messagebox, simpledialog

from src.profile_errors import ProfileValidationError


def delete_confirmation_message(item_label, mode="keep_files", extra_warning=""):
    if mode == "delete_files":
        consequence = (
            "Die Konfiguration und Zuordnungen werden gelöscht. "
            "Eindeutig zugehörige Dateiordner und die darin bereits abgelegten Dokumente "
            "werden GELÖSCHT. Gemeinsam genutzte oder mehrdeutige Ordner bleiben erhalten."
        )
    elif mode == "membership_only":
        consequence = (
            "Nur diese Zuordnung wird entfernt. Die Person, andere Profilzuordnungen "
            "und alle bereits abgelegten Dokumente bleiben erhalten."
        )
    else:
        consequence = (
            "Die Konfiguration und Zuordnungen werden gelöscht. "
            "Bereits abgelegte Dokumente bleiben erhalten."
        )
    extra = f"\n\n{extra_warning}" if extra_warning else ""
    return f"Soll {item_label} wirklich gelöscht werden?\n\n{consequence}{extra}"


def confirm_permanent_delete(parent, item_label, mode="keep_files", extra_warning=""):
    if not messagebox.askyesno(
        "Löschen bestätigen",
        delete_confirmation_message(item_label, mode, extra_warning),
        icon="warning",
        parent=parent,
    ):
        return False
    verification = simpledialog.askstring(
        "Löschen verifizieren",
        f"Gib exakt Yeah! ein, um {item_label} endgültig zu löschen:",
        parent=parent,
    )
    if verification != "Yeah!":
        if verification is not None:
            messagebox.showwarning(
                "Löschen abgebrochen",
                "Die Eingabe war nicht exakt „Yeah!“. Es wurde nichts gelöscht.",
                parent=parent,
            )
        return False
    return True


def delete_mail_credentials(account_ids, config=None):
    if not account_ids:
        return
    try:
        from src.mail_auth import delete_account_credentials

        for account_id in account_ids:
            try:
                delete_account_credentials(account_id, config)
            except Exception:
                pass
    except Exception:
        # A stale credential is preferable to undoing a successful profile deletion.
        pass


def safe_archive_path(service, profile, folder_name):
    try:
        root = service.resolve_storage_root(profile["id"]).resolve()
        target = (root / str(folder_name or "")).resolve()
    except (OSError, ProfileValidationError):
        return None
    if not folder_name or target == root or root not in target.parents:
        return None
    return target


def person_archive_paths(service, person_id):
    """Return only personal folders that are not also named for another person."""
    person = service.get_person(person_id)
    if not person:
        return [], []
    folder = (person.get("routing", {}) or {}).get("archive_folder") or person.get("display_name")
    candidates = []
    skipped = []
    for profile in service.list_profiles():
        belongs = (
            profile.get("type") == "individual" and profile.get("person_id") == person_id
        ) or any(
            member["id"] == person_id
            for member, _ in service.profile_members(profile["id"])
        )
        if not belongs or profile.get("type") == "organization":
            continue
        target = safe_archive_path(service, profile, folder)
        if not target:
            continue
        ambiguous = any(
            other.get("id") != person_id
            and str(
                (other.get("routing", {}) or {}).get("archive_folder")
                or other.get("display_name")
            ).casefold()
            == str(folder).casefold()
            for other in service.list_persons()
        )
        (skipped if ambiguous else candidates).append(target)
    return list(dict.fromkeys(candidates)), list(dict.fromkeys(skipped))


def profile_archive_paths(service, profile):
    if profile.get("type") == "family":
        names = [profile.get("archive_name") or "Gemeinsame Dokumente"]
        names.extend(
            (person.get("routing", {}) or {}).get("archive_folder")
            or person.get("display_name")
            for person, _ in service.profile_members(profile["id"])
        )
    elif profile.get("type") == "individual":
        person = service.get_person(profile.get("person_id"))
        names = [] if not person else [
            (person.get("routing", {}) or {}).get("archive_folder")
            or person.get("display_name")
        ]
    else:
        names = [
            (profile.get("routing", {}) or {}).get("archive_folder")
            or profile.get("display_name")
        ]
    paths = [
        path
        for name in names
        if (path := safe_archive_path(service, profile, name))
    ]
    safe, skipped = [], []
    for target in dict.fromkeys(paths):
        used_elsewhere = False
        for other in service.list_profiles():
            if other.get("id") == profile.get("id"):
                continue
            other_names = [
                (other.get("routing", {}) or {}).get("archive_folder")
                or other.get("display_name")
            ]
            if other.get("type") == "family":
                other_names = [other.get("archive_name") or "Gemeinsame Dokumente"]
                other_names.extend(
                    (person.get("routing", {}) or {}).get("archive_folder")
                    or person.get("display_name")
                    for person, _ in service.profile_members(other["id"])
                )
            if any(
                safe_archive_path(service, other, other_name) == target
                for other_name in other_names
            ):
                used_elsewhere = True
                break
        (skipped if used_elsewhere else safe).append(target)
    return safe, skipped


def delete_archive_paths(parent, paths):
    existing = [Path(path) for path in paths if Path(path).exists()]
    if not existing:
        messagebox.showinfo(
            "Keine Dateiordner",
            "Es wurden keine zugehörigen Dateiordner gefunden.",
            parent=parent,
        )
        return
    verification = simpledialog.askstring(
        "Dateien endgültig löschen",
        "Folgende Ordner werden unwiderruflich gelöscht:\n\n"
        + "\n".join(str(path) for path in existing)
        + "\n\nGib exakt DATEIEN LÖSCHEN ein:",
        parent=parent,
    )
    if verification != "DATEIEN LÖSCHEN":
        messagebox.showwarning(
            "Dateilöschung abgebrochen",
            "Die Dateiordner wurden nicht gelöscht.",
            parent=parent,
        )
        return
    failures = []
    for path in existing:
        try:
            shutil.rmtree(path)
        except OSError as exc:
            failures.append(f"{path}: {exc}")
    if failures:
        messagebox.showerror(
            "Nicht alle Ordner gelöscht",
            "Diese Ordner konnten nicht gelöscht werden und sind erhalten geblieben:\n\n"
            + "\n".join(failures),
            parent=parent,
        )
