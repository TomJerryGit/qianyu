# 生产发布链

## 一键发布

```powershell
powershell -ExecutionPolicy Bypass -File packaging\release.ps1 -Version 0.9.0
```

产物：

- `dist/installer/QianYu-0.9.0-setup.exe`
- `dist/QianYu-0.9.0-portable.zip`
- `dist/release.json`（版本、构建时间、文件大小、SHA-256）
- `dist/installer/SHA256SUMS.txt`

## 代码签名

### 1. 先拿到受信任证书

不能使用自签名证书做生产发布。可选：

- **OV/EV Code Signing 证书**：DigiCert、Sectigo、GlobalSign、SSL.com 等；
- 需要提交企业/个人信息、电话/域名验证；
- 2023 年 6 月后 CA/B 规则要求 OV/EV 私钥放在 **硬件 token/HSM**，很多证书不能导出 PFX；
- EV 证书对 SmartScreen 信誉更有利，但仍需时间积累。

证书必须具备：

- Extended Key Usage: **Code Signing (1.3.6.1.5.5.7.3.3)**；
- 私钥可访问；
- SHA-256；
- 未过期。

### 2. 安装 signtool

安装 Windows SDK：

- 下载 Windows SDK 安装器；
- 勾选 **Windows SDK Signing Tools for Desktop Apps**；
- 或安装 Visual Studio Build Tools 的 Windows SDK 组件。

验证：

```powershell
signtool /?
```

常见路径：

```
C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe
```

如果不在 PATH，用 `-Signtool` 显式传入。

### 3. 签名并发布

**方式 A：PFX 可导出**

```powershell
powershell -ExecutionPolicy Bypass -File packaging\release.ps1 `
  -Version 0.9.0 `
  -Pfx C:\secure\qianyu-codesign.pfx `
  -Password "<PFX密码>" `
  -Signtool "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe" `
  -RequireSignature
```

**方式 B：证书在 CurrentUser\My（硬件 token，常用）**

```powershell
# 查看指纹
Get-ChildItem Cert:\CurrentUser\My |
  Where-Object { $_.HasPrivateKey } |
  Format-Table Subject,Thumbprint,NotAfter

powershell -ExecutionPolicy Bypass -File packaging\release.ps1 `
  -Version 0.9.0 `
  -CertThumbprint "<SHA1指纹>" `
  -Signtool "C:\...\signtool.exe" `
  -RequireSignature
```

`-RequireSignature` 会：

1. 调 `sign.ps1` 签 `QianYu.exe` 和安装包；
2. 用 `Get-AuthenticodeSignature` 检查 `Status=Valid`；
3. 不通过直接中止，不生成 release.json/便携包。

### 4. 验证

```powershell
Get-AuthenticodeSignature dist\installer\QianYu-0.9.0-setup.exe |
  Format-List Status,StatusMessage,SignerCertificate,TimeStamperCertificate

signtool verify /pa /v dist\installer\QianYu-0.9.0-setup.exe
```

期望：

```
Status : Valid
TimeStamperCertificate : <timestamp cert>
```

### 5. 常见失败

| 错误 | 原因 |
|---|---|
| `No certificates were found...` | 证书无 Code Signing EKU / 无私钥 / 指纹错误 |
| `The specified PFX password is not correct` | PFX 密码错误 |
| `SignTool Error: No file digest algorithm specified` | 脚本已固定 `/fd SHA256`，检查 signtool 版本 |
| `Timestamp Server` 超时 | 换 `http://timestamp.sectigo.com` 或 `http://timestamp.digicert.com` |
| `Status=UnknownError` | 证书链不受信、证书未安装、或用了自签名 |
| SmartScreen 仍警告 | 新证书无信誉；EV/时间/下载量会改善，不是签名失败 |

### 6. 当前本机状态

- 无 CA 证书；
- 无 `signtool`；
- 自签名 PFX 签名返回 `UnknownError/NotSigned`；
- `release.ps1 -RequireSignature` 已验证会拦截未签名产物。

**所以本机无法完成生产签名；必须提供证书 + signtool。**

## 便携版

`release.ps1` 用 `Compress-Archive` 生成 `QianYu-<version>-portable.zip`，解压后直接运行 `QianYu.exe`，不写卸载注册表。

## 更新链

- `update.py`：manifest Ed25519 验签 → 下载 → SHA-256；
- 客户端下载后启动安装包，由用户完成安装；
- 自动静默替换/回滚仍未实现。

## Inno 卸载注册表

生产安装器使用 per-user（`PrivilegesRequired=lowest`），但 **不再让 Inno 的内置注册表写入决定安装成败**：

- `CreateUninstallRegKey=no`：Inno 不写内置卸载键，也不会因注册表拒绝而回滚；
- `[Code]` 在 `ssPostInstall` 用 HKCU **best effort** 写入 Add/Remove Programs 项：
  - DisplayName/DisplayVersion/Publisher/InstallLocation/DisplayIcon；
  - UninstallString/QuietUninstallString；
  - NoModify/NoRepair；
- 注册表被 ACL/策略拒绝时：安装继续，开始菜单卸载快捷方式仍可用，只是没有“应用和功能”条目；
- 卸载时 `CurUninstallStepChanged` 删除该 HKCU 键。

这样同时覆盖正常桌面（有卸载项）和受限环境（安装不失败）。**本机沙箱仍无法完成 GUI 安装验收**，因此该行为需在真实桌面做最终确认。

## 仍缺

- 真实代码签名证书；
- 真实桌面 Inno 安装/卸载注册表验证；
- Authenticode 校验（更新器目前只校验 SHA-256/Ed25519 manifest）。
