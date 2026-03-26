param ()

Write-Host "Generate commands.md gestartet..."

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# -------------------------------
# Helper
# -------------------------------

function Exists($path) {
    return Test-Path (Join-Path $ProjectRoot $path)
}

# -------------------------------
# Dynamische Checks
# -------------------------------

$HasDist = Exists "dist"
$HasBuildTools = Exists "build_tools"
$HasDocs = Exists "docs"
$HasProduktstaende = Exists "docs\Produktstände"
$HasInstaller = Exists "build_tools\installer.iss"

# -------------------------------
# Content Builder
# -------------------------------

$Content = @()

$Content += "# 📦 Sorterino – Commands & Workflow"
$Content += ""
$Content += "Diese Datei wurde automatisch generiert."
$Content += ""

# 🚀 Start
$Content += "# 🚀 Projekt starten"
$Content += ""
$Content += "python main.py"
$Content += ""

# 🖥 GUI
$Content += "# 🖥 GUI starten"
$Content += ""
$Content += "python -m src.gui.app"
$Content += ""

# ⚙️ Venv
$Content += "# ⚙️ Virtuelle Umgebung"
$Content += ""
$Content += "python -m venv .venv"
$Content += ".venv\Scripts\Activate"
$Content += "source .venv/bin/activate"
$Content += ""

# 📥 Pip
$Content += "# 📥 Abhängigkeiten"
$Content += ""
$Content += "pip install -r requirements.txt"
$Content += "pip freeze > requirements.txt"
$Content += ""

# 📊 Export
if ($HasDocs) {
    $Content += "# 📊 Projektstand exportieren"
    $Content += ""
    $Content += ".\docs\export_project.ps1 -Version vX.X.X"
    $Content += ""
}

# 🔍 Git
$Content += "# 🔍 Git Workflow"
$Content += ""
$Content += "git status"
$Content += "git add ."
$Content += 'git commit -m "Beschreibung"'
$Content += "git push"
$Content += ""

# 🏷 Version
$Content += "# 🏷 Versionierung"
$Content += ""
$Content += 'git tag -a vX.X.X -m "Sorterino Version"'
$Content += "git push origin vX.X.X"
$Content += ""

# 🧹 Cleanup
$Content += "# 🧹 Cleanup"
$Content += ""
$Content += "rmdir /s /q dist"
$Content += "rmdir /s /q build"
$Content += ""

# 🛠 Build
$Content += "# 🛠 Build"
$Content += ""
$Content += "pyinstaller src/gui/app.py"
$Content += ""

# 📦 Installer
if ($HasInstaller) {
    $Content += "# 📦 Installer"
    $Content += ""
    $Content += "build_tools/installer.iss"
    $Content += ""
}

# 📁 Struktur
$Content += "# 📁 Struktur"
$Content += ""

if ($HasDist) {
    $Content += "* Anwendung: dist/Sorterino/"
}

if ($HasProduktstaende) {
    $Content += "* Produktstände: docs/Produktstände/"
}

if ($HasBuildTools) {
    $Content += "* Build-Tools: build_tools/"
}

$Content += ""

# 💡 Hinweise
$Content += "# 💡 Hinweise"
$Content += ""
$Content += "* Build-Artefakte sind nicht im Git enthalten"
$Content += "* OCR läuft lokal"
$Content += ""

# -------------------------------
# Schreiben
# -------------------------------

$DocsDir = Join-Path $ProjectRoot "docs"

if (-not (Test-Path $DocsDir)) {
    New-Item -ItemType Directory -Path $DocsDir | Out-Null
}

$OutputFile = Join-Path $DocsDir "commands.md"

$Content | Out-File $OutputFile -Encoding utf8

Write-Host "commands.md wurde erstellt:"
Write-Host $OutputFile