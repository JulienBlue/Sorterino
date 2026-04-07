# 📦 Sorterino – Commands & Workflow

## 🚀 Projekt starten
python main.py

## 🖥 GUI starten
python -m src.gui.app

## ⚙️ Virtuelle Umgebung
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / Mac

## 📥 Abhängigkeiten
pip install -r requirements.txt
pip freeze > requirements.txt

## 📊 Projektstand exportieren
.\docs\export_project.ps1 -Version vX.X.X

## 🔍 Git Workflow
git status
git add .
git commit -m "Beschreibung"
git push

## 🏷 Versionierung (Release)
git add .
git commit -m "release: vX.X.X"

git tag -a vX.X.X -m "Sorterino vX.X.X"
git push origin main
git push origin vX.X.X

## 🧹 Cleanup (Build-Artefakte)
rmdir /s /q dist
rmdir /s /q build
del /s /q *.spec

## 🛠 Build (EXE)
pyinstaller Sorterino.spec --noconfirm

## 🐞 Debug Build (mit Konsole)
pyinstaller Sorterino.spec --noconfirm --debug=all

## 📦 Installer erstellen
iscc installer_docs/installer.iss

## 📁 Wichtige Projektstruktur
* Anwendung: `dist/Sorterino/`
* Templates: `assets/templates/`
* Icons: `assets/icons/`
* Installer: `installer_docs/`
* Produktstände: `docs/Produktstände/`

## 💡 Hinweise
* Templates werden zur Laufzeit in die Runtime kopiert
* Build-Artefakte sind nicht im Git enthalten
* OCR (Tesseract + Poppler) läuft vollständig lokal
* Für Releases immer Tag verwenden (vX.X.X)

## 🔥 Typischer Release-Flow
git add .
git commit -m "release: v0.7.0"

git tag -a v0.7.0 -m "Sorterino v0.7.0"
git push origin main
git push origin v0.7.0

rmdir /s /q dist
rmdir /s /q build




pyinstaller Sorterino.spec --noconfirm

iscc installer.iss