import os
import json
from pathlib import Path

import customtkinter as ctk

from src.constants import BACKUP_DIRECTORY_NAME

from src.initialize_workspace import get_base_path
from src.profile_service import ProfileService, ProfileValidationError
from src.gui.appearance import PRIMARY_TEXT


HELP_CONTENT = {
    "overview": (
        "Übersicht",
        "Hier siehst du den aktuellen Zustand von Sorterino und erreichst offene Dokumente direkt.",
        [
            "Lege zuerst mindestens ein Profil und dessen Dokumentenspeicher an.",
            "Lege Dateien über „Dokumente hinzufügen“ in den lokalen Eingangsordner.",
            "Mit „Jetzt verarbeiten“ werden neue Dokumente analysiert und zugeordnet.",
            "Die globalen Dokumentaktionen stehen dauerhaft unten links und zusätzlich im Tray-Menü bereit.",
        ],
    ),
    "documents": (
        "Dokumente",
        "Diese Seite trennt neue Dokumente, ungeklärte Fälle und technische Fehler.",
        [
            "Neu: Dateien warten im Eingang auf die Verarbeitung. Mailanhänge tragen direkt hinter dem Dateinamen das Badge ‚✉ E-Mail‘. Du kannst ein einzelnes Dokument öffnen, verarbeiten oder nach Bestätigung endgültig verwerfen.",
            "Startest du mehrere einzelne Dokumente, verarbeitet Sorterino sie nacheinander. Die Liste zeigt das aktive Dokument und den jeweiligen Platz in der Warteschlange.",
            "Zu prüfen: Profil oder Ablageziel war nicht eindeutig und muss von dir bestätigt werden.",
            "Auftragseingangsbestätigungen für Strom oder Gas sind Energieverträge und keine Rechnungen; Verbrauchswerte in kWh werden nicht als Geldbetrag behandelt.",
            "Fehler: Textextraktion, Dateiformat oder Speicherung ist technisch fehlgeschlagen.",
            "Unterstützt werden PDF, Word, ODT, RTF, TXT, Pages, EML, MSG sowie gängige Bild- und Scanformate einschließlich TIFF, WebP und HEIC.",
            "Pages ohne eingebettete Vorschau und alte DOC-Dateien ohne LibreOffice werden sicher unter „Zu prüfen“ abgelegt.",
            "Die Originaldatei bleibt bei ungeklärten Fällen erhalten.",
            "Verarbeitung, Dateiimport und Eingangsordner erreichst du dauerhaft unten links oder über das Tray-Menü.",
        ],
    ),
    "profiles": (
        "Profile",
        "Profile trennen private, familiäre und geschäftliche Dokumentkontexte.",
        [
            "Familie verwendet die Familienstruktur; als Kind markierte Mitglieder erhalten automatisch die Kindstruktur.",
            "Privatpersonen verwenden die Personenstruktur, Organisationen die Organisationsstruktur.",
            "Jedes Profil kann einen eigenen Dokumentenspeicher besitzen; technische Regeln und Strukturen liegen in den erweiterten Einstellungen.",
            "Dieselbe Person kann mehreren Kontexten angehören, beispielsweise Familie und Firma.",
            "Beim Entfernen kannst du nur eine Zuordnung lösen, Konfigurationsdaten löschen oder zusätzlich eindeutig zugehörige Dateiordner löschen.",
            "Konfigurations- und Dateilöschungen besitzen getrennte Bestätigungen; gemeinsam genutzte Ordner werden aus Sicherheitsgründen behalten.",
        ],
    ),
    "person": (
        "Person anlegen oder bearbeiten",
        "Hier pflegst du persönliche Daten, die Sorterino zur sicheren Zuordnung verwenden darf.",
        [
            "Vor- und Nachname sind Pflichtfelder; Geburtsdatum und E-Mail verbessern die Erkennung.",
            "Die freiwillige Geschlechtsangabe steuert nur passende Bezeichnungen wie Sohn, Tochter, Mitarbeiter oder Mitarbeiterin.",
            "Das Geburtsdatum wird getrennt als Tag, Monat und Jahr eingegeben.",
            "Kennungen werden beim Speichern normalisiert und – soweit möglich – über Prüfziffern validiert.",
            "Aktiviere „Kind“, damit innerhalb einer Familie die passende Kindstruktur verwendet wird.",
            "Beim Löschen einer Person werden ihre Profilzuordnungen entfernt; bereits abgelegte Dokumente bleiben erhalten.",
        ],
    ),
    "profile_edit": (
        "Profil bearbeiten",
        "Hier verwaltest du Dokumentenspeicher, Kontaktangaben und profilbezogene Kennungen.",
        [
            "Wähle ausdrücklich zwischen Standard-Speicherort und eigenem Speicherort.",
            "Der Archivordner ist der oberste Ordner dieses Profils im gewählten Speicher.",
            "Im Familienreiter „Beziehungen“ kannst du Ehe- oder Lebenspartner verknüpfen; beide Namen helfen Sorterino anschließend bei der Erkennung gemeinsamer Dokumente.",
            "Gemeinsame beziehungsweise geschäftliche Kennungen sollten nur am Profil hinterlegt werden, wenn sie den ganzen Kontext eindeutig bezeichnen.",
        ],
    ),
    "profile_new": (
        "Profil anlegen",
        "Lege einen klar benannten privaten, familiären oder geschäftlichen Dokumentkontext an.",
        [
            "Wähle zuerst, ob du eine Person, eine Familie oder eine Firma beziehungsweise Organisation verwalten möchtest.",
            "Der Anzeigename muss eindeutig sein.",
            "Ob eine Person minderjährig ist, berechnet Sorterino automatisch aus dem Geburtsdatum.",
            "Speicherort, Mitglieder, E-Mail-Konten und Kennungen können anschließend ergänzt werden.",
        ],
    ),
    "membership": (
        "Person zuordnen",
        "Eine bestehende Person kann einem Familien- oder Organisationsprofil zugeordnet werden.",
        [
            "Bei Familien wählst du Elternteil, Kind, Ehepartner:in, Partner:in, Geschwister- oder Großelternteil; über „Andere Beziehung …“ ist auch eine eigene Bezeichnung möglich.",
            "Bei Firmen wählst du eine vordefinierte Funktion oder trägst über „Eigene Funktion …“ eine passende Bezeichnung ein.",
            "Die Familienbeziehung bleibt dauerhaft bestehen; ein volljähriges Kind bleibt beispielsweise Sohn oder Tochter.",
            "Die persönlichen Stammdaten werden dabei nicht dupliziert.",
        ],
    ),
    "mail": (
        "Profilbezogene E-Mail-Konten",
        "E-Mail-Anhänge werden vor der Inhaltsprüfung dem gewählten Profil als Herkunftshinweis zugeordnet.",
        [
            "Google und Microsoft werden ausschließlich über die sichere Anmeldung im Standardbrowser verbunden.",
            "Apple, GMX, WEB.DE, IONOS und manuelle Anbieter verwenden ein eigens erzeugtes App-Passwort – niemals das normale Kontopasswort.",
            "Refresh-Tokens und App-Passwörter liegen im Windows-Anmeldeinformationsspeicher und weder in JSON-Dateien noch in Backups.",
            "Sorterino verwendet einen eigenen IMAP-Cursor. Auch bereits am Handy gelesene neue Nachrichten werden beim nächsten Start berücksichtigt.",
            "Widerspricht der Dokumentinhalt dem erwarteten Profil, landet die Datei zur manuellen Prüfung.",
        ],
    ),
    "mail_edit": (
        "E-Mail-Postfach bearbeiten",
        "Wähle den Anbieter und verbinde das Postfach mit der dafür vorgesehenen sicheren Methode.",
        [
            "Bei Google und Microsoft öffnet Sorterino den echten Anbieter-Login im Standardbrowser und sieht dein Passwort nicht.",
            "Die IMAP-Berechtigung kann technisch das ganze Postfach lesen; Sorterino prüft nur den anfänglichen Rückblick und danach neue Nachrichten. Es verändert weder Gelesen- noch Stern-Markierungen.",
            "Den einmaligen Rückblick legst du beim Verknüpfen auf ab jetzt, 7, 30, 90 oder 365 Tage fest.",
            "Bekannte Anbieter sind fest an ihren offiziellen Server und Port 993 gebunden. Nur bei „Anderer Anbieter“ sind Serverangaben frei.",
            "Nutze „Verbindung testen“, bevor du speicherst; alte Passwortverbindungen zu Google oder Microsoft müssen einmal neu verbunden werden.",
            "Das Postfach gehört ausschließlich zum aktuell gewählten Profil.",
        ],
    ),
    "manual_review": (
        "Dokument prüfen",
        "Ordne ein unsicheres Dokument einem Profil, gegebenenfalls einer Person und einem Ablageziel zu.",
        [
            "Öffne das Dokument und prüfe zuerst den Empfänger oder die enthaltenen Kennungen.",
            "Bei Rechnungen in Familien- oder Privatprofilen unterscheidest du zwischen „Privater Kauf“ und „Für eigenes Unternehmen“. Nur eine tatsächliche Firmenausgabe benötigt ein Firmenprofil.",
            "„Privat steuerlich absetzbar“ bleibt bei der ausgewählten Familie oder Person und wird mit dem gewählten Steuerjahr unter deren Steuerbelegen abgelegt. Sorterino erzeugt dabei keine versteckte zweite Kopie.",
            "Wähle bei Familiendokumenten „Gemeinsame Dokumente“, wenn keine einzelne Person betroffen ist.",
            "Die angebotenen Ordner stammen aus der aufgelösten Profil- beziehungsweise Personenvorlage.",
            "Über „Neuen Unterordner anlegen …“ kannst du die wirksame Struktur für das gewählte Profil beziehungsweise die gewählte Person dauerhaft ergänzen.",
            "Du kannst einen Jahresordner ergänzen und den Dokumentnamen vor der Ablage ändern. Mit „Originalnamen verwenden“ übernimmst du stattdessen exakt den bisherigen Namen; die Dateiendung bleibt immer erhalten.",
            f"Vor der manuellen Ablage sichert Sorterino die unveränderte Datei mit ihrem ursprünglichen Namen im zentralen Ordner „{BACKUP_DIRECTORY_NAME}“. Darin besitzt jedes Profil einen eigenen, verständlich benannten Unterordner. Der Erfolgsdialog zeigt Ablage- und Backup-Pfad an.",
            "Im klar abgegrenzten Ausnahmebereich kannst du das Dokument direkt in einen beliebigen Ordner außerhalb der Sorterino-Struktur legen.",
            "Unerwünschte Anhänge wie allgemeine Geschäftsbedingungen oder Werbung kannst du nach einer Bestätigung endgültig aus ‚Zu prüfen‘ verwerfen.",
        ],
    ),
    "settings": (
        "Einstellungen",
        "Diese Seite enthält ausschließlich globale Programmeinstellungen.",
        [
            "Der Standard-Dokumentenspeicher wird von Profilen ohne eigenen Speicherort verwendet.",
            "Der gemeinsame Eingang wird zunächst im Standard-Dokumentenspeicher angelegt und kann danach separat geändert werden.",
            "Prüfung, Fehler und Logs liegen weiterhin unter AppData und sind unabhängig vom Dokumentenspeicher.",
            "Darstellung und Autostart gelten für Sorterino insgesamt, nicht für einzelne Profile.",
            "Unter „Texterkennung“ siehst du, ob PDF/OCR, HEIC und alte Word-Dateien auf diesem Computer vollständig verarbeitet werden können.",
        ],
    ),
    "advanced": (
        "Erweiterte Einstellungen",
        "Hier können Programmeinstellungen und die vier Standardvorlagen direkt als JSON bearbeitet werden.",
        [
            "Ungültiges JSON wird nicht gespeichert.",
            "Diese technischen Einstellungen sind bewusst nur hier erreichbar und sollten nur mit Kenntnis der JSON-Struktur geändert werden.",
            "Vorlagen wirken auf alle Profile ihres Typs, sofern sie nicht überschrieben werden.",
        ],
    ),
    "json_editor": (
        "JSON bearbeiten",
        "Diese Ansicht ist für technische Sonderfälle und spätere individuelle Sortierlogik gedacht.",
        [
            "Ändere nur die benötigten Werte und behalte die JSON-Struktur bei.",
            "Profil-Overrides enthalten nur Abweichungen; nicht genannte Werte werden aus der Vorlage geerbt.",
            "Bei einem Fehler kannst du die Änderung verwerfen und mit dem Zurück-Pfeil zurückkehren.",
        ],
    ),
    "logs": (
        "Protokoll",
        "Das Protokoll zeigt technische Verarbeitungsschritte und Ursachen fehlgeschlagener Ablagen.",
        [
            "Suche bei Problemen nach dem Dateinamen und der letzten ERROR- oder WARN-Zeile.",
            "Persönliche Kennungen und E-Mail-Passwörter sollten nicht im Protokoll erscheinen.",
            "Fehlerhafte Originale findest du zusätzlich unter „Dokumente → Fehler“.",
        ],
    ),
}


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, master, config, context="overview"):
        super().__init__(master)
        self.title("Sorterino Hilfe")
        self.geometry("760x700")
        self.minsize(620, 520)
        self.transient(master)
        icon = get_base_path() / "assets" / "icons" / "default_icon_128.ico"
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass
        title, summary, steps = HELP_CONTENT.get(context, HELP_CONTENT["overview"])
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(scroll, text=f"Hilfe: {title}", font=("Arial", 24, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        ctk.CTkLabel(scroll, text=summary, wraplength=670, justify="left").pack(anchor="w", padx=10, pady=(0, 16))
        status, issues = diagnose(config, context)
        color = ("#d9f2df", "#173d23") if not issues else ("#ffe6c7", "#55320d")
        status_card = ctk.CTkFrame(scroll, fg_color=color)
        status_card.pack(fill="x", padx=10, pady=(0, 18))
        ctk.CTkLabel(status_card, text=status, font=("Arial", 17, "bold"), text_color=PRIMARY_TEXT).pack(anchor="w", padx=14, pady=(12, 5))
        for issue in issues:
            ctk.CTkLabel(status_card, text=f"• {issue}", wraplength=620, justify="left", text_color=PRIMARY_TEXT).pack(anchor="w", padx=14, pady=3)
        ctk.CTkLabel(status_card, text="").pack(pady=2)
        ctk.CTkLabel(scroll, text="Was du hier tun kannst", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(0, 6))
        for step in steps:
            ctk.CTkLabel(scroll, text=f"• {step}", wraplength=670, justify="left").pack(anchor="w", padx=16, pady=4)
        ctk.CTkButton(scroll, text="Hilfe schließen", command=self.destroy).pack(anchor="e", padx=10, pady=22)


def _existing_parent(path):
    """Return the nearest existing parent without creating user folders."""
    candidate = Path(path)
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return candidate if candidate.exists() else None


def _storage_is_available(path):
    path = Path(path)
    if path.exists():
        return path.is_dir() and os.access(path, os.W_OK)
    parent = _existing_parent(path)
    return bool(parent and parent.is_dir() and os.access(parent, os.W_OK))


def diagnose(config, context):
    issues = []
    if not config.app_root.exists() or not os.access(config.app_root, os.W_OK):
        issues.append("Sorterino kann seinen AppData-Ordner nicht beschreiben. Bitte prüfe die Windows-Berechtigungen für %APPDATA%\\Sorterino.")
    missing_presets = [
        name for name in ("family", "person", "child", "organization")
        if not (config.presets_root / name / "structure.json").exists()
        or not (config.presets_root / name / "rules.json").exists()
    ]
    if missing_presets:
        issues.append("Strukturvorlagen fehlen. Starte Sorterino neu; bleiben sie verschwunden, stelle den Ordner „presets“ aus einem Backup wieder her.")
    if context in {"overview", "documents", "profiles", "profile_edit", "manual_review"}:
        if not config.get("user_path"):
            issues.append("Es ist kein Standard-Dokumentenspeicher eingerichtet. Öffne Einstellungen → Dokumentquellen und wähle einen Ordner.")
        elif not _storage_is_available(config.get("user_path")):
            issues.append("Der Standard-Dokumentenspeicher ist nicht erreichbar. Schließe das Laufwerk an oder wähle unter Einstellungen einen neuen Ordner.")
    try:
        service = ProfileService(config)
        profiles = service.list_profiles()
        if context in {"overview", "documents", "profiles", "manual_review"} and not profiles:
            issues.append("Es ist noch kein Profil vorhanden. Öffne „Profile“ und lege eine Privatperson, Familie oder Organisation an.")
        for profile in profiles:
            try:
                storage = service.resolve_storage_root(profile["id"])
                if storage.exists() and not os.access(storage, os.W_OK):
                    issues.append(f"Der Speicherort von Profil „{profile.get('display_name', 'Unbenannt')}“ ist nicht beschreibbar. Prüfe die Ordnerberechtigungen oder wähle einen anderen Speicherort.")
                elif not _storage_is_available(storage):
                    issues.append(f"Der Speicherort von Profil „{profile.get('display_name', 'Unbenannt')}“ ist nicht erreichbar. Schließe das Laufwerk an oder ändere den Speicherort im Profil.")
            except ProfileValidationError as exc:
                issues.append(f"Profil „{profile.get('display_name', 'Unbenannt')}“: {exc} Öffne das Profil und korrigiere den Speicherort.")
        if context in {"mail", "mail_edit"}:
            from src.mail_auth import (
                MailAuthenticationError,
                has_account_credentials,
                oauth_client_config,
                validate_imap_settings,
            )
            for account in service.list_email_accounts():
                label = account.get("label") or "Unbenannt"
                try:
                    validate_imap_settings(account)
                    if account.get("auth_method") == "oauth2":
                        oauth_client_config(config, account.get("provider"))
                    if not has_account_credentials(account, config):
                        issues.append(f"Postfach „{label}“ muss erneut verbunden werden.")
                except MailAuthenticationError as exc:
                    issues.append(f"Postfach „{label}“: {exc}")
    except ProfileValidationError as exc:
        issues.append(f"Die Profildaten sind ungültig: {exc} Öffne „Profile“ und korrigiere die betroffenen Angaben.")
    if context in {"overview", "documents", "settings"}:
        if not getattr(config, "tesseract_path", None) or not config.tesseract_path.exists():
            issues.append("Die Texterkennung wurde nicht gefunden. Prüfe unter Einstellungen den Tesseract-Pfad beziehungsweise die Installation.")
        if not getattr(config, "poppler_path", None) or not config.poppler_path.exists():
            issues.append("Die PDF-Unterstützung wurde nicht gefunden. Prüfe unter Einstellungen den Poppler-Pfad beziehungsweise die Installation.")
    invalid_json = []
    for path in config.app_root.rglob("*.json"):
        if path.name.startswith("legacy."):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                json.load(handle)
        except (OSError, json.JSONDecodeError):
            invalid_json.append(str(path.relative_to(config.app_root)))
    if invalid_json:
        issues.append("Diese Konfigurationsdateien sind beschädigt: " + ", ".join(invalid_json) + ". Öffne die erweiterte Konfiguration und korrigiere das JSON oder stelle die Dateien aus einem Backup wieder her.")
    return ("Sorterino ist einsatzbereit" if not issues else "Sorterino benötigt deine Aufmerksamkeit", issues)
