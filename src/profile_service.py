import copy
import re
import shutil
import uuid
from pathlib import Path

from src.initialize_workspace import get_base_path
from src.identifier_formats import IdentifierFormatError, NORMALIZERS
from src.person_age import is_minor_from_birth_date, person_is_minor
from src.constants import BACKUP_DIRECTORY_NAME
from src.profile_errors import ProfileValidationError
from src.profile_registry import ProfileRegistryMixin


class ProfileService(ProfileRegistryMixin):
    """Loads and manages people, family profiles and organizations."""

    PROFILE_TYPES = {"individual", "family", "organization"}
    STRUCTURE_TEMPLATES = {"family", "adult", "child", "organization"}

    def __init__(self, config):
        if not config.profiles_path:
            raise ProfileValidationError("Zuerst muss ein Speicherort gewählt werden.")

        self.config = config
        self.path = Path(config.profiles_path)
        self.split_storage = hasattr(config, "profiles_root") and hasattr(config, "persons_root")
        self.profiles_root = Path(config.profiles_root) if self.split_storage else None
        self.persons_root = Path(config.persons_root) if self.split_storage else None
        self.template_root = get_base_path() / "assets" / "templates"
        self.data = self._load_registry()


    @staticmethod
    def _new_id(prefix):
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _clean(value):
        return str(value or "").strip()

    @staticmethod
    def _slug(value):
        value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return value[:40] or uuid.uuid4().hex[:8]

    @staticmethod
    def _validate_folder_name(value, label="Archivordner"):
        value = str(value or "").strip()
        if not value:
            raise ProfileValidationError(f"{label} darf nicht leer sein.")
        if value in {".", ".."} or any(char in value for char in '\\/:*?"<>|'):
            raise ProfileValidationError(
                f"{label} darf keine Pfad- oder für Windows ungültigen Zeichen enthalten."
            )

    def list_persons(self, include_inactive=False):
        persons = self.data.get("persons", [])
        if not include_inactive:
            persons = [p for p in persons if p.get("status", "active") == "active"]
        return sorted(persons, key=lambda p: p.get("display_name", "").casefold())

    def list_profiles(self, include_inactive=False):
        profiles = self.data.get("profiles", [])
        if not include_inactive:
            profiles = [p for p in profiles if p.get("status", "active") == "active"]
        return sorted(profiles, key=lambda p: p.get("display_name", "").casefold())

    def list_email_accounts(self, profile_id=None, enabled_only=False):
        accounts = self.data.get("email_accounts", [])
        if profile_id:
            accounts = [a for a in accounts if a.get("profile_id") == profile_id]
        if enabled_only:
            accounts = [a for a in accounts if a.get("enabled", True)]
        return sorted(accounts, key=lambda a: a.get("label", "").casefold())

    def get_email_account(self, account_id):
        return next(
            (a for a in self.data.get("email_accounts", []) if a.get("id") == account_id),
            None,
        )

    def save_email_account(self, profile_id, values, account_id=None):
        if not self.get_profile(profile_id):
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        if not self._clean(values.get("imap_server")) or not self._clean(values.get("username")):
            raise ProfileValidationError("IMAP-Server und E-Mail-Adresse sind Pflichtfelder.")
        account = self.get_email_account(account_id) if account_id else None
        if account is None:
            account = self._load_template("email_account")
            account["id"] = self._new_id("mail")
            account["profile_id"] = profile_id
            self.data.setdefault("email_accounts", []).append(account)
        elif account.get("profile_id") != profile_id:
            raise ProfileValidationError("Das E-Mail-Konto gehört zu einem anderen Profil.")
        original = copy.deepcopy(account)
        try:
            self._merge(account, values)
            from src.mail_auth import auth_method_for_provider, normalize_provider
            account["provider"] = normalize_provider(account.get("provider"))
            account["auth_method"] = auth_method_for_provider(account["provider"])
            from src.mail_auth import validate_imap_settings
            validate_imap_settings(account)
            account["label"] = self._clean(account.get("label")) or self._clean(account.get("username"))
            self.save()
        except Exception:
            account.clear()
            account.update(original)
            if not account_id and account in self.data.get("email_accounts", []):
                self.data["email_accounts"].remove(account)
            raise
        return account

    def remove_email_account(self, account_id):
        account = self.get_email_account(account_id)
        if not account:
            return False
        self.data["email_accounts"].remove(account)
        self.save()
        return True

    def get_person(self, person_id):
        return next((p for p in self.data["persons"] if p.get("id") == person_id), None)

    def get_profile(self, profile_id):
        return next((p for p in self.data["profiles"] if p.get("id") == profile_id), None)

    def create_person(
        self,
        first_name,
        last_name,
        middle_names=None,
        is_minor=False,
        date_of_birth="",
        display_name="",
        gender="",
    ):
        first_name = self._clean(first_name)
        last_name = self._clean(last_name)
        if not first_name or not last_name:
            raise ProfileValidationError("Vorname und Nachname sind Pflichtfelder.")

        middle_names = [self._clean(v) for v in (middle_names or []) if self._clean(v)]
        full_name = " ".join([first_name, *middle_names, last_name])
        person = self._load_template("person")
        person["id"] = self._new_id("person")
        person["display_name"] = self._clean(display_name) or full_name
        calculated_minor = is_minor_from_birth_date(date_of_birth)
        person["is_minor"] = bool(is_minor) if calculated_minor is None else calculated_minor
        person["name"].update({
            "first_name": first_name,
            "second_first_name": middle_names[0] if middle_names else "",
            "middle_names": middle_names,
            "last_name": last_name,
            "preferred_name": first_name,
        })
        person["personal"]["date_of_birth"] = self._clean(date_of_birth)
        person["personal"]["gender"] = self._clean(gender).casefold()
        person["matching"]["name_variants"] = list(dict.fromkeys([
            full_name,
            " ".join([first_name, middle_names[0], last_name]) if middle_names else "",
            f"{first_name} {last_name}",
        ]))
        person["matching"]["name_variants"] = [
            value for value in person["matching"]["name_variants"] if value
        ]
        person["routing"]["archive_folder"] = person["display_name"]
        person["routing"]["structure_template"] = "child" if person["is_minor"] else "adult"
        self.data["persons"].append(person)
        try:
            self.save()
        except Exception:
            self.data["persons"].remove(person)
            raise
        return person

    def update_person(self, person_id, changes):
        person = self.get_person(person_id)
        if not person:
            raise ProfileValidationError("Person wurde nicht gefunden.")
        original = copy.deepcopy(person)
        changes = self._normalize_identifier_fields(changes)
        if "date_of_birth" in (changes.get("personal", {}) or {}):
            calculated_minor = is_minor_from_birth_date(changes["personal"]["date_of_birth"])
            changes["is_minor"] = bool(calculated_minor) if calculated_minor is not None else False
            changes.setdefault("routing", {})["structure_template"] = (
                "child" if changes["is_minor"] else "adult"
            )
        try:
            if "pension_insurance_number" in (changes.get("identifiers", {}) or {}):
                person.setdefault("identifiers", {}).pop("social_security_number", None)
            self._merge(person, changes)
            self.save()
        except Exception:
            person.clear()
            person.update(original)
            raise
        return person

    def create_family(self, display_name, archive_name="Gemeinsame Dokumente"):
        return self._create_profile(
            "family",
            display_name,
            archive_name=archive_name or "Gemeinsame Dokumente",
        )

    def create_individual(self, person_id):
        person = self.get_person(person_id)
        if not person:
            raise ProfileValidationError("Person wurde nicht gefunden.")
        if any(
            profile.get("type") == "individual"
            and profile.get("person_id") == person_id
            and profile.get("status", "active") == "active"
            for profile in self.data["profiles"]
        ):
            raise ProfileValidationError("Für diese Person existiert bereits ein Privatpersonenprofil.")
        profile = self._create_profile(
            "individual",
            person["display_name"],
            person_id=person_id,
            structure_template="child" if person_is_minor(person) else "adult",
        )
        return profile

    def individual_profile_for(self, person_id):
        return next((
            profile for profile in self.data.get("profiles", [])
            if profile.get("type") == "individual"
            and profile.get("person_id") == person_id
            and profile.get("status", "active") == "active"
        ), None)

    def ensure_individual_profile(self, person_id):
        existing = self.individual_profile_for(person_id)
        return existing or self.create_individual(person_id)

    def promote_unassigned_persons(self):
        """Make legacy/orphaned people manageable as private profiles."""
        assigned = set()
        for profile in self.list_profiles():
            if profile.get("type") == "individual" and profile.get("person_id"):
                assigned.add(profile["person_id"])
            for person, _membership in self.profile_members(profile["id"]):
                assigned.add(person["id"])
        promoted = []
        for person in self.list_persons():
            if person["id"] in assigned:
                continue
            try:
                promoted.append(self.create_individual(person["id"]))
                assigned.add(person["id"])
            except ProfileValidationError:
                # Keep the person recoverable if a conflicting profile name needs manual resolution.
                continue
        return promoted

    def create_organization(self, display_name, organization_type="company"):
        profile = self._create_profile("organization", display_name)
        profile["organization_type"] = self._clean(organization_type) or "company"
        profile["name"]["legal_name"] = profile["display_name"]
        self.save()
        return profile

    def _create_profile(
        self,
        profile_type,
        display_name,
        archive_name=None,
        person_id=None,
        structure_template=None,
    ):
        if profile_type not in self.PROFILE_TYPES:
            raise ProfileValidationError("Unbekannter Profiltyp.")
        display_name = self._clean(display_name)
        if not display_name:
            raise ProfileValidationError("Der Profilname ist ein Pflichtfeld.")
        if any(p.get("display_name", "").casefold() == display_name.casefold()
               for p in self.data["profiles"] if p.get("status", "active") == "active"):
            raise ProfileValidationError("Ein aktives Profil mit diesem Namen existiert bereits.")

        profile = self._load_template(profile_type)
        profile["id"] = self._new_id(profile_type)
        profile["display_name"] = display_name
        profile["routing"]["archive_folder"] = archive_name or display_name
        if person_id:
            profile["person_id"] = person_id
        if structure_template:
            profile["routing"]["structure_template"] = structure_template
        if profile_type == "family":
            profile["archive_name"] = archive_name or "Gemeinsame Dokumente"
        self.data["profiles"].append(profile)
        try:
            self.save()
        except Exception:
            self.data["profiles"].remove(profile)
            raise
        self._enable_profile_system()
        return profile

    def _enable_profile_system(self):
        if not hasattr(self.config, "set"):
            return
        settings = dict(self.config.get("profile_system") or {})
        if not settings.get("enabled"):
            settings["enabled"] = True
            self.config.set("profile_system", settings)

    def update_profile(self, profile_id, changes):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        original = copy.deepcopy(profile)
        changes = self._normalize_identifier_fields(changes)
        try:
            if profile.get("type") == "family" and "household_identifiers" in changes:
                profile["household_identifiers"] = {}
            self._merge(profile, changes)
            self.save()
        except Exception:
            profile.clear()
            profile.update(original)
            raise
        return profile

    def add_membership(
        self,
        profile_id,
        person_id,
        role="",
        position="",
        department="",
        is_guardian=False,
    ):
        profile = self.get_profile(profile_id)
        person = self.get_person(person_id)
        if not profile or not person:
            raise ProfileValidationError("Profil oder Person wurde nicht gefunden.")
        if profile.get("type") == "individual":
            raise ProfileValidationError("Einer Privatperson können keine weiteren Personen zugeordnet werden.")

        memberships = self._memberships(profile)
        original_memberships = copy.deepcopy(memberships)
        existing = next((m for m in memberships if m.get("person_id") == person_id), None)
        if existing:
            existing.update({
                "role": self._clean(role),
                "position": self._clean(position),
                "department": self._clean(department),
                "is_guardian": bool(is_guardian),
            })
            membership = existing
        else:
            membership = self._load_template("membership")
            membership.update({
                "id": self._new_id("membership"),
                "person_id": person_id,
                "profile_id": profile_id,
                "context": profile["type"],
                "role": self._clean(role),
                "position": self._clean(position),
                "department": self._clean(department),
                "is_guardian": bool(is_guardian),
            })
            memberships.append(membership)
        try:
            self.save()
        except Exception:
            memberships[:] = original_memberships
            raise
        return membership

    def remove_membership(self, profile_id, person_id):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        memberships = self._memberships(profile)
        profile[self._membership_key(profile)] = [
            m for m in memberships if m.get("person_id") != person_id
        ]
        if profile.get("type") == "family":
            profile["partner_relationships"] = [
                relationship
                for relationship in profile.get("partner_relationships", [])
                if person_id not in relationship.get("person_ids", [])
            ]
        self.save()

    def set_partner_relationship(self, profile_id, first_person_id, second_person_id, relationship_type="married"):
        profile = self.get_profile(profile_id)
        if not profile or profile.get("type") != "family":
            raise ProfileValidationError("Partnerbeziehungen können nur in einer Familie gespeichert werden.")
        if first_person_id == second_person_id:
            raise ProfileValidationError("Bitte wähle zwei unterschiedliche Personen aus.")
        member_ids = {person["id"] for person, _membership in self.profile_members(profile_id)}
        if first_person_id not in member_ids or second_person_id not in member_ids:
            raise ProfileValidationError("Beide Personen müssen dieser Familie angehören.")
        relationship_type = self._clean(relationship_type).casefold()
        if relationship_type not in {"married", "civil_partnership", "partnership"}:
            raise ProfileValidationError("Die ausgewählte Partnerbeziehung ist nicht gültig.")
        relationships = profile.setdefault("partner_relationships", [])
        relationships[:] = [
            relationship for relationship in relationships
            if first_person_id not in relationship.get("person_ids", [])
            and second_person_id not in relationship.get("person_ids", [])
        ]
        relationships.append({
            "person_ids": [first_person_id, second_person_id],
            "type": relationship_type,
        })
        self.save()
        return relationships[-1]

    def remove_partner_relationship(self, profile_id, first_person_id, second_person_id):
        profile = self.get_profile(profile_id)
        if not profile or profile.get("type") != "family":
            raise ProfileValidationError("Familie wurde nicht gefunden.")
        pair = {first_person_id, second_person_id}
        profile["partner_relationships"] = [
            relationship for relationship in profile.get("partner_relationships", [])
            if set(relationship.get("person_ids", [])) != pair
        ]
        self.save()

    def deactivate_person(self, person_id):
        person = self.get_person(person_id)
        if not person:
            raise ProfileValidationError("Person wurde nicht gefunden.")
        person["status"] = "inactive"
        self.save()

    def deactivate_profile(self, profile_id):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        profile["status"] = "inactive"
        self.save()

    def delete_profile(self, profile_id):
        """Delete profile configuration while deliberately leaving document archives untouched."""
        profile = self.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        profile_copy = copy.deepcopy(profile)
        removed_accounts = [
            account for account in self.data.get("email_accounts", [])
            if account.get("profile_id") == profile_id
        ]
        self.data["profiles"].remove(profile)
        self.data["email_accounts"] = [
            account for account in self.data.get("email_accounts", [])
            if account.get("profile_id") != profile_id
        ]
        try:
            self.save()
        except Exception:
            self.data["profiles"].append(profile_copy)
            self.data["email_accounts"].extend(removed_accounts)
            raise
        self._remove_config_directory(self.profiles_root, profile_id)
        return [account.get("id") for account in removed_accounts if account.get("id")]

    def delete_person(self, person_id):
        """Delete a person and all of their profile memberships, never their documents."""
        person = self.get_person(person_id)
        if not person:
            raise ProfileValidationError("Person wurde nicht gefunden.")
        original = copy.deepcopy(self.data)
        individual_ids = {
            profile.get("id") for profile in self.data.get("profiles", [])
            if profile.get("type") == "individual" and profile.get("person_id") == person_id
        }
        removed_account_ids = [
            account.get("id") for account in self.data.get("email_accounts", [])
            if account.get("profile_id") in individual_ids and account.get("id")
        ]
        self.data["persons"] = [item for item in self.data["persons"] if item.get("id") != person_id]
        self.data["profiles"] = [
            profile for profile in self.data["profiles"] if profile.get("id") not in individual_ids
        ]
        self.data["email_accounts"] = [
            account for account in self.data.get("email_accounts", [])
            if account.get("profile_id") not in individual_ids
        ]
        for profile in self.data["profiles"]:
            key = self._membership_key(profile)
            profile[key] = [
                membership for membership in self._memberships(profile)
                if membership.get("person_id") != person_id
            ]
            if profile.get("type") == "family":
                profile["partner_relationships"] = [
                    relationship
                    for relationship in profile.get("partner_relationships", [])
                    if person_id not in relationship.get("person_ids", [])
                ]
        try:
            self.save()
        except Exception:
            self.data = original
            raise
        self._remove_config_directory(self.persons_root, person_id)
        for profile_id in individual_ids:
            self._remove_config_directory(self.profiles_root, profile_id)
        return removed_account_ids

    @staticmethod
    def _remove_config_directory(root, item_id):
        if root is None:
            return
        root = Path(root).resolve()
        target = (root / item_id).resolve()
        if target.parent != root:
            raise ProfileValidationError("Ungültiger Konfigurationspfad; Löschen wurde abgebrochen.")
        if target.exists():
            shutil.rmtree(target)

    def profile_members(self, profile_id):
        profile = self.get_profile(profile_id)
        if not profile:
            return []
        if profile.get("type") == "individual":
            person = self.get_person(profile.get("person_id"))
            return [] if not person else [(person, {"role": "Privatperson"})]
        result = []
        for membership in self._memberships(profile):
            person = self.get_person(membership.get("person_id"))
            if person:
                result.append((person, membership))
        return sorted(result, key=lambda item: item[0].get("display_name", "").casefold())

    def resolve_storage_root(self, profile_id):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ProfileValidationError("Profil wurde nicht gefunden.")
        routing = profile.get("routing", {}) or {}
        custom_root = self._clean(routing.get("storage_root"))
        if not routing.get("use_global_storage", True):
            if not custom_root:
                raise ProfileValidationError(
                    "Für den eigenen Profilspeicher muss ein Speicherort gewählt werden."
                )
            return Path(custom_root)
        user_path = self.config.get("user_path")
        if not user_path:
            raise ProfileValidationError("Der globale Speicherort ist nicht gesetzt.")
        return Path(user_path)

    def resolve_backup_directory(self, profile_id=None):
        """Return the central backup directory, optionally scoped to one profile."""
        user_path = self.config.get("user_path")
        if user_path:
            backup_directory = Path(user_path) / BACKUP_DIRECTORY_NAME
        else:
            # Before the first storage setup, keep the fallback in Sorterino's
            # private runtime area instead of writing beside an arbitrary profile.
            backup_directory = Path(self.config.backup_root)

        if not profile_id:
            return backup_directory

        profile = self.get_profile(profile_id)
        if not profile:
            return backup_directory
        folder_name = re.sub(
            r'[\\/*?:"<>|]', "", self._clean(profile.get("display_name"))
        ).strip()
        return backup_directory / (folder_name or profile_id)

    def validate_registry(self):
        person_ids = [p.get("id") for p in self.data.get("persons", [])]
        profile_ids = [p.get("id") for p in self.data.get("profiles", [])]
        if None in person_ids or "" in person_ids or len(person_ids) != len(set(person_ids)):
            raise ProfileValidationError("Personen-IDs fehlen oder sind nicht eindeutig.")
        if None in profile_ids or "" in profile_ids or len(profile_ids) != len(set(profile_ids)):
            raise ProfileValidationError("Profil-IDs fehlen oder sind nicht eindeutig.")

        known_persons = set(person_ids)
        active_profile_names = [
            self._clean(profile.get("display_name")).casefold()
            for profile in self.data.get("profiles", [])
            if profile.get("status", "active") == "active"
        ]
        if len(active_profile_names) != len(set(active_profile_names)):
            raise ProfileValidationError("Aktive Profilnamen müssen eindeutig sein.")
        for person in self.data.get("persons", []):
            name = person.get("name", {}) or {}
            if not self._clean(name.get("first_name")) or not self._clean(name.get("last_name")):
                raise ProfileValidationError("Jede Person benötigt Vor- und Nachnamen.")
            structure = (person.get("routing", {}) or {}).get("structure_template")
            if structure and structure not in self.STRUCTURE_TEMPLATES:
                raise ProfileValidationError("Eine Person verwendet eine unbekannte Strukturvorlage.")
            self._validate_folder_name(
                (person.get("routing", {}) or {}).get("archive_folder"),
                "Personenordner",
            )
        for profile in self.data.get("profiles", []):
            if profile.get("type") not in self.PROFILE_TYPES:
                raise ProfileValidationError("Ein Profil besitzt einen unbekannten Typ.")
            if not self._clean(profile.get("display_name")):
                raise ProfileValidationError("Jedes Profil benötigt einen Namen.")
            if profile.get("type") == "individual" and profile.get("person_id") not in known_persons:
                raise ProfileValidationError("Ein Privatpersonenprofil verweist auf eine unbekannte Person.")
            structure = (profile.get("routing", {}) or {}).get("structure_template")
            if structure and structure not in self.STRUCTURE_TEMPLATES:
                raise ProfileValidationError("Ein Profil verwendet eine unbekannte Strukturvorlage.")
            routing = profile.get("routing", {}) or {}
            self._validate_folder_name(routing.get("archive_folder"), "Profilordner")
            if not routing.get("use_global_storage", True) and not self._clean(routing.get("storage_root")):
                raise ProfileValidationError("Ein eigener Profilspeicher benötigt einen Speicherort.")
            if not routing.get("use_global_storage", True):
                storage_root = Path(self._clean(routing.get("storage_root")))
                if not storage_root.is_absolute():
                    raise ProfileValidationError("Der Profilspeicher muss ein absoluter Pfad sein.")
            for membership in self._memberships(profile):
                if membership.get("person_id") not in known_persons:
                    raise ProfileValidationError("Eine Mitgliedschaft verweist auf eine unbekannte Person.")
                if membership.get("profile_id") != profile.get("id"):
                    raise ProfileValidationError("Eine Mitgliedschaft verweist auf das falsche Profil.")
        known_profiles = set(profile_ids)
        account_ids = []
        for account in self.data.get("email_accounts", []):
            account_ids.append(account.get("id"))
            if account.get("profile_id") not in known_profiles:
                raise ProfileValidationError("Ein E-Mail-Konto verweist auf ein unbekanntes Profil.")
            if not self._clean(account.get("imap_server")) or not self._clean(account.get("username")):
                raise ProfileValidationError("Ein E-Mail-Konto ist unvollständig.")
            from src.mail_auth import OAUTH_PROVIDERS, normalize_provider
            provider = normalize_provider(account.get("provider"))
            method = account.get("auth_method")
            if method and provider in OAUTH_PROVIDERS and method != "oauth2":
                raise ProfileValidationError("Google- und Microsoft-Konten benötigen OAuth2.")
        if len(account_ids) != len(set(account_ids)):
            raise ProfileValidationError("E-Mail-Konto-IDs müssen eindeutig sein.")

    def migrate_legacy_company_profile(self):
        legacy = self.config.get("company_profile") or {}
        if self.data["profiles"] or not self._legacy_has_data(legacy):
            return None

        name = self._clean(legacy.get("name"))
        person_data = legacy.get("person", {}) or {}
        first_name = self._clean(person_data.get("first_name"))
        last_name = self._clean(person_data.get("last_name"))

        organization = None
        person = None
        if name:
            organization = self.create_organization(name)
            organization["addresses"] = self._legacy_address(legacy.get("address", {}))
            organization["contacts"] = self._legacy_contacts(legacy.get("contact", {}))
            organization["registration"]["tax_numbers"] = [
                value for value in [self._clean((legacy.get("financial", {}) or {}).get("tax_id"))]
                if value
            ]
            organization["matching"]["keywords"] = legacy.get("keywords", []) or []

        if first_name and last_name:
            person = self.create_person(first_name, last_name)
            person["addresses"] = self._legacy_address(legacy.get("address", {}))
            person["contacts"] = self._legacy_contacts(legacy.get("contact", {}))
            person["identifiers"]["tax_identification_number"] = self._clean(
                (legacy.get("financial", {}) or {}).get("tax_id")
            )

        if organization and person:
            self.add_membership(organization["id"], person["id"], role="owner")
        self.save()
        return {"organization": organization, "person": person}

    def legacy_migration_available(self):
        return not self.data["profiles"] and self._legacy_has_data(
            self.config.get("company_profile") or {}
        )

    @staticmethod
    def _merge(target, changes):
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                ProfileService._merge(target[key], value)
            else:
                target[key] = copy.deepcopy(value)

    @classmethod
    def _normalize_identifier_fields(cls, values):
        values = copy.deepcopy(values)
        try:
            for key, value in list(values.items()):
                if isinstance(value, dict):
                    values[key] = cls._normalize_identifier_fields(value)
                elif key == "ibans":
                    values[key] = [cls.normalize_iban(iban) for iban in value if cls._clean(iban)]
                elif key in NORMALIZERS:
                    normalizer = NORMALIZERS[key]
                    if isinstance(value, list):
                        values[key] = [normalizer(item) for item in value if cls._clean(item)]
                    else:
                        values[key] = normalizer(value)
        except IdentifierFormatError as exc:
            raise ProfileValidationError(str(exc)) from exc
        return values

    @staticmethod
    def normalize_iban(value):
        iban = re.sub(r"\s+", "", str(value or "")).upper()
        if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", iban):
            raise ProfileValidationError("Die IBAN hat kein gültiges Format.")
        rearranged = iban[4:] + iban[:4]
        numeric = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
        if int(numeric) % 97 != 1:
            raise ProfileValidationError("Die IBAN-Prüfsumme ist ungültig.")
        return iban

    @staticmethod
    def _membership_key(profile):
        return "member_relationships" if profile.get("type") == "family" else "memberships"

    def _memberships(self, profile):
        if profile.get("type") == "individual":
            return []
        key = self._membership_key(profile)
        return profile.setdefault(key, [])

    @staticmethod
    def _legacy_has_data(legacy):
        if not isinstance(legacy, dict):
            return False
        return any([
            legacy.get("name"),
            (legacy.get("person", {}) or {}).get("first_name"),
            (legacy.get("person", {}) or {}).get("last_name"),
        ])

    @staticmethod
    def _legacy_address(address):
        address = address or {}
        if not any(address.values()):
            return {}
        return {
            "street": address.get("street", ""),
            "postal_code": address.get("zip", ""),
            "city": address.get("city", ""),
            "country": "DE",
        }

    @staticmethod
    def _legacy_contacts(contact):
        contact = contact or {}
        emails = [] if not contact.get("email") else [{"type": "primary", "value": contact["email"]}]
        phones = [] if not contact.get("phone") else [{"type": "primary", "value": contact["phone"]}]
        return {"emails": emails, "phones": phones, "websites": []}
