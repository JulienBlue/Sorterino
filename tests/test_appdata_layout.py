import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.config import Config
from src.policy_resolver import PolicyResolver
from src.profile_service import ProfileService
from tests.test_profile_service import FakeConfig


class AppDataLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_layout_is_created_in_appdata_root(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        self.assertEqual(config.settings_path, self.root / "appdata" / "settings.json")
        for path in (
            config.incoming_root, config.manual_root, config.error_root,
            config.logs_root, config.profiles_root, config.persons_root,
            config.presets_root / "child" / "structure.json",
        ):
            self.assertTrue(path.exists(), path)

    def test_parallel_atomic_config_writes_remain_valid(self):
        target = self.root / "appdata" / "settings.json"

        with ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(
                lambda number: Config._write_json(target, {"write": number}),
                range(30),
            ))

        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertIn("write", data)
        self.assertEqual(list(target.parent.glob(".settings.json.*.tmp")), [])

    def test_standard_storage_creates_shared_incoming_folder(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        documents = self.root / "documents"
        (config.incoming_root / "wartend.pdf").write_bytes(b"PDF")

        config.set_standard_storage(documents)
        reloaded = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")

        self.assertEqual(reloaded.incoming_root, documents / "Sorterino - Eingang")
        self.assertTrue(reloaded.incoming_root.is_dir())
        self.assertTrue((reloaded.incoming_root / "wartend.pdf").exists())
        self.assertFalse(reloaded.get("incoming_path_custom"))

    def test_custom_incoming_folder_survives_standard_storage_change(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        custom_incoming = self.root / "scanner-input"
        config.set_standard_storage(self.root / "documents-one")
        config.set_incoming_storage(custom_incoming)
        config.set_standard_storage(self.root / "documents-two")
        reloaded = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")

        self.assertEqual(reloaded.incoming_root, custom_incoming)
        self.assertTrue(reloaded.get("incoming_path_custom"))

    def test_legacy_registry_and_runtime_are_copied_and_split(self):
        home = self.root / "home"
        home.mkdir()
        documents = self.root / "documents"
        old_configs = documents / "Sorterino - Runtime" / "configs"
        old_configs.mkdir(parents=True)
        (home / ".sorterino_config.json").write_text(
            json.dumps({"user_path": str(documents), "appearance_mode": "dark"}),
            encoding="utf-8",
        )
        legacy_config = FakeConfig(old_configs)
        legacy_config.profiles_path = old_configs / "profiles.json"
        legacy_service = ProfileService(legacy_config)
        family = legacy_service.create_family("Familie Hirte")
        child = legacy_service.create_person("Henri", "Hirte", ["Mika"], is_minor=True)
        legacy_service.add_membership(family["id"], child["id"], role="child")
        old_incoming = documents / "Sorterino - Runtime" / "incoming"
        old_incoming.mkdir()
        (old_incoming / "test.pdf").write_bytes(b"PDF")

        config = Config(app_data_root=self.root / "appdata", legacy_home=home)
        migrated = ProfileService(config)

        self.assertEqual(config.get("user_path"), str(documents))
        self.assertEqual(config.get("appearance_mode"), "dark")
        self.assertTrue((config.incoming_root / "test.pdf").exists())
        self.assertTrue((config.profiles_root / family["id"] / "profile.json").exists())
        self.assertTrue((config.persons_root / child["id"] / "person.json").exists())
        self.assertEqual(migrated.get_profile(family["id"])["display_name"], "Familie Hirte")
        self.assertTrue(legacy_config.profiles_path.exists(), "Die Legacy-Datei bleibt als Rückfall erhalten")

    def test_policy_layers_presets_profile_person_and_context(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        service = ProfileService(config)
        family = service.create_family("Familie Hirte")
        child = service.create_person("Henri", "Hirte", is_minor=True)
        service.add_membership(family["id"], child["id"], role="child")
        profile_root = config.profiles_root / family["id"]
        person_root = config.persons_root / child["id"]
        context_root = profile_root / "persons" / child["id"]
        context_root.mkdir(parents=True)
        (profile_root / "structure.override.json").write_text(json.dumps({"Profilablage": {}}), encoding="utf-8")
        (person_root / "structure.override.json").write_text(json.dumps({"Persönlich": {}}), encoding="utf-8")
        (context_root / "structure.override.json").write_text(json.dumps({"Nur in Familie": {}}), encoding="utf-8")

        structure = PolicyResolver(config, service).structure_for(family, [child["id"]])
        self.assertIn("Gesundheit", structure)
        self.assertIn("Profilablage", structure)
        self.assertIn("Persönlich", structure)
        self.assertIn("Nur in Familie", structure)

    def test_old_presets_receive_new_defaults_without_losing_custom_rules(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        rules_path = config.presets_root / "person" / "rules.json"
        rules_path.write_text(json.dumps({
            "rules": [{
                "id": "my_private_rule",
                "category": "Sonstiges",
                "document_type": "Eigene Dokumente",
                "strong_keywords": ["mein sonderfall"],
            }]
        }), encoding="utf-8")

        upgraded = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        rules = json.loads((upgraded.presets_root / "person" / "rules.json").read_text(encoding="utf-8"))
        ids = {rule.get("id") for rule in rules["rules"]}

        self.assertEqual(rules["schema_version"], 14)
        self.assertIn("tax_notice", ids)
        self.assertIn("assignment_sheet", ids)
        self.assertIn("certificate_of_conduct", ids)
        self.assertIn("housing_defect_documentation", ids)
        self.assertIn("my_private_rule", ids)

    def test_family_structure_upgrade_removes_known_duplicates_but_keeps_custom_folders(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        structure_path = config.presets_root / "family" / "structure.json"
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        structure["Gesundheit und Pflege"] = {"Alt": {}}
        structure["Finanzen"]["Kredite und Darlehen"] = {}
        structure["Identität und Urkunden"]["Geburts- und Heiratsurkunden"] = {}
        structure["Mein eigener Bereich"] = {"Unterlagen": {}}
        structure_path.write_text(json.dumps(structure), encoding="utf-8")
        (config.presets_root / "catalog.json").write_text(
            json.dumps({"structure_schema_version": 2}), encoding="utf-8"
        )

        upgraded = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        result = json.loads((upgraded.presets_root / "family" / "structure.json").read_text(encoding="utf-8"))

        self.assertNotIn("Gesundheit und Pflege", result)
        self.assertNotIn("Kredite und Darlehen", result["Finanzen"])
        self.assertNotIn("Geburts- und Heiratsurkunden", result["Identität und Urkunden"])
        self.assertIn("Geburtsurkunden", result["Identität und Urkunden"])
        self.assertIn("Eheurkunde", result["Identität und Urkunden"])
        self.assertIn("Mein eigener Bereich", result)
        self.assertIn("Identität und Urkunden", result)

    def test_deleting_split_profiles_removes_only_config_directories(self):
        config = Config(app_data_root=self.root / "appdata", legacy_home=self.root / "home")
        documents = self.root / "documents"
        documents.mkdir()
        config.set("user_path", str(documents))
        service = ProfileService(config)
        person = service.create_person("Sabine", "Hirte")
        private_profile = service.create_individual(person["id"])
        archive = documents / "Sabine Hirte"
        archive.mkdir()
        (archive / "Dokument.pdf").write_bytes(b"PDF")

        service.delete_person(person["id"])

        self.assertFalse((config.persons_root / person["id"]).exists())
        self.assertFalse((config.profiles_root / private_profile["id"]).exists())
        self.assertTrue((archive / "Dokument.pdf").exists())


if __name__ == "__main__":
    unittest.main()
