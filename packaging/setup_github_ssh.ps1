# Configure GitHub SSH access for this repository.
#
# Option A: add the public key in GitHub UI:
#   Settings -> SSH and GPG keys -> New SSH key
#
# Option B: let this script add it through the GitHub API (token needs
# "admin:public_key" for classic PAT, or Account "Git SSH keys: write"):
#   $env:GITHUB_TOKEN = "..."
#   powershell -ExecutionPolicy Bypass -File packaging\setup_github_ssh.ps1
#
# Then this script switches origin to SSH and pushes.

param(
    [string]$Repo = "TomJerryGit/qianyu",
    [string]$Key = "D:\qianyu\tools\ssh\qianyu_ed25519",
    [string]$Token = $env:GITHUB_TOKEN,
    [switch]$AssumedAdded,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$git = "C:\Program Files\Git\cmd\git.exe"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$pubPath = "$Key.pub"
if (-not (Test-Path $Key)) { throw "SSH private key not found: $Key" }
if (-not (Test-Path $pubPath)) { throw "SSH public key not found: $pubPath" }
$public = (Get-Content $pubPath -Raw).Trim()

# OpenSSH refuses overly permissive private keys on Windows.
try {
    & icacls $Key /inheritance:r /grant:r "$($env:USERNAME):(R)" | Out-Null
} catch {
    Write-Warning "Could not tighten key ACL: $($_.Exception.Message)"
}

Write-Host "Public key:"
Write-Host $public

if ($Token) {
    $headers = @{
        Authorization = "Bearer $Token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    try {
        Invoke-RestMethod -Method Post -Uri "https://api.github.com/user/keys" `
            -Headers $headers -ContentType "application/json" `
            -Body (@{ title = "QianYu Windows"; key = $public } | ConvertTo-Json) | Out-Null
        Write-Host "SSH key added to GitHub."
    } catch {
        Write-Host "GitHub API key add failed (maybe already present): $($_.Exception.Message)"
    }
} else {
    Write-Host "No GITHUB_TOKEN provided. Add the key manually in GitHub Settings -> SSH and GPG keys."
    if (-not $AssumedAdded) {
        Write-Host "After adding it, run again with -AssumedAdded."
        exit 0
    }
}

$env:GIT_SSH_COMMAND = "`"$ssh`" -i `"$Key`" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
& $git -C D:\qianyu remote set-url origin "git@github.com:$Repo.git"
Write-Host "Remote: $(& $git -C D:\qianyu remote get-url origin)"

# GitHub returns exit code 1 for a successful SSH auth message.
& $ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | ForEach-Object { Write-Host $_ }
if (-not $SkipPush) {
    & $git -C D:\qianyu push -u origin main
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }
}
