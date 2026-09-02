import copy
import json
import tempfile
from pathlib import Path

from src.profile_errors import ProfileValidationError


class ProfileRegistryMixin:
    def _load_registry(self):
        if self.split_storage:
            return self._load_split_registry()
        if not self.path.exists():
            data = self._load_template("profiles")
            self._write_json(self.path, data)

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileValidationError(
                f"Profildatei konnte nicht geladen werden: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ProfileValidationError("Die Profildatei muss ein JSON-Objekt sein.")

        defaults = self._load_template("profiles")
        for key, value in defaults.items():
            data.setdefault(key, copy.deepcopy(value))
        return data

    def _load_split_registry(self):
        data = self._load_template("profiles")
        data["persons"] = []
        data["profiles"] = []
        data["email_accounts"] = []
        for person_path in sorted(self.persons_root.glob("*/person.json")):
            person = self._read_json_file(person_path)
            if person:
                data["persons"].append(person)
        for profile_path in sorted(self.profiles_root.glob("*/profile.json")):
            profile = self._read_json_file(profile_path)
            if not profile:
                continue
            data["email_accounts"].extend(profile.pop("email_accounts", []) or [])
            data["profiles"].append(profile)
        if not data["profiles"] and not data["persons"]:
            legacy_path = getattr(self.config, "legacy_profiles_path", None)
            legacy = self._read_json_file(legacy_path) if legacy_path else None
            if legacy:
                for key in ("persons", "profiles", "email_accounts"):
                    data[key] = copy.deepcopy(legacy.get(key, []))
                self.data = data
                self.save()
        return data

    @staticmethod
    def _read_json_file(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    def _load_template(self, name):
        path = self.template_root / f"template.{name}.json"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileValidationError(
                f"Profiltemplate '{path.name}' konnte nicht geladen werden: {exc}"
            ) from exc

    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.flush()
                temp_path = Path(handle.name)
            temp_path.replace(path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def save(self):
        self.validate_registry()
        if not self.split_storage:
            self._write_json(self.path, self.data)
            return
        account_map = {}
        for account in self.data.get("email_accounts", []):
            account_map.setdefault(account.get("profile_id"), []).append(account)
        for person in self.data.get("persons", []):
            person_dir = self.persons_root / person["id"]
            self._write_json(person_dir / "person.json", person)
            for override_name in ("rules.override.json", "structure.override.json"):
                override = person_dir / override_name
                if not override.exists():
                    self._write_json(override, {})
        for profile in self.data.get("profiles", []):
            stored = copy.deepcopy(profile)
            stored["email_accounts"] = copy.deepcopy(account_map.get(profile["id"], []))
            profile_dir = self.profiles_root / profile["id"]
            self._write_json(profile_dir / "profile.json", stored)
            for override_name in ("rules.override.json", "structure.override.json"):
                override = profile_dir / override_name
                if not override.exists():
                    self._write_json(override, {})
        self._write_json(self.path, {
            "schema_version": 2,
            "profile_ids": [profile["id"] for profile in self.data.get("profiles", [])],
            "person_ids": [person["id"] for person in self.data.get("persons", [])],
        })

    def reload(self):
        self.data = self._load_registry()
