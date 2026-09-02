import json
import os
import copy
from pathlib import Path
import shutil
import tempfile
import threading
import time

from src.initialize_workspace import get_base_path


_JSON_WRITE_LOCK = threading.RLock()


class Config:
    """Central application configuration rooted in AppData/Roaming/Sorterino."""

    SETTINGS_KEYS = {
        "schema_version", "appearance_mode", "user_path", "auto_mode", "autostart",
        "daily_report_time", "profile_system", "company_profile", "ocr", "targets",
        "incoming_path", "incoming_path_custom", "storage_layout_version",
        "window_geometry", "hide_close_to_tray_notice",
    }

    def __init__(self, app_data_root=None, legacy_home=None):
        roaming = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
        self.app_root = Path(app_data_root) if app_data_root else roaming / "Sorterino"
        self.app_root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.app_root / "settings.json"
        self.config_path = self.settings_path
        self.runtime_root = self.app_root / "runtime"
        self.incoming_root = self.runtime_root / "incoming"
        self.logs_root = self.runtime_root / "logs"
        self.backup_root = self.runtime_root / "legacy-backup"
        self.manual_root = self.runtime_root / "manual"
        self.error_root = self.runtime_root / "errors"
        self.state_root = self.runtime_root / "state"
        self.profiles_root = self.app_root / "profiles"
        self.persons_root = self.app_root / "persons"
        self.presets_root = self.app_root / "presets"
        self.config_root = self.app_root
        self.profiles_path = self.profiles_root / "registry.json"
        self.oauth_clients_path = self.app_root / "oauth_clients.json"
        self.database_path = self.app_root / "sorterino.db"
        self.base_config_path = self.settings_path
        self.legacy_base_config_path = Path(legacy_home or Path.home()) / ".sorterino_config.json"
        self.legacy_profiles_path = None
        self._ensure_directories()
        self._migrate_legacy_layout()
        self._ensure_settings()
        self._ensure_oauth_clients()
        self.raw = self._read_json(self.settings_path)
        self.user_path = Path(self.raw["user_path"]) if self.raw.get("user_path") else None
        self.appearance_mode = self.raw.get("appearance_mode", "system")
        self._configure_incoming_root()
        self._install_presets()
        self.rules_path = self.presets_root / "person" / "rules.json"
        self.structure_path = self.presets_root / "person" / "structure.json"
        self._init_ocr()

    def _ensure_directories(self):
        for path in (
            self.runtime_root, self.incoming_root, self.logs_root, self.backup_root,
            self.manual_root, self.error_root, self.state_root, self.profiles_root,
            self.persons_root, self.presets_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _ensure_settings(self):
        template = self._read_json(get_base_path() / "assets" / "templates" / "template.config.json")
        settings = {key: value for key, value in template.items() if key in self.SETTINGS_KEYS}
        settings.update(self._read_json(self.settings_path))
        settings.setdefault("schema_version", 3)
        settings.setdefault("appearance_mode", "system")
        settings.setdefault("user_path", "")
        settings.setdefault("incoming_path", "")
        settings.setdefault("incoming_path_custom", False)
        settings.setdefault("hide_close_to_tray_notice", False)
        self._write_json(self.settings_path, settings)

    def _ensure_oauth_clients(self):
        """Install only public application registration data, never user tokens."""
        if self.oauth_clients_path.exists():
            return
        template = get_base_path() / "assets" / "templates" / "template.oauth_clients.json"
        self._write_json(self.oauth_clients_path, self._read_json(template))

    def _configure_incoming_root(self):
        configured = str(self.raw.get("incoming_path") or "").strip()
        previous_runtime_incoming = self.runtime_root / "incoming"
        if configured:
            self.incoming_root = Path(configured)
        elif self.user_path:
            self.incoming_root = self.user_path / "Sorterino - Eingang"
            self.raw["incoming_path"] = str(self.incoming_root)
            self.raw["incoming_path_custom"] = False
            self._write_json(self.settings_path, self.raw)
            if previous_runtime_incoming.exists() and previous_runtime_incoming.resolve() != self.incoming_root.resolve():
                shutil.copytree(previous_runtime_incoming, self.incoming_root, dirs_exist_ok=True)
        else:
            self.incoming_root = previous_runtime_incoming
        self.incoming_root.mkdir(parents=True, exist_ok=True)

    def _migrate_legacy_layout(self):
        migrated_registry = self.app_root / "legacy.profiles.json"
        if migrated_registry.exists():
            self.legacy_profiles_path = migrated_registry
        if self.settings_path.exists() and self._read_json(self.settings_path).get("storage_layout_version") == 2:
            return
        base = self._read_json(self.legacy_base_config_path)
        user_path = base.get("user_path")
        old_runtime = Path(user_path) / "Sorterino - Runtime" if user_path else None
        old_config = self._read_json(old_runtime / "configs" / "config.json") if old_runtime else {}
        merged = dict(base)
        merged.update(old_config)
        merged.update(self._read_json(self.settings_path))
        settings = {key: value for key, value in merged.items() if key in self.SETTINGS_KEYS}
        settings["schema_version"] = 3
        settings["storage_layout_version"] = 2
        settings["user_path"] = str(user_path or settings.get("user_path") or "")
        if not old_runtime or not old_runtime.exists():
            self._write_json(self.settings_path, settings)
            return
        old_configs = old_runtime / "configs"
        candidate = old_configs / "profiles.json"
        if candidate.exists():
            registry = self._read_json(candidate)
            if not isinstance(registry.get("persons"), list) or not isinstance(registry.get("profiles"), list):
                raise ValueError("Die bisherige profiles.json ist ungültig und wurde nicht migriert.")
            shutil.copy2(candidate, migrated_registry)
            self.legacy_profiles_path = migrated_registry
        for old_name, new_path in (
            ("incoming", self.incoming_root), ("manual_sort", self.manual_root),
            ("error", self.error_root), ("logs", self.logs_root),
            ("backup", self.backup_root),
        ):
            source = old_runtime / old_name
            if source.exists():
                shutil.copytree(source, new_path, dirs_exist_ok=True)
        for filename, preset_name in (("rules.json", "legacy.rules.json"), ("structure.json", "legacy.structure.json")):
            source = old_configs / filename
            target = self.app_root / preset_name
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
        self._write_json(self.settings_path, settings)

    def _install_presets(self):
        template_root = get_base_path() / "assets" / "templates"
        packaged_structure = self._read_json(template_root / "template.structure.json")
        legacy_structure = self._read_json(self.app_root / "legacy.structure.json")
        structure_catalog = self._merge_defaults(packaged_structure, legacy_structure)
        structure_catalog["schema_version"] = packaged_structure.get("schema_version", 1)
        packaged_rules = self._read_json(template_root / "template.rules.json")
        legacy_rules = self._read_json(self.app_root / "legacy.rules.json")
        rules = self._upgrade_rules(legacy_rules, packaged_rules) if legacy_rules else packaged_rules
        structures = structure_catalog.get("templates", {}) or {}
        catalog_state_path = self.presets_root / "catalog.json"
        installed_catalog_version = int(self._read_json(catalog_state_path).get("structure_schema_version", 1))
        template_catalog_version = int(structure_catalog.get("schema_version", 1))
        for name in ("family", "person", "child", "organization"):
            preset_dir = self.presets_root / name
            preset_dir.mkdir(parents=True, exist_ok=True)
            structure_path = preset_dir / "structure.json"
            rules_path = preset_dir / "rules.json"
            source_name = "adult" if name == "person" else name
            if not structure_path.exists():
                self._write_json(structure_path, structures.get(source_name, {}))
            else:
                installed_structure = self._read_json(structure_path)
                original_structure = copy.deepcopy(installed_structure)
                if installed_catalog_version < template_catalog_version:
                    installed_structure = self._migrate_structure_preset(name, installed_structure)
                merged_structure = self._merge_defaults(
                    structures.get(source_name, {}), installed_structure
                )
                if merged_structure != original_structure:
                    self._write_json(structure_path, merged_structure)
            if not rules_path.exists():
                self._write_json(rules_path, rules)
            else:
                installed_rules = self._read_json(rules_path)
                template_version = int(rules.get("schema_version", 1))
                installed_version = int(installed_rules.get("schema_version", 1))
                if installed_version < template_version:
                    upgraded = self._upgrade_rules(installed_rules, rules)
                    self._write_json(rules_path, upgraded)
        if installed_catalog_version < template_catalog_version:
            self._write_json(catalog_state_path, {"structure_schema_version": template_catalog_version})

    @staticmethod
    def _migrate_structure_preset(name, structure):
        """Remove only superseded standard folders; retain unknown/custom folders."""
        migrated = dict(structure or {})
        if name == "family":
            for obsolete in ("Gesundheit und Pflege", "Kinder und Betreuung"):
                migrated.pop(obsolete, None)
            finances = migrated.get("Finanzen")
            if isinstance(finances, dict):
                finances.pop("Kredite und Darlehen", None)
            housing = migrated.get("Wohnen")
            if isinstance(housing, dict):
                for obsolete in ("Miete oder Immobilie", "Nebenkosten", "Energie und Versorgung"):
                    housing.pop(obsolete, None)
        elif name == "person":
            finances = migrated.get("Finanzen")
            if isinstance(finances, dict):
                finances.pop("Kredite und Darlehen", None)
            migrated.pop("Gesundheit und Pflege", None)
            career = migrated.get("Arbeit und Karriere")
            if isinstance(career, dict):
                career.pop("Bewerbungen und Zeugnisse", None)
        elif name == "child":
            migrated.pop("Finanzen und Sparen", None)
        identity = migrated.get("Identität und Urkunden")
        if isinstance(identity, dict):
            identity.pop("Geburts- und Heiratsurkunden", None)
        old_authorities = migrated.get("Behörden und Steuern")
        if isinstance(old_authorities, dict):
            old_authorities.pop("Steuererklärungen", None)
            old_authorities.pop("Steuerbescheide", None)
            if not old_authorities:
                migrated.pop("Behörden und Steuern", None)
        return migrated

    @classmethod
    def _merge_defaults(cls, defaults, existing):
        """Add new preset keys while preserving user-edited existing values."""
        if not isinstance(defaults, dict) or not isinstance(existing, dict):
            return existing
        merged = dict(defaults)
        for key, value in existing.items():
            merged[key] = cls._merge_defaults(defaults.get(key), value) if key in defaults else value
        return merged

    @classmethod
    def _upgrade_rules(cls, installed, template):
        upgraded = cls._merge_defaults(template, installed)
        default_ids = {rule.get("id") for rule in template.get("rules", []) if rule.get("id")}
        default_signatures = {
            (rule.get("category"), rule.get("document_type"))
            for rule in template.get("rules", [])
        }
        custom = []
        for rule in installed.get("rules", []):
            if (
                rule.get("id") not in default_ids
                and (rule.get("category"), rule.get("document_type")) not in default_signatures
            ):
                custom.append(rule)
        upgraded["rules"] = list(template.get("rules", [])) + custom
        upgraded["schema_version"] = template.get("schema_version", 1)
        return upgraded

    def get(self, key, default=None):
        if key == "user_path":
            return str(self.user_path) if self.user_path else None
        if key == "appearance_mode":
            return self.appearance_mode
        return self.raw.get(key, default)

    def set(self, key, value):
        if key in {"user_path", "incoming_path"}:
            value = str(value)
        self.raw[key] = value
        self._write_json(self.settings_path, self.raw)
        if key == "user_path":
            self.user_path = Path(value) if value else None
        elif key == "appearance_mode":
            self.appearance_mode = value

    def set_standard_storage(self, value):
        value = Path(value)
        keep_custom_incoming = bool(self.raw.get("incoming_path_custom"))
        previous_incoming = self.incoming_root
        self.raw["user_path"] = str(value)
        self.user_path = value
        if not keep_custom_incoming:
            self.incoming_root = value / "Sorterino - Eingang"
            self.incoming_root.mkdir(parents=True, exist_ok=True)
            if previous_incoming.exists() and previous_incoming.resolve() != self.incoming_root.resolve():
                shutil.copytree(previous_incoming, self.incoming_root, dirs_exist_ok=True)
            self.raw["incoming_path"] = str(self.incoming_root)
            self.raw["incoming_path_custom"] = False
        self._write_json(self.settings_path, self.raw)

    def set_incoming_storage(self, value):
        self.incoming_root = Path(value)
        self.incoming_root.mkdir(parents=True, exist_ok=True)
        self.raw["incoming_path"] = str(self.incoming_root)
        self.raw["incoming_path_custom"] = True
        self._write_json(self.settings_path, self.raw)

    def _init_ocr(self):
        project_root = get_base_path()
        internal = project_root / "_internal"
        base = internal if internal.exists() else project_root
        ocr = self.raw.get("ocr", {}) or {}
        custom_tess = ocr.get("tesseract_path")
        self.tesseract_path = (
            (Path(custom_tess) if Path(custom_tess).is_absolute() else project_root / custom_tess).resolve()
            if custom_tess else (base / "third_party" / "tesseract" / "tesseract.exe").resolve()
        )
        custom_poppler = ocr.get("poppler_path")
        self.poppler_path = (
            (Path(custom_poppler) if Path(custom_poppler).is_absolute() else project_root / custom_poppler).resolve()
            if custom_poppler else (base / "third_party" / "poppler" / "Library" / "bin").resolve()
        )

    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _write_json(path, data):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _JSON_WRITE_LOCK:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary = Path(handle.name)
                for attempt in range(5):
                    try:
                        temporary.replace(path)
                        temporary = None
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.05 * (attempt + 1))
            finally:
                if temporary and temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
