"""Domain labels and membership queries shared by profile user interfaces."""

from src.person_age import person_is_minor


ORGANIZATION_POSITIONS = [
    "Mitarbeiter:in",
    "Geschäftsführer:in",
    "Inhaber:in",
    "Prokurist:in",
    "Abteilungsleitung",
    "Teamleitung",
    "Buchhaltung",
    "Personalwesen",
    "Auszubildende:r",
    "Praktikant:in",
    "Eigene Funktion …",
]

PARTNER_RELATIONSHIP_TYPES = {
    "Verheiratet": "married",
    "Eingetragene Lebenspartnerschaft": "civil_partnership",
    "Partnerschaft": "partnership",
}
PARTNER_RELATIONSHIP_LABELS = {
    value: label for label, value in PARTNER_RELATIONSHIP_TYPES.items()
}

FAMILY_ROLES = {
    "Elternteil": "parent",
    "Kind (Sohn / Tochter)": "child",
    "Ehepartner:in": "spouse",
    "Partner:in": "partner",
    "Geschwisterteil": "sibling",
    "Großelternteil": "grandparent",
    "Andere Beziehung …": None,
}

GENDER_VALUES = {
    "Keine Angabe": "",
    "Männlich": "male",
    "Weiblich": "female",
    "Divers": "diverse",
}
GENDER_LABELS = {value: label for label, value in GENDER_VALUES.items()}

ROLE_LABELS = {
    "private person": "Person",
    "privatperson": "Person",
}

GENDERED_ROLE_LABELS = {
    "child": ("Sohn", "Tochter", "Kind", "Kind"),
    "member": ("Vater", "Mutter", "Elternteil", "Elternteil"),
    "parent": ("Vater", "Mutter", "Elternteil", "Elternteil"),
    "spouse": ("Ehemann", "Ehefrau", "Ehepartner:in", "Ehepartner/in"),
    "partner": ("Partner", "Partnerin", "Partner:in", "Partner/in"),
    "sibling": ("Bruder", "Schwester", "Geschwister", "Geschwisterteil"),
    "grandparent": ("Großvater", "Großmutter", "Großelternteil", "Großelternteil"),
    "employee": ("Mitarbeiter", "Mitarbeiterin", "Mitarbeiter:in", "Mitarbeiter/in"),
    "owner": ("Inhaber", "Inhaberin", "Inhaber:in", "Inhaber/in"),
    "manager": ("Leiter", "Leiterin", "Leiter:in", "Leitung"),
    "director": (
        "Geschäftsführer",
        "Geschäftsführerin",
        "Geschäftsführer:in",
        "Geschäftsführung",
    ),
    "managing director": (
        "Geschäftsführer",
        "Geschäftsführerin",
        "Geschäftsführer:in",
        "Geschäftsführung",
    ),
    "ceo": (
        "Geschäftsführer",
        "Geschäftsführerin",
        "Geschäftsführer:in",
        "Geschäftsführung",
    ),
    "cfo": (
        "Kaufmännischer Leiter",
        "Kaufmännische Leiterin",
        "Kaufmännische Leitung",
        "Kaufmännische Leitung",
    ),
    "cto": (
        "Technischer Leiter",
        "Technische Leiterin",
        "Technische Leitung",
        "Technische Leitung",
    ),
    "intern": ("Praktikant", "Praktikantin", "Praktikant:in", "Praktikant/in"),
}


def split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def profile_saved_message(profile):
    kind = {
        "family": "Familie",
        "organization": "Firma",
        "individual": "Privatperson",
    }.get((profile or {}).get("type"), "Profil")
    name = (profile or {}).get("display_name") or "Profil"
    return f'{kind} „{name}“ wurde erfolgreich gespeichert.'


def gendered_label(value, person):
    labels = GENDERED_ROLE_LABELS.get(value.casefold())
    if not labels:
        return None
    gender = str((person.get("personal", {}) or {}).get("gender") or "").casefold()
    index = {"male": 0, "female": 1, "diverse": 2}.get(gender, 3)
    return labels[index]


def membership_label(profile_type, person, membership):
    if profile_type == "individual":
        return "Person"
    raw = (
        membership.get("position")
        if profile_type == "organization" and membership.get("position")
        else membership.get("role")
    )
    value = str(raw or "").strip()
    if value:
        return gendered_label(value, person) or ROLE_LABELS.get(value.casefold(), value)
    if profile_type == "family":
        return gendered_label("child", person) if person_is_minor(person) else "Familienmitglied"
    if profile_type == "organization":
        return gendered_label("employee", person)
    return "Person"


def available_people_for_profile(service, profile_id):
    assigned_ids = {
        person.get("id") for person, _membership in service.profile_members(profile_id)
    }
    return [
        person
        for person in service.list_persons()
        if person.get("id") not in assigned_ids
    ]


def family_profiles_for_person(service, person_id):
    """Return active family profiles containing the selected person."""
    return [
        profile
        for profile in service.list_profiles()
        if profile.get("type") == "family"
        and any(
            person.get("id") == person_id
            for person, _membership in service.profile_members(profile["id"])
        )
    ]


def all_people_assigned_message(profile_type):
    if profile_type == "family":
        return (
            "Alle bereits in Sorterino vorhandenen Personen gehören dieser Familie "
            "schon an. Für ein weiteres Familienmitglied kannst du eine neue Person anlegen."
        )
    return (
        "Alle bereits in Sorterino vorhandenen Personen sind dieser Firma oder Organisation "
        "schon zugeordnet. Für einen weiteren Mitarbeiter kannst du eine neue Person anlegen."
    )
