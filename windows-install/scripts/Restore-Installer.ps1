param([string]$BundleRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
$relative = 'installers/deepseek-harness-0.2.1-rc.2-win-x64.exe'
$manifest = Get-Content -LiteralPath (Join-Path $BundleRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$entry = @($manifest.files | Where-Object { $_.path -eq $relative })
if ($entry.Count -ne 1) { throw 'Missing installer manifest entry' }
$target = Join-Path $BundleRoot $relative
if (Test-Path -LiteralPath $target) {
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $entry[0].sha256) { return }
    throw 'Existing installer checksum mismatch; inspect before replacing'
}
$parts = @($manifest.files | Where-Object { $_.path -like ($relative + '.part*') } | Sort-Object path)
if ($parts.Count -ne 5) { throw 'Expected five installer parts' }
foreach ($part in $parts) {
    $path = Join-Path $BundleRoot $part.path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $part.sha256) { throw "Part checksum mismatch: $path" }
}
$temp = $target + '.assembling-' + [Guid]::NewGuid().ToString('N')
$stream = [IO.File]::Open($temp,[IO.FileMode]::CreateNew)
try {
    foreach ($part in $parts) {
        $inputStream = [IO.File]::OpenRead((Join-Path $BundleRoot $part.path))
        try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() }
    }
} finally { $stream.Dispose() }
if ((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash -ne $entry[0].sha256) { throw "Assembled checksum mismatch: $temp" }
Move-Item -LiteralPath $temp -Destination $target
Write-Host 'Harness installer assembled and SHA256 verified.' -ForegroundColor Green
