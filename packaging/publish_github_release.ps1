# Publish a GitHub Release and configure the libmpv Actions variables.
#
# Requires a PAT with repo scope:
#   $env:GITHUB_TOKEN = "github_pat_..."
#   powershell -ExecutionPolicy Bypass -File packaging\publish_github_release.ps1
#
# This does NOT sign anything. It publishes the unsigned RC and lets the
# release workflow use the uploaded libmpv asset.

param(
    [string]$Repo = "TomJerryGit/qianyu",
    [string]$Tag = "v0.9.0",
    [string]$Assets = "dist\github-release",
    [string]$Token = $env:GITHUB_TOKEN
)

$ErrorActionPreference = "Stop"
if (-not $Token) { throw "Set GITHUB_TOKEN (repo scope) before running." }
$headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}
$root = Split-Path -Parent $PSScriptRoot
$assetDir = if ([System.IO.Path]::IsPathRooted($Assets)) { $Assets } else { Join-Path $root $Assets }
$api = "https://api.github.com/repos/$Repo"

function Invoke-GitHub([string]$Method, [string]$Uri, $Body = $null) {
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 5)
}

$release = $null
try {
    $release = Invoke-GitHub "POST" "$api/releases" @{
        tag_name = $Tag
        target_commitish = "main"
        name = "QianYu 0.9.0"
        body = "QianYu 0.9.0 RC. Unsigned until SignPath Foundation signing is approved."
        draft = $true
        prerelease = $true
    }
    Write-Host "Created draft release $($release.id)"
} catch {
    Write-Host "Release create failed, trying existing tag: $($_.Exception.Message)"
    $release = Invoke-GitHub "GET" "$api/releases/tags/$Tag"
}

$uploadBase = ($release.upload_url -replace "\{.*$", "")
foreach ($file in Get-ChildItem $assetDir -File) {
    if ($file.Name -in @("README-upload.md", "SIGNPATH_APPLICATION.txt")) { continue }
    $uri = "$uploadBase?name=$([uri]::EscapeDataString($file.Name))"
    try {
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
            -ContentType "application/octet-stream" -InFile $file.FullName | Out-Null
        Write-Host "Uploaded $($file.Name)"
    } catch {
        Write-Warning "Upload skipped/failed for $($file.Name): $($_.Exception.Message)"
    }
}

$libmpvUrl = "https://github.com/$Repo/releases/download/$Tag/libmpv-2.dll"
$libmpvHash = (Get-FileHash (Join-Path $assetDir "libmpv-2.dll") -Algorithm SHA256).Hash.ToLowerInvariant()

function Set-ActionVariable([string]$Name, [string]$Value) {
    try {
        Invoke-GitHub "POST" "$api/actions/variables" @{ name = $Name; value = $Value } | Out-Null
    } catch {
        Invoke-GitHub "PATCH" "$api/actions/variables/$Name" @{ name = $Name; value = $Value } | Out-Null
    }
    Write-Host "Variable set: $Name"
}

Set-ActionVariable "LIBMPV_URL" $libmpvUrl
Set-ActionVariable "LIBMPV_SHA256" $libmpvHash

# Publish last: this creates the tag and triggers release.yml only after the
# libmpv asset and Actions variables exist.
Invoke-GitHub "PATCH" "$api/releases/$($release.id)" @{ draft = $false } | Out-Null
Write-Host "Published release $($release.id)"

Write-Host "Release: https://github.com/$Repo/releases/tag/$Tag"
Write-Host "Next: https://signpath.org/apply"
