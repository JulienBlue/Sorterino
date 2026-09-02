import re
from dataclasses import dataclass, field


@dataclass
class ProfileAssignment:
    profile_id: str
    person_ids: list = field(default_factory=list)
    confidence: float = 0.0
    matched_by: list = field(default_factory=list)


class ProfileMatcher:
    def __init__(self, profile_service, minimum_confidence=0.8):
        self.service = profile_service
        self.minimum_confidence = float(minimum_confidence or 0.8)

    @staticmethod
    def _normalize(value):
        return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())

    def match(self, text):
        text_lower = str(text or "").casefold()
        text_normalized = self._normalize(text)
        candidates = []
        for profile in self.service.list_profiles():
            score, reasons, people = self._score_profile(
                profile, text_lower, text_normalized
            )
            if score:
                candidates.append((score, profile, reasons, people))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        best = candidates[0]
        if best[0] < self.minimum_confidence:
            return None
        if len(candidates) > 1 and candidates[1][0] >= best[0] - 0.1:
            close_candidates = [
                candidate for candidate in candidates
                if candidate[0] >= best[0] - 0.1
            ]
            personal = [
                candidate for candidate in close_candidates
                if len(candidate[3]) == 1
                and "Personenname" in candidate[2]
                and (
                    "E-Mail-Adresse" in candidate[2]
                    or "Persönliche Kennung" in candidate[2]
                )
            ]
            weak_organization_reasons = {"Firmenname", "Profilstichwort"}
            mentioned_organizations = [
                candidate for candidate in close_candidates
                if candidate[1].get("type") == "organization"
                and not candidate[3]
                and set(candidate[2]).issubset(weak_organization_reasons)
            ]
            if (
                len(personal) != 1
                or len(mentioned_organizations) != len(close_candidates) - 1
            ):
                return None
            best = personal[0]
            best[2].append("Persönlicher Absender vor erwähnter Firma")
        return ProfileAssignment(
            profile_id=best[1]["id"],
            person_ids=best[3],
            confidence=min(1.0, best[0]),
            matched_by=best[2],
        )

    def match_document(self, text, filename):
        """Use an unambiguous filename only as fallback for ambiguous content."""
        combined = self.match(f"{text}\n{filename}")
        if combined:
            return combined
        filename_assignment = self.match(filename)
        if filename_assignment:
            filename_assignment.matched_by = list(dict.fromkeys([
                *filename_assignment.matched_by,
                "Eindeutiger Dateiname",
            ]))
        return filename_assignment

    def match_profile(self, profile_id, text, source_reason="Profilpostfach"):
        profile = self.service.get_profile(profile_id)
        if not profile:
            return None
        text_lower = str(text or "").casefold()
        score, reasons, people = self._score_profile(
            profile,
            text_lower,
            self._normalize(text),
        )
        return ProfileAssignment(
            profile_id=profile_id,
            person_ids=people,
            confidence=max(0.98, min(1.0, score)),
            matched_by=list(dict.fromkeys([source_reason, *reasons])),
        )

    def _score_profile(self, profile, text_lower, text_normalized):
        score = 0.0
        reasons = []
        person_ids = []
        matching = profile.get("matching", {}) or {}
        score += self._match_values(
            matching.get("name_variants", []), text_lower, 0.75, "Profilname", reasons
        )
        score += self._match_values(
            matching.get("customer_numbers", []), text_normalized, 1.0, "Kundennummer", reasons, normalize=True
        )
        score += self._match_values(
            matching.get("contract_numbers", []), text_normalized, 1.0, "Vertragsnummer", reasons, normalize=True
        )
        score += self._match_values(
            matching.get("keywords", []), text_lower, 0.45, "Profilstichwort", reasons
        )
        if any(value.casefold() in text_lower for value in matching.get("negative_keywords", []) if value):
            return 0.0, [], []

        profile_type = profile.get("type")
        if profile_type == "organization":
            names = [profile.get("display_name", "")]
            names.extend((profile.get("name", {}) or {}).get("trading_names", []))
            score += self._match_values(names, text_lower, 0.8, "Firmenname", reasons)
            registration = profile.get("registration", {}) or {}
            identifiers = [
                registration.get("vat_identification_number"),
                registration.get("business_identification_number"),
                registration.get("register_number"),
                registration.get("employer_number"),
            ] + registration.get("tax_numbers", [])
            score += self._match_values(identifiers, text_normalized, 1.0, "Firmenkennung", reasons, normalize=True)
            score += self._match_values(
                (profile.get("financial_identifiers", {}) or {}).get("ibans", []),
                text_normalized, 1.0, "IBAN", reasons, normalize=True
            )
            score += self._profile_contact_score(profile, text_lower, reasons)
            management = (profile.get("management", {}) or {}).get("managing_director", {}) or {}
            director_name = " ".join(filter(None, [
                management.get("first_name"), management.get("second_first_name"), management.get("last_name")
            ])).strip()
            score += self._match_values([director_name], text_lower, 0.45, "Geschäftsführung", reasons)
        elif profile_type == "family":
            household = profile.get("household_identifiers", {}) or {}
            score += self._match_values(
                household.get("tax_numbers", []),
                text_normalized,
                1.0,
                "Gemeinsame Steuernummer",
                reasons,
                normalize=True,
            )
            score += self._match_values(
                household.get("ibans", []), text_normalized, 1.0, "IBAN", reasons, normalize=True
            )
            score += self._profile_contact_score(profile, text_lower, reasons)

        members = self.service.profile_members(profile["id"])
        person_matches = []
        for person, membership in members:
            person_score, person_reasons = self._score_person(person, text_lower, text_normalized)
            if person_score:
                person_matches.append((person_score, person, membership, person_reasons))

        if person_matches:
            strongest = max(item[0] for item in person_matches)
            # Shared addresses alone can support the family context, but they
            # must not assign every household member to a personal document.
            selected = (
                [item for item in person_matches if item[0] >= strongest - 0.1]
                if strongest >= 0.8 else []
            )
            if selected:
                for person_score, person, membership, person_reasons in selected:
                    person_ids.append(person["id"])
                    score += min(person_score, 0.9)
                    reasons.extend(person_reasons)
                    if profile_type == "organization":
                        context_values = [membership.get("position"), membership.get("department")]
                        score += self._match_values(
                            context_values, text_lower, 0.15, "Firmenfunktion oder Abteilung", reasons
                        )
            else:
                score += min(strongest, 0.35)
        if profile_type == "family":
            people_by_id = {person["id"]: person for person, _membership in members}
            for relationship in profile.get("partner_relationships", []):
                partners = [people_by_id.get(person_id) for person_id in relationship.get("person_ids", [])]
                if len(partners) != 2 or not all(partners):
                    continue
                if all(self._person_name_present(person, text_lower) for person in partners):
                    score += 0.35
                    reasons.append("Verknüpfte Ehe-/Lebenspartner")
                    person_ids.extend(person["id"] for person in partners)
        return min(score, 1.5), list(dict.fromkeys(reasons)), list(dict.fromkeys(person_ids))

    def _profile_contact_score(self, profile, text_lower, reasons):
        score = 0.0
        contacts = profile.get("contacts", {}) or {}
        emails = [item.get("value") for item in contacts.get("emails", [])]
        score += self._match_values(emails, text_lower, 0.85, "Profil-E-Mail-Adresse", reasons)
        phones = [item.get("value") for item in contacts.get("phones", [])]
        score += self._match_values(
            phones, self._normalize(text_lower), 0.45, "Profil-Telefonnummer", reasons, normalize=True
        )
        address = profile.get("address", {}) or {}
        street = " ".join(filter(None, [address.get("street"), address.get("house_number")])).strip()
        postal_city = " ".join(filter(None, [address.get("postal_code"), address.get("city")])).strip()
        if street and postal_city and street.casefold() in text_lower and postal_city.casefold() in text_lower:
            score += 0.35
            reasons.append("Profilanschrift")
        return score

    def _person_name_present(self, person, text_lower):
        matching = person.get("matching", {}) or {}
        names = [person.get("display_name", ""), *matching.get("name_variants", [])]
        return bool(
            self._match_values(names, text_lower, 1.0, "", [])
            or self._match_name_tokens(names, text_lower)
        )

    def _score_person(self, person, text_lower, text_normalized):
        reasons = []
        matching = person.get("matching", {}) or {}
        names = list(matching.get("name_variants", []))
        if person.get("display_name"):
            names.append(person["display_name"])
        person_name = person.get("name", {}) or {}
        names.extend(person_name.get("previous_names", []))
        birth_name = person_name.get("birth_name")
        first_name = person_name.get("first_name")
        if birth_name and first_name:
            names.append(f"{first_name} {birth_name}")
        score = self._match_values(names, text_lower, 0.8, "Personenname", reasons)
        if not score and self._match_name_tokens(names, text_lower):
            # Formulare drucken Nach- und Vornamen oft in getrennten Feldern,
            # z. B. "Name: Hirte  Vorname: Julien Blue". Alle Bestandteile
            # müssen dafür eng beieinanderstehen; der bloße Familienname reicht
            # ausdrücklich nicht aus.
            score = 0.8
            reasons.append("Personenname in Formularfeldern")
        contacts = person.get("contacts", {}) or {}
        emails = [item.get("value") for item in contacts.get("emails", [])]
        score += self._match_values(emails, text_lower, 1.0, "E-Mail-Adresse", reasons)
        identifiers = person.get("identifiers", {}) or {}
        strong_values = [
            identifiers.get("tax_identification_number"),
            identifiers.get("health_insurance_number"),
            identifiers.get("social_security_number"),
            identifiers.get("pension_insurance_number"),
            identifiers.get("family_benefits_number"),
        ]
        strong_values.extend(identifiers.get("tax_numbers", []))
        strong_values.extend(identifiers.get("student_or_pupil_numbers", []))
        strong_values.extend(identifiers.get("ibans", []))
        score += self._match_values(strong_values, text_normalized, 1.0, "Persönliche Kennung", reasons, normalize=True)
        score += self._match_values(matching.get("customer_numbers", []), text_normalized, 1.0, "Kundennummer", reasons, normalize=True)
        score += self._match_values(matching.get("contract_numbers", []), text_normalized, 1.0, "Vertragsnummer", reasons, normalize=True)
        score += self._match_values(matching.get("keywords", []), text_lower, 0.4, "Personenstichwort", reasons)
        address = person.get("address", {}) or {}
        street = " ".join(filter(None, [address.get("street"), address.get("house_number")])).strip()
        postal_city = " ".join(filter(None, [address.get("postal_code"), address.get("city")])).strip()
        if street and postal_city and street.casefold() in text_lower and postal_city.casefold() in text_lower:
            score += 0.35
            reasons.append("Anschrift")
        if any(value.casefold() in text_lower for value in matching.get("negative_keywords", []) if value):
            return 0.0, []
        return min(score, 1.25), list(dict.fromkeys(reasons))

    @staticmethod
    def _match_name_tokens(names, text, maximum_span=120):
        for name in names or []:
            tokens = [
                token.casefold()
                for token in re.findall(r"[^\W_]+", str(name or ""), re.UNICODE)
                if len(token) >= 2
            ]
            if len(tokens) < 2:
                continue

            occurrences = []
            for token_index, token in enumerate(tokens):
                matches = list(re.finditer(rf"(?<!\w){re.escape(token)}(?!\w)", text))
                if not matches:
                    break
                occurrences.extend((match.start(), token_index) for match in matches)
            else:
                # OCR and complex layouts may print a name decoratively first
                # and normally again in the signature. Search every occurrence
                # instead of comparing only the first hit of each token.
                occurrences.sort()
                counts = [0] * len(tokens)
                covered = 0
                left = 0
                for right, (position, token_index) in enumerate(occurrences):
                    if counts[token_index] == 0:
                        covered += 1
                    counts[token_index] += 1
                    while covered == len(tokens):
                        left_position, left_token = occurrences[left]
                        if position - left_position <= maximum_span:
                            return True
                        counts[left_token] -= 1
                        if counts[left_token] == 0:
                            covered -= 1
                        left += 1
        return False

    def _match_values(self, values, haystack, weight, reason, reasons, normalize=False):
        for value in values or []:
            needle = self._normalize(value) if normalize else str(value or "").strip().casefold()
            if len(needle) >= 3 and needle in haystack:
                reasons.append(reason)
                return weight
        return 0.0
