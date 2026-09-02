# Sorterino – Befehle

Meine Kurzreferenz für PowerShell. Alle Befehle werden im Projektordner ausgeführt.

## Entwicklungsumgebung

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

Die requirements.txt nur ändern, wenn sich die benötigten Pakete wirklich geändert haben.

## Sorterino starten

Desktop-Anwendung:

    python -m src.gui.app

Ein einzelner Pipeline-Lauf ohne Oberfläche:

    python main.py

## Vor einem Commit prüfen

    python -m compileall -q main.py src tests
    python -m unittest discover -s tests -v
    git status --short
    git diff
    git diff --check

Bereits von Git erfasste Dateien finden, die inzwischen ignoriert werden:

    git ls-files -ci --exclude-standard

Prüfen, welche Ignore-Regel auf eine Datei wirkt:

    git check-ignore -v --no-index PFAD

## Lokale Sorterino-Daten

Ordnerinhalt anzeigen:

    Get-ChildItem -Recurse "$env:APPDATA\Sorterino"

Wichtige Dateien und Ordner:

    %APPDATA%\Sorterino\settings.json
    %APPDATA%\Sorterino\oauth_clients.json
    %APPDATA%\Sorterino\sorterino.db
    %APPDATA%\Sorterino\profiles\
    %APPDATA%\Sorterino\persons\
    %APPDATA%\Sorterino\presets\
    %APPDATA%\Sorterino\runtime\manual\
    %APPDATA%\Sorterino\runtime\errors\
    %APPDATA%\Sorterino\runtime\logs\
    %APPDATA%\Sorterino\runtime\state\

Diese Daten gehören zum lokalen Benutzer und dürfen nicht ins Repository.

Integrität und Statistik des Dokumentregisters lesend prüfen:

    @'
    from src.config import Config
    from src.document_registry import DocumentRegistry

    registry = DocumentRegistry(Config())
    print(registry.database.path)
    print(registry.database.integrity_check())
    print(registry.statistics())
    '@ | python -

Zurücksetzen und Neuaufbau des Registers erfolgen in Sorterino unter Einstellungen, Technische Konfiguration, Dokumentregister verwalten. Die Datenbank nicht löschen, solange Sorterino läuft.

## Anwendung bauen

Normaler Build:

    pyinstaller Sorterino.spec --noconfirm

Build mit Debug-Ausgaben:

    pyinstaller Sorterino.spec --noconfirm --debug=all

Windows-Installer erzeugen:

    iscc installer.iss

Danach liegen die Ergebnisse hier:

    dist\Sorterino\Sorterino.exe
    installer\Sorterino_Setup_v2.0beta.exe

Für einen vollständigen Build werden außerdem diese lokalen Laufzeiten benötigt:

    third_party\tesseract\tesseract.exe
    third_party\poppler\Library\bin\

## Buildordner leeren

Zuerst kontrollieren, welche Ordner entfernt werden:

    Resolve-Path .\build -ErrorAction SilentlyContinue
    Resolve-Path .\dist -ErrorAction SilentlyContinue

Danach gezielt löschen:

    Remove-Item -LiteralPath .\build -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath .\dist -Recurse -Force -ErrorAction SilentlyContinue

Die Sorterino.spec gehört zum Projekt und bleibt bestehen.

## Release-Check

1. Version und Herausgeber in installer.iss kontrollieren.
2. LICENSE, Programmsymbol, Tesseract und Poppler prüfen.
3. Tests und Compile-Prüfung ausführen.
4. Git-Diff einschließlich Whitespace-Prüfung kontrollieren.
5. Sorterino.exe bauen und starten.
6. Installer erstellen und eine Neuinstallation testen.
7. Ein Update über eine vorhandene Installation testen.
8. Profilerstellung, Dokumentregister, Tray, Verarbeitungsstopp und Hilfe prüfen.
9. Deinstallation testen. Archive, Eingang und Sorterino - Backups müssen erhalten bleiben.
10. Den fertigen Installer als GitHub-Release veröffentlichen.

Beispiel für Version v2.0beta:

    git status --short
    git add GEPRÜFTE_DATEIEN
    git diff --cached
    git commit -m "release: v2.0beta"
    git tag -a v2.0beta -m "Sorterino v2.0beta"
    git push origin main
    git push origin v2.0beta

Die Installer-EXE ist ein Release-Artefakt und gehört nicht in einen normalen Quellcode-Commit.

## Normaler Git-Ablauf

    git status --short
    git diff -- DATEI
    git add DATEI_ODER_ORDNER
    git diff --cached
    git commit -m "kurze beschreibung"
    git push

## Orientierung im Projekt

    README.txt            Bedienung und Funktionsübersicht
    README_DEV.txt        Architektur und technische Hinweise
    docs\commands.md      diese Befehlsübersicht
    assets\templates\    mitgelieferte Startvorlagen
    assets\icons\        Programmsymbole
    src\gui\              Desktopoberfläche
    tests\                automatisierte Tests
    Sorterino.spec        PyInstaller-Konfiguration
    installer.iss         Inno-Setup-Skript
    third_party\          lokale OCR- und PDF-Laufzeiten

## Speicherorte

Der gemeinsame Eingang heißt standardmäßig Sorterino - Eingang und liegt im Standard-Dokumentenspeicher. Endgültige Dokumente landen an den Speicherorten der jeweiligen Profile.

Originale werden unter folgendem Schema gesichert:

    STANDARD-DOKUMENTENSPEICHER\Sorterino - Backups\PROFILNAME

Mail-Passwörter und OAuth-Zugangsdaten liegen im Windows-Anmeldeinformationsmanager. Tesseract und Poppler arbeiten lokal. Bei der Deinstallation werden die Daten unter AppData nur nach Bestätigung entfernt; Dokumentarchive, Eingang und Backups bleiben erhalten.
