import json
import re
from pathlib import Path

from src.profile_service import ProfileValidationError
from src.storage_utils import FilesystemStorage
from src.policy_resolver import PolicyResolver
from src.document_registry import DocumentRegistry


class ManualFilingService:
    RESERVED_FOLDER_NAMES = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
        "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }

    def __init__(self, config, profile_service):
        self.config = config
        self.profiles = profile_service
        self.policy_resolver = (
            PolicyResolver(config, profile_service)
            if hasattr(config, "presets_root") else None
        )
        self.last_backup_path = None
        self.registry = DocumentRegistry(config)
        try:
            with open(config.structure_path, "r", encoding="utf-8") as handle:
                self.structure = json.load(handle)
        except (AttributeError, OSError, json.JSONDecodeError):
            self.structure = {}

    def destinations(self, profile_id, person_id=None):
        profile = self.profiles.get_profile(profile_id)
        if not profile:
            return []
        template = self._template(profile, person_id)
        result = []

        def walk(node, parts):
            if parts:
                result.append(Path(*parts))
            for name, child in (node or {}).items():
                if str(name).startswith("{"):
                    continue
                if isinstance(child, dict):
                    walk(child, parts + [name])

        walk(template, [])
        return result

    def _template(self, profile, person_id=None):
        if self.policy_resolver:
            return self.policy_resolver.structure_for(
                profile, [person_id] if person_id else []
            )
        template_name = (profile.get("routing", {}) or {}).get("structure_template")
        return (self.structure.get("templates", {}) or {}).get(template_name, {})

    def supports_private_tax_receipts(self, profile_id, person_id=None):
        profile = self.profiles.get_profile(profile_id)
        if not profile or profile.get("type") == "organization":
            return False
        node = self._template(profile, person_id)
        for part in (
            "Finanzamt und Steuern", "Einkommensteuer", "{year}",
            "02 Belege", "Sonstige Belege",
        ):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    @classmethod
    def _folder_parts(cls, value):
        raw = str(value or "").strip().replace("\\", "/")
        parts = [part.strip() for part in raw.split("/")]
        if not raw or any(not part for part in parts):
            raise ProfileValidationError("Bitte gib einen gültigen Unterordner ein.")
        if len(parts) > 5:
            raise ProfileValidationError("Es können höchstens fünf Unterordner auf einmal angelegt werden.")
        for part in parts:
            if part in {".", ".."} or any(char in part for char in '<>:"|?*'):
                raise ProfileValidationError("Der Unterordner enthält ungültige Zeichen.")
            cleaned = part.rstrip(" .")
            if not cleaned or cleaned.upper() in cls.RESERVED_FOLDER_NAMES:
                raise ProfileValidationError("Dieser Unterordnername ist unter Windows nicht zulässig.")
        return [part.rstrip(" .") for part in parts]

    def add_destination(self, profile_id, parent_destination, folder_path, person_id=None):
        if not self.policy_resolver:
            raise ProfileValidationError("Eigene Ablageziele sind in dieser Konfiguration nicht verfügbar.")
        profile = self.profiles.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        parent = Path(parent_destination)
        allowed = {str(path) for path in self.destinations(profile_id, person_id)}
        if str(parent) not in allowed:
            raise ProfileValidationError("Das übergeordnete Ablageziel ist nicht gültig.")
        if person_id:
            member_ids = {person["id"] for person, _membership in self.profiles.profile_members(profile_id)}
            if person_id not in member_ids:
                raise ProfileValidationError("Die ausgewählte Person gehört nicht zu diesem Profil.")
        parts = self._folder_parts(folder_path)
        target = parent.joinpath(*parts)
        if str(target) in allowed:
            return target

        profile_root = self.config.profiles_root / profile_id
        override_path = (
            profile_root / "persons" / person_id / "structure.override.json"
            if person_id else profile_root / "structure.override.json"
        )
        override = PolicyResolver._read(override_path)
        node = override
        for part in [*parent.parts, *parts]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise ProfileValidationError("An dieser Stelle kann kein Unterordner ergänzt werden.")
            node = child
        self.config._write_json(override_path, override)
        return target

    @staticmethod
    def _filename(source, new_name=None):
        if new_name is None:
            return source.name
        name = str(new_name).strip()
        if not name:
            raise ProfileValidationError("Bitte gib einen Dokumentnamen ein.")
        if Path(name).name != name or any(char in name for char in '<>:"/\\|?*'):
            raise ProfileValidationError("Der Dokumentname enthält ungültige Zeichen.")
        if name.casefold().endswith(source.suffix.casefold()):
            name = name[:-len(source.suffix)].rstrip()
        if not name or name in {".", ".."}:
            raise ProfileValidationError("Bitte gib einen gültigen Dokumentnamen ein.")
        if name.rstrip(" .").upper() in {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
            "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
            "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
        }:
            raise ProfileValidationError("Dieser Dokumentname ist unter Windows reserviert.")
        return f"{name.rstrip(' .')}{source.suffix}"

    @staticmethod
    def _year(value):
        year = str(value or "").strip()
        if not year:
            return None
        if not re.fullmatch(r"(?:19|20)\d{2}", year):
            raise ProfileValidationError("Das Jahr muss vierstellig sein, z. B. 2023.")
        return year

    def file_document(
        self,
        source_path,
        profile_id,
        destination,
        person_id=None,
        year=None,
        new_name=None,
        tax_receipt=False,
    ):
        source = Path(source_path)
        profile = self.profiles.get_profile(profile_id)
        if not source.is_file() or not profile:
            raise ProfileValidationError("Dokument oder Profil wurde nicht gefunden.")
        source_digest = self.registry.hash_file(source)
        destination = Path(destination)
        selected_year = self._year(year)
        if tax_receipt:
            if not selected_year:
                raise ProfileValidationError("Für einen Steuerbeleg muss ein Steuerjahr gewählt werden.")
            if not self.supports_private_tax_receipts(profile_id, person_id):
                raise ProfileValidationError("Dieses Profil besitzt keine Ablage für private Steuerbelege.")
            destination = Path(
                "Finanzamt und Steuern", "Einkommensteuer", selected_year,
                "02 Belege", "Sonstige Belege",
            )
        else:
            allowed = {str(path) for path in self.destinations(profile_id, person_id)}
            if str(destination) not in allowed:
                raise ProfileValidationError("Das ausgewählte Ablageziel ist nicht gültig.")
        filename = self._filename(source, new_name)
        base_folder = (profile.get("routing", {}) or {}).get("archive_folder") or profile["display_name"]
        if profile.get("type") == "family":
            if person_id:
                person = self.profiles.get_person(person_id)
                member_ids = {p["id"] for p, _m in self.profiles.profile_members(profile_id)}
                if not person or person_id not in member_ids:
                    raise ProfileValidationError("Die Person gehört nicht zu dieser Familie.")
                base_folder = (person.get("routing", {}) or {}).get("archive_folder") or person["display_name"]
            else:
                base_folder = profile.get("archive_name") or "Gemeinsame Dokumente"
        storage = FilesystemStorage(self.profiles.resolve_storage_root(profile_id))
        target = Path(base_folder) / destination
        if selected_year and not tax_receipt:
            target /= selected_year
        self.last_backup_path = FilesystemStorage(
            self.profiles.resolve_backup_directory(profile_id)
        ).backup(
            source, Path(), source.name
        )
        final = storage.store(source, target, filename)
        document_id = self.registry.register_document(
            self.last_backup_path,
            digest=source_digest,
            status="processed",
            location_type="backup",
            original_name=source.name,
            profile_id=profile_id,
            person_ids=[person_id] if person_id else [],
        )
        self.registry.add_location(document_id, final, "archive")
        self.registry.record_event(
            document_id, "manually_filed", status="success", reason="user_confirmed"
        )
        return final

    def file_document_outside_structure(
        self,
        source_path,
        destination_folder,
        new_name=None,
        profile_id=None,
    ):
        """Move a document directly into a user-selected existing folder."""
        source = Path(source_path)
        destination_folder = Path(destination_folder)
        if not source.is_file():
            raise ProfileValidationError("Das Dokument wurde nicht gefunden.")
        source_digest = self.registry.hash_file(source)
        if not destination_folder.is_dir():
            raise ProfileValidationError("Der ausgewählte Speicherort ist kein gültiger Ordner.")
        filename = self._filename(source, new_name)
        self.last_backup_path = FilesystemStorage(
            self.profiles.resolve_backup_directory(profile_id)
        ).backup(
            source, Path(), source.name
        )
        final = FilesystemStorage(destination_folder).store(source, Path(), filename)
        document_id = self.registry.register_document(
            self.last_backup_path,
            digest=source_digest,
            status="processed",
            location_type="backup",
            original_name=source.name,
            profile_id=profile_id,
        )
        self.registry.add_location(document_id, final, "external_archive")
        self.registry.record_event(
            document_id, "manually_filed", status="success", reason="external_location"
        )
        return final

    def discard_document(self, source_path):
        """Permanently remove one document from Sorterino's review folder."""
        source = Path(source_path)
        try:
            review_root = Path(self.config.manual_root).resolve()
            resolved = source.resolve(strict=True)
            resolved.relative_to(review_root)
        except (AttributeError, OSError, ValueError) as exc:
            raise ProfileValidationError(
                "Nur Dokumente aus ‚Zu prüfen‘ können verworfen werden."
            ) from exc
        if not resolved.is_file():
            raise ProfileValidationError("Das Dokument wurde nicht gefunden.")
        FilesystemStorage.ensure_movable(resolved)
        document_id = self.registry.register_document(
            resolved,
            status="discarded",
            location_type="review",
            original_name=resolved.name,
        )
        try:
            resolved.unlink()
        except PermissionError as exc:
            raise ProfileValidationError(
                "Das Dokument ist noch in einem anderen Programm geöffnet. Schließe es und versuche es erneut."
            ) from exc
        self.registry.mark_location_missing(document_id, resolved)
        self.registry.record_event(
            document_id, "discarded", status="discarded", reason="user_confirmed"
        )
        return resolved
