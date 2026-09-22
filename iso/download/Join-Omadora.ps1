$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$target = Join-Path $PSScriptRoot 'Omadora-44-x86_64.iso'
$expected = '9d503966771259684490fd22bd6eda5fc73d8b4f9e0dd6c81d03cc51709e3488'
if (Test-Path -LiteralPath $target) { throw 'An ISO already exists here. Move it elsewhere before joining the parts.' }
$parts = @('Omadora-44-x86_64.iso.part1', 'Omadora-44-x86_64.iso.part2')
foreach ($part in $parts) {
    if (-not (Test-Path -LiteralPath $part -PathType Leaf)) { throw "Missing $part. Download both parts into this folder." }
}
$output = [System.IO.File]::Open($target, [System.IO.FileMode]::CreateNew)
try {
    foreach ($part in $parts) {
        Write-Host "Combining $part..."
        $inputStream = [System.IO.File]::OpenRead((Join-Path $PSScriptRoot $part))
        try { $inputStream.CopyTo($output) } finally { $inputStream.Dispose() }
    }
} finally { $output.Dispose() }
Write-Host 'Checking the completed ISO...'
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $expected) {
    throw 'Checksum mismatch. Do not flash this ISO. Move the failed ISO out of this folder, download the parts again and retry.'
}
Write-Host 'Verified! Select Omadora-44-x86_64.iso in Fedora Media Writer to write your USB.'
