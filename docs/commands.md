# Sorterino Commands

Kurze Befehlsübersicht für Entwicklung, Build und Release.


## Umgebung einrichten

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

Abhängigkeiten nur dann neu schreiben, wenn sich Pakete wirklich geändert haben:

pip freeze > requirements.txt


## Anwendung starten

GUI starten:

python -m src.gui.app

Nur die Pipeline ausführen:

python main.py


## Projektstand prüfen

git status

git diff

Dateien anzeigen, die ignoriert werden sollten, aber bereits getrackt sind:

git ls-files -ci --exclude-standard

Ignore-Regel für einen Pfad prüfen:

git check-ignore -v --no-index <pfad>


## Build

PyInstaller-Build:

pyinstaller Sorterino.spec --noconfirm

Debug-Build mit Konsole:

pyinstaller Sorterino.spec --noconfirm --debug=all

Windows-Installer mit Inno Setup:

iscc installer.iss

Build-Ergebnis:

dist/Sorterino/

installer/Sorterino_Setup_vX.X.X.exe


## Release vorbereiten

Vor dem Release die Versionsnummer festlegen, zum Beispiel:

v1.0

Die Version muss an diesen Stellen zusammenpassen:

- installer.iss
- Name der Installer-EXE
- Commit-Message
- Git-Tag

Dann den Stand prüfen:

git status

git diff

Build und Installer neu erzeugen:

pyinstaller Sorterino.spec --noconfirm

iscc installer.iss

Installer kurz starten und prüfen, ob Installation, Start und erste Einrichtung sauber laufen.


## Git Push für Release

Beispiel für Version v1.0:

git status

git add .

git add installer/Sorterino_Setup_v1.0.exe

git commit -m "release: v1.0"

git tag -a v1.0 -m "Sorterino v1.0"

git push origin main

git push origin v1.0

Wenn die Version anders ist, überall dieselbe Nummer einsetzen:

git add installer/Sorterino_Setup_vX.X.X.exe

git commit -m "release: vX.X.X"

git tag -a vX.X.X -m "Sorterino vX.X.X"

git push origin main

git push origin vX.X.X


## Normaler Git-Ablauf ohne Release

git status

git add <datei-oder-ordner>

git commit -m "kurze beschreibung"

git push


## Cleanup

Lokale Build-Ausgabe entfernen:

rmdir /s /q dist

Optional auch den PyInstaller-Arbeitsordner entfernen:

rmdir /s /q build

Nicht pauschal *.spec löschen. Sorterino.spec ist Teil des Projekts.


## Projektstand exportieren

.\docs\export_project.ps1 -Version vX.X.X

Der Export landet unter:

docs/Produktstände/


## Wichtige Pfade

assets/templates/       Konfigurations-Templates

assets/icons/           Icons

docs/diagrams/          Diagramme

docs/screenshots/       Screenshots

docs/Produktstände/     exportierte Projektstände

dist/Sorterino/         PyInstaller-Ausgabe

installer.iss           Inno-Setup-Skript

installer/              fertige Installer-EXEs

third_party/            lokale Tesseract-/Poppler-Binaries


## Hinweise

- Templates werden beim ersten Start in die Runtime kopiert.
- Runtime-Konfigurationen liegen unter `Sorterino - Runtime\configs`.
- Tesseract und Poppler laufen lokal.
- Für den Build müssen `third_party/tesseract` und `third_party/poppler` lokal vorhanden sein.
- Der Installer wird für den Release mit gepusht.
