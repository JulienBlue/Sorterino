import os


def determine_target_path(document, structure: dict) -> str:

    metadata = document.metadata
    root = structure["root"]

    category = metadata.category
    document_type = metadata.document_type
    year = metadata.year
    employer = metadata.employer

    if category not in structure["areas"]:
        return os.path.join(root, "99_Sonstiges")

    area_config = structure["areas"][category]

    # Arbeit
    if category == "Arbeit" and employer:
        employer_folder = area_config["employer_folder"]

        base_path = os.path.join(
            root,
            category,
            employer_folder,
            employer
        )

        subfolder_template = area_config["subfolders"].get(document_type)

        if not subfolder_template:
            return os.path.join(base_path, "99_Sonstiges")

        subfolder = subfolder_template.replace(
            "{year}",
            str(year) if year else ""
        )

        return os.path.join(base_path, subfolder)

    # Steuer
    if category == "Steuer" and year:
        base_path = os.path.join(root, category, str(year))

        subfolder_template = area_config["subfolders"].get(document_type)

        if not subfolder_template:
            return os.path.join(base_path, "99_Sonstiges")

        return os.path.join(base_path, subfolder_template)

    # Versicherungen
    if category == "Versicherungen":
        base_path = os.path.join(root, category)

        subfolder_template = area_config["subfolders"].get(document_type)

        if not subfolder_template:
            return os.path.join(base_path, "99_Sonstiges")

        subfolder = subfolder_template.replace(
            "{year}",
            str(year) if year else ""
        )

        return os.path.join(base_path, subfolder)

    return os.path.join(root, "99_Sonstiges")