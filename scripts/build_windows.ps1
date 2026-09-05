[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildDirectory = Join-Path $projectRoot "build"
$distDirectory = Join-Path $projectRoot "dist"
$releaseDirectory = Join-Path $projectRoot "release"
$appDirectory = Join-Path $distDirectory "CleanDesk"
$archivePath = Join-Path $releaseDirectory "CleanDesk-Windows-x64.zip"

Push-Location $projectRoot
try {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed; release build stopped."
    }

    foreach ($directory in @($buildDirectory, $distDirectory)) {
        if (Test-Path -LiteralPath $directory) {
            Remove-Item -LiteralPath $directory -Recurse -Force
        }
    }
    New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --windowed `
        --name CleanDesk `
        --collect-all pycaw `
        main.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    Copy-Item -LiteralPath "README.md" -Destination (Join-Path $appDirectory "README.md")
    $packageContents = Join-Path $appDirectory "*"
    Compress-Archive -Path $packageContents -DestinationPath $archivePath -CompressionLevel Optimal

    $archive = Get-Item -LiteralPath $archivePath
    $hash = Get-FileHash -LiteralPath $archivePath -Algorithm SHA256
    Write-Host "PACKAGE=$($archive.FullName)"
    Write-Host "SIZE_BYTES=$($archive.Length)"
    Write-Host "SHA256=$($hash.Hash)"
}
finally {
    Pop-Location
}
