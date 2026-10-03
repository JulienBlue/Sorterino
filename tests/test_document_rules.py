import json
import unittest
from pathlib import Path

from src.document_analyzer import DocumentAnalyzer
from src.models import Document
from src.storage_utils import StoragePathBuilder


class _Logger:
    def debug(self, *_args):
        pass

    def warning(self, *_args):
        pass


class DocumentRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.rules = json.loads(
            (root / "assets" / "templates" / "template.rules.json").read_text(encoding="utf-8")
        )
        cls.structures = json.loads(
            (root / "assets" / "templates" / "template.structure.json").read_text(encoding="utf-8")
        )["templates"]

    def analyze(self, text, filename="Dokument.pdf"):
        document = Document(source_path=filename)
        document.mark_analyzed(text)
        classification, metadata, data = DocumentAnalyzer(
            self.rules, {}, _Logger()
        ).analyze(document)
        document.metadata = metadata
        document.extracted_data = data
        return document, classification

    def test_classifies_high_signal_private_documents(self):
        cases = [
            (
                "Einkommensteuerbescheid 2025 Finanzamt Steuernummer Rechtsbehelfsbelehrung",
                "Finanzamt und Steuern", "Einkommensteuer",
            ),
            (
                "Kontoauszug IBAN Buchungstag Wertstellung alter Kontostand neuer Kontostand",
                "Finanzen", "Kontoauszüge",
            ),
            (
                "Versicherungsschein Versicherungsnummer Versicherungsnehmer Versicherungsbeginn",
                "Versicherungen", "Versicherungspolicen",
            ),
            (
                "Arztbrief Patient Diagnose Befund Therapie",
                "Gesundheit", "Arztberichte und Befunde",
            ),
            (
                "Betriebskostenabrechnung Abrechnungszeitraum Heizkosten Vorauszahlungen",
                "Wohnen", "Nebenkostenabrechnungen",
            ),
        ]
        for text, category, document_type in cases:
            with self.subTest(document_type=document_type):
                _document, classification = self.analyze(text)
                self.assertEqual(classification.category, category)
                self.assertEqual(classification.document_type, document_type)
                self.assertGreaterEqual(classification.confidence, 0.8)

    def test_single_generic_word_does_not_classify(self):
        _document, classification = self.analyze("Informationen zu Ihrem Vertrag")
        self.assertEqual(classification.category, "MANUELL")

    def test_classifies_review_run_special_documents_without_false_metadata(self):
        cases = [
            (
                "Kuendigung Debeka HR_Hirte_Sabine.pdf",
                "Hiermit kündige ich den Vertrag zum nächstmöglichen Zeitpunkt. Debeka",
                "Versicherungen", "Kündigungen", "Hausratversicherung",
            ),
            (
                "Beratungsvertrag_systemische-Einzelberatung_Julien_260706.pdf",
                "Beratungsvertrag zwischen Auftraggeber und Berater für systemische Beratung",
                "Verträge und Abonnements", "Allgemeine Verträge", None,
            ),
            (
                "Rückbildungskurs - Teilnahmebescheinigung.pdf",
                "Teilnahmebescheinigung Rückbildungskurs am 29.07.2026",
                "Gesundheit", "Kurse und Therapien", None,
            ),
            (
                "Renteninformation 2026 - Julien_20260802_0001.pdf",
                "Deutsche Rentenversicherung Renteninformation. Bitte Personalausweis bereithalten.",
                "Rentenversicherung", "Renteninformation", None,
            ),
        ]
        for filename, text, category, document_type, insurance_type in cases:
            with self.subTest(filename=filename):
                document, classification = self.analyze(text, filename)
                self.assertEqual(classification.category, category)
                self.assertEqual(classification.document_type, document_type)
                self.assertIsNone(document.extracted_data.get("amount"))
                if insurance_type:
                    self.assertEqual(document.extracted_data["insurance_type"], insurance_type)

        rent_document, _classification = self.analyze(
            "Deutsche Rentenversicherung Renteninformation. Bitte Personalausweis bereithalten.",
            "Renteninformation 2026 - Julien_20260802_0001.pdf",
        )
        self.assertEqual(rent_document.extracted_data["date"], "02.08.2026")
        target = StoragePathBuilder(self.structures["adult"]).build(rent_document)
        self.assertEqual(target.parent, Path("Rentenversicherung", "Renteninformation"))
        self.assertEqual(target.name, "Renteninformation 2026.pdf")

    def test_debeka_policy_keeps_type_provider_and_contract_number(self):
        document, classification = self.analyze(
            "Versicherungsschein Debeka Allgemeine Versicherung AG Versicherungsnummer Versicherungsnehmer Versicherungsbeginn",
            "Tierhaftpflicht 22129575.7 - 22.02.2021 - 01.01.2023.pdf",
        )
        self.assertEqual(classification.document_type, "Versicherungspolicen")
        self.assertEqual(document.extracted_data["insurance_type"], "Tierhalterhaftpflichtversicherung")
        self.assertEqual(document.extracted_data["contract_number"], "22129575.7")
        self.assertEqual(document.extracted_data["vendor"], "Debeka Allgemeine Versicherung AG")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target.name,
            "2021-02-22 - Tierhalterhaftpflichtversicherung - Debeka Allgemeine Versicherung AG - 22129575.7.pdf",
        )

    def test_gothaer_accident_policy_prefers_labelled_contract_over_phone(self):
        text = """
Versicherungsschein Privat Kompakt Gothaer
Unfallversicherung
Swiss Life Select Deutschland GmbH
Telefon 0511 123242526
Versicherungsnehmer Sabine Hirte
Versicherungsnummer 95.007.078627 - 59.100 - PGP
Vertragslaufzeit Beginn: 06.08.2026 00:00 Uhr
Datum Ausgefertigt am 05.08.2026 um 18:03 Uhr
Gothaer Allgemeine Versicherung AG
"""

        document, classification = self.analyze(text, "Unfall_20260812_0001.pdf")

        self.assertEqual(classification.document_type, "Versicherungspolicen")
        self.assertEqual(document.extracted_data["insurance_type"], "Unfallversicherung")
        self.assertEqual(
            document.extracted_data["vendor"],
            "Gothaer Allgemeine Versicherung AG",
        )
        self.assertEqual(document.extracted_data["contract_number"], "95.007.078627")
        self.assertEqual(document.extracted_data["date"], "05.08.2026")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target.name,
            "2026-08-05 - Unfallversicherung - Gothaer Allgemeine Versicherung AG "
            "- 95.007.078627.pdf",
        )

    def test_classifies_long_insurance_offer_without_treating_premium_as_invoice(self):
        text = """
Barmenia EINFACH. MENSCHLICH.
Ihre Vertragsnummer (bitte stets angeben): Ihre Kundennummer: Datum:
120747528 913426340 08.08.2026
Angebot für eine Tierhalterhaftpflichtversicherung
- Verbindliches Angebot
- Versicherungsbedingungen zur Tierhalterhaftpflichtversicherung
Angebots-Nr. 120747528
Ausstellungsdatum/-grund 08.08.2026 Neuvertrag
Barmenia Allgemeine Versicherungs-AG
Bruttoprämie gemäß Zahlungsperiode 4,80 EUR
Wichtiger Hinweis: An dieses Angebot halten wir uns bis zum 05.09.26 gebunden.
"""

        document, classification = self.analyze(text, "vollstaendiges_angebot.pdf")

        self.assertEqual(classification.category, "Versicherungen")
        self.assertEqual(classification.document_type, "Versicherungsangebote")
        self.assertEqual(classification.confidence, 0.99)
        self.assertEqual(
            document.extracted_data["insurance_type"],
            "Tierhalterhaftpflichtversicherung",
        )
        self.assertEqual(
            document.extracted_data["vendor"],
            "Barmenia Allgemeine Versicherungs-AG",
        )
        self.assertEqual(document.extracted_data["contract_number"], "120747528")
        self.assertEqual(document.extracted_data["date"], "08.08.2026")
        self.assertIsNone(document.extracted_data["amount"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Versicherungen",
                "Versicherungsangebote",
                "2026",
                "2026-08-08 - Tierhalterhaftpflichtversicherung - Angebot "
                "- Barmenia Allgemeine Versicherungs-AG - 120747528.pdf",
            ),
        )

    def test_classifies_policy_cover_letter_as_correspondence_not_policy(self):
        text = """
Gothaer Allgemeine Versicherung AG
Versicherungsschein zu Ihrer Privat Kompakt Unfallversicherung
Versicherungsnummer 95.007.078627 - 59.100 - PGP 05.08.2026
Sehr geehrte Frau Hirte,
Sie haben sich für die Privat Kompakt Unfallversicherung entschieden.
Anbei erhalten Sie Ihren Versicherungsschein.
Widerrufsbelehrung
Versicherungsschein Privat Kompakt Unfallversicherung Seite 3 von 4
"""

        document, classification = self.analyze(
            text,
            "Unfall Anschreiben_20260812_0001.pdf",
        )

        self.assertEqual(classification.category, "Versicherungen")
        self.assertEqual(classification.document_type, "Versicherungsschreiben")
        self.assertEqual(
            document.extracted_data["document_kind"],
            "Begleitschreiben zum Versicherungsschein",
        )
        self.assertEqual(document.extracted_data["date"], "05.08.2026")
        self.assertEqual(
            document.extracted_data["insurance_type"],
            "Unfallversicherung",
        )
        self.assertEqual(document.extracted_data["contract_number"], "95.007.078627")
        self.assertEqual(
            document.extracted_data["vendor"],
            "Gothaer Allgemeine Versicherung AG",
        )
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Versicherungen",
                "Versicherungsschreiben",
                "2026",
                "2026-08-05 - Begleitschreiben - Unfallversicherung "
                "- Gothaer Allgemeine Versicherung AG - 95.007.078627.pdf",
            ),
        )

    def test_policy_does_not_mistake_date_fragment_for_amount(self):
        document, classification = self.analyze(
            "22.02.2021 22,02 EUR Versicherungsschein Debeka Allgemeine Versicherung AG Versicherungsnummer Versicherungsnehmer Versicherungsbeginn",
            "Tierhaftpflicht 22129575.7 - 22.02.2021 - 01.01.2023.pdf",
        )
        self.assertEqual(classification.document_type, "Versicherungspolicen")
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])

    def test_classifies_and_names_temporary_assignment_sheet(self):
        text = """
WIRMED GmbH Niederlassung Dortmund
Einsatzbegleitschein (Einsatz als Leiharbeitnehmer)
für Frau Sabine Schirmer
Beruf/Qualifikation: Altenpflege ex. 3 jährig
Kunden Nr. 8050306 Auftrag Nr. 80550116 Datum: 01.12.2021
bei Kunde: St. Josef Haus Seniorenzentrum
Einsatzort: Wohnbereich
Anmeldung bei Herrn Möncks am: Samstag, 01.01.2022
persönliche Schutzausrüstung stellt Entleiher Verleiher
Die monatliche Arbeitszeit im Rahmen des Auftrags beträgt 120,00 Stunden.
"""
        document, classification = self.analyze(text, "EBS 2022_01.pdf")
        self.assertEqual(classification.document_type, "Einsatzunterlagen")
        self.assertEqual(document.extracted_data["document_kind"], "Einsatzbegleitschein")
        self.assertEqual(document.extracted_data["employer"], "WIRMED GmbH")
        self.assertEqual(document.extracted_data["client"], "St. Josef Haus Seniorenzentrum")
        self.assertEqual(document.extracted_data["assignment_number"], "80550116")
        self.assertEqual(document.extracted_data["assignment_start"], "01.01.2022")
        self.assertEqual(document.extracted_data["monthly_hours"], "120,00")
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])
        self.assertIsNone(document.extracted_data["vendor"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[:3], ("Arbeit und Karriere", "Einsatzunterlagen", "2022"))
        self.assertEqual(
            target.name,
            "2022-01-01 - Einsatzbegleitschein - WIRMED GmbH - St. Josef Haus Seniorenzentrum - Auftrag 80550116.pdf",
        )

    def test_assignment_sheet_cleans_known_truncated_client_name(self):
        text = """
WIRMED GmbH
Einsatzbegleitschein (Einsatz als Leiharbeitnehmer)
bei Kunde: Caritas-Seniorenzentrum Pulhei
Auftrag Nr. 80650060
Einsatzbeginn: 01.09.2021
"""

        document, classification = self.analyze(text, "EBS 2021_09.pdf")

        self.assertEqual(classification.document_type, "Einsatzunterlagen")
        self.assertEqual(
            document.extracted_data["client"],
            "Caritas-Seniorenzentrum Pulheim",
        )
        self.assertIsNone(document.extracted_data["vendor"])

    def test_classifies_deferment_financial_statement(self):
        text = """
Aufstellung der zur Entscheidung über eine Stundung nach § 59 Abs. 1
Satz 1 Nr. 1 Bundeshaushaltsordnung (BHO) benötigten Angaben
Name, Vorname
Hirte, Julien Blue
Geschäftszeichen
IV- 05 2 84 517 6/06
1. Höhe meines Einkommens der letzten drei Monate
2. Aufstellung über mein Vermögen
3. Aufstellung über meine laufenden monatlichen Ausgaben
"""

        document, classification = self.analyze(
            text,
            "Aufstellung nach § 59 - Hirte 1-2.pdf",
        )

        self.assertEqual(classification.category, "Behörden und Leistungen")
        self.assertEqual(classification.document_type, "Sonstige Bescheide")
        self.assertEqual(
            document.extracted_data["document_kind"],
            "Vermögensauskunft zur Stundung",
        )
        self.assertEqual(
            document.extracted_data["processing_reference"],
            "IV- 05 2 84 517 6/06",
        )
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])
        self.assertIsNone(document.extracted_data["vendor"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Behörden und Leistungen",
                "Sonstige Bescheide",
                "Vermögensauskunft zur Stundung.pdf",
            ),
        )

    def test_classifies_bafog_income_assessment_without_tax_false_positive(self):
        text = """
Einkommensermittlung
nach § 18a BAföG
Mein Geschäftszeichen im Bundesverwaltungsamt
IV 01 - 76/1016
Darlehensnehmer
Name: Hirte, Julien Blue
Zeitraum 30.08.2024 - 31.01.2025
Arbeitslosengeld 1237,60 EUR
"""

        document, classification = self.analyze(
            text,
            "Einkommensermittlung nach § 18a - Hirte, Julien Blue.pdf",
        )

        self.assertEqual(classification.category, "Behörden und Leistungen")
        self.assertEqual(classification.document_type, "Formulare")
        self.assertEqual(
            document.extracted_data["document_kind"],
            "Einkommensermittlung nach § 18a BAföG",
        )
        self.assertEqual(document.extracted_data["date"], "30.08.2024")
        self.assertEqual(document.extracted_data["income_period_end"], "31.01.2025")
        self.assertEqual(document.extracted_data["vendor"], "Bundesverwaltungsamt")
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Behörden und Leistungen",
                "Formulare",
                "2024",
                "2024-08-30 - Einkommensermittlung nach § 18a BAföG "
                "- Bundesverwaltungsamt.pdf",
            ),
        )

    def test_repairs_ocr_damaged_bafog_income_period(self):
        text = """
Einkommensermittlung nach § 18a BAföG
Mein Geschäftszeichen im Bundesverwaltungsamt
Ehegattin/Ehegatte
Ich habe monatliche Einkünfte/Einnahmen
(bitte für den Zeitraum der letzten vier Monate angeben)
01.112094 -- 01.02.2025
"""

        document, classification = self.analyze(
            text,
            "Einkommensermittlung nach § 18a - Hirte, Sabine.pdf",
        )

        self.assertEqual(classification.document_type, "Formulare")
        self.assertEqual(document.extracted_data["date"], "01.11.2024")
        self.assertEqual(
            document.extracted_data["income_period_start"],
            "01.11.2024",
        )
        self.assertEqual(
            document.extracted_data["income_period_end"],
            "01.02.2025",
        )
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[:3], ("Behörden und Leistungen", "Formulare", "2024"))
        self.assertEqual(
            target.name,
            "2024-11-01 - Einkommensermittlung nach § 18a BAföG "
            "- Bundesverwaltungsamt.pdf",
        )

    def test_classifies_medical_discharge_letter_and_uses_discharge_date(self):
        text = """
KRANKENHAUS PORZ AM RHEIN gGmbH
VORLÄUFIGES DOKUMENT
Sehr geehrte Kolleginnen und Kollegen,
wir berichten über die Patientin Sabine Hirte, geb. 17.11.1986, die sich
vom 28.02.2026 bis 03.03.2026 bei
uns in Behandlung befand.
Patientendaten Anamnese Maternales Labor
stationärer Aufenthalt
Entlassuntersuchung
Empfehlungen / Procedere
Hirte Henri Mika, Lebendgeburt, Geschlecht männlich.
"""

        document, classification = self.analyze(text, "Entlassungsbrief.pdf")

        self.assertEqual(classification.category, "Gesundheit")
        self.assertEqual(classification.document_type, "Arztberichte und Befunde")
        self.assertEqual(document.extracted_data["document_kind"], "Entlassungsbrief")
        self.assertEqual(document.extracted_data["date"], "03.03.2026")
        self.assertEqual(document.extracted_data["treatment_start"], "28.02.2026")
        self.assertEqual(document.extracted_data["treatment_end"], "03.03.2026")
        self.assertEqual(document.extracted_data["vendor"], "Krankenhaus Porz am Rhein")
        self.assertIsNone(document.extracted_data["amount"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Gesundheit",
                "Arztberichte und Befunde",
                "2026",
                "2026-03-03 - Entlassungsbrief - Krankenhaus Porz am Rhein.pdf",
            ),
        )

    def test_classifies_insurance_contribution_invoice_from_specific_fields(self):
        text = """
Gothaer Allgemeine Versicherung AG
Beitragsrechnung zu Ihrer Privat Kompakt
Versicherungsnummer 95.007.078627 - 59.100 PGP
Aktenzeichen 477219234 06.08.2026
Vereinbarungsgemäß buchen wir den Betrag in Höhe von 7,34 Euro ab.
Beitragsrechnung:
Versicherungen Erhebungszeitraum Beitrag Vers.Steuer Gesamt
Unfall neu 06.08.2026 - 06.09.2026 6,17 1,17 7,34
Beitrag, fällig zum 06.08.2026 7,34
Besteht für Sie bei uns eine Tierhalterhaftpflichtversicherung?
RunID_Print: 1619484
"""

        document, classification = self.analyze(
            text,
            "Beitragsrechnung_20260812_0001.pdf",
        )

        self.assertEqual(classification.category, "Versicherungen")
        self.assertEqual(classification.document_type, "Versicherungsschreiben")
        self.assertEqual(document.extracted_data["document_kind"], "Beitragsrechnung")
        self.assertEqual(document.extracted_data["date"], "06.08.2026")
        self.assertEqual(document.extracted_data["amount"], "7,34")
        self.assertEqual(document.extracted_data["currency"], "EUR")
        self.assertEqual(
            document.extracted_data["vendor"],
            "Gothaer Allgemeine Versicherung AG",
        )
        self.assertEqual(
            document.extracted_data["contract_number"],
            "95.007.078627",
        )
        self.assertEqual(
            document.extracted_data["insurance_type"],
            "Unfallversicherung",
        )
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target,
            Path(
                "Versicherungen",
                "Versicherungsschreiben",
                "2026",
                "2026-08-06 - Beitragsrechnung - Gothaer Allgemeine Versicherung AG "
                "- 95.007.078627 - 7,34.pdf",
            ),
        )

    def test_terminations_use_their_respective_topic_folder(self):
        cases = [
            (
                "Hiermit kündige ich meinen Arbeitsvertrag beim Arbeitgeber.",
                "Arbeit und Karriere",
            ),
            (
                "Hiermit kündige ich den Mietvertrag. Vermieter und Mieter bestätigen den Zugang.",
                "Wohnen",
            ),
            (
                "Hiermit kündige ich den Vertrag mit der Vertragsnummer AB-4711.",
                "Verträge und Abonnements",
            ),
            (
                "Hiermit kündige ich meine Versicherung. Versicherungsnummer 123456.",
                "Versicherungen",
            ),
        ]
        for text, category in cases:
            with self.subTest(category=category):
                document, classification = self.analyze(text, "Kündigung.pdf")
                self.assertEqual(classification.category, category)
                self.assertEqual(classification.document_type, "Kündigungen")
                target = StoragePathBuilder(self.structures["adult"]).build(document)
                self.assertEqual(target.parts[:2], (category, "Kündigungen"))

    def test_contract_clauses_do_not_turn_documents_into_terminations(self):
        advisory, classification = self.analyze(
            "Beratungsvertrag zwischen Auftraggeber und Berater. Die Kündigung des Vertrages ist mit einer Frist möglich.",
            "Beratungsvertrag_systemische-Einzelberatung_Julien_260706.pdf",
        )
        self.assertEqual(classification.document_type, "Allgemeine Verträge")
        self.assertEqual(advisory.extracted_data["document_kind"], "Beratungsvertrag")

        policy, classification = self.analyze(
            "Versicherungsschein Debeka Allgemeine Versicherung AG Versicherungsnummer Versicherungsnehmer Versicherungsbeginn Kündigung Kündigungsfrist",
            "Hausrat 31103865.6 - 01.11.2017 - 01.01.2019.pdf",
        )
        self.assertEqual(classification.document_type, "Versicherungspolicen")
        self.assertEqual(policy.extracted_data["insurance_type"], "Hausratversicherung")

    def test_termination_filename_names_subject_provider_and_contract(self):
        document, classification = self.analyze(
            "Hiermit kündige ich meine Hausratversicherung bei der Debeka. Vertragsnummer 31103865.6",
            "Kuendigung Debeka HR_Hirte_Sabine.pdf",
        )
        self.assertEqual(classification.document_type, "Kündigungen")
        self.assertEqual(document.extracted_data["termination_subject"], "Hausratversicherung")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertIn("Kündigung - Hausratversicherung - Debeka", target.name)

    def test_structure_and_filename_use_classified_destination(self):
        document, classification = self.analyze(
            "Bescheid für 2026 über Einkommensteuer vom 09.08.2026 "
            "Finanzamt Steuernummer Rechtsbehelfsbelehrung"
        )
        self.assertEqual(classification.document_type, "Einkommensteuer")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[:5], ("Finanzamt und Steuern", "Einkommensteuer", "2026", "Steuerbescheide", "Einkommensteuerbescheid 2026.pdf"))
        self.assertIn("Einkommensteuerbescheid", target.name)

    def test_tax_notice_prefers_labeled_tax_year_over_earlier_reference_year(self):
        text = """
17 3C5D AF70 BB 2003 AE72
Bescheid für 2024 über Einkommensteuer, Solidaritätszuschlag
Steuernummer 216/2232/4020
vom 09.02.2026
Rechtsbehelfsbelehrung
"""
        document, classification = self.analyze(
            text, "Hirte - Einkommenssteuerbescheid 2024.pdf"
        )
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["tax_year"], "2024")
        target = StoragePathBuilder(self.structures["family"]).build(document)
        self.assertEqual(target.parts[2:4], ("2024", "Steuerbescheide"))
        self.assertEqual(target.name, "Einkommensteuerbescheid 2024.pdf")

    def test_classifies_police_report_as_legal_correspondence(self):
        text = """
Polizeipräsidium Köln
Aktenzeichen (Vorgangskennung des Hauptvorgangs)
260915-1851-IP6033
Bescheinigung über die Erstattung einer Anzeige
Anzeigenerstattung durch
Straftat(en)/Verletzte Bestimmung(en), kriminologische Bezeichnung
Einfacher Diebstahl an Kraftfahrzeugen (§ 242 StGB)
Ereignisort/ -zeit
Dienstag, 15.09.2026, 14:00 Uhr
Köln, 15.09.2026
"""
        document, classification = self.analyze(text, "Anzeigenbescheinigung_Haerlin.pdf")
        self.assertEqual(classification.category, "Rechtliches und Vorsorge")
        self.assertEqual(classification.document_type, "Rechtliche Korrespondenz")
        self.assertEqual(document.extracted_data["date"], "15.09.2026")
        self.assertEqual(document.extracted_data["document_kind"], "Anzeigenbescheinigung")
        self.assertIsNone(document.extracted_data["amount"])
        target = StoragePathBuilder(self.structures["family"]).build(document)
        self.assertIn("Anzeigenbescheinigung - Polizeipräsidium Köln", target.name)

    def test_classifies_recruitment_forms_as_application_documents(self):
        text = """
Bundesamt für Verfassungsschutz
Antrag auf Reisekostenzuschuss für Vorstellungsreisen
Einladende Organisationseinheit gemäß Einladungsschreiben
Beginn der Vorstellung
Bitte alle Arbeitgeber im öffentlichen Dienst angeben
"""
        document, classification = self.analyze(
            text, "2. Anlage InTelligenecDay 2026 Köln.pdf"
        )
        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(classification.document_type, "Bewerbungen")
        self.assertEqual(document.extracted_data["document_kind"], "Bewerbungsunterlagen")
        self.assertIsNone(document.extracted_data["amount"])
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertIn("Bewerbungsunterlagen - Bundesamt für Verfassungsschutz", target.name)

    def test_invitation_to_selection_event_wins_over_mentioned_identity_document(self):
        text = """
Bundesamt für Verfassungsschutz, Köln, 25.09.2026
Betreff: Deine Teilnahme am InTelligenceDay am 10. Oktober 2026
Lieber Julien Blue, wir freuen uns darauf, Dich persönlich kennenzulernen.
Auswahlgespräch mit der Personalgewinnung und Fachgespräch an den Fachständen.
Bitte bringe einen gültigen Personalausweis oder Reisepass mit.
Damit wir Deine Bewerbung weiter berücksichtigen können.
"""
        document, classification = self.analyze(text, "Hirte, Julien Blue.pdf")

        self.assertEqual(classification.category, "Arbeit und Karriere")
        self.assertEqual(
            classification.document_type, "Einladungen und Auswahlverfahren"
        )
        self.assertEqual(
            document.extracted_data["document_kind"],
            "Einladung zum Auswahlverfahren",
        )
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[0:2], (
            "Arbeit und Karriere", "Einladungen und Auswahlverfahren"
        ))
        self.assertIn("Einladung zum Auswahlverfahren", target.name)

    def test_extracts_labeled_contract_reference(self):
        document, classification = self.analyze(
            "Vertragsbestätigung Vertragsnummer: AB-2026-4711 Vertragsbeginn Laufzeit Kündigungsfrist"
        )
        self.assertEqual(classification.document_type, "Allgemeine Verträge")
        self.assertEqual(document.extracted_data["contract_number"], "AB-2026-4711")

    def test_classifies_joint_income_tax_return_by_tax_year(self):
        text = """
Einkommensteuererklärung für das Jahr 2023
Hauptvordruck ESt 1 A 2023
Steuernummer 216/2232/3797 Finanzamt Köln-Porz
Identifikationsnummer Zusammenveranlagung
"""
        document, classification = self.analyze(text, "Steuer 2023.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["tax_year"], "2023")
        target = StoragePathBuilder(self.structures["family"]).build(document)
        self.assertEqual(target.parts[:4], ("Finanzamt und Steuern", "Einkommensteuer", "2023", "Steuererklärung"))
        self.assertEqual(target.name, "2023 - Einkommensteuererklärung.pdf")

    def test_tax_return_tolerates_ocr_accent_error(self):
        text = """
Einkommensteuererklérung für das Jahr 2023
Hauptvordruck ESt 1 A 2023
Steuernummer 216/2232/3797 Finanzamt Köln-Porz
Identifikationsnummer Zusammenveranlagung
"""
        document, classification = self.analyze(text, "Steuer 2023.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["tax_year"], "2023")

    def test_full_tax_return_wins_over_embedded_wage_tax_certificate(self):
        text = """
Einkommensteuererklärung für das Jahr 2023
Hauptvordruck ESt 1 A Zusammenveranlagung Finanzamt Steuernummer
Anlage N Elektronische Lohnsteuerbescheinigung für 2023
Bruttoarbeitslohn 3.771,20 USD Einkommensersatzleistungen
"""
        document, classification = self.analyze(text, "Steuer 2023.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["document_kind"], "Einkommensteuererklärung")
        self.assertEqual(document.extracted_data["tax_section"], "Steuererklärung")
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])
        self.assertIsNone(document.extracted_data["description"])

    def test_classifies_elster_submission_confirmation(self):
        text = """
ELSTER - Versandbestätigung
Formular wurde versendet
Transferticket ep18944es4wwj46gjwh8bqt0enq1zxsa
Auftrag
Belegnachreichung zur Steuererklärung
Abgabezeit
Sonntag, 7. Juli 2024, 13:33:21
07.07.24, 13:33
https://www.elster.de/eportal/interpreter/versandbestaetigung/belegnachreichung-22
"""
        document, classification = self.analyze(text, "ELSTER - Versandbestätigung.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["date"], "07.07.2024")
        self.assertEqual(document.extracted_data["document_kind"], "ELSTER-Versandbestätigung")
        self.assertIsNone(document.extracted_data["amount"])
        self.assertIsNone(document.extracted_data["currency"])
        self.assertIsNone(document.extracted_data["invoice_number"])
        self.assertIsNone(document.extracted_data["contract_number"])
        target = StoragePathBuilder(self.structures["family"]).build(document)
        self.assertEqual(target.parts[:4], ("Finanzamt und Steuern", "Einkommensteuer", "2024", "ELSTER-Nachweise"))
        self.assertIn("Belegnachreichung zur Steuererklärung", target.name)

    def test_files_wage_tax_certificate_as_tax_receipt(self):
        text = """
Elektronische Lohnsteuerbescheinigung für 2023
Arbeitgeber Theater Hagen gGmbH
Bruttoarbeitslohn einbehaltene Lohnsteuer Steuer-Identifikationsnummer
"""
        document, classification = self.analyze(text, "Lohnsteuerbescheinigung.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        self.assertEqual(document.extracted_data["tax_year"], "2023")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(
            target.parts[:6],
            (
                "Finanzamt und Steuern", "Einkommensteuer", "2023",
                "Belege", "Arbeit und Werbungskosten",
                "2023 - Lohnsteuerbescheinigung.pdf",
            ),
        )

    def test_files_tax_document_request_separately_from_receipts(self):
        text = """
Finanzamt Köln-Porz Steuernummer 216/2232/3797
Aufforderung zur Vorlage von Belegen zur Einkommensteuererklärung für 2023
Bitte reichen Sie die bezeichneten Unterlagen innerhalb der Frist ein.
"""
        document, classification = self.analyze(text, "Nachforderung.pdf")
        self.assertEqual(classification.document_type, "Einkommensteuer")
        target = StoragePathBuilder(self.structures["family"]).build(document)
        self.assertEqual(target.parts[3], "Nachforderungen")

    def test_supplier_outgoing_invoice_is_recipient_incoming_invoice(self):
        text = """
Fokus MSP GmbH
Ausgangsrechnung
Belegnummer Kundennummer Datum Seite
Hades IT GmbH 115429 17683 28.03.2024 1/1
Riversuite OnBoarding Januar 2024
Wir stellen wie folgt in Rechnung.
Nettobetrag 649,00 EUR
Mehrwertsteuer 19,0 % 123,31 EUR
Gesamtpreis 772,31 EUR
Zahlungskonditionen 10 Tage
"""
        document, classification = self.analyze(text, "2.pdf")
        self.assertEqual(classification.document_type, "Eingangsrechnungen")
        self.assertGreaterEqual(classification.confidence, 0.9)
        self.assertEqual(document.extracted_data["invoice_number"], "115429")

    def test_date_only_invoice_filename_does_not_invent_number_or_vendor(self):
        data = DocumentAnalyzer(self.rules, {}, _Logger())._extract_from_filename(
            "Rechnung_01-09-2026.pdf"
        )

        self.assertFalse(data["force_outgoing"])
        self.assertNotIn("invoice_number", data)
        self.assertNotIn("vendor", data)

    def test_family_education_invitation_is_recognized_as_course(self):
        _document, classification = self.analyze(
            "Einladung zur DRK Familienbildung und Teilnahme am PEKiP Kurs",
            "DRK FBildung - Einladung - PEKiP.pdf",
        )

        self.assertEqual(classification.category, "Gesundheit")
        self.assertEqual(classification.document_type, "Kurse und Therapien")

    def test_generic_terms_are_not_misclassified_as_invoices(self):
        _document, classification = self.analyze(
            "Allgemeine Geschäftsbedingungen für die DHL Online Frankierung Rechnung und Zahlung",
            "dhl-agb-online-frankierung-202506.pdf",
        )

        self.assertEqual(classification.category, "MANUELL")
        self.assertEqual(classification.document_type, "Allgemeine Informationen")

    def test_invoice_total_is_preferred_over_item_price(self):
        text = """
Rechnung
Artikel 1 44,99 € 44,99 €
Zwischensumme                         80,98 €
Gesamt netto                          72,17 €
Umsatzsteuer (19,0%)                  13,71 €
Gesamtsumme                           85,88 €
"""

        document, _classification = self.analyze(text, "Lil' Leo Rechnung.pdf")

        self.assertEqual(document.extracted_data["amount"], "85,88")

    def test_invoice_total_is_found_when_ocr_separates_labels_and_values(self):
        text = """
Rechnung
Zwischensumme
Versand
Gesamt netto
Umsatzsteuer (19,0%)
Gesamtsumme
Preis
44,99
35,99
Summe
44,99
35,99
80,98
4,90
72,17
13,71
85,88
"""

        document, _classification = self.analyze(text, "Lil' Leo Rechnung.pdf")

        self.assertEqual(document.extracted_data["amount"], "85,88")


if __name__ == "__main__":
    unittest.main()
