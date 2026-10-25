# Authenticode 签名选项（可选）

QianYu 当前不依赖 SignPath，发布物未签名。  
如果未来需要减少 SmartScreen 提示，可选择以下方案；它们都不依赖 SignPath。

## 1. Certum Open Source Code Signing

适合开源项目：

- 需要 Certum 账户与身份验证；
- 证书通常为 OV/代码签名；
- 通过 `signtool.exe` 或 PFX；
- 成本较低，但审核/文档要求取决于证书类型。

接入：

```powershell
signtool sign /fd SHA256 /f cert.pfx /p <password> `
  /tr http://timestamp.digicert.com /td SHA256 QianYu.exe
```

PFX 密码放 GitHub Secret，不写入仓库。

## 2. Azure Trusted Signing

适合持续集成：

- Azure 订阅 + Trusted Signing 账户；
- 需要身份/组织验证；
- GitHub Actions 可用 OIDC 或服务主体；
- 签名在云端完成，私钥不落地。

注意：

- 有资格/地区/组织历史要求；
- 价格与配额随服务变化；
- 接入前确认当前政策。

## 3. 自有 PFX / HSM

适合已有代码签名证书：

- 本地或 CI 使用 PFX；
- EV 证书通常要求硬件 token/HSM；
- 私钥必须离线/受限保存；
- 泄露后吊销流程要预先准备。

`packaging/sign.ps1` 可继续作为 PFX 签名脚本。

## 4. Microsoft Store

- MSIX 打包；
- Store 负责签名；
- 需要 Store 账户与审核；
- 更新/分发由 Store 管理。

## 5. 无论哪种方案

- 私钥/密码绝不进仓库；
- CI 使用最小权限 Secret；
- 每次签名后校验：

```powershell
Get-AuthenticodeSignature dist\installer\QianYu-0.9.0-setup.exe |
  Format-List Status, SignerCertificate, TimeStamperCertificate
```

- Release 同时保留 SHA256/SBOM；
- 不把未签名包描述为“可信发布者”。
