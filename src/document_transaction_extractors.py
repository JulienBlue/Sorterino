import re


def extract_energy_order_confirmation(text):
    lower = text.casefold()
    normalized = re.sub(r"\s+", " ", lower)
    opening = normalized[:6000]
    confirmation = bool(
        re.search(r"auftragseingangsbest(?:ätigung|aetigung|atigung)", opening)
        and re.search(r"(?:strom|gas)\s*belieferung", opening)
        and re.search(r"auftrags\s*(?:nummer|nr\.?)", opening)
    )
    if not confirmation:
        return None

    order_match = re.search(
        r"auftrags\s*(?:nummer|nr\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./-]{2,30})",
        text,
        flags=re.IGNORECASE,
    )
    delivery_match = re.search(
        r"(?:voraussichtlicher\s+liefertermin(?:\s+ist)?|lieferbeginn)\s*[:]?\s*"
        r"(?:der\s+)?(\d{2}\.\d{2}\.\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    tariff_match = re.search(r"tarif\s*[:]?\s*([^\n\r]+)", text, flags=re.IGNORECASE)
    if "fuxx" in lower and "sparenergie" in lower:
        vendor = "Fuxx - Die Sparenergie GmbH"
    elif "plusstrom" in lower:
        vendor = "PlusStrom"
    else:
        vendor = None
    supply = (
        "Gasbelieferung"
        if re.search(r"gas\s*belieferung", opening)
        else "Strombelieferung"
    )
    order_number = order_match.group(1).strip(" .-") if order_match else None
    return {
        "amount": None,
        "currency": None,
        "vendor": vendor,
        "invoice_number": None,
        "contract_number": order_number,
        "order_number": order_number,
        "description": supply,
        "document_kind": "Auftragseingangsbestätigung",
        "energy_supply_type": supply,
        "brand": "PlusStrom" if "plusstrom" in lower else None,
        "tariff": tariff_match.group(1).strip()[:100] if tariff_match else None,
        "expected_delivery_date": delivery_match.group(1) if delivery_match else None,
        "shared_scope": "family",
    }

def extract_energy_contract_confirmation(text):
    lower = text.casefold()
    normalized = re.sub(r"\s+", " ", lower)
    opening = normalized[:7000]
    if not (
        re.search(r"vertragsbest(?:ä|a)tt?igung\s+(?:strom|gas)belieferung", opening)
        and re.search(r"vertragsnummer\s*[:#-]?\s*[a-z0-9./-]{4,}", opening)
        and any(term in opening for term in ("lieferbeginn", "belieferungsbeginn"))
    ):
        return None

    def match_value(pattern, flags=re.IGNORECASE):
        match = re.search(pattern, text, flags=flags)
        return match.group(1).strip() if match else None

    contract_number = match_value(
        r"Vertragsnummer\s*[:#-]?\s*([A-Z0-9./-]{4,30})"
    )
    customer_number = match_value(
        r"Kundennummer\s*[:#-]?\s*([A-Z0-9./-]{4,30})"
    )
    delivery_start = match_value(
        r"(?:Lieferbeginn|Belieferungsbeginn(?:\s+durch\s+uns\s+zum)?)\s*[:]?[\s\w]*?"
        r"(\d{2}\.\d{2}\.\d{4})"
    )
    tariff = match_value(r"Tarif\s*[:]?\s*([^\n\r]+)")
    market_location_id = match_value(
        r"Marktlokations\s*ID\s*[:#-]?\s*([0-9]{8,20})"
    )
    payment = match_value(
        r"Monatlicher\s+Zahlbetrag\s*[:]?\s*"
        r"([0-9]{1,3}(?:[. ][0-9]{3})*,[0-9]{2})"
    )
    if "fuxx" in lower and "sparenergie" in lower:
        vendor = "Fuxx - Die Sparenergie GmbH"
    elif "plusstrom" in lower:
        vendor = "PlusStrom"
    else:
        vendor = None
    supply = "Gasbelieferung" if "gasbelieferung" in opening else "Strombelieferung"
    return {
        "amount": payment,
        "currency": "EUR" if payment else None,
        "vendor": vendor,
        "invoice_number": None,
        "contract_number": contract_number,
        "customer_number": customer_number,
        "description": supply,
        "document_kind": "Vertragsbestätigung",
        "energy_supply_type": supply,
        "brand": "PlusStrom" if "plusstrom" in lower else None,
        "tariff": tariff[:100] if tariff else None,
        "delivery_start": delivery_start,
        "market_location_id": market_location_id,
        "monthly_payment": payment,
        "shared_scope": "family",
    }

def extract_return_confirmation(text):
    lower = text.casefold()
    if not (
        "retourenbestätigung" in lower
        and any(term in lower for term in (
            "warenrücksendung", "gutschriftsbetrag", "wir erstatten den warenwert"
        ))
    ):
        return None

    def match_value(pattern, flags=re.IGNORECASE):
        match = re.search(pattern, text, flags=flags)
        return match.group(1).strip() if match else None

    invoice_number = match_value(
        r"Korrekturrechnung(?:s)?-?Nr\.?\s*[:#-]?\s*([A-Z0-9./-]{4,30})"
    )
    order_number = match_value(
        r"Ihre\s+Bestell-?Nr\.?\s*[:#-]?\s*([A-Z0-9./-]{4,30})"
    )
    customer_number = match_value(
        r"Kunden-?Nr\.?\s*[:#-]?\s*([A-Z0-9./-]{4,30})"
    )
    amount = match_value(
        r"(?:^|\n)\s*Gutschriftsbetrag\s*:?\s*(?:EUR\s*)?"
        r"([0-9]{1,3}(?:[. ][0-9]{3})*,[0-9]{2})",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    product = match_value(
        r"\b\d{1,3}\s+\d{5,12}\s+(.+?)\s+\d{1,3}(?:[;,]\d{1,2})?\s+\d+\s+"
        r"[0-9]{1,3}(?:[. ][0-9]{3})*,[0-9]{2}\b"
    )
    vendor = (
        "Birkenstock Europe GmbH"
        if "birkenstock" in lower else None
    )
    return {
        "vendor": vendor,
        "brand": "Birkenstock" if vendor else None,
        "invoice_number": invoice_number,
        "correction_invoice_number": invoice_number,
        "order_number": order_number,
        "customer_number": customer_number,
        "amount": amount,
        "currency": "EUR" if amount else None,
        "description": product or "Warenrücksendung",
        "product": product,
        "document_kind": "Retourenbestätigung",
    }

def extract_cash_receipt(text):
    lower = text.casefold()
    receipt_signals = sum(
        bool(re.search(pattern, lower, flags=re.MULTILINE))
        for pattern in (
            r"(?:^|\n)\s*(?:summe|gesamt|zu zahlen)\b",
            r"\b(?:beleg|bon)-?nr\.?\b",
            r"\b(?:tse\s+transaktionsnummer|seriennr\.\s*kasse)\b",
            r"\b(?:mwst|ust)\b.{0,30}\b(?:netto|umsatz)\b",
            r"\b(?:visa|mastercard|girocard|bar|zahlung erfolgt)\b",
        )
    )
    has_date = bool(re.search(
        r"\b(?:datum\s*:?\s*)?\d{2}\.\d{2}\.(?:\d{2}|\d{4})\b", lower
    ))
    if receipt_signals < 3 or not has_date:
        return None

    def match_value(pattern, flags=re.IGNORECASE | re.MULTILINE):
        match = re.search(pattern, text, flags=flags)
        return match.group(1).strip() if match else None

    date = match_value(r"\bDatum\s*:?\s*(\d{2}\.\d{2}\.\d{4})\b")
    if not date:
        short_date = match_value(r"\bDatum\b[^\n\r]*?(\d{2}\.\d{2}\.\d{2})\b")
        if short_date:
            day, month, year = short_date.split(".")
            date = f"{day}.{month}.20{year}"
    amount = match_value(
        r"(?:^|\n)\s*(?:SUMME|GESAMT|ZU ZAHLEN)\s*(?:€|EUR)?\s*"
        r"([0-9]{1,3}(?:[. ][0-9]{3})*,[0-9]{2})\b"
    )
    if not amount:
        amount = match_value(
            r"(?:^|\n)\s*Betrag\s+EUR\s+"
            r"([0-9]{1,3}(?:[. ][0-9]{3})*,[0-9]{2})\b"
        )

    brand = None
    store_name = None
    vendor = None
    chain_patterns = (
        ("EDEKA", ("edeka",)),
        ("REWE", ("rewe",)),
        ("Lidl", ("lidl",)),
        ("ALDI", ("aldi",)),
        ("Kaufland", ("kaufland",)),
        ("PENNY", ("penny",)),
        ("Netto Marken-Discount", ("netto marken-discount",)),
        ("dm-drogerie markt", ("dm-drogerie", "dm.de")),
        ("ROSSMANN", ("rossmann",)),
    )
    for canonical, markers in chain_patterns:
        if any(marker in lower for marker in markers):
            brand = canonical
            break

    header_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()[:20]
        if line.strip()
    ]
    if brand == "EDEKA":
        market_line = next(
            (line for line in header_lines if re.search(r"\b(?:aktiv\s+markt|e[- ]?center)\b", line, re.I)),
            None,
        )
        store_name = market_line
        vendor = f"EDEKA {market_line}" if market_line else "EDEKA"
    elif brand:
        store_name = next(
            (line for line in header_lines if brand.casefold().split()[0] in line.casefold()),
            None,
        )
        vendor = store_name or brand
    else:
        store_name = next(
            (
                line for line in header_lines
                if not re.search(
                    r"(?:kassenbon|kundenbeleg|straße|str\.|\d{5}|tel\.|www\.|eur$)",
                    line,
                    re.I,
                )
            ),
            None,
        )
        vendor = store_name

    branch_number = match_value(
        r"Filiale\s+Pos\s+Bed\s+Bon\s*\n\s*"
        r"\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}\s+([0-9]{4,})"
    ) or match_value(r"\bFiliale\s*[:#-]\s*([A-Z0-9./-]+)")

    return {
        "date": date,
        "amount": amount,
        "currency": "EUR" if amount else None,
        "vendor": vendor,
        "brand": brand,
        "store_name": store_name,
        "receipt_number": match_value(r"\b(?:Beleg|Bon)-?Nr\.?\s*:?\s*([A-Z0-9./-]+)"),
        "branch_number": branch_number,
        "tse_transaction_number": match_value(
            r"\bTSE\s+Transaktionsnummer\s*:?\s*([A-Z0-9./-]+)"
        ),
        "invoice_number": None,
        "contract_number": None,
        "description": "Kassenbon",
        "document_kind": "Kassenbon",
    }
