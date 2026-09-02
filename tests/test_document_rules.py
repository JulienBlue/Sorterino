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
                "Rentenversicherung", "Renteninformationen", None,
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
        self.assertEqual(target.parts[:3], ("Rentenversicherung", "Renteninformationen", "2026"))
        self.assertIn("Renteninformation", target.name)

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
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[:3], ("Arbeit und Karriere", "Einsatzunterlagen", "2022"))
        self.assertEqual(
            target.name,
            "2022-01-01 - Einsatzbegleitschein - WIRMED GmbH - St. Josef Haus Seniorenzentrum - Auftrag 80550116.pdf",
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
            "09.08.2026 Einkommensteuerbescheid Finanzamt Steuernummer Rechtsbehelfsbelehrung"
        )
        self.assertEqual(classification.document_type, "Einkommensteuer")
        target = StoragePathBuilder(self.structures["adult"]).build(document)
        self.assertEqual(target.parts[:5], ("Finanzamt und Steuern", "Einkommensteuer", "2026", "05 Steuerbescheide", "2026-08-09 - Einkommensteuerbescheid.pdf"))
        self.assertIn("Einkommensteuerbescheid", target.name)

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
        self.assertEqual(target.parts[:4], ("Finanzamt und Steuern", "Einkommensteuer", "2023", "01 Steuererklärung"))
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
        self.assertEqual(document.extracted_data["tax_section"], "01 Steuererklärung")
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
        self.assertEqual(target.parts[:4], ("Finanzamt und Steuern", "Einkommensteuer", "2024", "04 ELSTER-Nachweise"))
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
                "02 Belege", "Arbeit und Werbungskosten",
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
        self.assertEqual(target.parts[3], "03 Nachforderungen")

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


if __name__ == "__main__":
    unittest.main()
