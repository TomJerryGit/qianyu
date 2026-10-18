# Per-user portable installer for 浅语影音 0.9.
# No admin required; copies the PyInstaller folder and creates shortcuts.
#
# Install:   powershell -ExecutionPolicy Bypass -File packaging\install.ps1
# Uninstall: powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -Uninstall
# Test:      ... -Target D:\temp\QianYu -NoShortcuts -NoAssociations

param(
    [string]$Source = "",
    [string]$Target = "$env:LOCALAPPDATA\Programs\QianYu",
    [switch]$Uninstall,
    [switch]$NoShortcuts,
    [switch]$NoAssociations
)

$ErrorActionPreference = "Stop"
$exeName = "QianYu.exe"
$appName = "浅语影音"

function Remove-Shortcuts {
    $paths = @(
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Programs")) "$appName.lnk")
    )
    foreach ($path in $paths) {
        if (Test-Path $path) { Remove-Item $path -Force }
    }
}

if ($Uninstall) {
    $installedExe = Join-Path $Target $exeName
    if (Test-Path $installedExe) {
        try { Start-Process -FilePath $installedExe -ArgumentList "--unregister-associations" -Wait -WindowStyle Hidden } catch {}
    }
    Remove-Shortcuts
    if (Test-Path $Target) { Remove-Item $Target -Recurse -Force }
    Write-Host "已卸载：$Target"
    exit 0
}

if (-not $Source) {
    $Source = Join-Path (Split-Path -Parent $PSScriptRoot) "dist\QianYu"
}
$Source = (Resolve-Path $Source).Path
$sourceExe = Join-Path $Source $exeName
if (-not (Test-Path $sourceExe)) {
    throw "找不到 $sourceExe；请先运行 packaging\build.ps1 或指定 -Source"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item (Join-Path $Source "*") $Target -Recurse -Force
Write-Host "已复制到：$Target"

if (-not $NoShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $links = @(
        (Join-Path ([Environment]::GetFolderPath("Programs")) "$appName.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk")
    )
    foreach ($link in $links) {
        try {
            $shortcut = $shell.CreateShortcut($link)
            $shortcut.TargetPath = Join-Path $Target $exeName
            $shortcut.WorkingDirectory = $Target
            $shortcut.Description = "$appName 0.9"
            $shortcut.Save()
        } catch {
            Write-Warning "创建快捷方式失败：$link"
        }
    }
}

if (-not $NoAssociations) {
    try {
        Start-Process -FilePath (Join-Path $Target $exeName) -ArgumentList "--register-associations" -Wait -WindowStyle Hidden
        Write-Host "已注册音频文件关联（可在应用内取消）"
    } catch {
        Write-Warning "注册文件关联失败：$($_.Exception.Message)"
    }
}

Write-Host "安装完成：$Target\$exeName"
