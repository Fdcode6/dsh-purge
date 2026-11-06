$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
$bundleRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'Restore-Installer.ps1') -BundleRoot $bundleRoot

function Test-Bundle {
    $manifest = Get-Content -LiteralPath (Join-Path $bundleRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        $itemPath = [IO.Path]::GetFullPath((Join-Path $bundleRoot $entry.path))
        if (-not $itemPath.StartsWith($bundleRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'Invalid manifest path'
        }
        if (-not (Test-Path -LiteralPath $itemPath -PathType Leaf)) { throw "Missing: $itemPath" }
        if ((Get-FileHash -LiteralPath $itemPath -Algorithm SHA256).Hash -ne $entry.sha256) {
            throw "SHA256 mismatch: $itemPath"
        }
    }
    Write-Host 'Bundle integrity: PASS' -ForegroundColor Green
}

function Start-Installer([string]$name) {
    $installer = Join-Path $bundleRoot ('installers\' + $name)
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid') {
        throw "Installer signature is not Valid ($($signature.Status)); inspect manually: $installer"
    }
    Write-Host "Signer: $($signature.SignerCertificate.Subject)"
    # This is the interactive installer selected by the user.
    $p = Start-Process -FilePath $installer -PassThru -Wait
    Write-Host "Installer exit: $($p.ExitCode). Verify the application/driver separately."
}

function Disable-HarnessUpdates {
    $defaultInstall = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness'
    $installDir = Read-Host "Harness install directory (Enter for $defaultInstall)"
    if ([string]::IsNullOrWhiteSpace($installDir)) { $installDir = $defaultInstall }
    & (Join-Path $PSScriptRoot 'Disable-Harness-Updates.ps1') -InstallDir $installDir
}

function Find-Python313 {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        'C:\Python313\python.exe',
        (Join-Path $env:ProgramFiles 'Python313\python.exe')
    )
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $found = & $pyLauncher.Source -3.13 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $candidates = @($found) + $candidates }
    }
    foreach ($p in $candidates | Select-Object -Unique) {
        if (Test-Path -LiteralPath $p) {
            & $p -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,13) and sys.maxsize > 2**32 else 1)'
            if ($LASTEXITCODE -eq 0) { return $p }
        }
    }
    throw 'Python 3.13 x64 was not found. Install it with menu option 1; for a custom path, run offline_setup.py with that interpreter.'
}

Test-Bundle
while ($true) {
    Write-Host ''
    Write-Host '1 - Install Python 3.13.1 x64 (interactive)'
    Write-Host '2 - Install official DeepSeek Harness 0.2.1-rc.2 (interactive)'
    Write-Host '3 - Install Nmap 7.992 / Npcap (interactive)'
    Write-Host '4 - Configure plugin, cwd fix and all local tools (offline)'
    Write-Host '5 - Verify the 15 local tools'
    Write-Host '6 - Disable official Harness desktop updates (fully exit it first)'
    Write-Host '0 - Exit'
    $choice = Read-Host 'Choose'
    try {
        switch ($choice) {
            '1' { Start-Installer 'python-3.13.1-amd64.exe' }
            '2' {
                Write-Host 'At the installer finish screen, UNCHECK Launch DeepSeek Harness. Then this menu disables its update source.'
                Start-Installer 'deepseek-harness-0.2.1-rc.2-win-x64.exe'
                Disable-HarnessUpdates
            }
            '6' { Disable-HarnessUpdates }
            '3' { Start-Installer 'nmap-7.992-setup.exe' }
            { $_ -eq '4' -or $_ -eq '5' } {
                $python = Find-Python313
                $defaultRoot = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }
                Write-Host 'Use the actual desktop profile. Launch Harness once to initialize it, then fully exit it before option 4.'
                $selectedRoot = Read-Host "DSH_HOME (Enter for $defaultRoot)"
                if ([string]::IsNullOrWhiteSpace($selectedRoot)) { $selectedRoot = $defaultRoot }
                $mode = if ($choice -eq '4') { 'configure' } else { 'verify' }
                & $python (Join-Path $PSScriptRoot 'offline_setup.py') $mode --dsh-root $selectedRoot
                if ($LASTEXITCODE -ne 0) { throw 'Setup/verification failed. Read the error; do not mark it complete.' }
            }
            '0' { return }
            default { Write-Host 'Choose 0 through 6.' }
        }
    } catch { Write-Host $_.Exception.Message -ForegroundColor Red }
}
