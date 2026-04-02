import os


class PathResolver:

    def __init__(self, structure):
        self.structure = structure
        self._doc_type_map = self._build_doc_type_map()

    # --------------------------------------------------
    # 🔥 BUILD MAPPING (STRUCTURE → DOMAIN)
    # --------------------------------------------------

    def _build_doc_type_map(self):
        """
        Baut Mapping:
        Ausgangsrechnung -> Ausgangsrechnungen
        Eingangsrechnung -> Eingangsrechnungen
        """

        mapping = {}

        for category, types in self.structure.items():
            for folder_name in types.keys():

                normalized = folder_name.lower()

                # einfache Heuristik: plural → singular
                if normalized.endswith("en"):
                    singular = normalized[:-2]
                else:
                    singular = normalized

                mapping[singular] = folder_name

        return mapping

    # --------------------------------------------------
    # 🔥 RESOLVE DOC TYPE
    # --------------------------------------------------

    def _resolve_doc_type(self, doc_type: str):

        if not doc_type:
            return None

        key = doc_type.lower()

        # 1️⃣ direkter Treffer
        if key in self._doc_type_map:
            return self._doc_type_map[key]

        # 2️⃣ fallback: einfach zurückgeben
        return doc_type

    # --------------------------------------------------
    # MAIN
    # --------------------------------------------------

    def resolve(self, metadata):

        category = metadata.category
        doc_type = metadata.document_type
        year = metadata.year
        contexts = metadata.contexts or {}

        if not category:
            return None

        path_parts = [category]

        # --------------------------------------------------
        # DOC TYPE (FIXED)
        # --------------------------------------------------

        resolved_type = self._resolve_doc_type(doc_type)

        if resolved_type:
            path_parts.append(resolved_type)

        # --------------------------------------------------
        # YEAR
        # --------------------------------------------------

        if year:
            path_parts.append(str(year))

        # --------------------------------------------------
        # MONTH
        # --------------------------------------------------

        month_number = contexts.get("month_number")
        month_name = contexts.get("month_name")

        if month_number and month_name:
            path_parts.append(f"{month_number} {month_name} {year}")

        # --------------------------------------------------
        # FINAL PATH
        # --------------------------------------------------

        return os.path.join(*path_parts)