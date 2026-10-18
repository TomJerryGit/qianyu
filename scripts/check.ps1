# Local verification helper (Windows PowerShell)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPYCACHEPREFIX = "$env:TEMP\qianyu-pycache"
$env:PYTHONIOENCODING = "utf-8"
python -m compileall -q src tests/unit
if ($LASTEXITCODE -ne 0) { throw "compile failed" }

python -m unittest tests.unit.test_core tests.unit.test_library tests.unit.test_windows tests.unit.test_update -v
if ($LASTEXITCODE -ne 0) { throw "core tests failed" }

if (Test-Path "libmpv-2.dll") {
    python -m unittest tests.unit.test_engine tests.unit.test_audio_quality -v
    if ($LASTEXITCODE -ne 0) { throw "engine tests failed" }
} else {
    Write-Host "libmpv-2.dll not found; skipping engine tests"
}

$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QPA_FONTDIR = "C:\Windows\Fonts"
python spike\ui_smoke.py
if ($LASTEXITCODE -ne 0) { throw "UI smoke failed" }
python spike\bench_library.py
Write-Host "ALL CHECKS DONE"
