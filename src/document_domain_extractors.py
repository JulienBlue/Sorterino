import re
from pathlib import Path


class DomainDocumentExtractors:
    def _extract_home_savings_contract(self, text):
        provider = None
        if "schwäbisch hall" in text.casefold() or "schwaebisch hall" in text.casefold():
            provider = "Schwäbisch Hall"
        else:
            provider_match = re.search(
                r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß&.\-]*(?:\s+[A-Za-zÄÖÜäöüß&.\-]+){0,5}"
                r"\s+Bausparkasse(?:\s+(?:AG|GmbH))?)",
                text,
            )
            if provider_match:
                provider = provider_match.group(1).strip()

        contract_number = None
        number_match = re.search(
            r"(?:Bausparvertrag\s+Nr\.?|Bausparnummer)\s*:?\s*"
            r"([0-9][0-9 ]{4,}[A-Z](?:\s*[0-9]{1,3})?)",
            text,
            flags=re.IGNORECASE,
        )
        if number_match:
            contract_number = re.sub(r"\s+", " ", number_match.group(1)).strip()

        contract_reference = None
        if contract_number:
            reference_match = re.search(r"([A-Z])\s*(\d{1,3})\s*$", contract_number)
            if reference_match:
                contract_reference = (
                    f"{reference_match.group(1).upper()} {reference_match.group(2)}"
                )

        contract_sum = None
        sum_match = re.search(
            r"Bausparsumme\s*:?\s*([0-9]{1,3}(?:[. ][0-9]{3})*(?:,[0-9]{2})?)\s*(?:€|EUR)",
            text,
            flags=re.IGNORECASE,
        )
        if sum_match:
            contract_sum = sum_match.group(1).replace(" ", "")
            if "," not in contract_sum:
                contract_sum += ",00"

        return {
            "vendor": provider,
            "provider": provider,
            "contract_number": contract_number,
            "contract_reference": contract_reference,
            "contract_sum": contract_sum,
            "amount": None,
            "currency": "EUR",
            "description": "Bausparvertrag",
            "document_kind": "Bausparvertrag",
        }

    @staticmethod
    def _extract_job_application(text):
        dates = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
        closing_date = re.search(
            r"(?:^|\n)\s*[A-ZÄÖÜ][A-Za-zÄÖÜäöüß .-]{1,40}\s+"
            r"(\d{2}\.\d{2}\.\d{4})\s*$",
            text,
            flags=re.MULTILINE,
        )
        date = closing_date.group(1) if closing_date else (dates[-1] if dates else None)

        employer = None
        flat_text = re.sub(r"\s+", " ", text)
        employer_match = re.search(
            r"(?:bewerb\w*\b.{0,140}?)\b(?:bei|an)\s+"
            r"(?:der|die|den|das)?\s*"
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß&.' -]{2,70}?)"
            r"\s+(?:auf|als|um)\b",
            flat_text,
            flags=re.IGNORECASE,
        )
        if employer_match:
            employer = re.sub(r"\s+", " ", employer_match.group(1)).strip(" ,.-")

        job_title = None
        body_title_match = re.search(
            r"(?:stelle|position)\s+als\s+"
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9/+&.'() -]{2,80}?)"
            r"(?=\s+(?:im|bei|am|zum)\b|[.,;:]|$)",
            flat_text,
            flags=re.IGNORECASE,
        )
        if body_title_match:
            job_title = re.sub(r"\s+", " ", body_title_match.group(1)).strip(" ,.-")
        if not job_title:
            for line in (line.strip() for line in text.splitlines() if line.strip()):
                heading_match = re.search(
                    r"bewerbung\s+als\s+(.+)$", line, flags=re.IGNORECASE
                )
                if not heading_match:
                    continue
                candidate = re.split(
                    r"\s+(?:im\s+gro(?:ß|ss)raum|am\s+standort|"
                    r"in\s+der\s+region|für\s+den\s+raum)\b",
                    heading_match.group(1),
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0]
                job_title = re.sub(r"\s+", " ", candidate).strip(" ,.-") or None
                break

        if job_title and job_title.isupper():
            job_title = job_title.lower().capitalize()

        return {
            "date": date,
            "vendor": employer,
            "prospective_employer": employer,
            "job_title": job_title,
            "amount": None,
            "currency": None,
            "description": "Bewerbung",
            "document_kind": "Bewerbungsanschreiben",
        }

    @staticmethod
    def _extract_marriage_certificate(text):
        marriage_date = None
        date_match = re.search(
            r"(?:Eheschließung|Eheschliessung)[\s\S]{0,500}?"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if date_match:
            marriage_date = date_match.group(1)

        register_number = None
        register_match = re.search(r"\bE\s*(\d{1,6})\s*/\s*(20\d{2})\b", text)
        if register_match:
            register_number = f"E {register_match.group(1)}/{register_match.group(2)}"

        registry_office = None
        office_match = re.search(
            r"Standesamt[ \t]+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß -]{2,50})",
            text,
        )
        if office_match:
            registry_office = re.sub(r"\s+", " ", office_match.group(1)).strip()
        elif re.search(r"\bK[oö]ln\b", text, flags=re.IGNORECASE):
            registry_office = "Köln"

        authority = f"Standesamt {registry_office}" if registry_office else "Standesamt"
        return {
            "date": marriage_date,
            "amount": None,
            "currency": None,
            "vendor": authority,
            "description": "Eheschließung",
            "document_kind": "Eheurkunde",
            "marriage_date": marriage_date,
            "register_number": register_number,
            "registry_office": registry_office,
        }

    @staticmethod
    def _extract_identity_document(text):
        text_upper = text.upper()
        is_identity_card = "IDD<<" in text_upper or "PERSONALAUSWEIS" in text_upper
        if not is_identity_card and "DATE OF EXPIRY" not in text_upper:
            return {}

        birth_date = None
        birth_match = re.search(
            r"(?:Geburtstag|Date\s+of\s+birth)[\s\S]{0,180}?"
            r"(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if birth_match:
            birth_date = birth_match.group(1)

        valid_until = None
        expiry_match = re.search(
            r"(?:G[üu]ltig\s+bis|Giiltig\s+bis|Date\s+of\s+expiry)"
            r"[\s\S]{0,100}?(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if expiry_match:
            valid_until = expiry_match.group(1)

        document_number = next(
            (
                candidate for candidate in re.findall(r"\b[A-Z0-9]{9}\b", text_upper)
                if any(char.isdigit() for char in candidate)
                and any(char.isalpha() for char in candidate)
            ),
            None,
        )

        holder_name = None
        mrz_name = re.search(
            r"(?m)^\s*([A-ZÄÖÜ]{2,})<<([A-ZÄÖÜ]+(?:<[A-ZÄÖÜ]+)+)<+",
            text_upper,
        )
        if mrz_name:
            first_names = " ".join(mrz_name.group(2).split("<")).title()
            holder_name = f"{first_names} {mrz_name.group(1).title()}"
        holder_match = re.search(
            r"Name/Surname/Nom[\s\S]{0,180}?\b([A-ZÄÖÜ]{2,})\b"
            r"[\s\S]{0,100}?(?:Vornamen|Given\s+names)[^\r\n]*\s*"
            r"([A-ZÄÖÜ][A-ZÄÖÜ ]{1,60})",
            text,
            flags=re.IGNORECASE,
        )
        if not holder_name and holder_match:
            first_names = re.sub(r"\s+", " ", holder_match.group(2)).strip().title()
            last_name = holder_match.group(1).title()
            holder_name = f"{first_names} {last_name}"

        return {
            "date": None,
            "amount": None,
            "currency": None,
            "vendor": None,
            "description": "Personalausweis",
            "document_kind": "Personalausweis",
            "date_of_birth": birth_date,
            "valid_until": valid_until,
            "document_number": document_number,
            "holder_name": holder_name,
        }

    def _extract_employment_certificate(self, text, filename):
        def labeled_company_name(value):
            match = re.search(
                r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9&.' -]{1,90}?\b"
                r"(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|UG|KG|GbR|OHG))\b",
                str(value or ""),
                flags=re.IGNORECASE,
            )
            if not match:
                return None
            result = re.sub(r"\s+", " ", match.group(1)).strip(" .-")
            return re.sub(
                r"\bGmbH\s*&\s*Co\.?\s*KG\b",
                "GmbH & Co. KG",
                result,
                flags=re.IGNORECASE,
            )

        employer_field = re.search(
            r"Angaben\s+zu\s+den\s+betrieblichen\s+Daten\s+des\s+Arbeitgebers"
            r"[\s\S]{0,500}?\bName\s*:\s*([^\r\n]+)",
            text,
            flags=re.IGNORECASE,
        )
        field_employer = (
            labeled_company_name(employer_field.group(1))
            if employer_field else None
        )
        candidates = []
        for line in (line.strip() for line in text.splitlines() if line.strip()):
            matches = re.findall(
                r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß&.\-]*(?:\s+[A-Za-z0-9ÄÖÜäöüß]"
                r"[A-Za-z0-9ÄÖÜäöüß&.\-]*){0,5}\s+(?:GmbH|AG|UG|KG|GbR|OHG))\b",
                line,
            )
            candidates.extend(matches)
        employer = field_employer or next(
            (
                candidate.strip()
                for candidate in reversed(candidates)
                if "bundesagentur" not in candidate.casefold()
            ),
            None,
        )

        if not employer:
            stem = Path(filename).stem
            stem = re.sub(r"\barbeitsbescheinigung\b", "", stem, flags=re.IGNORECASE)
            stem = re.sub(r"\b(?:hohe\s+qualität|hohe\s+qualitaet|compressed)\b", "", stem, flags=re.IGNORECASE)
            employer = re.sub(r"[_\-]+", " ", stem).strip() or None

        return {
            "vendor": employer,
            "employer": employer,
            "currency": "EUR",
            "document_kind": "Arbeitsbescheinigung",
        }

    def _extract_payroll_statement(self, text, filename=None):
        # OCR frequently inserts a space between the decimal comma and cents.
        # Normalize only that unambiguous amount form before extracting values.
        text = re.sub(r",\s+(?=\d{2}\b)", ",", text)
        month_numbers = {
            "januar": "01", "februar": "02", "märz": "03", "maerz": "03",
            "april": "04", "mai": "05", "juni": "06", "juli": "07",
            "august": "08", "september": "09", "oktober": "10",
            "november": "11", "dezember": "12",
        }
        periods = []
        for period_match in re.finditer(
            r"(?:für|fuer)\s+(januar|februar|märz|maerz|april|mai|juni|juli|"
            r"august|september|oktober|november|dezember)\s+(20\d{2})",
            text,
            flags=re.IGNORECASE,
        ):
            periods.append(
                f"{month_numbers[period_match.group(1).casefold()]}.{period_match.group(2)}"
            )
        for numeric_period in re.finditer(
                r"(?:korrektur\s+)?(?:gehalts|entgelt|lohn)abrechnung\s+"
                r"(\d{1,2})\s*[./]\s*(20\d{2})",
                text,
                flags=re.IGNORECASE,
        ):
            periods.append(
                f"{int(numeric_period.group(1)):02d}.{numeric_period.group(2)}"
            )
        for combined_period in re.finditer(
            r"(?:^|\n)\s*(?:lohn-?\s*und\s*gehaltsabrechnung|"
            r"lohn-?\s*/?\s*gehaltsabrechnung)\s+"
            r"(\d{1,2})\s*[./]\s*(20\d{2})",
            text,
            flags=re.IGNORECASE,
        ):
            periods.append(
                f"{int(combined_period.group(1)):02d}.{combined_period.group(2)}"
            )
        periods = sorted(
            set(periods),
            key=lambda value: (int(value.split(".")[1]), int(value.split(".")[0])),
        )
        if not periods and filename:
            stem = Path(filename).stem
            year_month = re.search(
                r"(?<!\d)(20\d{2})\s*[-_.]\s*(0?[1-9]|1[0-2])(?!\d)",
                stem,
            )
            month_year = re.search(
                r"(?<!\d)(0?[1-9]|1[0-2])\s*[-_.]\s*(20\d{2})(?!\d)",
                stem,
            )
            if year_month:
                periods = [f"{int(year_month.group(2)):02d}.{year_month.group(1)}"]
            elif month_year:
                periods = [f"{int(month_year.group(1)):02d}.{month_year.group(2)}"]
        period = periods[0] if len(periods) == 1 else None

        def amount_after(label, span=120, take_last=False):
            match = re.search(
                rf"{label}([\s\S]{{0,{span}}})",
                text,
                flags=re.IGNORECASE,
            )
            if not match:
                return None
            amounts = re.findall(
                r"[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}",
                match.group(1),
            )
            if not amounts:
                return None
            return amounts[-1] if take_last else amounts[0]

        employer = None
        for line in (line.strip() for line in text.splitlines() if line.strip()):
            match = re.search(
                r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß&.\-]*(?:\s+[A-Z0-9ÄÖÜ]"
                r"[A-Za-z0-9ÄÖÜäöüß&.\-]*){0,5}\s+(?:gGmbH|GmbH|AG|UG|KG|GbR|OHG))\b",
                line,
                flags=re.IGNORECASE,
            )
            if match:
                employer = match.group(1).strip()
                break

        issue_date_match = re.search(
            r"(?:Abrechnung\s+der\s+Brutto/Netto-Bezüge|"
            r"(?:Gehalts|Entgelt|Lohn)abrechnung)[^\n\r]{0,100}?"
            r"\b(\d{2}\.\d{2}\.20\d{2})\b",
            text,
            flags=re.IGNORECASE,
        )
        amount_pattern = r"[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}"
        immediate_gross = re.findall(
            rf"Gesamt-?Brutto\s*(?:\r?\n)\s*({amount_pattern})",
            text,
            flags=re.IGNORECASE,
        )
        gross = (
            immediate_gross[-1]
            if immediate_gross
            else amount_after(r"Gesamt-?Brutto") or amount_after(r"Gesamtbrutto")
        )
        net = amount_after(r"Netto-?Verdienst") or amount_after(r"Nettoverdienst")
        payout = amount_after(r"Auszahlungsbetrag", span=180, take_last=True)
        if not payout:
            payout_match = re.search(
                r"(?:Auszahlung|Differenz\s+f(?:ü|ue)r\s+Folgemonate)[^\n\r]*?"
                r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})",
                text,
                flags=re.IGNORECASE,
            )
            payout = payout_match.group(1) if payout_match else None
        correction = bool(re.search(r"Korrektur\s+(?:Gehalts|Entgelt|Lohn)abrechnung", text, re.IGNORECASE))
        return {
            "date": issue_date_match.group(1) if issue_date_match else None,
            "payroll_period": period,
            "payroll_periods": periods,
            "vendor": employer,
            "employer": employer,
            "gross_amount": gross,
            "net_amount": net,
            "payout_amount": payout,
            "amount": payout or net,
            "currency": "EUR",
            "document_kind": "Korrektur Gehaltsabrechnung" if correction else "Entgeltabrechnung",
        }

    def _extract_tax_document(self, text, classification_reason=None):
        lower = text.casefold()
        confirmation = "versandbestätigung" in lower and "formular wurde versendet" in lower
        tax_year = None
        for pattern in (
            r"einkommensteuererklärung\s+für\s+das\s+jahr\s+(20\d{2})",
            r"einkommensteuererkl.rung\s+für\s+das\s+jahr\s+(20\d{2})",
            r"hauptvordruck\s+est\s*1\s*a[\s\S]{0,80}\b(20\d{2})\b",
            r"(?:lohnsteuerbescheinigung|einkommensteuererklärung)[\s\S]{0,60}\b(20\d{2})\b",
            r"einkommensteuererklärung\s+für\s+(20\d{2})",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                tax_year = match.group(1)
                break

        if confirmation:
            submitted = re.search(
                r"Abgabezeit[\s\S]{0,80}?(\d{1,2})\.\s*([A-Za-zÄÖÜäöüß]+)\s+(20\d{2})",
                text,
                flags=re.IGNORECASE,
            )
            months = {
                "januar": "01", "februar": "02", "märz": "03", "maerz": "03",
                "april": "04", "mai": "05", "juni": "06", "juli": "07",
                "august": "08", "september": "09", "oktober": "10",
                "november": "11", "dezember": "12",
            }
            date = None
            if submitted and submitted.group(2).casefold() in months:
                date = f"{int(submitted.group(1)):02d}.{months[submitted.group(2).casefold()]}.{submitted.group(3)}"
            task = re.search(r"Auftrag\s*\n?\s*([^\n\r]+)", text, flags=re.IGNORECASE)
            ticket = re.search(r"Transferticket\s*\n?\s*([A-Za-z0-9]+)", text, flags=re.IGNORECASE)
            return {
                "date": date,
                "tax_year": tax_year,
                "tax_section": "04 ELSTER-Nachweise",
                "document_kind": "ELSTER-Versandbestätigung",
                "submission_type": task.group(1).strip() if task else None,
                "transfer_ticket": ticket.group(1) if ticket else None,
                "vendor": "ELSTER",
                "amount": None,
                "currency": None,
                "invoice_number": None,
                "contract_number": None,
                "description": None,
            }

        is_full_return = bool(
            "hauptvordruck est 1 a" in lower
            or "einkommensteuererklärung für das jahr" in lower
            or "einkommensteuererklérung für das jahr" in lower
        )
        if is_full_return:
            kind = "Einkommensteuererklärung"
            section = "01 Steuererklärung"
        elif "lohnsteuerbescheinigung" in lower:
            kind = "Lohnsteuerbescheinigung"
            section = "02 Belege/Arbeit und Werbungskosten"
        elif any(value in lower for value in (
            "aufforderung zur vorlage von belegen", "belege nachreichen", "nachreichung von belegen"
        )):
            kind = "Nachforderung von Steuerbelegen"
            section = "03 Nachforderungen"
        elif any(value in lower for value in (
            "einkommensteuerbescheid", "festsetzung der einkommensteuer", "rechtsbehelfsbelehrung"
        )):
            kind = "Einkommensteuerbescheid"
            section = "05 Steuerbescheide"
        else:
            kind = "Einkommensteuererklärung"
            section = "01 Steuererklärung"

        if not tax_year:
            years = re.findall(r"\b(20\d{2})\b", text)
            tax_year = years[0] if years else None
        return {
            "tax_year": tax_year,
            "tax_section": section,
            "document_kind": kind,
            "vendor": "Finanzamt" if "finanzamt" in lower else None,
            "amount": None,
            "currency": None,
            "invoice_number": None,
            "contract_number": None,
            "description": None,
        }

    def _extract_income_certificate(self, text):
        dates = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
        issue_date = None
        signature_match = re.search(
            r"(\d{2}\.\d{2}\.\d{4})\s+(?:Datum\s*/\s*Unterschrift|Datum\s+Unterschrift)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if signature_match:
            issue_date = signature_match.group(1)
        elif dates:
            # Employer forms commonly print the issue/signature date last.
            issue_date = dates[-1]

        def labeled_amount(label):
            match = re.search(
                rf"{label}[^\n\r]*?([0-9]{{1,3}}(?:\.[0-9]{{3}})*,[0-9]{{2}})\s*(?:Euro|EUR)",
                text,
                flags=re.IGNORECASE,
            )
            return match.group(1) if match else None

        company_candidates = []
        for line in (line.strip() for line in text.splitlines() if line.strip()):
            matches = re.findall(
                r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß&.\-]*(?:\s+[A-Z0-9ÄÖÜ][A-Za-z0-9ÄÖÜäöüß&.\-]*){0,5}\s+(?:GmbH|AG|UG|KG|GbR|OHG))\b",
                line,
            )
            company_candidates.extend(matches)
        ignored = ("sesam software", "adag payroll", "payroll services")
        employer_candidates = [
            candidate.strip() for candidate in company_candidates
            if not any(value in candidate.casefold() for value in ignored)
        ]
        employer = employer_candidates[-1] if employer_candidates else None

        name_match = re.search(
            r"Name:\s*([^\n\r]+?)\s+Vorname:\s*([^\n\r]+?)(?:\s+Geburtsdatum:|$)",
            text,
            flags=re.IGNORECASE,
        )
        employee_name = None
        if name_match:
            employee_name = f"{name_match.group(2).strip()} {name_match.group(1).strip()}"

        gross = labeled_amount(r"Bruttoarbeitsentgelt(?:\s*\([^)]*\))?:")
        net = labeled_amount(r"Nettoarbeitsentgelt:")
        return {
            "date": issue_date,
            "vendor": employer,
            "employer": employer,
            "employee_name": employee_name,
            "gross_amount": gross,
            "net_amount": net,
            "amount": gross,
            "currency": "EUR" if gross or net or "beträge in eur" in text.casefold() else None,
            "document_kind": "Einkommensbescheinigung",
        }
