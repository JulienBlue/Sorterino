param (
    [string]$Version = "0.1.0"
)

Write-Host "Script started"

# -------------------------------------------------
# Projekt-Root bestimmen
# -------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# -------------------------------------------------
# Ignorierte Oberordner definieren
# -------------------------------------------------
$IgnoredFolders = @(
    ".git",
    ".venv",
    "third_party",
    "__pycache__",
    ".pytest_cache",
    ".sorterino_runtime"
)

# -------------------------------------------------
# Ignorierte Inhalte sammeln
# -------------------------------------------------
$IgnoredDetails = @{}

foreach ($folder in $IgnoredFolders) {

    $fullPath = Join-Path $ProjectRoot $folder

    if (Test-Path $fullPath) {

        $subItems = Get-ChildItem $fullPath -Directory | Select-Object -ExpandProperty Name
        $IgnoredDetails[$folder] = $subItems
    }
}

# -------------------------------------------------
# Ausgabe im Terminal
# -------------------------------------------------
Write-Host ""
Write-Host "Ignorierte Oberordner und deren erste Ebene:"
Write-Host ""

foreach ($folder in $IgnoredDetails.Keys) {

    Write-Host " - $folder"

    foreach ($sub in $IgnoredDetails[$folder]) {
        Write-Host "    -> $sub"
    }

    if (-not $IgnoredDetails[$folder]) {
        Write-Host "    (leer oder keine Unterordner)"
    }

    Write-Host ""
}

# -------------------------------------------------
# Output-Datei in docs speichern
# -------------------------------------------------
$OutputFile = Join-Path $ScriptDir "Projektstand_$Version.txt"

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile
}

# -------------------------------------------------
# Ignorier-Regex bauen
# -------------------------------------------------
$IgnorePattern = ($IgnoredFolders | ForEach-Object { "\\$_\\" }) -join "|"

# -------------------------------------------------
# Projekt scannen
# -------------------------------------------------
Get-ChildItem $ProjectRoot -Recurse -File `
| Where-Object {
    $_.FullName -notmatch $IgnorePattern -and
    $_.Extension -match "\.(py|json|md|txt)$"
} `
| Sort-Object FullName `
| ForEach-Object {

    Add-Content $OutputFile "===== $($_.FullName) ====="
    Add-Content $OutputFile ""
    Get-Content $_.FullName | Add-Content $OutputFile
    Add-Content $OutputFile "`n"
}

# -------------------------------------------------
# Ignorierte Ordner auch ins File schreiben
# -------------------------------------------------
Add-Content $OutputFile "`n"
Add-Content $OutputFile "===== Ignorierte Oberordner ====="
Add-Content $OutputFile ""

foreach ($folder in $IgnoredDetails.Keys) {

    Add-Content $OutputFile $folder

    foreach ($sub in $IgnoredDetails[$folder]) {
        Add-Content $OutputFile "  - $sub"
    }

    if (-not $IgnoredDetails[$folder]) {
        Add-Content $OutputFile "  (leer oder keine Unterordner)"
    }

    Add-Content $OutputFile ""
}

Write-Host "Projektstand wurde gespeichert unter: $OutputFile"