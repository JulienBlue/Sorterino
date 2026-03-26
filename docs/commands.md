# 📦 Sorterino – Commands & Workflow

Diese Datei wurde automatisch generiert.

# 🚀 Projekt starten

python main.py

# 🖥 GUI starten

python -m src.gui.app

# ⚙️ Virtuelle Umgebung

python -m venv .venv
.venv\Scripts\Activate
source .venv/bin/activate

# 📥 Abhängigkeiten

pip install -r requirements.txt
pip freeze > requirements.txt

# 📊 Projektstand exportieren

.\docs\export_project.ps1 -Version vX.X.X

# 🔍 Git Workflow

git status
git add .
git commit -m "Beschreibung"
git push

# 🏷 Versionierung

git tag -a vX.X.X -m "Sorterino Version"
git push origin vX.X.X

# 🧹 Cleanup

rmdir /s /q dist
rmdir /s /q build

# 🛠 Build

pyinstaller src/gui/app.py

# 📦 Installer

build_tools/installer.iss

# 📁 Struktur

* Anwendung: dist/Sorterino/
* Produktstände: docs/Produktstände/
* Build-Tools: build_tools/

# 💡 Hinweise

* Build-Artefakte sind nicht im Git enthalten
* OCR läuft lokal