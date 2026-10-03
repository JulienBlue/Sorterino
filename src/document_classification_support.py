import re
from pathlib import Path

from src.models import Classification


class DocumentClassificationSupport:
    @staticmethod
    def _classify_special_document(text_lower, filename):
        """Resolve high-signal document families before generic weighted rules."""
        filename_lower = Path(filename).stem.casefold()
        property_context = f"{filename_lower} {text_lower}"

        generic_legal_attachment = bool(
            re.search(r"\b(?:agb|widerrufsrecht)\b", filename_lower)
            or "allgemeine geschäftsbedingungen" in text_lower
        )
        if generic_legal_attachment:
            return Classification(
                "MANUELL", 0.99, "Allgemeine Informationen",
                reason="Allgemeine Bedingungen",
            )

        bafog_income_context = f"{filename_lower} {text_lower}"
        bafog_income_signals = sum(
            value in bafog_income_context
            for value in (
                "einkommensermittlung",
                "18a bafög",
                "18a bafog",
                "bundesverwaltungsamt",
                "darlehensnehmer",
            )
        )
        if "einkommensermittlung" in bafog_income_context and bafog_income_signals >= 2:
            return Classification(
                "Behörden und Leistungen",
                0.99,
                "Formulare",
                reason="Einkommensermittlung nach § 18a BAföG",
            )

        medical_discharge_signals = sum(
            value in text_lower
            for value in (
                "wir berichten über die patientin",
                "wir berichten uber die patientin",
                "entlassuntersuchung",
                "stationärer aufenthalt",
                "stationarer aufenthalt",
                "empfehlungen / procedere",
            )
        )
        if (
            "entlassungsbrief" in filename_lower
            or "entlassungsbericht" in filename_lower
            or medical_discharge_signals >= 2
        ):
            return Classification(
                "Gesundheit",
                0.99,
                "Arztberichte und Befunde",
                reason="Entlassungsbrief",
            )

        deferment_statement_signals = sum(
            value in text_lower
            for value in (
                "entscheidung über eine stundung",
                "entscheidung uber eine stundung",
                "§ 59 abs. 1",
                "bundeshaushaltsordnung",
                "höhe meines einkommens",
                "aufstellung über mein vermögen",
                "laufenden monatlichen ausgaben",
            )
        )
        if (
            deferment_statement_signals >= 2
            or (
                "aufstellung nach § 59" in filename_lower
                and "stundung" in text_lower
            )
        ):
            return Classification(
                "Behörden und Leistungen",
                0.99,
                "Sonstige Bescheide",
                reason="Vermögensauskunft zur Stundung",
            )

        insurance_invoice_signals = sum(
            value in text_lower
            for value in (
                "beitragsrechnung zu ihrer",
                "beitragsrechnung:",
                "versicherungsnummer",
                "versicherungsbeitrag",
                "beitrag, fällig",
                "beitrag, fallig",
            )
        )
        if (
            "beitragsrechnung" in f"{filename_lower} {text_lower}"
            and insurance_invoice_signals >= 2
        ):
            return Classification(
                "Versicherungen",
                0.99,
                "Versicherungsschreiben",
                reason="Versicherungs-Beitragsrechnung",
            )

        insurance_offer_signals = sum(
            value in text_lower
            for value in (
                "angebot für eine",
                "verbindliches angebot",
                "angebots-nr.",
                "angebots-nr",
                "an dieses angebot halten wir uns",
                "ausstellungsdatum/-grund",
            )
        )
        if insurance_offer_signals >= 2 and "versicherung" in text_lower:
            return Classification(
                "Versicherungen",
                0.99,
                "Versicherungsangebote",
                reason="Versicherungsangebot",
            )

        if (
            "anschreiben" in filename_lower
            and "anbei erhalten sie ihren versicherungsschein" in text_lower
        ):
            return Classification(
                "Versicherungen",
                0.99,
                "Versicherungsschreiben",
                reason="Begleitschreiben zum Versicherungsschein",
            )

        family_course_context = f"{filename_lower} {text_lower}"
        if (
            any(value in family_course_context for value in (
                "familienbildung", "pekip", "mit kind", "eltern-kind",
            ))
            and any(value in family_course_context for value in (
                "einladung", "kurs", "veranstaltung", "teilnahme",
            ))
        ):
            return Classification(
                "Gesundheit", 0.96, "Kurse und Therapien",
                reason="Einladung Familienbildung",
            )

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

        invitation_signals = sum(
            value in text_lower
            for value in (
                "deine teilnahme am intelligenceday",
                "wir freuen uns darauf, dich",
                "auswahlgespräch mit der personalgewinnung",
                "fachgespräch an den fachständen",
                "deine bewerbung weiter berücksichtigen",
            )
        )
        if invitation_signals >= 2:
            return Classification(
                "Arbeit und Karriere", 0.99, "Einladungen und Auswahlverfahren",
                reason="Einladung zum Auswahlverfahren",
            )

        police_report_signals = sum(
            value in text_lower
            for value in (
                "bescheinigung über die erstattung einer anzeige",
                "anzeigenerstattung durch",
                "straftat(en)",
                "ereignisort/ -zeit",
                "polizeipräsidium",
            )
        )
        if police_report_signals >= 2:
            return Classification(
                "Rechtliches und Vorsorge", 0.99, "Rechtliche Korrespondenz",
                reason="Anzeigenbescheinigung",
            )

        application_attachment_signals = sum(
            value in text_lower
            for value in (
                "vorstellungsreisen",
                "beginn der vorstellung",
                "einstellungshindernis",
                "personalakte/n",
                "einladende organisationseinheit",
                "arbeitgeber im öffentlichen dienst",
            )
        )
        if application_attachment_signals >= 2:
            return Classification(
                "Arbeit und Karriere", 0.96, "Bewerbungen",
                reason="Bewerbungsunterlagen",
            )

        pension_signals = sum(
            value in text_lower
            for value in ("deutsche rentenversicherung", "renteninformation", "rentenversicherungsnummer")
        )
        if "renteninformation" in (text_lower + " " + filename_lower) and pension_signals >= 2:
            return Classification(
                "Rentenversicherung", 0.99, "Renteninformation",
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
                else:
                    # OCR may separate individual digits, for example:
                    # Gültig bis: 1 6. 1 0.2030. Compact only the short value
                    # area after the label so unrelated dates are ignored.
                    label = re.search(
                        r"g.{0,2}ltig\s+bis\s*:?",
                        combined,
                        flags=re.IGNORECASE,
                    )
                    if label:
                        value_area = combined[label.end():label.end() + 40]
                        compact = re.sub(r"\s+", "", value_area)
                        spaced_date = re.match(
                            r"(0[1-9]|[12]\d|3[01])\."
                            r"(0[1-9]|1[0-2])\."
                            r"((?:19|20)\d{2})",
                            compact,
                        )
                        if spaced_date:
                            valid_until = ".".join(spaced_date.groups())

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
        client = match(r"(?:bei\s+Kunde|Entleiher)\s*:\s*([^\r\n]+)")
        if client and client.casefold() == "caritas-seniorenzentrum pulhei":
            client = "Caritas-Seniorenzentrum Pulheim"
        return {
            "amount": None,
            "currency": None,
            # The generic vendor extraction commonly picks up the form title
            # here. Employer and client are the meaningful parties.
            "vendor": None,
            "document_kind": "Einsatzbegleitschein",
            "employer": employer,
            "client": client,
            "assignment_number": match(r"Auftrag\s*(?:Nr\.?|Nummer)\s*[:#-]?\s*([A-Z0-9./-]+)"),
            "assignment_start": assignment_start,
            "monthly_hours": match(r"monatliche\s+Arbeitszeit[^\d]{0,60}([0-9]+,[0-9]{2})"),
        }

    @staticmethod
    def _extract_deferment_financial_statement(text):
        reference = re.search(
            r"Gesch[aä]ftszeichen\s*[\r\n:.-]*\s*"
            r"([A-Z0-9][A-Z0-9 /.-]{4,40})",
            text,
            flags=re.IGNORECASE,
        )
        processing_reference = None
        if reference:
            processing_reference = re.sub(
                r"\s+",
                " ",
                reference.group(1),
            ).strip(" .:-")
        return {
            "amount": None,
            "currency": None,
            "vendor": None,
            "description": None,
            "document_kind": "Vermögensauskunft zur Stundung",
            "processing_reference": processing_reference,
        }

    @staticmethod
    def _extract_bafog_income_assessment(text):
        period = re.search(
            r"\b(\d{2}\.\d{2}\.\d{4})\b[^\d\r\n]{0,12}"
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
            text,
        )
        reference = re.search(
            r"(?:Gesch[aä]ftszeichen(?:\s+im\s+Bundesverwaltungsamt)?)"
            r"\s*[:\r\n-]+\s*(IV\s*[A-Z0-9 /.-]{4,40})",
            text,
            flags=re.IGNORECASE,
        )
        processing_reference = None
        if reference:
            processing_reference = re.sub(r"\s+", " ", reference.group(1)).strip(" .:-")

        period_start = period.group(1) if period else None
        period_end = period.group(2) if period else None
        if not period:
            # Scanned forms often lose the separator before the year and may
            # confuse one year digit (for example 01.112094 instead of
            # 01.11.2024). Restrict recovery to the explicitly labelled
            # four-month income period so unrelated dates remain untouched.
            label = re.search(r"letzten\s+vier\s+monate", text, re.IGNORECASE)
            if label:
                period_text = text[label.end():label.end() + 350]
                candidates = re.findall(
                    r"\b(\d{2})\.(\d{2})\.?((?:19|20)\d{2})\b",
                    period_text,
                )
                if len(candidates) >= 2:
                    start_day, start_month, start_year = candidates[0]
                    end_day, end_month, end_year = candidates[1]
                    start_year_number = int(start_year)
                    end_year_number = int(end_year)
                    if abs(start_year_number - end_year_number) > 1:
                        start_year_number = end_year_number - (
                            1 if int(start_month) > int(end_month) else 0
                        )
                    period_start = (
                        f"{start_day}.{start_month}.{start_year_number:04d}"
                    )
                    period_end = f"{end_day}.{end_month}.{end_year}"
        return {
            "date": period_start,
            "amount": None,
            "currency": None,
            "vendor": "Bundesverwaltungsamt",
            "description": None,
            "document_kind": "Einkommensermittlung nach § 18a BAföG",
            "income_period_start": period_start,
            "income_period_end": period_end,
            "processing_reference": processing_reference,
        }

    @staticmethod
    def _extract_medical_discharge_letter(text):
        stay = re.search(
            r"(?:vom|von)\s+(\d{2}\.\d{2}\.\d{4})\s+"
            r"bis\s+(\d{2}\.\d{2}\.\d{4})[\s\S]{0,120}?"
            r"(?:Behandlung|Aufenthalt)",
            text,
            flags=re.IGNORECASE,
        )
        treatment_start = stay.group(1) if stay else None
        treatment_end = stay.group(2) if stay else None

        hospital = None
        if "krankenhaus porz am rhein" in text.casefold():
            hospital = "Krankenhaus Porz am Rhein"

        return {
            "date": treatment_end,
            "amount": None,
            "currency": None,
            "vendor": hospital,
            "description": None,
            "document_kind": "Entlassungsbrief",
            "treatment_start": treatment_start,
            "treatment_end": treatment_end,
        }

    @staticmethod
    def _extract_insurance_invoice(text):
        folded = text.casefold()

        date = None
        for pattern in (
            r"Aktenzeichen[^\r\n]{0,60}?(\d{2}\.\d{2}\.\d{4})",
            r"Seite\s+\d+\s+vom\s+(\d{2}\.\d{2}\.\d{4})",
            r"\b(?:GoSMART\s+)?(\d{2}\.\d{2}\.\d{4})\b",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                date = match.group(1)
                break

        contract = re.search(
            r"Versicherungsnummer\s+(\d[\d.]{5,})",
            text,
            flags=re.IGNORECASE,
        )

        amount = None
        for pattern in (
            r"Betrag\s+in\s+H[oö]he\s+von\s+(\d+(?:[.,]\d{2}))",
            r"Beitrag,\s*f[aä]llig[^\r\n]{0,80}?(\d+(?:[.,]\d{2}))",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                amount = match.group(1).replace(".", ",")
                break

        vendor = None
        if "gothaer allgemeine versicherung" in folded:
            vendor = "Gothaer Allgemeine Versicherung AG"
        elif "debeka allgemeine versicherung" in folded:
            vendor = "Debeka Allgemeine Versicherung AG"

        insurance_type = None
        if re.search(r"(?im)^\s*unfall(?:\s+neu)?\b", text):
            insurance_type = "Unfallversicherung"
        elif "privathaftpflicht" in folded:
            insurance_type = "Privathaftpflichtversicherung"
        elif "hausrat" in folded:
            insurance_type = "Hausratversicherung"
        elif "tierhalterhaftpflicht" in folded:
            insurance_type = "Tierhalterhaftpflichtversicherung"

        return {
            "date": date,
            "amount": amount,
            "currency": "EUR" if amount else None,
            "vendor": vendor,
            "invoice_number": None,
            "contract_number": contract.group(1) if contract else None,
            "description": None,
            "insurance_type": insurance_type,
            "document_kind": "Beitragsrechnung",
        }

    @classmethod
    def _extract_insurance_offer(cls, text, filename):
        date = re.search(
            r"(?:Datum|Ausstellungsdatum(?:/-grund)?)\s*:?\s*"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        number = re.search(
            r"Ihre\s+Vertragsnummer[^\r\n]*[\r\n]+\s*"
            r"([A-Z0-9./-]{5,30})",
            text,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:Ihre\s+Vertragsnummer|Angebots-Nr\.?)\s*"
            r"(?:\(bitte stets angeben\))?\s*:?\s*([A-Z0-9./-]{5,30})",
            text,
            flags=re.IGNORECASE,
        )
        folded = text.casefold()
        if "barmenia allgemeine versicherung" in folded:
            vendor = "Barmenia Allgemeine Versicherungs-AG"
        elif "gothaer allgemeine versicherung" in folded:
            vendor = "Gothaer Allgemeine Versicherung AG"
        else:
            vendor = None
        return {
            "date": date.group(1) if date else None,
            "amount": None,
            "currency": None,
            "vendor": vendor,
            "contract_number": number.group(1) if number else None,
            "description": None,
            "insurance_type": cls._insurance_type_from_text_and_filename(
                text, filename
            ),
            "document_kind": "Versicherungsangebot",
        }

    @classmethod
    def _extract_insurance_cover_letter(cls, text, filename):
        date = re.search(
            r"Versicherungsnummer[^\r\n]{0,80}?"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:PNC-POST|erstellt(?:\s+am)?)\s*"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        number = re.search(
            r"Versicherungsnummer\s*[:#-]?\s*"
            r"(\d{2,3}(?:\.\d{3,6}){1,3}|\d{6,12}(?:\.\d+)?)",
            text,
            flags=re.IGNORECASE,
        )
        folded = text.casefold()
        if "gothaer allgemeine versicherung" in folded:
            vendor = "Gothaer Allgemeine Versicherung AG"
        elif "debeka allgemeine versicherung" in folded:
            vendor = "Debeka Allgemeine Versicherung AG"
        else:
            vendor = None
        return {
            "date": date.group(1) if date else None,
            "amount": None,
            "currency": None,
            "vendor": vendor,
            "contract_number": number.group(1) if number else None,
            "description": None,
            "insurance_type": cls._insurance_type_from_text_and_filename(
                text, filename
            ),
            "document_kind": "Begleitschreiben zum Versicherungsschein",
        }

    @staticmethod
    def _insurance_type_from_text_and_filename(text, filename):
        combined = f"{Path(filename).stem.casefold()} {text.casefold()}"
        mappings = (
            (("tierhalterhaftpflicht", "tierhaftpflicht", " thv"), "Tierhalterhaftpflichtversicherung"),
            (("privathaftpflicht", "privat haftpflicht", " phv"), "Privathaftpflichtversicherung"),
            (("hausrat", " hr_", " hr "), "Hausratversicherung"),
            (("unfallversicherung", "unfall_", "unfall "), "Unfallversicherung"),
        )
        for markers, label in mappings:
            if any(marker in combined for marker in markers):
                return label
        return None

    @classmethod
    def _extract_insurance_document(cls, text, filename):
        combined = f"{filename}\n{text}"
        labelled_number = re.search(
            r"Versicherungsnummer\s*[:#-]?\s*"
            r"(\d{2,3}(?:\.\d{3,6}){1,3}|\d{6,12}(?:\.\d+)?)",
            text,
            flags=re.IGNORECASE,
        )
        fallback_number = re.search(
            r"\b(\d{6,12}(?:\.\d+)?)\b",
            Path(filename).stem,
            flags=re.IGNORECASE,
        )
        number = labelled_number or fallback_number
        lower = combined.casefold()
        if "gothaer allgemeine versicherung" in lower:
            vendor = "Gothaer Allgemeine Versicherung AG"
        elif "debeka" in lower:
            vendor = "Debeka Allgemeine Versicherung AG"
        else:
            vendor = None
        date_match = re.search(
            r"Ausgefertigt\s+am\s+(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        ) or re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", Path(filename).stem)
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

    @staticmethod
    def _extract_police_report(text):
        event = re.search(
            r"(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)?,?\s*"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        issued = re.search(r"Köln,\s*(\d{2}\.\d{2}\.\d{4})", text, re.IGNORECASE)
        reference = re.search(
            r"Aktenzeichen[^\r\n]*\r?\n\s*([A-Z0-9-]{8,})",
            text,
            flags=re.IGNORECASE,
        )
        offence = re.search(
            r"Straftat\(en\)[^\r\n]*\r?\n\s*([^\r\n]+)",
            text,
            flags=re.IGNORECASE,
        )
        return {
            "date": (issued or event).group(1) if (issued or event) else None,
            "amount": None,
            "currency": None,
            "vendor": "Polizeipräsidium Köln"
            if "polizeipräsidium köln" in text.casefold() else "Polizei",
            "invoice_number": None,
            "contract_number": None,
            "description": offence.group(1).strip() if offence else None,
            "document_kind": "Anzeigenbescheinigung",
            "reference_number": reference.group(1) if reference else None,
        }
