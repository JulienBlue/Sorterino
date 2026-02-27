import os


class PathResolver:

    def __init__(self, structure):
        self.structure = structure

    def resolve(self, metadata):
        category = metadata.category
        doc_type = metadata.document_type
        year = metadata.year
        contexts = metadata.contexts or {}

        if not category:
            return None

        path_parts = [category]

        if doc_type:
            path_parts.append(doc_type + "en" if not doc_type.endswith("en") else doc_type)

        if year:
            path_parts.append(str(year))

        month_number = contexts.get("month_number")
        month_name = contexts.get("month_name")

        if month_number and month_name:
            path_parts.append(f"{month_number} {month_name}")

        return "\\".join(path_parts)