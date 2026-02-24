import os


class PathResolver:

    def __init__(self, structure: dict):
        self.structure = structure
        self.root = structure["root"]
        self.tree = structure["structure"]

    def resolve(self, metadata) -> str:
        """
        Returns relative path inside Bürokratie (WITHOUT root)
        """

        category = metadata.category

        if not category or category not in self.tree:
            return "99_Sonstiges"

        path_parts = [category]

        node = self.tree[category]

        resolved = self._walk(node, metadata)

        if resolved:
            path_parts.extend(resolved)
        else:
            path_parts.append("99_Sonstiges")

        return os.path.join(*path_parts)

    def _walk(self, node: dict, metadata) -> list | None:

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

            # Dynamic placeholders
            if key in dynamic_values:
                next_node = value
                sub_path = self._walk(next_node, metadata)
                return [dynamic_values[key]] + (sub_path or [])

            # Match document type
            if key == metadata.document_type:
                return [key]

            # Continue recursion
            if isinstance(value, dict):
                sub_path = self._walk(value, metadata)
                if sub_path:
                    return [key] + sub_path

        return None