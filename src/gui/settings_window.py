import customtkinter as ctk
import json


class SettingsWindow(ctk.CTkToplevel):

    def __init__(self, master, config):
        super().__init__(master)

        self.title("Einstellungen")
        self.geometry("800x600")

        self.config = config

        self.create_ui()
        self.load_all()

    # ---------------- UI ----------------

    def create_ui(self):

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_config = self.tabs.add("Config")
        self.tab_rules = self.tabs.add("Rules")
        self.tab_structure = self.tabs.add("Structure")

        # ---------- CONFIG ----------

        self.config_text = ctk.CTkTextbox(self.tab_config)
        self.config_text.pack(fill="both", expand=True)

        self.save_config_btn = ctk.CTkButton(
            self.tab_config,
            text="Config speichern",
            command=self.save_config
        )
        self.save_config_btn.pack(pady=5)

        # ---------- RULES ----------

        self.rules_text = ctk.CTkTextbox(self.tab_rules)
        self.rules_text.pack(fill="both", expand=True)

        self.save_rules_btn = ctk.CTkButton(
            self.tab_rules,
            text="Rules speichern",
            command=self.save_rules
        )
        self.save_rules_btn.pack(pady=5)

        # ---------- STRUCTURE ----------

        self.structure_text = ctk.CTkTextbox(self.tab_structure)
        self.structure_text.pack(fill="both", expand=True)

        self.save_structure_btn = ctk.CTkButton(
            self.tab_structure,
            text="Structure speichern",
            command=self.save_structure
        )
        self.save_structure_btn.pack(pady=5)

    # ---------------- LOAD ----------------

    def load_all(self):
        self.load_config()
        self.load_rules()
        self.load_structure()

    def load_config(self):
        try:
            with open(self.config.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.config_text.delete("0.0", "end")
            self.config_text.insert("0.0", json.dumps(data, indent=2))

        except Exception as e:
            print("Config Load Fehler:", e)

    def load_rules(self):
        try:
            with open(self.config.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.rules_text.delete("0.0", "end")
            self.rules_text.insert("0.0", json.dumps(data, indent=2))

        except Exception as e:
            print("Rules Load Fehler:", e)

    def load_structure(self):
        try:
            with open(self.config.structure_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.structure_text.delete("0.0", "end")
            self.structure_text.insert("0.0", json.dumps(data, indent=2))

        except Exception as e:
            print("Structure Load Fehler:", e)

    # ---------------- SAVE ----------------

    def save_config(self):
        try:
            data = json.loads(self.config_text.get("0.0", "end"))

            with open(self.config.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print("Config Save Fehler:", e)

    def save_rules(self):
        try:
            data = json.loads(self.rules_text.get("0.0", "end"))

            with open(self.config.rules_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print("Rules Save Fehler:", e)

    def save_structure(self):
        try:
            data = json.loads(self.structure_text.get("0.0", "end"))

            with open(self.config.structure_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print("Structure Save Fehler:", e)