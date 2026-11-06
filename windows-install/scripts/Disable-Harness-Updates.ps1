param([string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness'))
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
$installRoot = [IO.Path]::GetFullPath($InstallDir)
if (-not (Test-Path -LiteralPath (Join-Path $installRoot 'DeepSeek Harness.exe') -PathType Leaf)) { throw "Harness executable not found: $installRoot" }
if (Get-Process 'DeepSeek Harness' -ErrorAction SilentlyContinue) { throw 'Fully exit Harness, including its tray icon, then run menu option 6 again.' }
$resources = Join-Path $installRoot 'resources'
$source = Join-Path $resources 'app-update.yml'
$disabled = Join-Path $resources 'app-update.yml.disabled-local-repair'
if (Test-Path -LiteralPath $source) {
    if (Test-Path -LiteralPath $disabled) { throw 'Both update configs exist. Inspect them before changing either file.' }
    $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    Rename-Item -LiteralPath $source -NewName 'app-update.yml.disabled-local-repair'
    if ((Get-FileHash -LiteralPath $disabled -Algorithm SHA256).Hash -ne $hash) { throw 'Preserved config hash mismatch' }
}
if ((Test-Path -LiteralPath $source) -or -not (Test-Path -LiteralPath $disabled)) { throw 'Update-source disable verification failed' }
Write-Host 'PASS: official desktop update source disabled; original config preserved.' -ForegroundColor Green
