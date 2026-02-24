import json
import os


class StructureLoader:

    def __init__(self, structure_path: str):
        self.structure_path = structure_path

    def load_structure(self) -> dict:
        if not os.path.exists(self.structure_path):
            raise FileNotFoundError(
                f"Structure file not found: {self.structure_path}"
            )

        with open(self.structure_path, "r", encoding="utf-8") as f:
            return json.load(f)