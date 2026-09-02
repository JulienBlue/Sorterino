import re


class IdentifierFormatError(ValueError):
    pass


def _compact(value):
    return re.sub(r"[\s./-]+", "", str(value or "")).upper()


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def tax_id(value):
    number = _digits(value)
    if not number:
        return ""
    if len(number) != 11:
        raise IdentifierFormatError("Die Steuer-ID muss aus 11 Ziffern bestehen.")
    product = 10
    for digit in map(int, number[:10]):
        total = (digit + product) % 10 or 10
        product = (2 * total) % 11
    check = 11 - product
    check = 0 if check == 10 else check
    if check != int(number[-1]):
        raise IdentifierFormatError("Die Prüfziffer der Steuer-ID ist ungültig.")
    return number


def tax_number(value):
    number = _digits(value)
    if not number:
        return ""
    if len(number) not in {10, 11, 13}:
        raise IdentifierFormatError("Eine Steuernummer muss 10, 11 oder im ELSTER-Format 13 Ziffern haben.")
    if len(number) == 13 and number[4] != "0":
        raise IdentifierFormatError("Bei einer 13-stelligen ELSTER-Steuernummer muss die fünfte Stelle 0 sein.")
    return number


def pension_number(value):
    number = _compact(value)
    if not number:
        return ""
    if not re.fullmatch(r"\d{8}[A-Z]\d{3}", number):
        raise IdentifierFormatError("Die Rentenversicherungsnummer muss 12 Stellen haben, z. B. 12 170839 J 008.")
    letter = str(ord(number[8]) - 64).zfill(2)
    checksum_input = number[:8] + letter + number[9:11]
    weights = (2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1)
    checksum = sum(sum(map(int, str(int(digit) * weight))) for digit, weight in zip(checksum_input, weights)) % 10
    if checksum != int(number[-1]):
        raise IdentifierFormatError("Die Prüfziffer der Rentenversicherungsnummer ist ungültig.")
    return number


def health_insurance_number(value):
    number = _compact(value)
    if number and not re.fullmatch(r"[A-Z]\d{9}", number):
        raise IdentifierFormatError("Die Krankenversichertennummer muss aus einem Buchstaben und 9 Ziffern bestehen.")
    return number


def family_benefits_number(value):
    number = _compact(value)
    if number and not re.fullmatch(r"\d{3}FK\d{6}", number):
        raise IdentifierFormatError("Die Kindergeldnummer muss dem Format 123FK123456 entsprechen.")
    return number


def vat_id(value):
    number = _compact(value)
    if not number:
        return ""
    if number.startswith("DE") and not re.fullmatch(r"DE\d{9}", number):
        raise IdentifierFormatError("Eine deutsche Umsatzsteuer-ID muss aus DE und 9 Ziffern bestehen.")
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{2,12}", number):
        raise IdentifierFormatError("Die Umsatzsteuer-ID hat kein gültiges Format.")
    return number


def business_id(value):
    number = _compact(value)
    if not number:
        return ""
    match = re.fullmatch(r"DE(\d{9})(\d{5})?", number)
    if not match:
        raise IdentifierFormatError("Die Wirtschafts-ID muss dem Format DE123456789-00001 entsprechen.")
    return f"DE{match.group(1)}" + (f"-{match.group(2)}" if match.group(2) else "")


def employer_number(value):
    number = _digits(value)
    if number and len(number) != 8:
        raise IdentifierFormatError("Die Betriebsnummer muss aus 8 Ziffern bestehen.")
    return number


def creditor_id(value):
    number = _compact(value)
    if not number:
        return ""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{3}[A-Z0-9]{1,28}", number) or len(number) > 35:
        raise IdentifierFormatError("Die Gläubiger-ID hat kein gültiges SEPA-Format.")
    if number.startswith("DE") and len(number) != 18:
        raise IdentifierFormatError("Eine deutsche Gläubiger-ID muss 18 Stellen haben.")
    check_value = number[:4] + "000" + number[7:]
    rearranged = check_value[4:] + check_value[:4]
    numeric = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    if int(numeric) % 97 != 1:
        raise IdentifierFormatError("Die Prüfziffer der Gläubiger-ID ist ungültig.")
    return number


def eori(value):
    number = _compact(value)
    if not number:
        return ""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{1,15}", number):
        raise IdentifierFormatError("Die EORI-Nummer hat kein gültiges Format.")
    if number.startswith("DE") and len(number) != 17:
        raise IdentifierFormatError("Eine deutsche EORI-Nummer muss aus DE und 15 weiteren Zeichen bestehen.")
    return number


def generic(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


NORMALIZERS = {
    "tax_identification_number": tax_id,
    "tax_numbers": tax_number,
    "pension_insurance_number": pension_number,
    "social_security_number": pension_number,
    "health_insurance_number": health_insurance_number,
    "family_benefits_number": family_benefits_number,
    "student_or_pupil_numbers": generic,
    "vat_identification_number": vat_id,
    "business_identification_number": business_id,
    "employer_number": employer_number,
    "creditor_identification_number": creditor_id,
    "eori_number": eori,
    "register_number": generic,
    "professional_association_number": generic,
    "chamber_membership_number": generic,
}
