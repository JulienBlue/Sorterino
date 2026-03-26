param (
    [string]$Version = "dev"
)

Write-Host "Script started"

# -------------------------------
# Projekt-Root bestimmen
# -------------------------------

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# -------------------------------
# Ignore-Liste (einfach & klar!)
# -------------------------------

$IgnoredFolders = @(
    ".pytest_cache",
    ".venv",
    ".vscode",
    "docs\Produktstände",
    "build",
    "dist",
    "__pycache__"
)

# -------------------------------
# Anzeige
# -------------------------------

Write-Host ""
Write-Host "Ignorierte Ordner:"
$IgnoredFolders | ForEach-Object { Write-Host " - $_" }

# -------------------------------
# Output vorbereiten
# -------------------------------

$OutputDir = Join-Path $ScriptDir "Produktstände"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$OutputFile = Join-Path $OutputDir "Projektstand_$Version.txt"

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile
}

# -------------------------------
# IGNORE CHECK (JETZT RICHTIG)
# -------------------------------

function Is-Ignored($relativePath) {

    $rel = $relativePath -replace "/", "\"

    foreach ($ignored in $IgnoredFolders) {

        $ign = $ignored -replace "/", "\"

        # enthält Ordner irgendwo im Pfad
        if ($rel -like "*$ign*") {
            return $true
        }
    }

    return $false
}

# -------------------------------
# Dateien sammeln
# -------------------------------

$Content = @()

Get-ChildItem -Path $ProjectRoot -Recurse -File -Force |
Where-Object {

    $relative = $_.FullName.Replace($ProjectRoot, "").TrimStart("\\")

    (-not (Is-Ignored $relative)) -and
    ($_.Extension -match "\.(py|json|md|txt|iss)$")
} |
Sort-Object FullName |
ForEach-Object {

    $relative = $_.FullName.Replace($ProjectRoot, "").TrimStart("\\")

    $Content += "===== $relative ====="
    $Content += ""

    try {
        $Content += Get-Content $_.FullName -ErrorAction Stop
    }
    catch {
        $Content += "[Fehler beim Lesen]"
    }

    $Content += ""
}

# -------------------------------
# Ignorierte Ordner anhängen
# -------------------------------

$Content += ""
$Content += "===== Ignorierte Ordner ====="
$Content += ""

$IgnoredFolders | ForEach-Object { $Content += $_ }

# -------------------------------
# Schreiben
# -------------------------------

$Content | Out-File $OutputFile -Encoding utf8BOM

Write-Host ""
Write-Host "Projektstand gespeichert unter:"
Write-Host $OutputFile