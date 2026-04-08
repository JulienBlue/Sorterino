import re
from src.models import Classification, DocumentMetadata


class DocumentAnalyzer:

    # CONFIG / INIT
    def __init__(self, rules, company_profile, logger):
        self.rules = rules
        self.company = company_profile or {}
        self.logger = logger

    # ANALYSE / START
    def analyze(self, document):

        text = document.extracted_text or ""

        # 🔥 Fallback wenn OCR leer
        if not text.strip():
            self.logger.warning("Kein OCR Text → fallback auf Dateiname")
            text = (document.filename or "").lower()

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

        lines = [l.strip() for l in text_lower.splitlines() if l.strip()]

        first_block = " ".join(lines[:10])
        last_block = " ".join(lines[-10:])

        # =========================
        # COMPANY CONTEXT
        # =========================
        company_keywords = [k.lower() for k in self.company.get("keywords", [])]

        if self.company.get("name"):
            company_keywords.append(self.company["name"].lower())

        def contains_company(block):
            return any(k in block for k in company_keywords)

        company_top = contains_company(first_block)
        company_bottom = contains_company(last_block)
        company_any = contains_company(text_lower)

        # =========================
        # UST-ID
        # =========================
        ust_id = (self.company.get("financial", {}) or {}).get("tax_id", "")
        ust_norm = ust_id.lower().replace(" ", "")
        text_norm = text_lower.replace(" ", "")

        has_ust = bool(ust_norm and ust_norm in text_norm)

        # =========================
        # VENDOR
        # =========================
        vendor = self._extract_vendor(text_lower)
        vendor_lower = vendor.lower() if vendor else ""

        # =========================
        # RULE LOOP
        # =========================
        for rule in self.rules:
            keywords = rule.get("keywords", [])

            if not keywords:
                continue

            # ✅ FIX: nur text_lower verwenden
            matches = sum(1 for k in keywords if k.lower() in text_lower)

            if matches == 0:
                continue

            score = matches / len(keywords)
            doc_type = rule.get("document_type")

            # =========================
            # leichte Boosts
            # =========================
            if company_any and doc_type == "Rechnung":
                score += 0.1

            if any(x in text_lower for x in ["zahlung", "überweisung", "zahlbar", "fällig"]):
                score += 0.05

            # =========================
            # BEST MATCH
            # =========================
            if score > best_score:
                best_score = score
                best = rule

        # =========================
        # FALLBACK
        # =========================
        if not best or best_score < 0.25:
            return Classification("MANUELL", 0.0, "Unsortiert")

        doc_type = best["document_type"]

        # =========================
        # EIN / AUS LOGIK
        # =========================
        if doc_type == "Rechnung":

            if has_ust or company_top:
                doc_type = "Ausgangsrechnungen"

            elif company_bottom:
                doc_type = "Eingangsrechnungen"

            else:
                if vendor_lower:
                    is_own_vendor = any(k in vendor_lower for k in company_keywords)

                    if is_own_vendor:
                        doc_type = "Ausgangsrechnungen"
                    else:
                        doc_type = "Eingangsrechnungen"

        return Classification(
            category=best["category"],
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
            "vendor": self._extract_vendor(text)
        }

    def _extract_date(self, text):
        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        return match.group(1) if match else None

    def _extract_amount(self, text):
        match = re.findall(r"([0-9]+,[0-9]{2})", text)
        return match[-1] if match else None

    # =========================
    # VENDOR DETECTION
    # =========================
    def _extract_vendor(self, text):

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        top_lines = lines[:20]

        company_keywords = [k.lower() for k in self.company.get("keywords", [])]

        def is_own_company(line):
            return any(k in line.lower() for k in company_keywords)

        def is_address_block(i):
            if i + 2 >= len(top_lines):
                return False

            l2 = top_lines[i + 1].lower()
            l3 = top_lines[i + 2].lower()

            has_street = any(x in l2 for x in ["straße", "str.", "weg", "platz"])
            has_zip = re.search(r"\d{5}", l3)

            return has_street and has_zip

        candidates = []

        for line in top_lines:
            l = line.lower()
            score = 0

            if any(x in l for x in ["gmbh", "ug", "ag", "ltd", "kg", "ohg"]):
                score += 4

            if re.search(r"\d{5}", l):
                score += 1

            if any(x in l for x in ["straße", "str.", "weg", "platz"]):
                score += 1

            if any(x in l for x in ["rechnung", "angebot", "datum"]):
                score -= 2

            if score > 0:
                candidates.append((line, score))

        if not candidates:
            for i in range(len(top_lines) - 2):
                if is_address_block(i):
                    return top_lines[i]

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        vendor = candidates[0][0]

        if is_own_company(vendor):
            for alt, _ in candidates[1:]:
                if not is_own_company(alt):
                    return alt

        return vendor