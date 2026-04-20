import re
from pathlib import Path
from src.models import Classification, DocumentMetadata


class DocumentAnalyzer:
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

        for key, value in filename_info.items():
            if value:
                extracted[key] = value

        if filename_info.get("force_outgoing"):
            classification = Classification("BUCHHALTUNG", 1.0, "Ausgangsrechnungen")
        elif filename_info.get("force_incoming"):
            classification = Classification("BUCHHALTUNG", 0.5, "Eingangsrechnungen")
        else:
            classification = self._classify(text_lower)

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

    def _classify(self, text_lower):
        invoice_rule = next(
            (
                r for r in self.rules
                if r.get("category") == "BUCHHALTUNG"
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

    def _extract(self, text):

        return {
            "date": self._extract_date(text),
            "amount": self._extract_amount(text),
            "currency": self._extract_currency(text),
            "vendor": self._extract_vendor(text),
            "invoice_number": self._extract_invoice_number(text),
            "description": self._extract_description(text)
        }

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
        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        if match:
            return match.group(1)

        match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{2})\b", text)
        if match:
            day, month, year = match.groups()
            return f"{day}.{month}.20{year}"

        month_map = {
            "january": "01", "januar": "01",
            "february": "02", "februar": "02",
            "march": "03", "märz": "03", "maerz": "03",
            "april": "04",
            "may": "05", "mai": "05",
            "june": "06", "juni": "06",
            "july": "07", "juli": "07",
            "august": "08",
            "september": "09",
            "october": "10", "oktober": "10",
            "november": "11",
            "december": "12", "dezember": "12"
        }

        text_lower = text.lower()

        match = re.search(r"\b([a-zäöü]+)\s+(\d{1,2}),\s*(\d{4})\b", text_lower, flags=re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            month = month_map.get(month_name.lower())
            if month:
                return f"{int(day):02d}.{month}.{year}"

        match = re.search(r"\b(\d{1,2})\.\s*([a-zäöü]+)\s+(\d{4})\b", text_lower, flags=re.IGNORECASE)
        if match:
            day, month_name, year = match.groups()
            month = month_map.get(month_name.lower())
            if month:
                return f"{int(day):02d}.{month}.{year}"

        return None

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
        for pattern in patterns:
            matches.extend(re.findall(pattern, text))

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
