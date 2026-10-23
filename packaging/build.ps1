# Build 浅语影音 0.9 (PyInstaller + optional Inno Setup installer).
param(
    [switch]$Installer,
    [switch]$SkipApp
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $SkipApp) {
    $venvPy = Join-Path $root "tools\venv311\Scripts\python.exe"
    if (Test-Path $venvPy) {
        & $venvPy -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\qianyu-pyside6.spec
    } else {
        pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\qianyu.spec
    }
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
}

if ($Installer) {
    $appDir = Join-Path $root "dist\QianYu"
    if (Test-Path $appDir) {
        foreach ($name in @("LICENSE", "COPYRIGHT", "NOTICE", "THIRD_PARTY_NOTICES.md", "SOURCE_OFFER.md")) {
            $source = Join-Path $root $name
            if (Test-Path $source) {
                Copy-Item $source (Join-Path $appDir $name) -Force
            }
        }
    }
    $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    $isccPath = $null
    if ($iscc) {
        $isccPath = $iscc.Source
    } else {
        $portable = Join-Path $root "tools\InnoSetup\ISCC.exe"
        if (Test-Path $portable) {
            $isccPath = $portable
        }
    }
    if (-not $isccPath) {
        throw "Inno Setup 6 (iscc.exe) not found. Install it or build the portable folder only."
    }
    & $isccPath packaging\qianyu.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
    Write-Host "Installer: dist\installer\QianYu-0.9.0-setup.exe"
} else {
    Write-Host "Portable build: dist\QianYu\QianYu.exe"
}

Write-Host "Code signing is not configured; sign dist\QianYu\* and the installer before release."
