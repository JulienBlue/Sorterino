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
        text_lower = text.lower()

        if not text.strip():
            return Classification("MANUELL", 0.0), None, {}

        extracted = self._extract(text)

        classification = self._classify(text_lower)

        metadata = DocumentMetadata(
            category=classification.category,
            document_type=classification.document_type,
            invoice_date=extracted.get("date")
        )

        return classification, metadata, extracted

    # ANALYSE / KLASSIFIZIERUNG
    def _classify(self, text):

        best = None
        best_score = 0

        company_keywords = self.company.get("keywords", [])

        for rule in self.rules:
            keywords = rule.get("keywords", [])

            matches = sum(1 for k in keywords if k.lower() in text)
            if matches == 0:
                continue

            score = matches / len(keywords)

            if any(k.lower() in text for k in company_keywords):
                if rule.get("document_type") == "Ausgangsrechnungen":
                    score += 0.2

            if "zahlung" in text or "überweisung" in text:
                if rule.get("document_type") == "Eingangsrechnungen":
                    score += 0.1

            if score > best_score:
                best_score = score
                best = rule

        if not best:
            return Classification("MANUELL", 0.0)

        return Classification(
            category=best["category"],
            document_type=best["document_type"],
            confidence=round(best_score, 2)
        )

    # EXTRAKTION / START
    def _extract(self, text):

        return {
            "date": self._extract_date(text),
            "amount": self._extract_amount(text),
            "vendor": self._extract_vendor(text)
        }

    # EXTRAKTION / DATUM
    def _extract_date(self, text):
        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        return match.group(1) if match else None

    # EXTRAKTION / BETRAG
    def _extract_amount(self, text):
        match = re.findall(r"([0-9]+,[0-9]{2})", text)
        return match[-1] if match else None

    # EXTRAKTION / ANBIETER
    def _extract_vendor(self, text):
        lines = text.splitlines()
        for line in lines[:20]:
            if "gmbh" in line.lower():
                return line.strip()
        return None