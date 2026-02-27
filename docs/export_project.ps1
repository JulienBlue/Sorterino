param (
    [string]$Version = ""
)

Write-Host "Script started"

# Projekt-Root bestimmen
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# Ignorierte Root-Ordner
$IgnoredFolders = @(
    ".pytest_cache",
    ".venv",
    ".vscode",
    "backups",
    "docs",
    "logs",
    "third_party",
    "__pycache__"
)

# Nur existierende Root-Ordner berücksichtigen
$IgnoredFolders = $IgnoredFolders | Where-Object {
    Test-Path (Join-Path $ProjectRoot $_)
}

# Terminal-Ausgabe
Write-Host "`nIgnorierte Root-Ordner:`n"

foreach ($folder in $IgnoredFolders) {

    Write-Host " - $folder"

    $subItems = Get-ChildItem (Join-Path $ProjectRoot $folder) -Directory -ErrorAction SilentlyContinue

    if ($subItems) {
        $subItems | ForEach-Object {
            Write-Host "    -> $($_.Name)"
        }
    }
    else {
        Write-Host "    (leer oder keine Unterordner)"
    }

    Write-Host ""
}

# Output-Datei
$OutputFile = Join-Path $ScriptDir "Produktstände/Projektstand_$Version.txt"
if (Test-Path $OutputFile) { Remove-Item $OutputFile }

# Ignore-Regex robuster
$IgnorePattern = ($IgnoredFolders | ForEach-Object { "(\\|^)$_(\\|$)" }) -join "|"

# Dateiinhalt sammeln
$Content = @()

Get-ChildItem $ProjectRoot -Recurse -File |
Where-Object {
    $_.FullName -notmatch $IgnorePattern -and
    $_.Extension -match "\.(py|json|md|txt)$"
} |
Sort-Object FullName |
ForEach-Object {

    $Content += "===== $($_.FullName) ====="
    $Content += ""
    $Content += Get-Content $_.FullName
    $Content += "`n"
}

# Ignorierte Ordner ins File schreiben
$Content += "`n===== Ignorierte Root-Ordner =====`n"

foreach ($folder in $IgnoredFolders) {

    $Content += $folder

    $subItems = Get-ChildItem (Join-Path $ProjectRoot $folder) -Directory -ErrorAction SilentlyContinue

    if ($subItems) {
        $subItems | ForEach-Object {
            $Content += "  - $($_.Name)"
        }
    }
    else {
        $Content += "  (leer oder keine Unterordner)"
    }

    $Content += ""
}

# Einmaliges Schreiben (sauberer)
$Content | Set-Content $OutputFile -Encoding UTF8

Write-Host "Projektstand gespeichert unter: $OutputFile"