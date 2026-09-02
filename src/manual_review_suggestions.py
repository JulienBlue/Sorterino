import hashlib
import re
from pathlib import Path

from src.models import Document, DocumentMetadata


class ManualReviewSuggestionStore:
    """Persist analysis hints for documents that still need human approval."""

    def __init__(self, config):
        state_root = Path(getattr(config, "state_root", getattr(config, "logs_root", ".")))
        self.root = state_root / "manual-review"
        self._write_json = getattr(config, "_write_json", None)
        self._read_json = getattr(config, "_read_json", None)

    def _path(self, document_path):
        normalized = str(Path(document_path).resolve()).casefold()
        key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
        return self.root / f"{key}.json"

    def save(self, document_path, suggestion):
        payload = {key: value for key, value in (suggestion or {}).items() if value not in (None, "", [])}
        if not payload:
            return
        payload["document_name"] = Path(document_path).name
        target = self._path(document_path)
        if self._write_json:
            self._write_json(target, payload)
        else:
            import json
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, document_path):
        target = self._path(document_path)
        if self._read_json:
            return self._read_json(target)
        try:
            import json
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def remove(self, document_path):
        try:
            self._path(document_path).unlink()
        except FileNotFoundError:
            pass


def build_manual_suggestion(
    document,
    *,
    classification=None,
    metadata=None,
    extracted=None,
    assignment=None,
    profile_service=None,
    path_builder=None,
):
    """Build the persisted UI hint for a document requiring human review."""
    data = dict(extracted or {})
    category = getattr(classification, "category", None) or getattr(metadata, "category", None)
    document_type = (
        getattr(classification, "document_type", None)
        or getattr(metadata, "document_type", None)
    )
    if not category or category == "MANUELL":
        tentative = tentative_destination(document.extracted_text, document.filename)
        if tentative:
            category, document_type = tentative

    suggestion = {
        "profile_id": assignment.profile_id if assignment else data.get("profile_id"),
        "person_ids": list(
            assignment.person_ids if assignment else data.get("person_ids") or []
        ),
        "category": category,
        "document_type": document_type,
        "year": suggested_year(data, document.filename),
    }
    _apply_general_information_hint(suggestion, document)
    _apply_invoice_context_hint(
        suggestion,
        document,
        data,
        profile_service=profile_service,
    )
    _apply_preview_name(suggestion, document, data, path_builder)
    return suggestion


def _apply_general_information_hint(suggestion, document):
    if not likely_general_information_attachment(
        document.extracted_text, document.filename
    ):
        return
    suggestion.update({
        "review_kind": "general_information_attachment",
        "review_notice": "Wahrscheinlich allgemeine Bedingungen – Verwerfen prüfen",
    })
    bank_terms = any(
        marker in document.extracted_text.casefold()
        for marker in (
            "online-banking", "kontoübergreifende vollmacht",
            "elektronischen postfach", "bank gmbh",
        )
    )
    if bank_terms:
        suggestion.update({
            "category": "Finanzen",
            "document_type": "Banken und Konten",
        })


def _apply_invoice_context_hint(suggestion, document, data, profile_service=None):
    filename_words = re.sub(r"[_\-]+", " ", document.filename).casefold()
    document_type = suggestion.get("document_type")
    invoice_like = (
        document_type in {"Eingangsrechnungen", "Ausgangsrechnungen", "Kassenbons"}
        or bool(re.search(r"\b(?:rechnung|invoice|kassenbon)\b", filename_words))
        or bool(data.get("invoice_number") and data.get("vendor"))
    )
    if not invoice_like:
        return
    profile = (
        profile_service.get_profile(suggestion["profile_id"])
        if profile_service and suggestion.get("profile_id") else None
    )
    if document_type == "Kassenbons":
        is_organization = bool(profile and profile.get("type") == "organization")
        suggestion.update({
            "review_kind": "invoice_context",
            "document_label": "Kassenbon",
            "invoice_usage": "business" if is_organization else "private",
            "tax_relevant": False,
            "category": "Buchhaltung" if is_organization else "Anschaffungen und Garantien",
            "document_type": "Eingangsrechnungen" if is_organization else "Kassenbons",
        })
    elif not profile or profile.get("type") != "organization":
        suggestion.update({
            "review_kind": "invoice_context",
            "invoice_usage": "private",
            "tax_relevant": False,
            "category": "Anschaffungen und Garantien",
            "document_type": "Kaufbelege",
        })


def _apply_preview_name(suggestion, document, data, path_builder):
    category = suggestion.get("category")
    document_type = suggestion.get("document_type")
    if not category or category == "MANUELL":
        return
    suggestion["destination_parts"] = [
        value for value in (category, document_type)
        if value and value != "Unsortiert"
    ]
    if not path_builder:
        return
    try:
        preview = Document(source_path=document.source_path)
        preview.metadata = DocumentMetadata(category, document_type)
        preview.extracted_data = data
        suggestion["suggested_name"] = path_builder._generate_filename(preview)
    except (AttributeError, KeyError, TypeError, ValueError):
        return


