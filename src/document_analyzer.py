import re
from pathlib import Path
from src.models import Classification, DocumentMetadata


class DocumentAnalyzer:

    # =========================
    # CONFIG / INIT
    # =========================
    def __init__(self, rules, company_profile, logger):
        if isinstance(rules, dict):
            self.rules = rules.get("rules", [])
            self.extraction = rules.get("extraction", {}) or {}
        else:
            self.rules = rules
            self.extraction = {}
        self.company = company_profile or {}
        self.logger = logger

    # =========================
    # NORMALIZE
    # =========================
    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", text.lower())
    
    def _is_own_entity(self, line: str) -> bool:
        l = line.lower()
        profile = self.company or {}

        # Firmenname
        name = (profile.get("name") or "").lower()
        if name and name in l:
            return True

        # Firmenname (Token-Check, toleranter)
        if name:
            tokens = [t for t in re.split(r"\W+", name) if len(t) >= 3]
            if tokens and all(t in l for t in tokens):
                return True

        # 🔥 PERSON (NEU)
        person = profile.get("person", {}) or {}
        first = (person.get("first_name") or "").lower()
        last = (person.get("last_name") or "").lower()

        full_name = f"{first} {last}".strip()

        if full_name and full_name in l:
            return True

        # Email / Domain
        email = (profile.get("contact", {}).get("email") or "").lower()
        if email and email in l:
            return True

        if email and "@" in email:
            domain = email.split("@")[1]
            if domain in l:
                return True

        # IBAN
        iban = (profile.get("financial", {}).get("iban") or "")
        if iban and self._normalize(iban) in self._normalize(line):
            return True

        # Keywords (aus Profil)
        keywords = profile.get("keywords", []) or []
        if any(k.lower() in l for k in keywords if k):
            return True

        return False

    # =========================
    # OWN INVOICE CHECK
    # =========================
    def is_own_invoice(self, text):

        text_lower = text.lower()
        text_norm = self._normalize(text)
        profile = self.company or {}

        # =========================
        # NAME LOGIK (FIRMA ODER PERSON)
        # =========================
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

        # =========================
        # ANDERE FELDER
        # =========================
        iban = (profile.get("financial", {}).get("iban") or "").strip()
        tax_id = (profile.get("financial", {}).get("tax_id") or "").strip()
        email = (profile.get("contact", {}).get("email") or "").strip().lower()
        phone = (profile.get("contact", {}).get("phone") or "").strip()

        has_iban = bool(iban and self._normalize(iban) in text_norm)
        has_tax = bool(tax_id and tax_id.lower() in text_lower)
        has_email = bool(email and email in text_lower)
        has_phone = bool(phone and self._normalize(phone) in text_norm)

        # =========================
        # ADDRESS (optional, extra Sicherheit)
        # =========================
        address = profile.get("address", {}) or {}
        street = (address.get("street") or "").strip().lower()
        zip_code = (address.get("zip") or "").strip()
        city = (address.get("city") or "").strip().lower()

        has_street = bool(street and street in text_lower)
        has_zip = bool(zip_code and zip_code in text_lower)
        has_city = bool(city and city in text_lower)
        has_address = has_street and (has_zip or has_city)

        # Entscheidung ohne Score
        if has_iban or has_tax:
            decision = True
        elif has_name and (has_email or has_phone):
            decision = True
        else:
            decision = False

        self.logger.debug(
            "[OWN CHECK] "
            f"name={has_name} | iban={has_iban} | tax={has_tax} | "
            f"email={has_email} | phone={has_phone} | address={has_address} | "
            f"own={decision}"
        )

        return decision

        # Analyse
    def analyze(self, document):

        text = document.extracted_text or ""
        filename_info = self._extract_from_filename(document.filename)

        if not text.strip():
            self.logger.warning("Kein OCR Text → fallback auf Dateiname")
            text = document.filename.lower()

        text_lower = text.lower()

        extracted = self._extract(text)

        # Dateiname schlägt OCR, wenn vorhanden
        for key, value in filename_info.items():
            if value:
                extracted[key] = value

        # Dateiname hat Priorität
        if filename_info.get("force_outgoing"):
            classification = Classification("BUCHHALTUNG", 1.0, "Ausgangsrechnungen")
        elif filename_info.get("force_incoming"):
            classification = Classification("BUCHHALTUNG", 0.5, "Eingangsrechnungen")
        else:
            classification = self._classify(text_lower)

        metadata = DocumentMetadata(
            category=classification.category,
            document_type=classification.document_type,
            invoice_date=extracted.get("date")
        )

        return classification, metadata, extracted

    # Dateiname auswerten (Ein-/Ausgang)
    def _extract_from_filename(self, filename: str) -> dict:
        name = Path(filename).stem

        # Rechnung_100012 vom 03.03.2025 Neue Formen AD Group GmbH
        # Rechnung 1000003 tom und perla
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

        # Eingangsrechnungen: 21.03.2024 Lieferant - Thema - 99,00
        in_match = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+)$", name)
        if in_match:
            date = in_match.group(1)
            rest = in_match.group(2)
            parts = [p.strip() for p in rest.split(" - ") if p.strip()]

            vendor = parts[0] if parts else None
            amount = None

            if parts:
                last = parts[-1]
                if re.match(r"^\d{1,3}(?:\.\d{3})*,\d{2}$", last):
                    amount = last
                elif re.match(r"^\d+(?:[.,]\d{2})$", last):
                    amount = last.replace(".", ",")

            return {
                "date": date,
                "vendor": vendor,
                "amount": amount,
                "force_incoming": True,
                "force_outgoing": False
            }

        return {"force_outgoing": False}

    # Klassifizierung
    def _classify(self, text_lower):

        best = None
        best_score = 0

        for rule in self.rules:
            keywords = rule.get("keywords", [])

            if not keywords:
                continue

            matches = sum(1 for k in keywords if k.lower() in text_lower)

            if matches == 0:
                continue

            score = matches / len(keywords)

            if score > best_score:
                best_score = score
                best = rule

        if not best or best_score < 0.25:
            # Fallback: Rechnung-Trigger aus rules.json
            invoice_rule = next(
                (
                    r for r in self.rules
                    if r.get("category") == "BUCHHALTUNG"
                    and r.get("document_type") == "Rechnung"
                ),
                None
            )

            invoice_keywords = (invoice_rule or {}).get("keywords", [])

            if any(k.lower() in text_lower for k in invoice_keywords):
                return Classification("BUCHHALTUNG", 0.25, "Rechnung")

            return Classification("MANUELL", 0.0, "Unsortiert")

        category = best["category"]
        base_type = best["document_type"]

        # 🔥 EIN/AUS IMMER ÜBERSCHREIBEN
        if "rechnung" in base_type.lower():

            if self.is_own_invoice(text_lower):
                doc_type = "Ausgangsrechnungen"
                self.logger.debug("[CLASSIFY] Eigene Rechnung → AUSGANG")
            else:
                doc_type = "Eingangsrechnungen"
                self.logger.debug("[CLASSIFY] Fremde Rechnung → EINGANG")

        else:
            doc_type = base_type

        return Classification(
            category=category,
            document_type=doc_type,
            confidence=round(best_score, 2)
        )

    # Extraktion
    def _extract(self, text):

        return {
            "date": self._extract_date(text),
            "amount": self._extract_amount(text),
            "vendor": self._extract_vendor(text),
            "invoice_number": self._extract_invoice_number(text),
            "description": self._extract_description(text)
        }

    # Config helper
    def _get_list(self, key, fallback):
        value = self.extraction.get(key, fallback)
        return value if isinstance(value, list) else fallback

    def _get_int(self, key, fallback):
        try:
            return int(self.extraction.get(key, fallback))
        except Exception:
            return fallback

    # Basic extracts
    def _extract_date(self, text):
        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        return match.group(1) if match else None

    def _extract_amount(self, text):
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

        values = [
            float(m.replace(".", "").replace(",", "."))
            for m in matches
        ]

        best = max(values)

        return f"{best:.2f}".replace(".", ",")

    # Invoice-Nummer
    def _extract_invoice_number(self, text):

        text_lower = text.lower()

        patterns = self._get_list("invoice_number_patterns", [
            # Rechnung
            r"(rechnung\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rechn\.\s*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rg[\.\-\s]*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rgnr[:\s\-]*)([a-z0-9\/\-]{3,})",

            # Beleg
            r"(beleg\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(dokument\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",

            # Englisch
            r"(invoice\s*(no\.?|number)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(inv[\.\s]*no\.?[:\s\-]*)([a-z0-9\/\-]{3,})",

            # Dateiname
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

                # =========================
                # 🔥 HARTE FILTER
                # =========================

                # muss mindestens eine Zahl enthalten
                if not any(c.isdigit() for c in candidate):
                    continue

                # zu kurz
                if len(candidate) < 3:
                    continue

                # typische Müllwerte
                if candidate in blacklist:
                    continue

                # darf NICHT mit "re" anfangen (Mail-Referenz!)
                if candidate.startswith("re-") or candidate.startswith("re:"):
                    continue

                # zu lang → OCR Müll
                if len(candidate) > 25:
                    continue

                return candidate

        return None

        # Description
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

    # Vendor-Erkennung
    def _extract_vendor(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        own_name = (self.company.get("name") or "").lower()

        blacklist = self._get_list("vendor_blacklist", [
            "betrag", "summe", "rechnung", "datum",
            "seite", "total", "mwst",
            "bank", "verbindung", "bankverbindung",
            "iban", "bic", "konto", "swift",
            "guten tag", "vielen dank", "freundliche grüße",
            "leistung", "zahlungsbedingungen",
            "rechnungsbetrag", "übersicht",
            "im auftrag von", "auftrag von",
            "service", "team", "kunde", "rechnung nr"
        ])

        company_suffixes = self._get_list("vendor_company_suffixes", [
            "gmbh", "ag", "ug", "kg", "ltd"
        ])

        address_terms = self._get_list("vendor_address_terms", [
            "straße", "str.", "gasse", "platz"
        ])

        max_words = self._get_int("vendor_max_words", 5)
        max_digits = self._get_int("vendor_max_digits", 2)
        window = self._get_int("vendor_scan_window", 10)

        def is_valid(line):
            l = line.lower()

            if self._is_own_entity(line):
                return False

            if any(b in l for b in blacklist):
                return False

            if sum(c.isdigit() for c in line) > max_digits:
                return False

            if any(x in l for x in address_terms):
                return False
            
            if any(x in l for x in ["iban", "bic", "bank", "konto"]):
                return False

            if len(line.split()) > max_words:
                return False

            if self._is_own_entity(line):
                return False

            if l.startswith(("wir ", "es ", "für ", "danke")):
                return False

            return True

        def looks_like_company(line):
            l = line.lower()

            return (
                any(x in l for x in company_suffixes)
                or (len(line.split()) in [2, 3] and not any(c.isdigit() for c in line))
            )

        def clean(line):
            line = re.sub(r"[^\w\.\- ]", "", line)
            line = re.sub(r"^(cig|firma|name)\s+", "", line, flags=re.IGNORECASE)
            words = line.split()
            if words and len(words[-1]) <= 2 and "." not in words[-1]:
                words = words[:-1]
            return " ".join(words[:3])

        # eigene Firma finden
        own_index = None
        for i, line in enumerate(lines):
            if own_name and own_name in line.lower():
                own_index = i
                break

        # Ausgang → Kunde unterhalb
        if own_index is not None and self.is_own_invoice(text):
            for line in lines[own_index + 1: own_index + window]:
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        # Eingang → Lieferant oberhalb
        if own_index is not None:
            for line in reversed(lines[max(0, own_index - window):own_index]):
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        # Fallback
        for line in lines[:20]:
            if is_valid(line) and looks_like_company(line):
                return clean(line)

        return None
