param(
    [string]$AppVersion,
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $AppVersion) {
    $VersionSource = Get-Content "src\version.py" -Raw
    $VersionMatch = [regex]::Match($VersionSource, 'APP_VERSION\s*=\s*"(?<version>\d+\.\d+\.\d+)(?:beta)?"')
    if (-not $VersionMatch.Success) {
        throw "APP_VERSION konnte nicht aus src\version.py gelesen werden."
    }
    $AppVersion = $VersionMatch.Groups["version"].Value + ".0"
}

if ($AppVersion -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Die MSIX-Version muss vier numerische Bestandteile haben, z. B. 2.2.4.0."
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtuelle Umgebung fehlt: $Python"
}

if (-not $SkipPyInstaller) {
    & $Python -m PyInstaller --noconfirm --clean "Sorterino.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller-Build fehlgeschlagen."
    }
}

$AppSource = Join-Path $ProjectRoot "dist\Sorterino"
if (-not (Test-Path (Join-Path $AppSource "Sorterino.exe"))) {
    throw "dist\Sorterino\Sorterino.exe fehlt. Baue Sorterino zuerst mit PyInstaller."
}

$MakeAppxCandidates = @(
    (Get-Command MakeAppx.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\MakeAppx.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName)
) | Where-Object { $_ } | Select-Object -First 1

if (-not $MakeAppxCandidates) {
    throw "MakeAppx.exe fehlt. Installiere das Windows 10/11 SDK mit den Signing Tools."
}
$MakeAppx = $MakeAppxCandidates

$StageRoot = Join-Path $ProjectRoot "build\msix"
$PackageRoot = Join-Path $StageRoot "package"
$OutputRoot = Join-Path $ProjectRoot "installer\store"
$OutputFile = Join-Path $OutputRoot "Sorterino_$($AppVersion)_x64.msix"

$ResolvedProjectRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
$ResolvedPackageRoot = [IO.Path]::GetFullPath($PackageRoot)
if (-not $ResolvedPackageRoot.StartsWith($ResolvedProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Der MSIX-Stagingpfad liegt außerhalb des Projektverzeichnisses."
}

if (Test-Path $PackageRoot) {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $PackageRoot "Sorterino") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $PackageRoot "Assets") -Force | Out-Null
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

Copy-Item -Path (Join-Path $AppSource "*") -Destination (Join-Path $PackageRoot "Sorterino") -Recurse -Force

# The upstream distributions contain training, diagnostic and uninstall tools
# that Sorterino never executes. Keep only the OCR/PDF command line programs
# actually used by the application; DLLs and data files remain untouched.
$ThirdPartyRoot = Join-Path $PackageRoot "Sorterino\_internal\third_party"
$AllowedThirdPartyExecutables = @(
    "poppler\Library\bin\pdfinfo.exe",
    "poppler\Library\bin\pdftoppm.exe",
    "poppler\Library\bin\pdftocairo.exe",
    "tesseract\tesseract.exe"
)
if (Test-Path $ThirdPartyRoot) {
    Get-ChildItem $ThirdPartyRoot -Recurse -Filter "*.exe" | ForEach-Object {
        $RelativePath = $_.FullName.Substring($ThirdPartyRoot.Length + 1)
        if ($AllowedThirdPartyExecutables -notcontains $RelativePath) {
            Remove-Item -LiteralPath $_.FullName -Force
        }
    }
}

$ManifestTemplate = Get-Content "store\AppxManifest.xml.in" -Raw
$Manifest = $ManifestTemplate.Replace("@PACKAGE_VERSION@", $AppVersion)
Set-Content -LiteralPath (Join-Path $PackageRoot "AppxManifest.xml") -Value $Manifest -Encoding utf8

& $Python "tools\create_msix_assets.py" `
    --source "assets\icons\default_icon_128.ico" `
    --output (Join-Path $PackageRoot "Assets")
if ($LASTEXITCODE -ne 0) {
    throw "MSIX-Bildressourcen konnten nicht erzeugt werden."
}

if (Test-Path $OutputFile) {
    Remove-Item -LiteralPath $OutputFile -Force
}

& $MakeAppx pack /d $PackageRoot /p $OutputFile /o
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx konnte das MSIX-Paket nicht erzeugen."
}

Write-Host "MSIX erstellt: $OutputFile"
Write-Host "Dieses Paket ist für den Upload ins Partner Center noch absichtlich unsigniert."
