import json
import os


class FormatsLoader:

    def __init__(self, path: str):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"Supported formats file not found: {self.path}"
            )

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data
