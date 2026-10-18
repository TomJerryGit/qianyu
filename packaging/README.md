# 打包与安装

## 便携目录

```powershell
& 'D:\qianyu\tools\venv311\Scripts\python.exe' -m PyInstaller --noconfirm packaging\qianyu-pyside6.spec
# 产物：dist-pyside6\QianYu\QianYu.exe（PySide6 / Python 3.11）
```

## 安装器

- `install.ps1`：按用户复制到 `%LOCALAPPDATA%\Programs\QianYu`，创建开始菜单/桌面快捷方式，可选注册音频关联；无需管理员。`-Uninstall` 卸载。已用 PySide6 包验证安装/启动/卸载。
- `qianyu.iss`：Inno Setup 6 安装包脚本；本机已安装 6.7.3 到 `tools\InnoSetup`，`build.ps1 -Installer` 会优先用 PATH 的 iscc，找不到再用该目录。
- 最新安装包：`dist\installer\QianYu-0.9.0-setup.exe`（基于 PySide6，未签名）。
- 沙箱验证：`qianyu-sandbox.iss` 使用 `CreateUninstallRegKey=no`，已完成安装 → `--smoke` 0 → 卸载删除；生产包仍需真实桌面写卸载注册表。

```powershell
# 免 Inno 的按用户安装（先运行 build.ps1 生成 dist\QianYu）
powershell -ExecutionPolicy Bypass -File packaging\install.ps1

# 使用已有构建产物
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -Source dist-pyside6\QianYu

# 卸载
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -Uninstall

# Inno Setup（可选）
packaging\build.ps1 -Installer
```

> Inno Setup 6.7.3 已安装到 `tools\InnoSetup`；安装包已编译。签名/自动更新仍需发布工程。
