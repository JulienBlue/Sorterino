import os


class PathResolver:

    def __init__(self, structure: dict):
        self.tree = structure

    def resolve(self, metadata) -> str:

        category = metadata.category

        if not category or category not in self.tree:
            return "99_Sonstiges"

        path_parts = [category]
        node = self.tree[category]

        resolved = self._walk(node, metadata)

        if resolved:
            path_parts.extend(resolved)

        return os.path.join(*path_parts)

    def _walk(self, node: dict, metadata):

        if not isinstance(node, dict):
            return None

        dynamic_values = {
            f"{{{key}}}": value
            for key, value in metadata.contexts.items()
            if value
        }

        if metadata.year:
            dynamic_values["{Jahr}"] = str(metadata.year)

        for key, value in node.items():

            # Dynamischer Platzhalter
            if key in dynamic_values:
                sub_path = self._walk(value, metadata)
                return [dynamic_values[key]] + (sub_path or [])

            # Dokumenttyp
            if key == metadata.document_type:
                sub_path = self._walk(value, metadata)
                return [key] + (sub_path or [])

            # Rekursiv weiter
            if isinstance(value, dict):
                sub_path = self._walk(value, metadata)
                if sub_path:
                    return [key] + sub_path

        return None