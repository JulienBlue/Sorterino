import re
from pathlib import Path

from src.models import Classification


class DocumentClassificationSupport:
    @staticmethod
    def _classify_special_document(text_lower, filename):
        """Resolve high-signal document families before generic weighted rules."""
        filename_lower = Path(filename).stem.casefold()
        property_context = f"{filename_lower} {text_lower}"

        if "energieausweis" in property_context:
            return Classification(
                "Wohnen", 0.99, "Immobilienunterlagen",
                reason="Energieausweis",
            )
        if "teilungserkl" in property_context:
            return Classification(
                "Wohnen", 0.99, "Immobilienunterlagen",
                reason="Teilungserklärung",
            )
        if "grundriss" in filename_lower:
            return Classification(
                "Wohnen", 0.99, "Immobilienunterlagen",
                reason="Grundriss",
            )

        pension_signals = sum(
            value in text_lower
            for value in ("deutsche rentenversicherung", "renteninformation", "rentenversicherungsnummer")
        )
        if "renteninformation" in (text_lower + " " + filename_lower) and pension_signals >= 2:
            return Classification(
                "Rentenversicherung", 0.99, "Renteninformationen",
                reason="Renteninformation",
            )

        is_termination_declaration = bool(
            re.search(r"\b(?:hiermit\s+)?k(?:ü|ue)ndige\s+ich\b", text_lower)
            or re.search(r"^k(?:ü|ue)ndigung\b", filename_lower)
        )
        if is_termination_declaration:
            combined = f"{filename_lower} {text_lower}"
            if any(value in combined for value in (
                "debeka", "versicherung", "versicherungsnummer", " phv", " thv", " hr_"
            )):
                category = "Versicherungen"
            elif any(value in combined for value in ("arbeitsvertrag", "arbeitgeber")):
                category = "Arbeit und Karriere"
            elif any(value in combined for value in ("mietvertrag", "vermieter", "mieter")):
                category = "Wohnen"
            else:
                category = "Verträge und Abonnements"
            return Classification(category, 0.96, "Kündigungen", reason="Kündigungserklärung")

        if "beratungsvertrag" in (text_lower + " " + filename_lower) and any(
            value in text_lower for value in ("auftraggeber", "berater", "beratung")
        ):
            return Classification(
                "Verträge und Abonnements", 0.96, "Allgemeine Verträge",
                reason="Beratungsvertrag",
            )

        if (
            "rückbildungskurs" in (text_lower + " " + filename_lower)
            and "teilnahmebescheinigung" in (text_lower + " " + filename_lower)
        ):
            return Classification(
                "Gesundheit", 0.96, "Kurse und Therapien",
                reason="Teilnahmebescheinigung Rückbildungskurs",
            )

        assignment_signals = sum(
            value in text_lower
            for value in (
                "einsatzbegleitschein", "einsatz als leiharbeitnehmer", "entleiher",
                "verleiher", "einsatzort", "auftrag nr", "auftrag nr.", "bei kunde",
            )
        )
        if (
            assignment_signals >= 2
            and ("einsatz" in text_lower or re.fullmatch(r"ebs[ _-].+", filename_lower))
        ):
            return Classification(
                "Arbeit und Karriere", 0.96, "Einsatzunterlagen",
                reason="Einsatzbegleitschein",
            )

        invoice_context = f"{filename_lower} {text_lower}"
        if re.search(r"(?<!\w)rechnung(?!\w)", filename_lower) and sum(
            value in invoice_context
            for value in ("rechnung", "rechnungsnummer", "gesamtbetrag", "zahlbar", "betrag", "eur")
        ) >= 2:
            return Classification("Buchhaltung", 0.9, "Eingangsrechnungen", reason="Rechnung")
        supplier_invoice_signals = sum(
            value in text_lower
            for value in (
                "ausgangsrechnung", "wir stellen", "in rechnung", "nettobetrag",
                "mehrwertsteuer", "gesamtpreis", "zahlungskonditionen", "belegnummer",
            )
        )
        if supplier_invoice_signals >= 3:
            return Classification(
                "Buchhaltung", 0.95, "Eingangsrechnungen",
                reason="Lieferantenrechnung",
            )
        return None

    @staticmethod
    def _extract_property_document(text, filename, reason=None):
        combined = f"{Path(filename).stem} {text}"
        folded = combined.casefold()
        kind = reason
        if kind not in {"Energieausweis", "Teilungserklärung", "Grundriss"}:
            if "energieausweis" in folded:
                kind = "Energieausweis"
            elif "teilungserkl" in folded:
                kind = "Teilungserklärung"
            elif "grundriss" in Path(filename).stem.casefold():
                kind = "Grundriss"

        valid_until = None
        if kind == "Energieausweis":
            match = re.search(
                r"(?:g(?:ü|u)ltig\s+bis\D{0,20})?"
                r"((?:19|20)\d{2})[-_.](0[1-9]|1[0-2])[-_.](0[1-9]|[12]\d|3[01])",
                combined,
                flags=re.IGNORECASE,
            )
            if match:
                year, month, day = match.groups()
                valid_until = f"{day}.{month}.{year}"
            else:
                match = re.search(
                    r"g(?:ü|u)ltig\s+bis\D{0,20}"
                    r"(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.((?:19|20)\d{2})",
                    combined,
                    flags=re.IGNORECASE,
                )
                if match:
                    valid_until = ".".join(match.groups())

        return {
            "date": None,
            "amount": None,
            "currency": None,
            "vendor": None,
            "invoice_number": None,
            "contract_number": None,
            "description": kind,
            "document_kind": kind,
            "valid_until": valid_until,
            "shared_scope": "family",
        }

    @staticmethod
    def _extract_supplier_invoice_fields(text):
        fields = {}
        layout = re.search(
            r"Belegnummer\s+Kundennummer\s+Datum(?:\s+Seite)?\s+"
            r"(?:[^\r\n]*?\s+)?([A-Z0-9./-]{3,})\s+[A-Z0-9./-]+\s+"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if layout:
            fields["invoice_number"] = layout.group(1)
            fields["date"] = layout.group(2)
        return fields

    @staticmethod
    def _extract_assignment_sheet(text, filename):
        def match(pattern, flags=re.IGNORECASE):
            result = re.search(pattern, text, flags=flags)
            return re.sub(r"\s+", " ", result.group(1)).strip(" .:-") if result else None

        assignment_start = match(
            r"(?:Anmeldung[^\r\n]{0,100}?am|Einsatzbeginn)\s*:?[\s\w,.-]*?"
            r"(\d{2}\.\d{2}\.\d{4})"
        )
        if not assignment_start:
            period = re.search(r"\bEBS[ _-]((?:19|20)\d{2})[ _-](0[1-9]|1[0-2])\b", filename, re.I)
            if period:
                assignment_start = f"01.{period.group(2)}.{period.group(1)}"
        employer = "WIRMED GmbH" if "wirmed" in text.casefold() else None
        return {
            "amount": None,
            "currency": None,
            "document_kind": "Einsatzbegleitschein",
            "employer": employer,
            "client": match(r"(?:bei\s+Kunde|Entleiher)\s*:\s*([^\r\n]+)"),
            "assignment_number": match(r"Auftrag\s*(?:Nr\.?|Nummer)\s*[:#-]?\s*([A-Z0-9./-]+)"),
            "assignment_start": assignment_start,
            "monthly_hours": match(r"monatliche\s+Arbeitszeit[^\d]{0,60}([0-9]+,[0-9]{2})"),
        }

    @staticmethod
    def _insurance_type_from_text_and_filename(text, filename):
        combined = f"{Path(filename).stem.casefold()} {text.casefold()}"
        mappings = (
            (("tierhalterhaftpflicht", "tierhaftpflicht", " thv"), "Tierhalterhaftpflichtversicherung"),
            (("privathaftpflicht", "privat haftpflicht", " phv"), "Privathaftpflichtversicherung"),
            (("hausrat", " hr_", " hr "), "Hausratversicherung"),
        )
        for markers, label in mappings:
            if any(marker in combined for marker in markers):
                return label
        return None

    @classmethod
    def _extract_insurance_document(cls, text, filename):
        combined = f"{filename}\n{text}"
        number = re.search(
            r"(?:Versicherungsnummer\s*[:#-]?\s*)?\b(\d{6,12}(?:\.\d+)?)\b",
            combined,
            flags=re.IGNORECASE,
        )
        lower = combined.casefold()
        vendor = "Debeka Allgemeine Versicherung AG" if "debeka" in lower else None
        date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", Path(filename).stem)
        return {
            "date": date_match.group(1) if date_match else None,
            "amount": None,
            "currency": None,
            "vendor": vendor,
            "contract_number": number.group(1) if number else None,
            "insurance_type": cls._insurance_type_from_text_and_filename(text, filename),
            "document_kind": "Versicherungspolice",
        }

    @classmethod
    def _extract_termination(cls, text, filename):
        number = re.search(
            r"(?:Vertrags|Versicherungs)(?:nummer|nr\.?)\s*[:#-]?\s*([A-Z0-9./-]{4,30})",
            text,
            flags=re.IGNORECASE,
        )
        combined = f"{filename} {text}".casefold()
        insurance_type = cls._insurance_type_from_text_and_filename(text, filename)
        return {
            "amount": None,
            "currency": None,
            "vendor": "Debeka" if "debeka" in combined else None,
            "contract_number": number.group(1) if number else None,
            "insurance_type": insurance_type,
            "termination_subject": insurance_type,
            "document_kind": "Kündigung",
        }

    @staticmethod
    def _extract_pension_information(text, filename):
        compact_date = re.search(
            r"(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)", filename
        )
        date = None
        if compact_date:
            date = f"{compact_date.group(3)}.{compact_date.group(2)}.{compact_date.group(1)}"
        if not date:
            written = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
            date = written.group(1) if written else None
        return {
            "date": date,
            "amount": None,
            "currency": None,
            "vendor": "Deutsche Rentenversicherung",
            "description": "Renteninformation",
            "document_kind": "Renteninformation",
        }

    @staticmethod
    def _extract_housing_defect(text):
        dates = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
        parsed = sorted(
            dates,
            key=lambda value: tuple(reversed([int(part) for part in value.split(".")])),
        )
        address = re.search(
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .-]+\s+\d+[a-zA-Z]?,\s*\d{5}\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß -]+)",
            text,
        )
        subject = "Warmwasserversorgung" if "warmwasserversorgung" in text.casefold() else None
        return {
            "date": parsed[-1] if parsed else None,
            "amount": None,
            "currency": None,
            "document_kind": "Mängeldokumentation",
            "documentation_period_start": parsed[0] if parsed else None,
            "documentation_period_end": parsed[-1] if parsed else None,
            "defect_subject": subject,
            "property_address": address.group(1).strip() if address else None,
            "defect_status": "besteht fort" if "besteht" in text.casefold() and "fort" in text.casefold() else None,
            "shared_scope": "family",
        }

    @staticmethod
    def _extract_certificate_of_conduct(text):
        issue = re.search(
            r"(?:Bonn|Berlin),?\s+den\s+(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        reference = re.search(r"Verarbeitungsdaten\s*:\s*([0-9/]+)", text, re.IGNORECASE)
        no_record = bool(re.search(r"Keine\s+Eintragung|No\s+record|N[ée]ant", text, re.IGNORECASE))
        return {
            "date": issue.group(1) if issue else None,
            "amount": None,
            "currency": None,
            "invoice_number": None,
            "vendor": "Bundesamt für Justiz" if "bundesamt für justiz" in text.casefold() else None,
            "document_kind": "Führungszeugnis",
            "record_status": "Keine Eintragung" if no_record else None,
            "processing_reference": reference.group(1) if reference else None,
        }
