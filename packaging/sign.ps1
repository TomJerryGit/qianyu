# Sign the portable exe and/or Inno installer.
#
# Development (self-signed, NOT trusted by other machines):
#   powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -CreateSelfSigned
#
# Production, PFX:
#   powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
#     -Pfx C:\secure\qianyu-codesign.pfx -Password <password> -RequireTrusted
#
# Production, certificate in CurrentUser\My (hardware token / non-exportable):
#   powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
#     -Thumbprint <SHA1> -RequireTrusted
#
# If signtool is not on PATH, pass -Signtool "C:\...\signtool.exe" or install
# the Windows SDK Build Tools. Without signtool, Set-AuthenticodeSignature is
# used as a fallback (still requires a valid certificate).

param(
    [string[]]$Path = @("dist\QianYu\QianYu.exe", "dist\installer\QianYu-0.9.0-setup.exe"),
    [string]$Pfx = "",
    [string]$Password = "",
    [string]$Thumbprint = "",
    [string]$Signtool = "",
    [string]$Timestamp = "http://timestamp.digicert.com",
    [string]$Subject = "CN=QianYu Dev",
    [switch]$CreateSelfSigned,
    [switch]$NoTimestamp,
    [switch]$RequireTrusted
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Find-Signtool {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path -LiteralPath $Explicit) { return (Resolve-Path -LiteralPath $Explicit).Path }
        throw "signtool not found: $Explicit"
    }
    $onPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path $kits) {
        $candidate = Get-ChildItem $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }
    return $null
}

$cert = $null
if ($Pfx) {
    $secure = ConvertTo-SecureString $Password -AsPlainText -Force
    $cert = Import-PfxCertificate -FilePath $Pfx -CertStoreLocation Cert:\CurrentUser\My -Password $secure
    $Thumbprint = $cert.Thumbprint
    Write-Host "Using PFX certificate: $Thumbprint"
} elseif ($Thumbprint) {
    $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $Thumbprint } | Select-Object -First 1
    if (-not $cert) { throw "Certificate not found in CurrentUser\My: $Thumbprint" }
} elseif ($CreateSelfSigned) {
    $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $Subject -and $_.HasPrivateKey } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature -FriendlyName "QianYu Dev Code Signing"
        Write-Host "Created self-signed certificate: $($cert.Thumbprint)"
    }
    $Thumbprint = $cert.Thumbprint
} else {
    throw "Provide -Pfx/-Password, -Thumbprint, or use -CreateSelfSigned for development verification."
}

$signtoolPath = Find-Signtool -Explicit $Signtool
foreach ($file in $Path) {
    if (-not (Test-Path -LiteralPath $file)) {
        Write-Warning "Skipping missing file: $file"
        continue
    }
    if ($signtoolPath) {
        $arguments = @("sign", "/fd", "SHA256")
        if (-not $NoTimestamp) { $arguments += @("/tr", $Timestamp, "/td", "SHA256") }
        if ($Thumbprint) { $arguments += @("/sha1", $Thumbprint) }
        $arguments += $file
        Write-Host "signtool: $file"
        & $signtoolPath @arguments
        if ($LASTEXITCODE -ne 0) { throw "signtool failed for $file (exit $LASTEXITCODE)" }
    } else {
        if ($NoTimestamp) {
            $result = Set-AuthenticodeSignature -FilePath $file -Certificate $cert
        } else {
            $result = Set-AuthenticodeSignature -FilePath $file -Certificate $cert -TimestampServer $Timestamp
        }
        Write-Host "$file => $($result.Status)"
    }
    if ($RequireTrusted) {
        $status = (Get-AuthenticodeSignature -LiteralPath $file).Status
        if ($status -ne "Valid") { throw "Signature not trusted/valid for ${file}: $status" }
    }
}

if (-not $signtoolPath) {
    Write-Host "signtool not found; used Set-AuthenticodeSignature fallback."
}
Write-Host "Self-signed signatures are for development only; release requires a trusted code-signing certificate."
