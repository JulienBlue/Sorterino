param (
    [string]$Version = "dev"
)

Write-Host "Script started"

# Projekt-Root bestimmen
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# Ignoriert wird im Wesentlichen die .gitignore plus docs/.
# docs/ wird ausgelassen, damit alte Projektstand-Exporte nicht wieder
# in neue Projektstand-Exporte hineinkopiert werden.
$IgnoredPaths = @(
    ".agents",
    ".DS_Store",
    ".env",
    ".git",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "installer_output",
    "third_party",
    "Thumbs.db"
)

Write-Host ""
Write-Host "Ignorierte Pfade:"
$IgnoredPaths | ForEach-Object { Write-Host " - $_" }

# Output vorbereiten
$OutputDirName = "Produktst" + [char]0x00E4 + "nde"
$OutputDir = Join-Path $ScriptDir $OutputDirName

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$OutputFile = Join-Path $OutputDir "Projektstand_$Version.txt"

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile
}

function Is-Ignored($relativePath) {
    $rel = ($relativePath -replace "/", "\").TrimStart("\")
    $firstPart = ($rel -split "\\")[0]

    foreach ($ignored in $IgnoredPaths) {
        $ign = ($ignored -replace "/", "\").Trim("\")

        if ($rel -eq $ign) {
            return $true
        }

        if ($firstPart -eq $ign) {
            return $true
        }
    }

    return $false
}

# Dateien sammeln
$Content = @()

Get-ChildItem -Path $ProjectRoot -Recurse -File -Force |
Where-Object {
    $relative = $_.FullName.Replace($ProjectRoot, "").TrimStart("\")

    (-not (Is-Ignored $relative)) -and
    ($_.Extension -match "\.(py|json|md|txt|iss|spec)$")
} |
Sort-Object FullName |
ForEach-Object {
    $relative = $_.FullName.Replace($ProjectRoot, "").TrimStart("\")

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

$Content += ""
$Content += "===== Ignorierte Pfade ====="
$Content += ""

$IgnoredPaths | ForEach-Object { $Content += $_ }

$Content | Out-File $OutputFile -Encoding utf8

Write-Host ""
Write-Host "Projektstand gespeichert unter:"
Write-Host $OutputFile
