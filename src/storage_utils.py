import os
import shutil
import re
from pathlib import Path
from typing import List

from src.models import Document
from src.document_formats import is_ignored_source_name
from src.date_utils import german_month_name, split_german_date


class SourceFileBusyError(OSError):
    """The source exists but Windows currently prevents moving it."""


def discard_file_within(source_path: Path, allowed_root: Path) -> Path:
    """Delete exactly one file after proving it is contained by allowed_root."""
    root = Path(allowed_root).resolve()
    try:
        source = Path(source_path).resolve(strict=True)
        source.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("Die Datei liegt nicht im erlaubten Ordner.") from exc
    if not source.is_file():
        raise ValueError("Das Dokument wurde nicht gefunden.")
    try:
        source.unlink()
    except PermissionError as exc:
        raise SourceFileBusyError(
            f"Datei ist noch in einem anderen Programm geöffnet: '{source.name}'"
        ) from exc
    return source

def sanitize(text: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", text)
    return clean.strip()[:100]


class FolderDocumentSource:

    def __init__(self, root_path: Path):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def fetch_documents(self) -> List[Document]:

        documents = []

        for root, _, files in os.walk(self.root_path):

            if os.path.basename(root).startswith("."):
                continue

            files.sort()

            for file_name in files:
                if file_name.startswith(".") or is_ignored_source_name(file_name):
                    continue

                full_path = Path(root) / file_name

                if not full_path.is_file():
                    continue

                documents.append(Document(source_path=full_path))

        return documents


class FileDocumentSource:
    """A pipeline source restricted to one explicitly selected document."""

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    def fetch_documents(self) -> List[Document]:
        path = self.file_path
        if (
            not path.is_file()
            or path.name.startswith(".")
            or is_ignored_source_name(path.name)
        ):
            return []
        return [Document(source_path=path)]


class FilesystemStorage:

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def store(self, source_path: str, target_directory: Path, new_name: str) -> str:

        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name
        target_path = self._get_unique_path(target_path)

        try:
            shutil.move(str(source), str(target_path))
        except PermissionError as e:
            raise SourceFileBusyError(
                f"Datei ist noch in einem anderen Programm geöffnet: '{source.name}'"
            ) from e
        except Exception as e:
            raise OSError(
                f"Datei konnte nicht nach '{target_path}' verschoben werden"
            ) from e
        return str(target_path)

    @staticmethod
    def ensure_movable(source_path: str) -> None:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)
        try:
            os.rename(source, source)
        except PermissionError as exc:
            raise SourceFileBusyError(
                f"Datei ist noch in einem anderen Programm geöffnet: '{source.name}'"
            ) from exc

    def _get_unique_path(self, target_path: Path) -> Path:

        if not target_path.exists():
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        for counter in range(1, 10000):
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name

            if not new_path.exists():
                return new_path

        raise RuntimeError("Kein eindeutiger Dateiname gefunden")
    
    def backup(self, source_path: str, target_directory: Path, new_name: str) -> str:
        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name
        target_path = self._get_unique_path(target_path)

        try:
            shutil.copy2(str(source), str(target_path))
        except Exception as e:
            raise OSError(
                f"Backup konnte nicht nach '{target_path}' geschrieben werden"
            ) from e
        return str(target_path)


