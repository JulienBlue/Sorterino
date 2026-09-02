import re
from pathlib import Path
from src.date_utils import extract_document_date
from src.document_domain_extractors import DomainDocumentExtractors
from src.document_classification_support import DocumentClassificationSupport
from src.document_transaction_extractors import (
    extract_cash_receipt,
    extract_energy_contract_confirmation,
    extract_energy_order_confirmation,
    extract_return_confirmation,
)
from src.models import Classification, DocumentMetadata


class DocumentAnalyzer(DomainDocumentExtractors, DocumentClassificationSupport):
    def __init__(self, rules, company_profile, logger):
        if isinstance(rules, dict):
            self.rules = rules.get("rules", [])
            self.extraction = rules.get("extraction", {}) or {}
        else:
            self.rules = rules
            self.extraction = {}
        self.company = company_profile or {}
        self.logger = logger

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", text.lower())

    def _company_name_tokens(self):
        own_name = (self.company.get("name") or "").lower()
        legal_forms = {
            "gmbh", "ag", "ug", "kg", "ltd",
            "gbr", "ohg", "mbh", "ek", "e", "k"
        }
        return [
            token for token in re.split(r"\W+", own_name)
            if len(token) >= 4 and token not in legal_forms
        ]

    def _company_name(self):
        return (self.company.get("name") or "").strip()
    
    def _is_own_entity(self, line: str) -> bool:
        l = line.lower()
        profile = self.company or {}

        name = (profile.get("name") or "").lower()

        if name and name in l:
            return True

        if name:
            tokens = [t for t in re.split(r"\W+", name) if len(t) >= 3]
            if tokens and all(t in l for t in tokens):
                return True

        person = profile.get("person", {}) or {}
        first = (person.get("first_name") or "").lower()
        last = (person.get("last_name") or "").lower()

        full_name = f"{first} {last}".strip()

        if full_name and full_name in l:
            return True

        email = (profile.get("contact", {}).get("email") or "").lower()
        if email and email in l:
            return True

        if email and "@" in email:
            domain = email.split("@")[1]
            if domain in l:
                return True

        address = profile.get("address", {}) or {}
        street = (address.get("street") or "").strip().lower()
        zip_code = (address.get("zip") or "").strip()
        city = (address.get("city") or "").strip().lower()

        has_street = bool(street and street in l)
        has_zip = bool(zip_code and zip_code in l)
        has_city = bool(city and city in l)

        if has_street and (has_zip or has_city):
            return True

        iban = (profile.get("financial", {}).get("iban") or "")
        if iban and self._normalize(iban) in self._normalize(line):
            return True

        keywords = profile.get("keywords", []) or []
        if any(k.lower() in l for k in keywords if k):
            return True

        return False

    def is_own_invoice(self, text, log_check: bool = True):

        text_lower = text.lower()
        text_norm = self._normalize(text)
        profile = self.company or {}

        company_name = (profile.get("name") or "").strip().lower()

        person = profile.get("person", {}) or {}
        first_name = (person.get("first_name") or "").strip().lower()
        last_name = (person.get("last_name") or "").strip().lower()

        name_variants = []

        if company_name:
            name_variants.append(company_name)
        elif first_name and last_name:
            name_variants.append(f"{first_name} {last_name}")
            name_variants.append(f"{last_name} {first_name}")

        has_name = any(n in text_lower for n in name_variants) if name_variants else False

        iban = (profile.get("financial", {}).get("iban") or "").strip()
        tax_id = (profile.get("financial", {}).get("tax_id") or "").strip()
        email = (profile.get("contact", {}).get("email") or "").strip().lower()
        phone = (profile.get("contact", {}).get("phone") or "").strip()

        has_iban = bool(iban and self._normalize(iban) in text_norm)
        has_tax = bool(tax_id and tax_id.lower() in text_lower)
        has_email = bool(email and email in text_lower)
        has_phone = bool(phone and self._normalize(phone) in text_norm)

        address = profile.get("address", {}) or {}
        street = (address.get("street") or "").strip().lower()
        zip_code = (address.get("zip") or "").strip()
        city = (address.get("city") or "").strip().lower()

        has_street = bool(street and street in text_lower)
        has_zip = bool(zip_code and zip_code in text_lower)
        has_city = bool(city and city in text_lower)
        has_address = has_street and (has_zip or has_city)

        if has_iban:
            decision = True
        elif has_name and has_tax and (has_email or has_phone):
            decision = True
        elif has_name and has_email and has_phone:
            decision = True
        else:
            decision = False

        if log_check:
            self.logger.debug(
                "[OWN CHECK] "
                f"name={has_name} | iban={has_iban} | tax={has_tax} | "
                f"email={has_email} | phone={has_phone} | address={has_address} | "
                f"own={decision}"
            )

        return decision

    def analyze(self, document):

        text = document.extracted_text or ""
        filename_info = self._extract_from_filename(document.filename)

        if not text.strip():
            self.logger.warning("Kein OCR Text → fallback auf Dateiname")
            text = document.filename.lower()

        text_lower = text.lower()

        extracted = self._extract(text)

        energy_order = self._extract_energy_order_confirmation(text)
        energy_contract = self._extract_energy_contract_confirmation(text)
        return_confirmation = self._extract_return_confirmation(text)
        cash_receipt = self._extract_cash_receipt(text)

        for key, value in filename_info.items():
            if value:
                extracted[key] = value

        if energy_contract:
            classification = Classification(
                "Wohnen", 0.99, "Energieverträge",
                reason="Vertragsbestätigung Energie",
            )
            extracted.update(energy_contract)
        elif energy_order:
            classification = Classification(
                "Wohnen", 0.99, "Energieverträge",
                reason="Auftragseingangsbestätigung Energie",
            )
            extracted.update(energy_order)
        elif return_confirmation:
            classification = Classification(
                "Anschaffungen und Garantien", 0.99,
                "Retouren und Erstattungen",
                reason="Retourenbestätigung",
            )
            extracted.update(return_confirmation)
        elif cash_receipt:
            classification = Classification(
                "Anschaffungen und Garantien", 0.99, "Kassenbons",
                reason="Kassenbon",
            )
            extracted.update(cash_receipt)
        elif filename_info.get("force_outgoing"):
            classification = Classification("Buchhaltung", 1.0, "Ausgangsrechnungen")
        elif filename_info.get("force_incoming"):
            classification = Classification("Buchhaltung", 0.5, "Eingangsrechnungen")
        else:
            classification = self._classify(text_lower, document.filename)

        if classification.document_type == "Bescheinigungen":
            if classification.reason == "Arbeitsbescheinigung":
                extracted.update(
                    self._extract_employment_certificate(text, document.filename)
                )
            else:
                extracted.update(self._extract_income_certificate(text))

        if classification.document_type == "Gehaltsabrechnungen":
            extracted.update(self._extract_payroll_statement(text, document.filename))

        if classification.document_type == "Einkommensteuer":
            extracted.update(self._extract_tax_document(text, classification.reason))

        if classification.document_type == "Eingangsrechnungen":
            extracted.update(self._extract_supplier_invoice_fields(text))

        if classification.document_type == "Einsatzunterlagen":
            extracted.update(self._extract_assignment_sheet(text, document.filename))

        if classification.document_type == "Versicherungspolicen":
            extracted.update(self._extract_insurance_document(text, document.filename))

        if classification.document_type == "Kündigungen":
            extracted.update(self._extract_termination(text, document.filename))

        if classification.document_type == "Allgemeine Verträge" and (
            "beratungsvertrag" in text_lower or "beratungsvertrag" in document.filename.casefold()
        ):
            extracted.update({"document_kind": "Beratungsvertrag"})

        if classification.document_type == "Kurse und Therapien":
            extracted.update({
                "amount": None,
                "currency": None,
                "document_kind": "Teilnahmebescheinigung",
            })

        if classification.document_type == "Renteninformationen":
            extracted.update(self._extract_pension_information(text, document.filename))

        if classification.document_type == "Instandhaltung" and (
            "dokumentation des mangels" in text_lower or "mängeldokumentation" in text_lower
        ):
            extracted.update(self._extract_housing_defect(text))

        if classification.document_type == "Immobilienunterlagen":
            extracted.update(
                self._extract_property_document(
                    text,
                    document.filename,
                    classification.reason,
                )
            )

        if classification.document_type == "Führungszeugnisse":
            extracted.update(self._extract_certificate_of_conduct(text))

        if classification.document_type == "Sparen und Vermögen":
            extracted.update(self._extract_home_savings_contract(text))

        if classification.document_type == "Bewerbungen":
            extracted.update(self._extract_job_application(text))

        if classification.document_type == "Eheurkunde":
            extracted.update(self._extract_marriage_certificate(text))

        if classification.document_type == "Identitätsdokumente":
            extracted.update(self._extract_identity_document(text))

        if classification.document_type == "Kontoauszuege":
            vendor = self._extract_statement_vendor(text_lower)
            if vendor:
                extracted["vendor"] = vendor

        metadata = DocumentMetadata(
            category=classification.category,
            document_type=classification.document_type,
            invoice_date=extracted.get("date")
        )

        return classification, metadata, extracted

    _extract_energy_order_confirmation = staticmethod(extract_energy_order_confirmation)
    _extract_energy_contract_confirmation = staticmethod(extract_energy_contract_confirmation)
    _extract_return_confirmation = staticmethod(extract_return_confirmation)
    _extract_cash_receipt = staticmethod(extract_cash_receipt)

    def _extract_from_filename(self, filename: str) -> dict:
        name = Path(filename).stem

        out_pattern = r"^rechnung[_\s-]*(\d+)\s*(?:vom\s*)?(\d{2}\.\d{2}\.\d{4})?\s*(.+)?$"
        m = re.match(out_pattern, name, flags=re.IGNORECASE)
        if m:
            invoice_number = m.group(1)
            date = m.group(2)
            vendor = m.group(3)

            if vendor:
                vendor = vendor.replace("_", " ").strip()

            return {
                "invoice_number": invoice_number,
                "date": date,
                "vendor": vendor if vendor else None,
                "force_outgoing": True
            }

        in_match = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+)$", name)
        if in_match:
            date = in_match.group(1)
            rest = in_match.group(2)
            parts = [p.strip() for p in rest.split(" - ") if p.strip()]

            vendor = parts[0] if parts else None
            amount = None
            currency = None

            if parts:
                last = parts[-1]
                if re.match(r"^\d{1,3}(?:\.\d{3})*,\d{2}$", last):
                    amount = last
                elif re.match(r"^\d+(?:[.,]\d{2})$", last):
                    amount = last.replace(".", ",")
                else:
                    loose_amount = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+)", last)
                    if loose_amount:
                        raw = loose_amount.group(1)
                        amount = raw if "," in raw else f"{raw},00"

                if re.search(r"(?:\$|usd|us-dollar|dollar|\bd\b)", last, flags=re.IGNORECASE):
                    currency = "USD"

            return {
                "date": date,
                "vendor": vendor,
                "amount": amount,
                "currency": currency,
                "force_incoming": True,
                "force_outgoing": False
            }

        return {"force_outgoing": False, "force_incoming": False}

    def _classify(self, text_lower, filename=""):
        special = self._classify_special_document(text_lower, filename)
        if special:
            return special

        home_savings_strong = sum(
            term in text_lower
            for term in (
                "ihr neuer bausparvertrag",
                "bausparurkunde",
                "bausparvertrag nr",
            )
        )
        home_savings_support = sum(
            term in text_lower
            for term in (
                "bausparsumme",
                "bausparnummer",
                "regelsparbeitrag",
                "bausparkasse",
                "guthabenzins",
                "wahlzuteilung",
            )
        )
        if home_savings_strong >= 1 and home_savings_support >= 3:
            return Classification(
                category="Finanzen",
                document_type="Sparen und Vermögen",
                confidence=min(1.0, 0.82 + home_savings_support * 0.03),
                reason="Bausparvertrag",
            )

        elster_confirmation = (
            "versandbestätigung" in text_lower
            and "formular wurde versendet" in text_lower
            and ("elster" in text_lower or "transferticket" in text_lower)
        )
        if elster_confirmation:
            return Classification(
                category="Finanzamt und Steuern",
                document_type="Einkommensteuer",
                confidence=0.99,
                reason="ELSTER-Versandbestätigung",
            )

        tax_return_support = sum(
            term in text_lower
            for term in (
                "hauptvordruck est 1 a",
                "einkommensteuererklärung für das jahr",
                "zusammenveranlagung",
                "identifikationsnummer",
                "steuernummer",
            )
        )
        if "einkommensteuererklärung" in text_lower and tax_return_support >= 3:
            return Classification(
                category="Finanzamt und Steuern",
                document_type="Einkommensteuer",
                confidence=min(0.99, 0.82 + tax_return_support * 0.03),
                reason="Einkommensteuererklärung",
            )

        payroll_terms = (
            "abrechnung der brutto/netto-bez",
            "entgeltabrechnung",
            "gehaltsabrechnung",
            "lohnabrechnung",
            "lohn- und gehaltsabrechnung",
        )
        payroll_support = sum(
            term in text_lower
            for term in (
                "gesamt-brutto",
                "gesamtbrutto",
                "netto-verdienst",
                "auszahlungsbetrag",
                "steuer-brutto",
                "sv-brutto",
                "steuerbrutto",
                "nettoverdienst",
                "lohnsteuer",
                "elstam verfahren",
            )
        )
        if any(term in text_lower for term in payroll_terms) and payroll_support >= 2:
            return Classification(
                category="Arbeit und Karriere",
                document_type="Gehaltsabrechnungen",
                confidence=min(1.0, 0.8 + payroll_support * 0.04),
            )

        employment_certificate_support = sum(
            term in text_lower
            for term in (
                "bundesagentur für arbeit",
                "bundesagentur fur arbeit",
                "angaben zum arbeitgeber",
                "angaben zur arbeitnehmerin",
                "angaben zum beschäftigungsverhältnis",
                "angaben zum beschaftigungsverhaltnis",
            )
        )
        if "arbeitsbescheinigung" in text_lower and employment_certificate_support >= 2:
            return Classification(
                category="Arbeit und Karriere",
                document_type="Bescheinigungen",
                confidence=min(1.0, 0.85 + employment_certificate_support * 0.03),
                reason="Arbeitsbescheinigung",
            )

        certificate_terms = {
            "einkommensbescheinigung",
            "verdienstbescheinigung",
            "nachweis über die höhe des arbeitsentgelts",
            "nachweis ueber die hoehe des arbeitsentgelts",
        }
        strong_certificate_matches = sum(term in text_lower for term in certificate_terms)
        supporting_terms = sum(
            term in text_lower
            for term in ("bruttoarbeitsentgelt", "nettoarbeitsentgelt", "arbeitnehmer", "beschäftigungsverhältnis")
        )
        if strong_certificate_matches and supporting_terms >= 1:
            return Classification(
                category="Arbeit und Karriere",
                document_type="Bescheinigungen",
                confidence=min(1.0, 0.8 + supporting_terms * 0.05),
            )

        rule_classification = self._classify_by_weighted_rules(text_lower)
        if rule_classification:
            return rule_classification

        invoice_rule = next(
            (
                r for r in self.rules
                if r.get("category") == "Buchhaltung"
                and r.get("document_type") == "Rechnung"
            ),
            None
        )

        invoice_keywords = (invoice_rule or {}).get("keywords", [])

        if not invoice_keywords:
            return Classification("MANUELL", 0.0, "Unsortiert")

        matches = sum(1 for k in invoice_keywords if k.lower() in text_lower)
        score = matches / len(invoice_keywords) if invoice_keywords else 0

        if matches == 0 or score < 0.15:
            return Classification("MANUELL", 0.0, "Unsortiert")

        if self.is_own_invoice(text_lower):
            doc_type = "Ausgangsrechnungen"
            self.logger.debug("[CLASSIFY] Eigene Rechnung → AUSGANG")
        else:
            doc_type = "Eingangsrechnungen"
            self.logger.debug("[CLASSIFY] Fremde Rechnung → EINGANG")

        return Classification(
            category=invoice_rule["category"],
            document_type=doc_type,
            confidence=round(score, 2)
        )


    def _classify_by_weighted_rules(self, text_lower):
        """Classify conservatively using strong anchors and supporting terms."""
        candidates = []
        for rule in self.rules:
            if rule.get("document_type") == "Rechnung":
                continue
            negative = [str(value).casefold() for value in rule.get("negative_keywords", []) if value]
            if any(value in text_lower for value in negative):
                continue
            strong = [str(value).casefold() for value in rule.get("strong_keywords", []) if value]
            support = [str(value).casefold() for value in rule.get("keywords", []) if value]
            strong_hits = sum(value in text_lower for value in strong)
            support_hits = sum(value in text_lower for value in support)
            minimum_support = int(rule.get("minimum_support", 2))
            if strong_hits < int(rule.get("minimum_strong", 1)):
                if not rule.get("allow_support_only") or support_hits < minimum_support:
                    continue
            elif support_hits < int(rule.get("support_with_strong", 0)):
                continue
            confidence = min(0.99, 0.72 + strong_hits * 0.12 + support_hits * 0.035)
            if not strong_hits:
                confidence = min(0.88, 0.58 + support_hits * 0.075)
            candidates.append((confidence, strong_hits, support_hits, rule))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        if len(candidates) > 1 and candidates[1][0] >= candidates[0][0] - 0.05:
            self.logger.debug(
                "[CLASSIFY] Mehrdeutig: "
                f"{candidates[0][3].get('id')} / {candidates[1][3].get('id')}"
            )
            return None
        confidence, _strong_hits, _support_hits, rule = candidates[0]
        return Classification(
            category=rule["category"],
            document_type=rule["document_type"],
            confidence=round(confidence, 2),
            reason=rule.get("label") or rule.get("id"),
        )


    def _extract(self, text):

        return {
            "date": self._extract_date(text),
            "amount": self._extract_amount(text),
            "currency": self._extract_currency(text),
            "vendor": self._extract_vendor(text),
            "invoice_number": self._extract_invoice_number(text),
            "contract_number": self._extract_contract_number(text),
            "description": self._extract_description(text)
        }

    @staticmethod
    def _extract_contract_number(text):
        match = re.search(
            r"(?:vertrags(?:nummer|nr\.)|policen(?:nummer|nr\.)|darlehens(?:nummer|nr\.))"
            r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9./-]{2,30})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        value = match.group(1).strip(" .-")
        return value if any(char.isdigit() for char in value) else None

    def _extract_currency(self, text):
        text_lower = text.lower()

        if (
            "$" in text
            or re.search(r"\busd\b", text_lower)
            or re.search(r"\bus-dollar\b", text_lower)
            or re.search(r"\bdollar\b", text_lower)
        ):
            return "USD"

        if "eur" in text_lower or "€" in text:
            return "EUR"

        return None

    def _get_list(self, key, fallback):
        value = self.extraction.get(key, fallback)
        return value if isinstance(value, list) else fallback

    def _get_int(self, key, fallback):
        try:
            return int(self.extraction.get(key, fallback))
        except Exception:
            return fallback

    def _get_dict(self, key, fallback):
        value = self.extraction.get(key, fallback)
        return value if isinstance(value, dict) else fallback

    def _extract_date(self, text):
        return extract_document_date(text)

    def _extract_amount(self, text):
        def normalize_amount(raw: str):
            raw = raw.strip()
            if "," in raw and "." in raw:
                if raw.rfind(",") > raw.rfind("."):
                    value = float(raw.replace(".", "").replace(",", "."))
                else:
                    value = float(raw.replace(",", ""))
            else:
                value = float(raw.replace(",", "."))
            return f"{value:.2f}".replace(".", ",")

        receipt_candidates = []
        for line in [l.strip() for l in text.splitlines() if l.strip()]:
            lower = line.lower()
            if "brutto" in lower or re.search(r"\b\d{1,2}%\b", lower):
                matches = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d+[.,]\d{2}", line)
                for match in matches:
                    try:
                        receipt_candidates.append(float(normalize_amount(match).replace(",", ".")))
                    except Exception:
                        continue

        if receipt_candidates:
            best = max(receipt_candidates)
            return f"{best:.2f}".replace(".", ",")

        label_groups = [
            [
                "gesamtpreis", "gesamtbetrag", "endbetrag", "rechnungsbetrag", "zu zahlen", "zahlbetrag", "invoice total", "amount due", "fälliger betrag", "faelliger betrag", "falliger betrag"
            ],
            [
                "summe", "gesamt", "total", "invoice amount", "betrag"
            ]
        ]

        number_patterns = [
            r"\d{1,3}(?:\.\d{3})*,\d{2}",
            r"\d{1,3}(?:,\d{3})*\.\d{2}",
            r"\d+[.,]\d{2}"
        ]

        for labels in label_groups:
            candidates = []
            label_pattern = "|".join(re.escape(label) for label in labels)

            for number_pattern in number_patterns:
                pattern = rf"(?:{label_pattern})\D{{0,20}}({number_pattern})"
                matches = re.findall(pattern, text, flags=re.IGNORECASE)

                for match in matches:
                    try:
                        normalized = normalize_amount(match)
                        candidates.append(float(normalized.replace(",", ".")))
                    except Exception:
                        continue

            if candidates:
                best = max(candidates)
                return f"{best:.2f}".replace(".", ",")

        patterns = self._get_list("amount_patterns", [
            r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b",      # 1.234,56
            r"\b\d{1,3}(?:,\d{3})*\.\d{2}\b",      # 1,234.56
            r"\b\d+[.,]\d{2}\b"                   # 99,00 or 99.00
        ])

        matches = []
        for line in text.splitlines():
            lower = line.casefold()
            if any(unit in lower for unit in ("kwh", "mwh", "kilowattstunde", "jahresverbrauch")):
                continue
            for pattern in patterns:
                matches.extend(re.findall(pattern, line))

        if not matches:
            return None

        values = []
        for m in matches:
            try:
                values.append(float(normalize_amount(m).replace(",", ".")))
            except Exception:
                continue

        if not values:
            return None

        best = max(values)

        return f"{best:.2f}".replace(".", ",")

    def _extract_invoice_number(self, text):

        text_lower = text.lower()

        patterns = self._get_list("invoice_number_patterns", [
            r"(rechnung\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rechn\.\s*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rg[\.\-\s]*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rgnr[:\s\-]*)([a-z0-9\/\-]{3,})",

            r"(beleg\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(dokument\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",

            r"(invoice\s*(no\.?|number)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(inv[\.\s]*no\.?[:\s\-]*)([a-z0-9\/\-]{3,})",

            r"(rechnung[_\s\-]*)(\d{3,})"
        ])

        blacklist = self._get_list("invoice_number_blacklist", [
            "re", "ref", "re:", "awb", "pos",
            "nr", "en", "summe", "seite"
        ])

        for pattern in patterns:
            matches = re.findall(pattern, text_lower)

            for match in matches:
                candidate = match[-1].strip()

                if not any(c.isdigit() for c in candidate):
                    continue

                if len(candidate) < 3:
                    continue

                if candidate in blacklist:
                    continue

                if candidate.startswith("re-") or candidate.startswith("re:"):
                    continue

                if len(candidate) > 25:
                    continue

                return candidate

        return None

    def _extract_description(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        keywords = self._get_list("description_keywords", [
            "installation", "lizenz", "abo",
            "vertrag", "leistung", "service",
            "support", "wartung"
        ])

        blacklist = self._get_list("description_blacklist", [
            "datum", "rechnung", "betrag",
            "mwst", "gesamt", "kunde"
        ])

        max_len = self._get_int("description_max_length", 80)
        max_words = self._get_int("description_max_words", 5)

        for line in lines:
            l = line.lower()

            if any(k in l for k in keywords):

                if any(b in l for b in blacklist):
                    continue

                if len(line) > max_len:
                    continue

                if any(char.isdigit() for char in line):
                    continue

                return " ".join(line.split()[:max_words])

        return None

    def _extract_statement_vendor(self, text_lower: str):
        vendor_map = self._get_dict("statement_vendor_map", {
            "vivid": "VIVID",
            "volksbank": "Volksbank",
            "sparkasse": "Sparkasse",
            "postbank": "Postbank",
            "dkb": "DKB",
            "commerzbank": "Commerzbank",
            "ing": "ING",
            "paypal": "PayPal"
        })

        for key, value in vendor_map.items():
            if key in text_lower:
                return value

        return None

    def _extract_vendor(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        own_tokens = self._company_name_tokens()
        own_invoice = self.is_own_invoice(text, log_check=False)

        blacklist = self._get_list("vendor_blacklist", [
            "betrag", "summe", "rechnung", "datum",
            "seite", "total", "mwst",
            "bank", "verbindung", "bankverbindung",
            "iban", "bic", "konto", "swift",
            "guten tag", "vielen dank", "freundliche grüße",
            "leistung", "zahlungsbedingungen",
            "rechnungsbetrag", "übersicht",
            "im auftrag von", "auftrag von",
            "service", "team", "kunde", "rechnung nr",
            "fachberater", "ansprechpartner",
            "invoice & close", "online bezahlen", "verkauft von"
        ])
        blacklist = list({
            *blacklist,
            "fachberater",
            "ansprechpartner",
            "invoice & close",
            "online bezahlen",
            "verkauft von"
        })

        company_suffixes = self._get_list("vendor_company_suffixes", [
            "gmbh", "ag", "ug", "kg", "ltd", "mbb"
        ])
        company_suffixes = list({*company_suffixes, "mbb"})

        address_terms = self._get_list("vendor_address_terms", [
            "straße", "str.", "gasse", "platz"
        ])

        max_words = self._get_int("vendor_max_words", 5)
        max_digits = self._get_int("vendor_max_digits", 2)
        window = self._get_int("vendor_scan_window", 10)

        def is_valid(line):
            line_for_checks = re.sub(
                r"\b(?:bill to|rechnungsempfänger|rechnungsempfanger|ansprechpartner)\b",
                "",
                line,
                flags=re.IGNORECASE
            ).strip()
            l = line_for_checks.lower()

            if self._is_own_entity(line):
                return False

            if any(b in l for b in blacklist):
                return False

            if sum(c.isdigit() for c in line_for_checks) > max_digits:
                return False

            if "@" in line_for_checks:
                return False

            if any(x in l for x in address_terms):
                return False
            
            if any(x in l for x in ["iban", "bic", "bank", "konto"]):
                return False

            if len(line_for_checks.split()) > max_words:
                return False

            if own_tokens and any(t in l for t in own_tokens):
                return False

            if l.startswith(("wir ", "es ", "für ", "danke")):
                return False

            return True

        def looks_like_company(line):
            line_for_checks = re.sub(
                r"\b(?:bill to|rechnungsempfänger|rechnungsempfanger|ansprechpartner)\b",
                "",
                line,
                flags=re.IGNORECASE
            ).strip()
            l = line_for_checks.lower()

            return (
                any(x in l for x in company_suffixes)
                or ("." in line_for_checks and not any(c.isdigit() for c in line_for_checks))
                or (len(line_for_checks.split()) in [2, 3] and not any(c.isdigit() for c in line_for_checks))
            )

        def clean(line):
            line = re.sub(
                r"\b(?:bill to|rechnungsempfänger|rechnungsempfanger|ansprechpartner)\b",
                "",
                line,
                flags=re.IGNORECASE
            )
            line = re.split(
                r"\b(?:liefer-/?leistungsdatum|leistungsdatum|lieferdatum|rechnungsdatum|fälligkeit|falligkeit|rechnungsnummer)\b",
                line,
                flags=re.IGNORECASE
            )[0]
            line = re.sub(r"[^\w\.\-& ]", "", line)
            line = re.sub(r"^(cig|firma|name)\s+", "", line, flags=re.IGNORECASE)

            suffix_pattern = "|".join(re.escape(s) for s in company_suffixes)
            domain_match = re.findall(
                rf"([\w.\-]*\.[\w.\-]+(?:\s+(?:{suffix_pattern})))",
                line,
                flags=re.IGNORECASE
            )
            if domain_match:
                return domain_match[-1].strip()

            company_match = re.findall(
                rf"([\w&.\-]+(?:\s+[\w&.\-]+){{0,5}}\s+(?:{suffix_pattern}))",
                line,
                flags=re.IGNORECASE
            )
            if company_match:
                return company_match[0].strip()

            words = line.split()
            trimmed = []

            for word in words:
                trimmed.append(word)
                normalized = word.lower().rstrip(".")
                if normalized in company_suffixes:
                    words = trimmed
                    break

            if words and len(words[-1]) <= 2 and "." not in words[-1]:
                words = words[:-1]
            return " ".join(words[:4])

        def extract_from_own_line(line):
            own_name = self._company_name()
            if not own_name:
                return None

            match = re.search(re.escape(own_name), line, flags=re.IGNORECASE)
            if not match:
                return None

            tail = line[match.end():].strip(" -|:+")
            if not tail:
                return None

            if "@" in tail:
                return None

            lowered = tail.lower()
            if not (any(s in lowered for s in company_suffixes) or "." in tail):
                return None

            cleaned = clean(tail)
            if cleaned and not self._is_own_entity(cleaned):
                return cleaned

            return None

        if own_invoice:
            own_indices = [i for i, line in enumerate(lines) if self._is_own_entity(line)]

            if len(own_indices) >= 2:
                start = own_indices[0] + 1
                end = own_indices[1]

                for line in lines[start:end]:
                    l = line.lower()

                    if any(char.isdigit() for char in line):
                        continue

                    if l in {"deutschland", "germany"}:
                        continue

                    if any(x in l for x in address_terms):
                        continue

                    cleaned = clean(line)
                    if cleaned and len(cleaned.split()) >= 2:
                        return cleaned

        own_index = None
        for i, line in enumerate(lines):
            if self._is_own_entity(line):
                own_index = i
                break

        if own_index is not None and not own_invoice:
            same_line_vendor = extract_from_own_line(lines[own_index])
            if same_line_vendor:
                return same_line_vendor

        if own_index is not None and own_invoice:
            for line in lines[own_index + 1: own_index + window]:
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        if own_index is not None:
            if not own_invoice:
                for line in reversed(lines[max(0, own_index - window):own_index]):
                    l = line.lower()
                    if self._is_own_entity(line):
                        continue
                    if any(suffix in l for suffix in company_suffixes):
                        cleaned = clean(line)
                        if cleaned:
                            return cleaned

            for line in reversed(lines[max(0, own_index - window):own_index]):
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        for line in lines[:20]:
            if is_valid(line) and looks_like_company(line):
                return clean(line)

        return None
