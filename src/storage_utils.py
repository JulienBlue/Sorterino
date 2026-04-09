import os
import shutil
import re
from pathlib import Path
from typing import List

from src.models import Document

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

# HELPER / SANITIZE
def sanitize(text: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", text)
    return clean.strip()[:100]


# SOURCE / INPUT
class FolderDocumentSource:

    # CONFIG / INIT
    def __init__(self, root_path: Path):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    # SOURCE / FETCH
    def fetch_documents(self) -> List[Document]:

        documents = []

        for root, _, files in os.walk(self.root_path):

            if os.path.basename(root).startswith("."):
                continue

            files.sort()

            for file_name in files:
                if file_name.startswith("."):
                    continue

                full_path = Path(root) / file_name

                if not full_path.is_file():
                    continue

                ext = full_path.suffix.lower()
                if not ext or ext not in ALLOWED_EXTENSIONS:
                    continue

                documents.append(Document(source_path=full_path))

        return documents


# STORAGE / OUTPUT
class FilesystemStorage:

    # CONFIG / INIT
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    # STORAGE / SAVE
    def store(self, source_path: str, target_directory: Path, new_name: str) -> str:

        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name
        target_path = self._get_unique_path(target_path)

        try:
            shutil.move(str(source), str(target_path))
            return str(target_path)
        except Exception as e:
            print(f"[ERROR] Datei konnte nicht verschoben werden: {e}")
            return str(source)

    # STORAGE / UNIQUE PATH
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
    
    # BACKUP
    def backup(self, source_path: str, target_directory: Path, new_name: str) -> str:
        source = Path(source_path)

        target_dir = self.base_path / target_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / new_name
        target_path = self._get_unique_path(target_path)

        try:
            shutil.copy2(str(source), str(target_path))
            return str(target_path)
        except Exception as e:
            print(f"[ERROR] Backup fehlgeschlagen: {e}")
            return str(source)


# STORAGE / PATH BUILDER
class StoragePathBuilder:

    # CONFIG / INIT
    def __init__(self, structure: dict):
        self.structure = structure

    # PATH / BUILD
    def build(self, document: Document) -> Path:

        category = document.metadata.category or "DIVERSES"
        doc_type = document.metadata.document_type or "Unsortiert"

        structure_category = self.structure.get(category, {})

        filename = self._generate_filename(document)

        if doc_type not in structure_category:
            return Path(category, "Unsortiert", filename)
        
        node = structure_category.get(doc_type)

        path_parts = [category, doc_type]

        # PATH / DATE
        date = document.extracted_data.get("date")

        if date:
            try:
                d, m, y = date.split(".")

                month_names = [
                    "Januar","Februar","März","April","Mai","Juni",
                    "Juli","August","September","Oktober","November","Dezember"
                ]

                month_name = month_names[int(m) - 1]

                if "{year}" in node:
                    path_parts.append(y)

                    sub = node["{year}"]

                    if "{month_number} {month_name}" in sub:
                        path_parts.append(f"{m} {month_name}")

            except Exception as e:
                print(f"[WARN] Datum konnte nicht verarbeitet werden: {e}")

        return Path(*path_parts) / filename

    # FILENAME / GENERATE
    def _generate_filename(self, document: Document) -> str:

        data = document.extracted_data
        doc_type = document.metadata.document_type or ""

        date = data.get("date")
        vendor = data.get("vendor")
        amount = data.get("amount")
        invoice_number = data.get("invoice_number")
        description = data.get("description")

        ext = Path(document.source_path).suffix

        # =========================
        # 📤 AUSGANGSRECHNUNG
        # =========================
        if doc_type == "Ausgangsrechnungen":

            parts = ["Rechnung"]

            # 🔥 WICHTIG: aus extracted_data, NICHT regex
            if invoice_number:
                parts.append(invoice_number)

            if date:
                parts.append(date)

            if vendor:
                parts.append(sanitize(vendor))
            else:
                parts.append("Kunde")

            return "_".join(parts) + ext

        # =========================
        # 📥 EINGANGSRECHNUNG
        # =========================
        else:

            parts = []

            # Datum
            if date:
                parts.append(date)

            # Vendor
            if vendor:
                parts.append(sanitize(vendor))
            else:
                fallback = Path(document.source_path).stem.split(" - ")[0]
                parts.append(sanitize(fallback) or "Unbekannt")

            # Beschreibung
            if description:
                parts.append(sanitize(description))

            # Betrag
            if amount:
                parts.append(amount)

            if not parts:
                parts = ["document"]

            return "_".join(parts) + ext