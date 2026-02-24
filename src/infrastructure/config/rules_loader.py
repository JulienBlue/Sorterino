import json
import os


class RulesLoader:

    def __init__(self, rules_path: str):
        self.rules_path = rules_path

    def load_rules(self):
        if not os.path.exists(self.rules_path):
            raise FileNotFoundError(
                f"Rules file not found: {self.rules_path}"
            )

        with open(self.rules_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("rules", [])
