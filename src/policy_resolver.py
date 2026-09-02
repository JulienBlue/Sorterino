import copy
import json

from src.person_age import person_is_minor


class PolicyResolver:
    """Resolve preset → profile → person → profile/person-context overrides."""

    def __init__(self, config, profile_service=None):
        self.config = config
        self.profiles = profile_service

    def rules_for(self, profile=None, person_ids=None):
        return self._resolve("rules", profile, person_ids)

    def structure_for(self, profile=None, person_ids=None):
        return self._resolve("structure", profile, person_ids)

    def _resolve(self, kind, profile, person_ids):
        person_ids = list(person_ids or [])
        preset = self._preset_name(profile, person_ids)
        result = self._read(self.config.presets_root / preset / f"{kind}.json")
        if profile:
            profile_root = self.config.profiles_root / profile["id"]
            result = self._merge(result, self._read(profile_root / f"{kind}.override.json"))
            for person_id in person_ids:
                result = self._merge(
                    result,
                    self._read(self.config.persons_root / person_id / f"{kind}.override.json"),
                )
                result = self._merge(
                    result,
                    self._read(profile_root / "persons" / person_id / f"{kind}.override.json"),
                )
        return result

    def _preset_name(self, profile, person_ids):
        if not profile:
            return "person"
        if profile.get("type") == "organization":
            return "organization"
        if profile.get("type") == "family":
            if len(person_ids) == 1 and self.profiles:
                person = self.profiles.get_person(person_ids[0])
                return "child" if person and person_is_minor(person) else "person"
            return "family"
        return "person"

    @staticmethod
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @classmethod
    def _merge(cls, base, override):
        result = copy.deepcopy(base or {})
        for key, value in (override or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = cls._merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
