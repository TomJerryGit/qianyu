#requires -Version 5.1
param(
    [string]$Version = "0.9.0",
    [switch]$SkipBuild,
    [string]$Pfx = "",
    [string]$Password = "",
    [string]$CertThumbprint = "",
    [string]$Signtool = "",
    [string]$Timestamp = "http://timestamp.digicert.com",
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Dist = Join-Path $Root "dist"
$AppDist = Join-Path $Root "dist-pyside6"
$Installer = Join-Path $Dist "installer\QianYu-$Version-setup.exe"
$Portable = Join-Path $Dist "QianYu-$Version-portable.zip"
$Manifest = Join-Path $Dist "release.json"

if (-not $SkipBuild) {
    & (Join-Path $Root "packaging\build.ps1") -Installer
}

if (-not (Test-Path $Installer)) { throw "installer not found: $Installer" }

if ($Pfx -or $CertThumbprint) {
    $signArgs = @{
        Path = @($Installer, (Join-Path $Dist "QianYu\QianYu.exe"))
        Timestamp = $Timestamp
    }
    if ($Pfx) { $signArgs.Pfx = $Pfx; $signArgs.Password = $Password }
    if ($CertThumbprint) { $signArgs.Thumbprint = $CertThumbprint }
    if ($Signtool) { $signArgs.Signtool = $Signtool }
    if ($RequireSignature) { $signArgs.RequireTrusted = $true }
    & (Join-Path $Root "packaging\sign.ps1") @signArgs
}

if ($RequireSignature) {
    $signature = Get-AuthenticodeSignature -LiteralPath $Installer
    if ($signature.Status -ne "Valid") {
        throw "Release blocked: installer signature status is $($signature.Status), expected Valid."
    }
    Write-Host "Signature verified: $($signature.SignerCertificate.Subject)"
}

$AppDir = Join-Path $AppDist "QianYu"
if (-not (Test-Path $AppDir)) { throw "app build not found: $AppDir" }
if (Test-Path $Portable) { Remove-Item $Portable -Force }
Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $Portable -CompressionLevel Optimal

function Get-Sha256([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$files = @($Installer, $Portable)
$entries = foreach ($file in $files) {
    [ordered]@{
        name = Split-Path -Leaf $file
        size = (Get-Item -LiteralPath $file).Length
        sha256 = Get-Sha256 $file
    }
}

$release = [ordered]@{
    product = "QianYu"
    version = $Version
    built_at = (Get-Date).ToUniversalTime().ToString("o")
    platform = "windows-x64"
    qt = "PySide6 6.8.3"
    python = "3.11"
    files = @($entries)
    notes = "CUE/album playback, online metadata/lyrics/cover, tag editing, duplicate detection."
}
$release | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Manifest -Encoding UTF8

$lines = foreach ($entry in $entries) { "$($entry.sha256)  $($entry.name)" }
$lines | Set-Content -LiteralPath (Join-Path $Dist "installer\SHA256SUMS.txt") -Encoding ASCII

Write-Host "Portable: $Portable"
Write-Host "Manifest: $Manifest"
Write-Host "Installer SHA256: $((Get-Sha256 $Installer))"
