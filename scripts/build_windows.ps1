[CmdletBinding()]
param([string]$Python = "python")

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$releaseDirectory = Join-Path $projectRoot "release"

Push-Location $projectRoot
try {
    & $Python -c "import struct, sys; sys.exit(0 if sys.platform == 'win32' and struct.calcsize('P') == 8 else 1)"
    if ($LASTEXITCODE -ne 0) { throw "Build requires 64-bit Windows Python." }

    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; release build stopped." }

    New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx `
        --name CleanDesk --distpath $releaseDirectory --collect-all pycaw main.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

    $executable = Get-Item -LiteralPath (Join-Path $releaseDirectory "CleanDesk.exe")
    $hash = Get-FileHash -LiteralPath $executable.FullName -Algorithm SHA256
    "$($hash.Hash.ToLowerInvariant())  CleanDesk.exe" | Set-Content `
        -LiteralPath (Join-Path $releaseDirectory "SHA256SUMS.txt") -Encoding ascii
    Write-Host "EXE=$($executable.FullName)"
    Write-Host "SIZE_BYTES=$($executable.Length)"
    Write-Host "SHA256=$($hash.Hash)"
}
finally { Pop-Location }