class StoragePathBuilder:

    def __init__(self, structure: dict):
        self.structure = structure

    def build(self, document: Document) -> Path:

        category = document.metadata.category or "DIVERSES"
        doc_type = document.metadata.document_type or "Unsortiert"

        structure_category = self.structure.get(category, {})

        filename = self._generate_filename(document)

        if doc_type in structure_category:
            node = structure_category.get(doc_type)
            path_parts = [category, doc_type]
        elif isinstance(structure_category, dict) and (
            not structure_category or any(str(key).startswith("{") for key in structure_category)
        ):
            node = structure_category
            path_parts = [category]
        else:
            fallback = "Sonstiges" if "Sonstiges" in self.structure else category
            return Path(fallback, filename) if fallback == "Sonstiges" else Path(category, "Unsortiert", filename)

        date = document.extracted_data.get("date")
        tax_year = document.extracted_data.get("tax_year")
        payroll_period = document.extracted_data.get("payroll_period")
        payroll_periods = document.extracted_data.get("payroll_periods") or []
        assignment_start = document.extracted_data.get("assignment_start")
        payroll_year = None
        if payroll_period:
            try:
                _payroll_month, payroll_year = str(payroll_period).split(".")
            except ValueError:
                payroll_year = None
        elif payroll_periods:
            payroll_years = {
                str(value).split(".")[-1]
                for value in payroll_periods
                if re.fullmatch(r"(?:0[1-9]|1[0-2])\.(?:19|20)\d{2}", str(value))
            }
            if len(payroll_years) == 1:
                payroll_year = next(iter(payroll_years))

        if tax_year and isinstance(node, dict) and "{year}" in node:
            path_parts.append(str(tax_year))
            tax_section = document.extracted_data.get("tax_section")
            if tax_section:
                path_parts.extend(
                    part for part in str(tax_section).replace("\\", "/").split("/") if part
                )
        elif payroll_year and isinstance(node, dict) and "{year}" in node:
            path_parts.append(payroll_year)
        elif assignment_start and isinstance(node, dict) and "{year}" in node:
            try:
                _day, _month, assignment_year = str(assignment_start).split(".")
                path_parts.append(assignment_year)
            except ValueError:
                pass
        elif date:
            date_parts = split_german_date(date)
            if date_parts:
                _day, month, year = date_parts
                if "{year}" in node:
                    path_parts.append(year)

                    sub = node["{year}"]

                    tax_section = document.extracted_data.get("tax_section")
                    if tax_section:
                        path_parts.extend(
                            part for part in str(tax_section).replace("\\", "/").split("/") if part
                        )

                    if "{month_number} {month_name}" in sub:
                        path_parts.append(f"{month} {german_month_name(month)}")

        return Path(*path_parts) / filename

    def _generate_filename(self, document: Document) -> str:

        data = document.extracted_data
        doc_type = document.metadata.document_type or ""

        date = data.get("date")
        vendor = data.get("vendor")
        amount = data.get("amount")
        currency = data.get("currency")
        invoice_number = data.get("invoice_number")

        ext = Path(document.source_path).suffix

        if doc_type == "Kontoauszuege":
            parts = ["Kontoauszug"]

            if vendor:
                parts.append(sanitize(vendor))

            month_name = None
            if date:
                date_parts = split_german_date(date)
                month_name = german_month_name(date_parts[1]) if date_parts else None

            if month_name:
                parts.append(month_name)

            return " - ".join(parts) + ext

        if doc_type == "Ausgangsrechnungen":
            parts = ["Rechnung"]

            if invoice_number:
                parts.append(invoice_number)

            if date:
                parts.append("vom")
                parts.append(date)

            if vendor:
                parts.append(sanitize(vendor))
            else:
                parts.append("Kunde")

            return " ".join(parts) + ext

        if doc_type == "Eingangsrechnungen":
            parts = []

            if date:
                parts.append(date)
            else:
                parts.append("ohne Datum")

            if vendor:
                parts.append(sanitize(vendor))
            else:
                fallback = Path(document.source_path).stem.split(" - ")[0]
                parts.append(sanitize(fallback) or "Unbekannt")

            if amount:
                amount_label = amount
                if currency == "USD":
                    amount_label = f"{amount} USD"
                parts.append(amount_label)

            return " - ".join(parts) + ext

        if doc_type == "Kaufbelege":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Kaufbeleg")
            if vendor:
                parts.append(sanitize(vendor))
            if amount:
                amount_label = sanitize(str(amount))
                if currency:
                    amount_label = f"{amount_label} {sanitize(str(currency))}"
                parts.append(amount_label)
            return " - ".join(parts) + ext

        if doc_type == "Kassenbons":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Kassenbon")
            if vendor:
                parts.append(sanitize(vendor))
            if amount:
                amount_label = sanitize(str(amount))
                if currency:
                    amount_label += f" {sanitize(str(currency))}"
                parts.append(amount_label)
            return " - ".join(parts) + ext

        if doc_type == "Retouren und Erstattungen" and data.get("document_kind") == "Retourenbestätigung":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Retourenbestätigung")
            provider = data.get("brand") or vendor
            if provider:
                parts.append(sanitize(provider))
            if data.get("product"):
                parts.append(sanitize(data["product"]))
            reference = data.get("correction_invoice_number") or invoice_number
            if reference:
                parts.append(sanitize(reference))
            if amount:
                amount_label = sanitize(str(amount))
                if currency:
                    amount_label += f" {sanitize(str(currency))}"
                parts.append(amount_label)
            return " - ".join(parts) + ext

        if doc_type == "Energieverträge" and data.get("document_kind") == "Auftragseingangsbestätigung":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            supply = data.get("energy_supply_type") or "Energiebelieferung"
            parts.append(f"Auftragseingangsbestätigung {sanitize(supply)}")
            provider = data.get("brand") or vendor
            if provider:
                parts.append(sanitize(provider))
            order_number = data.get("order_number") or data.get("contract_number")
            if order_number:
                parts.append(f"Auftrag {sanitize(order_number)}")
            return " - ".join(parts) + ext

        if doc_type == "Energieverträge" and data.get("document_kind") == "Vertragsbestätigung":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            supply = data.get("energy_supply_type") or "Energiebelieferung"
            parts.append(f"Vertragsbestätigung {sanitize(supply)}")
            provider = data.get("brand") or vendor
            if provider:
                parts.append(sanitize(provider))
            if data.get("contract_number"):
                parts.append(f"Vertrag {sanitize(data['contract_number'])}")
            return " - ".join(parts) + ext

        if doc_type == "Bescheinigungen" and data.get("document_kind") == "Einkommensbescheinigung":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Einkommensbescheinigung")
            if data.get("employer"):
                parts.append(sanitize(data["employer"]))
            return " - ".join(parts) + ext

        if doc_type == "Bescheinigungen" and data.get("document_kind") == "Arbeitsbescheinigung":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Arbeitsbescheinigung")
            if data.get("employer"):
                parts.append(sanitize(data["employer"]))
            return " - ".join(parts) + ext

        if doc_type == "Gehaltsabrechnungen":
            parts = []
            period = data.get("payroll_period")
            periods = data.get("payroll_periods") or []
            if len(periods) > 1:
                normalized_periods = []
                for value in periods:
                    try:
                        month, year = str(value).split(".")
                        normalized_periods.append(f"{year}-{month}")
                    except ValueError:
                        normalized_periods.append(sanitize(str(value)))
                if normalized_periods:
                    consecutive = all(
                        int(current[:4]) * 12 + int(current[5:7])
                        == int(previous[:4]) * 12 + int(previous[5:7]) + 1
                        for previous, current in zip(
                            normalized_periods, normalized_periods[1:]
                        )
                        if re.fullmatch(r"\d{4}-\d{2}", previous)
                        and re.fullmatch(r"\d{4}-\d{2}", current)
                    )
                    parts.append(
                        f"{normalized_periods[0]} bis {normalized_periods[-1]}"
                        if consecutive else ", ".join(normalized_periods)
                    )
            elif period:
                try:
                    month, year = period.split(".")
                    parts.append(f"{year}-{month}")
                except ValueError:
                    parts.append(sanitize(period))
            elif date:
                try:
                    _, month, year = date.split(".")
                    parts.append(f"{year}-{month}")
                except ValueError:
                    parts.append(sanitize(date))
            document_kind = data.get("document_kind") or "Entgeltabrechnung"
            if len(periods) > 1 and document_kind == "Entgeltabrechnung":
                document_kind = "Entgeltabrechnungen"
            parts.append(document_kind)
            if data.get("employer"):
                parts.append(sanitize(data["employer"]))
            return " - ".join(parts) + ext

        if doc_type == "Einsatzunterlagen":
            parts = []
            relevant_date = data.get("assignment_start") or date
            if relevant_date:
                try:
                    day, month, year = relevant_date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(relevant_date))
            parts.append(data.get("document_kind") or "Einsatzunterlage")
            if data.get("employer"):
                parts.append(sanitize(data["employer"]))
            if data.get("client"):
                parts.append(sanitize(data["client"]))
            if data.get("assignment_number"):
                parts.append(f"Auftrag {sanitize(data['assignment_number'])}")
            return " - ".join(parts) + ext

        if doc_type == "Einkommensteuer":
            if data.get("document_kind") == "ELSTER-Versandbestätigung":
                parts = []
                if date:
                    try:
                        day, month, year = date.split(".")
                        parts.append(f"{year}-{month}-{day}")
                    except ValueError:
                        parts.append(sanitize(date))
                parts.append("ELSTER-Versandbestätigung")
                if data.get("submission_type"):
                    parts.append(sanitize(data["submission_type"]))
                return " - ".join(parts) + ext
            tax_year = data.get("tax_year")
            kind = data.get("document_kind")
            parts = []
            if kind == "Einkommensteuerbescheid" and date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            elif tax_year:
                parts.append(str(tax_year))
            elif date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append(kind or "Steuererklärung")
            if data.get("vendor") and data.get("document_kind") not in {
                "Einkommensteuererklärung", "Einkommensteuerbescheid"
            }:
                parts.append(sanitize(data["vendor"]))
            return " - ".join(parts) + ext

        if doc_type == "Sparen und Vermögen" and data.get("document_kind") == "Bausparvertrag":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Bausparvertrag")
            if data.get("provider"):
                parts.append(sanitize(data["provider"]))
            if data.get("contract_reference"):
                parts.append(sanitize(data["contract_reference"]))
            return " - ".join(parts) + ext

        if doc_type == "Bewerbungen":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Bewerbungsanschreiben")
            if data.get("job_title"):
                parts.append(sanitize(data["job_title"]))
            if data.get("prospective_employer"):
                parts.append(sanitize(data["prospective_employer"]))
            return " - ".join(parts) + ext

        if doc_type == "Kündigungen":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Kündigung")
            if data.get("termination_subject"):
                parts.append(sanitize(data["termination_subject"]))
            elif data.get("insurance_type"):
                parts.append(sanitize(data["insurance_type"]))
            elif data.get("termination_context"):
                parts.append(sanitize(data["termination_context"]))
            if vendor:
                parts.append(sanitize(vendor))
            if data.get("contract_number"):
                parts.append(sanitize(data["contract_number"]))
            return " - ".join(parts) + ext

        if doc_type == "Versicherungspolicen" and data.get("insurance_type"):
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append(sanitize(data["insurance_type"]))
            if vendor:
                parts.append(sanitize(vendor))
            if data.get("contract_number"):
                parts.append(sanitize(data["contract_number"]))
            return " - ".join(parts) + ext

        if doc_type == "Allgemeine Verträge" and data.get("document_kind") == "Beratungsvertrag":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Beratungsvertrag")
            if data.get("description"):
                parts.append(sanitize(data["description"]))
            return " - ".join(parts) + ext

        if doc_type == "Kurse und Therapien" and data.get("document_kind"):
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append(sanitize(data["document_kind"]))
            return " - ".join(parts) + ext

        if doc_type == "Renteninformationen":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append(data.get("document_kind") or "Renteninformation")
            if vendor:
                parts.append(sanitize(vendor))
            return " - ".join(parts) + ext

        if doc_type == "Eheurkunde" and data.get("document_kind") == "Eheurkunde":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Eheurkunde")
            if data.get("registry_office"):
                parts.append(f"Standesamt {sanitize(data['registry_office'])}")
            return " - ".join(parts) + ext

        if doc_type == "Identitätsdokumente" and data.get("document_kind") == "Personalausweis":
            parts = ["Personalausweis"]
            valid_until = data.get("valid_until")
            if valid_until:
                try:
                    day, month, year = valid_until.split(".")
                    parts.append(f"gültig bis {year}-{month}-{day}")
                except ValueError:
                    parts.append(f"gültig bis {sanitize(valid_until)}")
            return " - ".join(parts) + ext

        if doc_type == "Führungszeugnisse":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Führungszeugnis")
            if vendor:
                parts.append(sanitize(vendor))
            return " - ".join(parts) + ext

        if doc_type == "Instandhaltung" and data.get("document_kind") == "Mängeldokumentation":
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append("Mängeldokumentation")
            if data.get("defect_subject"):
                parts.append(sanitize(data["defect_subject"]))
            return " - ".join(parts) + ext

        if doc_type == "Immobilienunterlagen" and data.get("document_kind"):
            parts = [sanitize(data["document_kind"])]
            valid_until = data.get("valid_until")
            if valid_until and data.get("document_kind") == "Energieausweis":
                date_parts = split_german_date(valid_until)
                if date_parts:
                    day, month, year = date_parts
                    parts.append(f"gültig bis {year}-{month}-{day}")
            return " - ".join(parts) + ext

        generic_labels = {
            "Einkommensteuer": "Steuerdokument",
            "Kontoauszüge": "Kontoauszug",
            "Versicherungspolicen": "Versicherungspolice",
            "Versicherungsschreiben": "Versicherungsschreiben",
            "Arztberichte und Befunde": "Arztbericht",
            "Krankenkassenschreiben": "Krankenkassenschreiben",
            "Arbeitsverträge": "Arbeitsvertrag",
            "Arbeitszeugnisse": "Arbeitszeugnis",
            "Mietverträge": "Mietvertrag",
            "Nebenkostenabrechnungen": "Nebenkostenabrechnung",
            "Energieabrechnungen": "Energieabrechnung",
            "Energieverträge": "Energievertrag",
            "Telekommunikation": "Telekommunikation",
            "Darlehensverträge": "Darlehensvertrag",
            "Kindergeld": "Kindergeld",
            "Schule und Betreuung": "Schule und Betreuung",
            "Identitätsdokumente": "Identitätsdokument",
            "Fahrzeugdokumente": "Fahrzeugdokument",
            "Allgemeine Verträge": "Vertrag",
            "Bewerbungen": "Bewerbungsanschreiben",
        }
        if doc_type in generic_labels:
            parts = []
            if date:
                try:
                    day, month, year = date.split(".")
                    parts.append(f"{year}-{month}-{day}")
                except ValueError:
                    parts.append(sanitize(date))
            parts.append(generic_labels[doc_type])
            if vendor:
                parts.append(sanitize(vendor))
            reference = data.get("contract_number") or data.get("invoice_number")
            if reference:
                parts.append(sanitize(reference))
            return " - ".join(parts) + ext

        fallback_name = sanitize(Path(document.source_path).stem) or "document"
        return fallback_name + ext
