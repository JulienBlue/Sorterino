def save_config(self):
    import json

    self.config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(self.config_path, "w", encoding="utf-8") as f:
        json.dump(self.config_data, f, indent=2)