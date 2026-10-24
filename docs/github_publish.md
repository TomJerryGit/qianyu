# 发布到 GitHub

## 1. 仓库

- GitHub 账号：https://github.com
- public 仓库：`qianyu`
- 许可证：GPL-3.0-only

## 2. 上传源码

不要把以下内容提交进 Git：

- `libmpv-2.dll`（117 MB，超过 GitHub 单文件限制）；
- `dist/`、`build*/`、`tools/`；
- PFX/私钥、签名 token。

## 3. 打 tag，自动发布 Release

`release.yml` 会：

- 下载固定版本的 `mpv-dev-x86_64`；
- 校验 SHA-256；
- 解压 `libmpv-2.dll`；
- PyInstaller 构建；
- Inno 编译安装包；
- 生成便携 ZIP 和 `SHA256SUMS.txt`；
- 用 GitHub Actions token 创建 prerelease 并上传资产。

本地执行：

```powershell
$git = "C:\Program Files\Git\cmd\git.exe"
& $git -C D:\qianyu tag v0.9.0
& $git -C D:\qianyu push origin v0.9.0
```

查看：

```
https://github.com/TomJerryGit/qianyu/actions
https://github.com/TomJerryGit/qianyu/releases/tag/v0.9.0
```

## 4. 签名策略

QianYu **不依赖 SignPath**。

- 当前发布物未签名；
- 用户通过 `SHA256SUMS.txt` 和源 tag 校验；
- SmartScreen 可能提示未知发布者；
- 未来如需要 Authenticode，可使用项目自有证书、Certum OSS 或 Azure Trusted Signing；
- 签名是可选步骤，不影响构建/发布。

详见 [unsigned_distribution.md](unsigned_distribution.md) 和
[CODE_SIGNING_POLICY.md](../CODE_SIGNING_POLICY.md)。

## 5. 自动发布脚本（可选）

如果本机有 GitHub PAT（repo 权限）：

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
powershell -ExecutionPolicy Bypass -File packaging\publish_github_release.ps1
```

注意：当前优先使用 tag + Actions 自动发布；PAT 仅作为本地备用。
