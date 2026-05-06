$ErrorActionPreference = "Stop"

$generator = Join-Path $PSScriptRoot "generate_doku_assets.py"
$updater = Join-Path $PSScriptRoot "update_projektdoku_xml.py"

& python $generator
& python $updater