def suggested_year(extracted, filename=""):
    data = extracted or {}
    tax_year = str(data.get("tax_year") or "").strip()
    if re.fullmatch(r"(?:19|20)\d{2}", tax_year):
        return tax_year
    payroll = str(data.get("payroll_period") or "").strip()
    match = re.search(r"(?:^|\.)(19\d{2}|20\d{2})$", payroll)
    if match:
        return match.group(1)
    date = str(data.get("date") or "").strip()
    match = re.search(r"(?:19|20)\d{2}", date)
    if match:
        return match.group(0)
    match = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", str(filename or ""))
    return match.group(1) if match else None


def tentative_destination(text="", filename=""):
    """Offer a review-only destination for useful but non-decisive signals."""
    value = f"{filename}\n{text}".casefold()
    if "beratungsvertrag" in value:
        return "Verträge und Abonnements", "Allgemeine Verträge"
    if "rückbildung" in value and any(
        term in value for term in ("teilnahmebescheinigung", "teilgenommen", "kurs")
    ):
        return "Gesundheit", "Kurse und Therapien"
    filename_value = str(filename or "").casefold().replace("_", " ")
    text_value = str(text or "").casefold()
    has_termination = bool(
        re.search(r"\b(?:kündigung|kuendigung)\b", filename_value)
        or re.search(
            r"\b(?:hiermit\s+)?(?:kündige\s+ich|kündigen\s+wir|wir\s+kündigen|ich\s+kündige|"
            r"kuendige\s+ich|kuendigen\s+wir|wir\s+kuendigen|ich\s+kuendige)\b|"
            r"\bkündigung\s+(?:meiner|unserer)\b",
            text_value,
        )
    )
    if not has_termination:
        return None
    if "debeka" in value and re.search(r"\b(?:hr|phv|thv)\b", value.replace("_", " ")):
        return "Versicherungen", "Kündigungen"
    employment_signals = (
        "personalabteilung", "human resources", " hr ", "arbeitgeber",
        "arbeitsverhältnis", "arbeitsverhaeltnis", "arbeitsvertrag",
    )
    insurance_signals = (
        "versicherung", "versicherungsnummer", "versicherungsschein",
        "versicherungsnehmer", "police",
    )
    padded = f" {value.replace('_', ' ')} "
    if any(term in padded for term in employment_signals):
        return "Arbeit und Karriere", "Kündigungen"
    if any(term in padded for term in insurance_signals):
        return "Versicherungen", "Kündigungen"
    if any(term in padded for term in ("mietvertrag", "mieter", "vermieter")):
        return "Wohnen", "Kündigungen"
    return "Verträge und Abonnements", "Kündigungen"


def likely_general_information_attachment(text="", filename=""):
    """Identify likely generic terms/privacy annexes for a review-only warning.

    This deliberately does not decide that a document may be deleted.  It only
    marks strong combinations that are typical for reusable legal information
    supplied alongside an actual contract or form.
    """
    value = f"{filename}\n{text}".casefold()
    generic_markers = (
        "allgemeine geschäftsbedingungen",
        "datenschutzinformationen",
        "datenschutzinformation zur vollmacht",
        "bedingungen vollmacht",
        "online-banking-bedingungen",
        "sonderbedingungen zum elektronischen postfach",
        "preis- und leistungsverzeichnis",
    )
    marker_count = sum(marker in value for marker in generic_markers)
    explicit_title = bool(re.search(
        r"(?:datenschutzinformation(?:en)?|bedingungswerk|allgemeine\s+"
        r"geschäftsbedingungen|sonderbedingungen)",
        str(filename or "").casefold(),
    ))
    return marker_count >= 2 or (explicit_title and marker_count >= 1)


def person_id_from_filename(members, filename):
    """Match first and last name in either filename order, but only if unique."""
    normalized = re.sub(r"[^a-z0-9äöüß]", "", str(filename or "").casefold())
    matches = []
    for person, _membership in members or []:
        name = person.get("name", {}) or {}
        first = re.sub(r"[^a-z0-9äöüß]", "", str(name.get("first_name") or "").casefold())
        last = re.sub(r"[^a-z0-9äöüß]", "", str(name.get("last_name") or "").casefold())
        if first and last and first in normalized and last in normalized:
            matches.append(person.get("id"))
    unique = list(dict.fromkeys(value for value in matches if value))
    return unique[0] if len(unique) == 1 else None


def best_destination_label(destination_map, suggestion):
    """Return the closest existing folder to an analyzer suggestion."""
    if not destination_map or not suggestion:
        return None
    desired = [
        str(part).casefold()
        for part in (suggestion.get("destination_parts") or [])
        if str(part).strip()
    ]
    category = str(suggestion.get("category") or "").casefold()
    document_type = str(suggestion.get("document_type") or "").casefold()

    ranked = []
    for label, path in destination_map.items():
        parts = [part.casefold() for part in Path(path).parts]
        score = 0
        if desired:
            common = 0
            for actual, expected in zip(parts, desired):
                if actual != expected:
                    break
                common += 1
            score += common * 20
            if parts == desired:
                score += 100
        if category and category in parts:
            score += 12
        if document_type and document_type in parts:
            score += 18
        if score:
            ranked.append((score, len(parts), label))
    return max(ranked, default=(0, 0, None))[2]
