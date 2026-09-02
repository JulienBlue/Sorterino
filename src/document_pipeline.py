import os
import re
from pathlib import Path

from src.storage_utils import FilesystemStorage, SourceFileBusyError, StoragePathBuilder
from src.document_analyzer import DocumentAnalyzer
from src.models import Document, DocumentStatus
from src.reporting import DailyReportManager
from src.profile_matcher import ProfileMatcher
from src.policy_resolver import PolicyResolver
from src.manual_review_suggestions import (
    ManualReviewSuggestionStore,
    build_manual_suggestion,
)
from src.document_formats import SUPPORTED_EXTENSIONS
from src.document_text_extractor import DocumentExtractionError, DocumentNeedsReview
from src.constants import BACKUP_DIRECTORY_NAME
from src.duplicate_index import ExactDuplicateIndex


class DocumentPipeline:
    def __init__(
        self,
        config,
        sources,
        ocr_service,
        runtime_storage,
        archive_storage,
        logger,
        rules,
        structure,
        profile_service=None,
        stop_requested=None,
    ):
        self.sources = sources
        self.ocr = ocr_service
        self.runtime = runtime_storage
        self.archive = archive_storage
        self.logger = logger
        self.stop_requested = stop_requested or (lambda: False)

        self.config = config
        self.rules = rules

        self.analyzer = DocumentAnalyzer(
            rules,
            config.raw.get("company_profile", {}),
            logger
        )

        self.path_builder = StoragePathBuilder(structure or {})
        self.structure = structure or {}
        self.profile_service = profile_service
        self.policy_resolver = (
            PolicyResolver(config, profile_service)
            if hasattr(config, "presets_root") else None
        )
        profile_settings = config.raw.get("profile_system", {}) or {}
        self.profile_matcher = (
            ProfileMatcher(
                profile_service,
                profile_settings.get("minimum_assignment_confidence", 0.8),
            )
            if profile_service else None
        )
        self.reporter = DailyReportManager(config.logs_root)
        self.manual_suggestions = ManualReviewSuggestionStore(config)

        if profile_service:
            duplicate_root = profile_service.resolve_backup_directory()
        else:
            duplicate_root = self.archive.base_path / BACKUP_DIRECTORY_NAME
        self.duplicates = ExactDuplicateIndex(config, duplicate_root, logger)

        self.supported_extensions = SUPPORTED_EXTENSIONS

        targets = config.raw.get("targets", {})
        self.manual_sort_target = Path(getattr(config, "manual_root", targets.get("manual", "manual_sort"))).name
        self.error_target = Path(getattr(config, "error_root", targets.get("error", "error"))).name

    def run(self):
        documents = []
        for source in self.sources:
            documents.extend(source.fetch_documents())
        if not documents:
            self.logger.info("Keine neuen Dateien gefunden")
            self.logger.info("Pipeline fertig 0 Dokument(e) verarbeitet")
            return

        groups, ungrouped = self._group_import_duplicates(documents)
        for document in ungrouped:
            if self.stop_requested():
                break
            self._process(document)
        for digest, candidates in groups:
            if self.stop_requested():
                break
            primary = self._select_import_primary(candidates)
            self._process(primary)
            if self.stop_requested():
                break
            for duplicate in candidates:
                if duplicate is primary:
                    continue
                self._store_import_duplicate(duplicate, primary.filename, digest)
        self.logger.info(f"Pipeline fertig {len(documents)} Dokument(e) verarbeitet")

    def _cancelled(self, document):
        if not self.stop_requested():
            return False
        self.logger.info(
            f"Verarbeitung gestoppt – {document.filename} bleibt im Eingangsordner"
        )
        return True

    def _group_import_duplicates(self, documents):
        grouped = {}
        ungrouped = []
        for document in documents:
            path = Path(document.source_path)
            if path.suffix.casefold() not in self.supported_extensions:
                ungrouped.append(document)
                continue
            try:
                digest = self.duplicates.hash_file(path)
            except OSError:
                ungrouped.append(document)
                continue
            grouped.setdefault(digest, []).append(document)
        duplicate_groups = []
        for digest, candidates in grouped.items():
            if len(candidates) == 1:
                ungrouped.extend(candidates)
            else:
                duplicate_groups.append((digest, candidates))
        return duplicate_groups, ungrouped

    @classmethod
    def _select_import_primary(cls, candidates):
        return max(
            candidates,
            key=lambda document: (
                cls._filename_quality(document.filename),
                document.filename.casefold(),
            ),
        )

    @staticmethod
    def _filename_quality(filename):
        stem = Path(filename).stem.strip()
        words = re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", stem)
        score = min(len(stem), 80) + len(words) * 12
        if re.fullmatch(r"\d+", stem):
            score -= 100
        if re.fullmatch(r"[0-9a-f-]{24,}", stem, re.IGNORECASE):
            score -= 100
        if re.match(r"^(img|dsc|scan|document|datei)[-_ ]?\d*", stem, re.IGNORECASE):
            score -= 45
        if re.search(r"(?:kopie|copy|\(\d+\))$", stem, re.IGNORECASE):
            score -= 25
        return score

    def _store_import_duplicate(self, document, selected_name, digest):
        filename = document.filename
        self.logger.info(
            f"Duplikat im selben Import erkannt: {filename} "
            f"(ausgewählt: {selected_name})"
        )
        try:
            self._store_runtime(
                document,
                self.manual_sort_target,
                filename,
                "MANUAL",
                "manual",
                "same_import_duplicate",
                {
                    "review_kind": "same_import_duplicate",
                    "review_notice": "Duplikat aus demselben Import",
                    "selected_import_name": selected_name,
                    "sha256": digest,
                },
            )
            document.status = DocumentStatus.STORED
        except SourceFileBusyError:
            self.logger.info(
                f"{filename} ist noch geöffnet – Verarbeitung wird später erneut versucht"
            )

    def _store_runtime(self, document, target, filename, log_label, event_status, reason, suggestion=None):
        final = self.runtime.store(document.source_path, target, filename)
        if event_status == "manual" and final and suggestion:
            self.manual_suggestions.save(final, suggestion)
        self.logger.log(f"{log_label}: {filename}")
        self.reporter.record_event({
            "status": event_status,
            "reason": reason,
            "original_name": filename,
            "final_name": Path(final).name if final else filename,
            "target_folder": str(Path(final).parent) if final else str(target),
        })
        return final

    def _manual_suggestion(self, document, classification=None, metadata=None, extracted=None, assignment=None):
        return build_manual_suggestion(
            document,
            classification=classification,
            metadata=metadata,
            extracted=extracted,
            assignment=assignment,
            profile_service=self.profile_service,
            path_builder=self.path_builder,
        )

    def _missing_required_data(self, document: Document):
        doc_type = (document.metadata.document_type or "") if document.metadata else ""
        data = document.extracted_data or {}

        if doc_type == "Ausgangsrechnungen":
            required = {
                "date": data.get("date"),
                "vendor": data.get("vendor"),
                "invoice_number": data.get("invoice_number"),
            }
        elif doc_type == "Eingangsrechnungen":
            required = {
                "date": data.get("date"),
                "vendor": data.get("vendor"),
            }
        elif doc_type == "Bescheinigungen":
            required = {"employer": data.get("employer")}
            if data.get("document_kind") != "Arbeitsbescheinigung":
                required["date"] = data.get("date")
        elif doc_type == "Gehaltsabrechnungen":
            periods = data.get("payroll_periods") or []
            required = {"employer": data.get("employer")}
            if not data.get("payroll_period") and not periods:
                required["payroll_period"] = None
            period_years = {
                str(value).split(".")[-1]
                for value in periods
                if re.fullmatch(r"(?:0[1-9]|1[0-2])\.(?:19|20)\d{2}", str(value))
            }
            if len(period_years) > 1:
                required["payroll_period_years"] = None
        else:
            return []

        return [key for key, value in required.items() if not value]

    @staticmethod
    def _requires_invoice_context_review(metadata, active_profile):
        return bool(
            metadata
            and (
                metadata.document_type == "Kassenbons"
                or metadata.document_type in {"Eingangsrechnungen", "Ausgangsrechnungen"}
                and active_profile
                and active_profile.get("type") != "organization"
            )
            and active_profile
        )

    def _process(self, document: Document):
        filename = os.path.basename(document.source_path)
        ext = os.path.splitext(filename)[1].lower()

        self.logger.log(f"IN: {filename}")
        self.logger.info(f"Verarbeite {document.source_path}")

        if self._cancelled(document):
            return

        try:
            FilesystemStorage.ensure_movable(document.source_path)
        except SourceFileBusyError:
            self.logger.info(
                f"{filename} ist noch geöffnet – Verarbeitung wird später erneut versucht"
            )
            return
        except FileNotFoundError:
            self.logger.info(f"{filename} wurde bereits verarbeitet")
            return

        if ext not in self.supported_extensions:
            self.logger.info(f"Unsupported Format {ext}")
            self._store_runtime(document, self.error_target, filename, "UNSUPPORTED", "error", "unsupported_format")
            document.status = DocumentStatus.ERROR
            return

        if self._cancelled(document):
            return

        try:
            source_digest, duplicate_match = self.duplicates.find(document.source_path)
        except OSError as exc:
            source_digest, duplicate_match = None, None
            self.logger.warning(f"Duplikatprüfung fehlgeschlagen: {exc}")
        if self._cancelled(document):
            return
        if duplicate_match:
            duplicate_path = duplicate_match.path
            duplicate_notice = (
                "Bytegleiches Duplikat erkannt"
                if duplicate_match.file_present
                else "Dokument wurde bereits früher verarbeitet"
            )
            self.logger.info(
                f"{duplicate_notice}: {filename}"
                + (f" (vorhanden: {duplicate_path})" if duplicate_path else "")
            )
            self._store_runtime(
                document,
                self.manual_sort_target,
                filename,
                "MANUAL",
                "manual",
                "exact_duplicate",
                {
                    "review_kind": "exact_duplicate",
                    "review_notice": duplicate_notice,
                    "duplicate_of": str(duplicate_path) if duplicate_path else "",
                    "duplicate_available": duplicate_match.file_present,
                    "previous_status": duplicate_match.status,
                    "sha256": source_digest,
                },
            )
            document.status = DocumentStatus.STORED
            return

        self.logger.debug("Dokumentinhalt wird gelesen")
        if not self.ocr:
            self.logger.warning("Dokumentextraktion deaktiviert → direkt manuell")
            text = ""
        else:
            try:
                text = self.ocr.extract_text(document.source_path)
            except DocumentNeedsReview as exc:
                if self._cancelled(document):
                    return
                self.logger.info(f"Dokument benötigt manuelle Prüfung: {exc}")
                self._store_runtime(
                    document, self.manual_sort_target, filename,
                    "MANUAL", "manual", exc.reason,
                )
                document.status = DocumentStatus.STORED
                return
            except DocumentExtractionError as exc:
                if self._cancelled(document):
                    return
                self.logger.error(f"Dokument konnte nicht gelesen werden: {exc}")
                self._store_runtime(
                    document, self.error_target, filename,
                    "ERROR", "error", exc.reason,
                )
                document.status = DocumentStatus.ERROR
                return

        if self._cancelled(document):
            return

        if text is None:
            self.logger.error("Dokumentextraktion fehlgeschlagen → Datei in Error")
            self._store_runtime(document, self.error_target, filename, "ERROR", "error", "extraction_error")
            document.status = DocumentStatus.ERROR
            return

        if not text or not text.strip():
            self.logger.info("Kein Text erkannt manuell")
            self._store_runtime(document, self.manual_sort_target, filename, "MANUAL", "manual", "ocr_empty")
            document.status = DocumentStatus.STORED
            return

        self.logger.debug(f"Extrahierter Text {len(text)} Zeichen")

        document.mark_analyzed(text)
        assignment = None
        active_profile = None
        analyzer = self.analyzer
        if self.profile_matcher:
            matching_text = f"{text}\n{filename}"
            hinted_profile_id = self._mail_profile_hint(document.source_path)
            detected_assignment = self.profile_matcher.match_document(text, filename)
            if (
                hinted_profile_id
                and detected_assignment
                and detected_assignment.profile_id != hinted_profile_id
            ):
                self.logger.info("E-Mail-Profil widerspricht Dokumentinhalt manuell")
                preview, preview_metadata, preview_extracted = analyzer.analyze(document)
                self._store_runtime(
                    document,
                    self.manual_sort_target,
                    filename,
                    "MANUAL",
                    "manual",
                    "profile_conflict",
                    self._manual_suggestion(document, preview, preview_metadata, preview_extracted),
                )
                document.status = DocumentStatus.STORED
                return
            assignment = (
                self.profile_matcher.match_profile(hinted_profile_id, matching_text)
                if hinted_profile_id else detected_assignment
            )
            if not assignment:
                preview, _metadata, _extracted = analyzer.analyze(document)
                if preview.category and preview.category != "MANUELL":
                    self.logger.info(
                        "Profil nicht eindeutig erkannt "
                        f"({preview.category} / {preview.document_type}) manuell"
                    )
                else:
                    self.logger.info("Profil nicht eindeutig erkannt manuell")
                self._store_runtime(
                    document,
                    self.manual_sort_target,
                    filename,
                    "MANUAL",
                    "manual",
                    "profile_unresolved",
                    self._manual_suggestion(document, preview, _metadata, _extracted),
                )
                document.status = DocumentStatus.STORED
                return
            active_profile = self.profile_service.get_profile(assignment.profile_id)
            active_rules = (
                self.policy_resolver.rules_for(active_profile, assignment.person_ids)
                if self.policy_resolver else self.rules
            )
            analyzer = DocumentAnalyzer(
                active_rules,
                self._company_profile(active_profile),
                self.logger,
            )

        classification, metadata, extracted = analyzer.analyze(document)
        if self._cancelled(document):
            return
        if assignment:
            extracted["profile_id"] = assignment.profile_id
            extracted["person_ids"] = assignment.person_ids
            extracted["profile_confidence"] = assignment.confidence
            extracted["profile_matched_by"] = assignment.matched_by

        self.logger.info(
            f"Klassifikation {classification.category} "
            f"{classification.confidence:.2f}"
        )

        self.logger.debug(f"Extrahiert {extracted}")

        if not classification.category or classification.category == "MANUELL":
            self.logger.info("Nicht zuordenbar manuell")
            self._store_runtime(
                document, self.manual_sort_target, filename, "MANUAL", "manual", "classify_none",
                self._manual_suggestion(document, classification, metadata, extracted, assignment),
            )
            document.status = DocumentStatus.STORED
            return

        document.mark_classified(classification)
        document.metadata = metadata
        document.extracted_data = extracted

        if self._requires_invoice_context_review(metadata, active_profile):
            label = "Kassenbon" if metadata.document_type == "Kassenbons" else "Rechnung"
            self.logger.info(f"{label}: private oder geschäftliche Verwendung prüfen")
            self._store_runtime(
                document,
                self.manual_sort_target,
                filename,
                "MANUAL",
                "manual",
                "invoice_context_review",
                self._manual_suggestion(
                    document, classification, metadata, extracted, assignment
                ),
            )
            document.status = DocumentStatus.STORED
            return

        missing_fields = self._missing_required_data(document)
        if missing_fields:
            self.logger.info(
                "Unvollständige Extraktion manuell "
                + ", ".join(missing_fields)
            )
            self._store_runtime(
                document,
                self.manual_sort_target,
                filename,
                "MANUAL",
                "manual",
                "missing_required_data",
                self._manual_suggestion(document, classification, metadata, extracted, assignment),
            )
            document.status = DocumentStatus.STORED
            return

        try:
            path_builder = self.path_builder
            if active_profile:
                if self.policy_resolver:
                    template = self.policy_resolver.structure_for(
                        active_profile, assignment.person_ids
                    )
                else:
                    template_name = (active_profile.get("routing", {}) or {}).get(
                        "structure_template"
                    )
                    template = (self.structure.get("templates", {}) or {}).get(template_name)
                if template:
                    path_builder = StoragePathBuilder(template)
            target_path = path_builder.build(document)
            target_path = self._profile_relative_path(
                active_profile,
                assignment,
                target_path,
                extracted,
            )
        except Exception as e:
            self.logger.error(f"{filename} PATH ERROR {e}")
            self._store_runtime(document, self.error_target, filename, "ERROR", "error", "path_error")
            document.status = DocumentStatus.ERROR
            return

        self.logger.debug(f"Zielpfad {target_path}")

        if self._cancelled(document):
            return

        try:
            archive = self.archive
            backup_path = None
            if active_profile:
                archive = FilesystemStorage(
                    self.profile_service.resolve_storage_root(active_profile["id"])
                )
            try:
                if active_profile:
                    backup_directory = self.profile_service.resolve_backup_directory(
                        active_profile["id"]
                    )
                    backup_path = FilesystemStorage(backup_directory).backup(
                        document.source_path, Path(), filename
                    )
                else:
                    backup_path = archive.backup(
                        document.source_path, BACKUP_DIRECTORY_NAME, filename
                    )
                self.logger.debug(f"Backup erstellt: {filename}")
            except Exception as backup_error:
                self.logger.warning(f"Backup fehlgeschlagen: {backup_error}")
            final = archive.store(
                document.source_path,
                target_path.parent,
                target_path.name
            )
            try:
                document_id = self.duplicates.register(
                    backup_path or final,
                    source_digest,
                    location_type="backup" if backup_path else "archive",
                    original_name=filename,
                    profile_id=assignment.profile_id if assignment else None,
                    person_ids=assignment.person_ids if assignment else [],
                    metadata=self._registry_metadata(document),
                )
                if backup_path:
                    self.duplicates.registry.add_location(
                        document_id, final, "archive"
                    )
                self.duplicates.registry.record_event(
                    document_id,
                    "processed",
                    status="success",
                    reason="ok",
                    details={"source_name": filename},
                )
            except OSError as duplicate_error:
                self.logger.warning(
                    f"Duplikatindex konnte nicht aktualisiert werden: {duplicate_error}"
                )

            self.logger.log(f"OUT: {filename} {final}")
            self.logger.debug(f"________________________________")

            self.reporter.record_event({
                "status": "success",
                "reason": "ok",
                "original_name": filename,
                "final_name": Path(final).name if final else filename,
                "target_folder": str(Path(final).parent) if final else str(target_path.parent),
                "profile_id": assignment.profile_id if assignment else None,
                "person_ids": assignment.person_ids if assignment else [],
            })

            document.mark_stored(str(final))

        except SourceFileBusyError:
            self.logger.info(
                f"{filename} ist noch geöffnet – Verarbeitung wird später erneut versucht"
            )
            return
        except Exception as e:
            self.logger.error(f"{filename} {str(e)}")
            if Path(document.source_path).exists():
                try:
                    self._store_runtime(
                        document, self.error_target, filename,
                        "ERROR", "error", "store_error"
                    )
                except SourceFileBusyError:
                    self.logger.info(
                        f"{filename} ist noch geöffnet – Verarbeitung wird später erneut versucht"
                    )
            document.status = DocumentStatus.ERROR

    @staticmethod
    def _registry_metadata(document):
        extracted = document.extracted_data or {}
        safe_fields = {
            key: extracted.get(key)
            for key in (
                "date", "amount", "currency", "vendor", "document_kind",
                "invoice_number", "contract_number", "order_number",
                "payroll_period", "payroll_periods", "tax_year",
            )
            if extracted.get(key) not in (None, "", [])
        }
        safe_fields.update({
            "category": document.metadata.category if document.metadata else None,
            "document_type": (
                document.metadata.document_type if document.metadata else None
            ),
        })
        return safe_fields

    def _profile_relative_path(self, profile, assignment, target_path, extracted=None):
        if not profile:
            return target_path
        routing = profile.get("routing", {}) or {}
        base_folder = routing.get("archive_folder") or profile.get("display_name")
        if profile.get("type") == "organization" and not routing.get("use_global_storage", True):
            # A custom organization root is the company folder itself. Adding
            # archive_folder here would produce paths such as Hades IT/Hades IT.
            base_folder = None
        if profile.get("type") == "family":
            if (extracted or {}).get("shared_scope") == "family":
                base_folder = profile.get("archive_name") or "Gemeinsame Dokumente"
            elif assignment and len(assignment.person_ids) == 1:
                person = self.profile_service.get_person(assignment.person_ids[0])
                if person:
                    base_folder = (
                        (person.get("routing", {}) or {}).get("archive_folder")
                        or person.get("display_name")
                    )
            else:
                base_folder = profile.get("archive_name") or "Gemeinsame Dokumente"
        return Path(base_folder) / target_path if base_folder else target_path

    @staticmethod
    def _company_profile(profile):
        if not profile or profile.get("type") != "organization":
            return {}
        address = profile.get("address", {}) or {}
        contacts = profile.get("contacts", {}) or {}
        registration = profile.get("registration", {}) or {}
        financial = profile.get("financial_identifiers", {}) or {}
        emails = contacts.get("emails", [])
        phones = contacts.get("phones", [])
        return {
            "name": (profile.get("name", {}) or {}).get("legal_name") or profile.get("display_name", ""),
            "keywords": (profile.get("matching", {}) or {}).get("keywords", []),
            "address": {
                "street": " ".join(filter(None, [address.get("street"), address.get("house_number")])),
                "zip": address.get("postal_code", ""),
                "city": address.get("city", ""),
            },
            "contact": {
                "email": emails[0].get("value", "") if emails else "",
                "phone": phones[0].get("value", "") if phones else "",
            },
            "financial": {
                "iban": (financial.get("ibans") or [""])[0],
                "tax_id": (
                    registration.get("vat_identification_number")
                    or (registration.get("tax_numbers") or [""])[0]
                ),
            },
        }

    def _mail_profile_hint(self, source_path):
        if not self.profile_service or not self.config.incoming_root:
            return None
        from src.mail_fetcher import mail_profile_hint
        hinted = mail_profile_hint(self.config, source_path, self.profile_service)
        if hinted:
            return hinted
        # Compatibility with files imported by older Sorterino versions.
        try:
            relative = Path(source_path).resolve().relative_to(
                Path(self.config.incoming_root).resolve()
            )
        except (OSError, ValueError):
            return None
        if len(relative.parts) < 3:
            return None
        profile_id, account_id = relative.parts[0], relative.parts[1]
        account = self.profile_service.get_email_account(account_id)
        if account and account.get("profile_id") == profile_id:
            return profile_id
        return None
