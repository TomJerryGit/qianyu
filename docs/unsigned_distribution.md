# 无 SignPath 的分发设计

QianYu 不再依赖 SignPath Foundation 或任何第三方免费签名服务。发布流程按
“可验证的未签名构建 + 未来可选自有 Authenticode 证书”设计。

## 当前状态

```
Authenticode 签名：无
发布方式：GitHub Releases
主要资产：便携 ZIP、安装包、QianYu.exe、SHA256SUMS.txt
```

未签名构建在 Windows 上可能出现 SmartScreen/UAC 警告，这是预期行为，不能
伪装成已签名或绕过系统安全提示。

## 完整性验证

每个 Release 提供：

- `SHA256SUMS.txt`；
- 源仓库 tag；
- 可复现的 GitHub Actions 构建日志；
- 可选 Ed25519 更新 manifest 签名。

用户验证：

```powershell
Get-FileHash .\QianYu-0.9.0-setup.exe -Algorithm SHA256
Get-FileHash .\QianYu-0.9.0-portable.zip -Algorithm SHA256
```

与 Release 中的 `SHA256SUMS.txt` 对比。

## 更新链

自动更新只信任：

1. 已配置的 manifest URL；
2. Ed25519 签名公钥；
3. SHA-256 文件校验。

签名证书不是更新链的必需条件；即使没有 Authenticode，更新仍通过
manifest 签名和哈希校验。

## 发布方式

- GitHub Release（主渠道）；
- 便携 ZIP（推荐给不愿意运行安装器的用户）；
- Inno Setup 安装包（可选）；
- winget / Scoop / Chocolatey 清单可作为后续渠道。

## SmartScreen

未签名应用可能显示：

```
Windows protected your PC
```

用户需要点击“更多信息 → 仍要运行”。  
不要教用户关闭系统安全功能；只在下载页明确说明未签名状态和校验方法。

## 未来可选签名

如果以后需要 Authenticode，可改用：

- Certum Open Source Code Signing；
- Azure Trusted Signing（若符合资格）；
- 自有 OV/EV 证书 + PFX/HSM；
- Microsoft Store 分发（由 Store 签名）。

现有 `packaging/sign.ps1` 已支持 PFX；签名是可选步骤，不影响构建、更新和
分发流程。**不把 SignPath 作为发布链的前置条件。**

## 团队责任

- 构建产物只能来自本仓库公开 CI；
- Release 必须上传校验和；
- 发现哈希不一致立即撤回对应 Release；
- 不声称未签名构建为“已签名/可信发布者”。
