import re
from src.models import Classification, DocumentMetadata


class DocumentAnalyzer:

    # =========================
    # CONFIG / INIT
    # =========================
    def __init__(self, rules, company_profile, logger):
        self.rules = rules
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

        return False

    # =========================
    # OWN INVOICE CHECK
    # =========================
    def is_own_invoice(self, text):

        text_norm = self._normalize(text)
        profile = self.company

        name = (profile.get("name") or "").lower()
        iban = (profile.get("financial", {}).get("iban") or "")
        tax_id = (profile.get("financial", {}).get("tax_id") or "")
        email = (profile.get("contact", {}).get("email") or "")
        phone = (profile.get("contact", {}).get("phone") or "")

        has_name = name and name in text.lower()
        has_iban = iban and self._normalize(iban) in text_norm
        has_tax = tax_id and tax_id.lower() in text.lower()
        has_email = email and email.lower() in text.lower()
        has_phone = phone and self._normalize(phone) in text_norm

        self.logger.debug(
            f"[OWN CHECK] name={has_name}, iban={has_iban}, tax={has_tax}, email={has_email}, phone={has_phone}"
        )

        return all([has_name, has_iban, has_tax, has_email, has_phone])

    # =========================
    # ANALYSE / START
    # =========================
    def analyze(self, document):

        text = document.extracted_text or ""

        if not text.strip():
            self.logger.warning("Kein OCR Text → fallback auf Dateiname")
            text = document.filename.lower()

        text_lower = text.lower()

        extracted = self._extract(text)
        classification = self._classify(text_lower)

        metadata = DocumentMetadata(
            category=classification.category,
            document_type=classification.document_type,
            invoice_date=extracted.get("date")
        )

        return classification, metadata, extracted

    # =========================
    # KLASSIFIZIERUNG
    # =========================
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

    # =========================
    # EXTRAKTION
    # =========================
    def _extract(self, text):

        return {
            "date": self._extract_date(text),
            "amount": self._extract_amount(text),
            "vendor": self._extract_vendor(text),
            "invoice_number": self._extract_invoice_number(text),
            "description": self._extract_description(text)
        }

    # =========================
    # BASIC EXTRACTIONS
    # =========================
    def _extract_date(self, text):
        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        return match.group(1) if match else None

    def _extract_amount(self, text):
        matches = re.findall(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b", text)

        if not matches:
            return None

        values = [
            float(m.replace(".", "").replace(",", "."))
            for m in matches
        ]

        best = max(values)

        return f"{best:.2f}".replace(".", ",")

    # =========================
    # INVOICE NUMBER
    # =========================
    def _extract_invoice_number(self, text):

        text_lower = text.lower()

        patterns = [
            # 🇩🇪 Rechnung Varianten
            r"(rechnung\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rechn\.\s*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rg[\.\-\s]*nr\.?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(rgnr[:\s\-]*)([a-z0-9\/\-]{3,})",

            # 📄 Beleg / Dokument
            r"(beleg\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(dokument\s*(nr\.?|nummer)?[:\s\-]*)([a-z0-9\/\-]{3,})",

            # 🌍 Englisch
            r"(invoice\s*(no\.?|number)?[:\s\-]*)([a-z0-9\/\-]{3,})",
            r"(inv[\.\s]*no\.?[:\s\-]*)([a-z0-9\/\-]{3,})",

            # 🔥 Sonderfall Dateiname
            r"(rechnung[_\s\-]*)(\d{3,})"
        ]

        blacklist = [
            "re", "ref", "re:", "awb", "pos",
            "nr", "en", "summe", "seite"
        ]

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

    # =========================
    # DESCRIPTION
    # =========================
    def _extract_description(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        keywords = [
            "installation", "lizenz", "abo",
            "vertrag", "leistung", "service",
            "support", "wartung"
        ]

        blacklist = [
            "datum", "rechnung", "betrag",
            "mwst", "gesamt", "kunde"
        ]

        for line in lines:
            l = line.lower()

            if any(k in l for k in keywords):

                if any(b in l for b in blacklist):
                    continue

                if len(line) > 80:
                    continue

                if any(char.isdigit() for char in line):
                    continue

                return " ".join(line.split()[:5])

        return None

    # =========================
    # VENDOR DETECTION (FINAL 🔥)
    # =========================
    def _extract_vendor(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        own_name = (self.company.get("name") or "").lower()

        blacklist = [
            "betrag", "summe", "rechnung", "datum",
            "seite", "total", "mwst",
            "bank", "verbindung", "bankverbindung",
            "iban", "bic", "konto", "swift",
            "guten tag", "vielen dank", "freundliche grüße",
            "leistung", "zahlungsbedingungen",
            "rechnungsbetrag", "übersicht",
            "im auftrag von", "auftrag von",
            "service", "team", "kunde", "rechnung nr"
        ]

        def is_valid(line):
            l = line.lower()

            if self._is_own_entity(line):
                return False

            if any(b in l for b in blacklist):
                return False

            if sum(c.isdigit() for c in line) > 2:
                return False

            if any(x in l for x in ["straße", "str.", "gasse", "platz"]):
                return False
            
            if any(x in l for x in ["iban", "bic", "bank", "konto"]):
                return False

            if len(line.split()) > 5:
                return False

            if self._is_own_entity(line):
                return False

            if l.startswith(("wir ", "es ", "für ", "danke")):
                return False

            return True

        def looks_like_company(line):
            l = line.lower()

            return (
                any(x in l for x in ["gmbh", "ag", "ug", "kg", "ltd"])
                or (len(line.split()) in [2, 3] and not any(c.isdigit() for c in line))
            )

        def clean(line):
            line = re.sub(r"[^\w\.\- ]", "", line)
            line = re.sub(r"^(cig|firma|name)\s+", "", line, flags=re.IGNORECASE)
            words = line.split()
            return " ".join(words[:3])

        # 🔍 eigene Firma finden
        own_index = None
        for i, line in enumerate(lines):
            if own_name and own_name in line.lower():
                own_index = i
                break

        # 📤 AUSGANG → Kunde unterhalb
        if own_index is not None and self.is_own_invoice(text):
            for line in lines[own_index + 1: own_index + 10]:
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        # 📥 EINGANG → Lieferant oberhalb
        if own_index is not None:
            for line in reversed(lines[max(0, own_index - 10):own_index]):
                if is_valid(line) and looks_like_company(line):
                    return clean(line)

        # 🔁 FALLBACK
        for line in lines[:20]:
            if is_valid(line) and looks_like_company(line):
                return clean(line)

        return None