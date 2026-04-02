from typing import List, Dict, Any


def validate_config(
    rules: List[Dict[str, Any]],
    structure: Dict[str, Any],
    company_profile: Dict[str, Any]
) -> List[str]:

    errors: List[str] = []

    # --------------------------------------------------
    # 🔍 STRUCTURE ANALYSE
    # --------------------------------------------------

    structure_categories = set(structure.keys())
    structure_types = set()

    for category, types in structure.items():

        if not isinstance(types, dict):
            errors.append(f"Structure: Kategorie '{category}' ist kein Objekt")
            continue

        for doc_type in types.keys():
            structure_types.add(doc_type.lower())

    # --------------------------------------------------
    # 🔍 RULES VALIDATION
    # --------------------------------------------------

    if not rules:
        errors.append("rules.json ist leer oder fehlt")
        return errors

    for i, rule in enumerate(rules):

        prefix = f"Rule[{i}]"

        # --------------------------------------------------
        # Pflichtfelder
        # --------------------------------------------------

        category = rule.get("category")
        document_type = rule.get("document_type")
        keywords = rule.get("keywords")

        if not category:
            errors.append(f"{prefix}: category fehlt")

        if not document_type:
            errors.append(f"{prefix}: document_type fehlt")

        if not keywords or not isinstance(keywords, list):
            errors.append(f"{prefix}: keywords fehlen oder sind ungültig")

        # --------------------------------------------------
        # CATEGORY EXISTIERT?
        # --------------------------------------------------

        if category and category not in structure_categories:
            errors.append(f"{prefix}: category '{category}' existiert nicht in structure")

        # --------------------------------------------------
        # DOCUMENT TYPE MATCH?
        # --------------------------------------------------

        if document_type:

            dt_lower = document_type.lower()

            # mögliche Varianten
            variants = {
                dt_lower,
                dt_lower + "en",
                dt_lower + "n",
                dt_lower.rstrip("e") + "en"
            }

            if not any(v in structure_types for v in variants):
                errors.append(
                    f"{prefix}: document_type '{document_type}' passt zu keinem structure-Eintrag"
                )

        # --------------------------------------------------
        # KEYWORDS VALIDIEREN
        # --------------------------------------------------

        if keywords:

            for k in keywords:
                if not isinstance(k, str) or not k.strip():
                    errors.append(f"{prefix}: ungültiges keyword '{k}'")

        # --------------------------------------------------
        # CONDITIONS VALIDIEREN
        # --------------------------------------------------

        conditions = rule.get("conditions", {})

        if conditions:

            if not isinstance(conditions, dict):
                errors.append(f"{prefix}: conditions müssen ein Objekt sein")
                continue

            if conditions.get("must_contain_company_name") and not company_profile.get("name"):
                errors.append(
                    f"{prefix}: requires company name but none configured"
                )

            if conditions.get("must_not_contain_company_name") and not company_profile.get("name"):
                errors.append(
                    f"{prefix}: condition uses company name but none configured"
                )

    # --------------------------------------------------
    # 🔍 COMPANY PROFILE
    # --------------------------------------------------

    if not isinstance(company_profile, dict):
        errors.append("company_profile ist kein Objekt")

    # --------------------------------------------------
    # FINAL
    # --------------------------------------------------

    return errors