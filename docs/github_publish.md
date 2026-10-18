# 发布到 GitHub 并申请 SignPath

## 1. 创建仓库

- GitHub 账号：https://github.com
- 新建 public 仓库：`qianyu`
- 建议在创建时选择 **GNU General Public License v3.0**，GitHub 会自动放入完整 GPL 文本（替代当前的精简 `LICENSE`）。

## 2. 上传源码

本机没有 `git` 命令，可用 GitHub Desktop 或网页上传：

- 上传 `src/`、`packaging/`、`tests/`、`docs/`、`README.md`、`pyproject.toml` 等；
- **不要上传** `libmpv-2.dll`（117 MB，超过 GitHub 单文件 100 MB 限制，且 `.gitignore` 已排除）；
- 不要上传 `dist/`、`build*/`、`tools/`、`spike/fixtures/*.mp4`。

创建后把真实地址/用户名填进：

- `CODE_SIGNING_POLICY.md` 的 `@YOUR_GITHUB_USERNAME`
- `docs/signpath_application.md`
- `README.md` 中的链接

## 3. 打 tag，自动发布 Release

`release.yml` 已改为自动完成：

- 从 shinchiro/mpv-winbuild-cmake 下载**固定版本**的 `mpv-dev-x86_64`；
- 校验 SHA-256；
- 解压 `libmpv-2.dll`；
- PyInstaller 构建；
- Inno 编译安装包；
- 生成便携 ZIP 和 SHA256SUMS；
- 用 GitHub Actions 自带 token 创建 `prerelease` 并上传资产。

本机执行：

```powershell
$git = "C:\Program Files\Git\cmd\git.exe"
& $git -C D:\qianyu tag v0.9.0
& $git -C D:\qianyu push origin v0.9.0
```

然后打开：

```
https://github.com/TomJerryGit/qianyu/actions
```

等待 `release` workflow 完成，Release 会自动出现在：

```
https://github.com/TomJerryGit/qianyu/releases/tag/v0.9.0
```

> 不再需要配置 `LIBMPV_URL` / `LIBMPV_SHA256`。

## 4. 申请 SignPath

- 打开 https://signpath.org/apply
- 填仓库地址、GPL-3.0、Release 链接、构建方式
- 附上 `CODE_SIGNING_POLICY.md` 和 `PRIVACY.md`
- 等待人工审核；可能因项目信誉不足被拒

## 6. 通过后

- 配置 `SIGNPATH_API_TOKEN` secret；
- 用 SignPath 的 GitHub Action 提交签名请求；
- 人工批准；
- 下载签名后的 exe/installer；
- `Get-AuthenticodeSignature` 应为 `Valid`。

## 自动发布脚本（可选）

如果本机有 GitHub PAT（repo 权限）：

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
powershell -ExecutionPolicy Bypass -File packaging\publish_github_release.ps1
```

它会创建 `v0.9.0` Release、上传 `dist\github-release` 资产，并设置
`LIBMPV_URL` / `LIBMPV_SHA256` 两个 Actions 变量。

## 当前状态

- 仓库已创建并推送：https://github.com/TomJerryGit/qianyu
- `CODE_SIGNING_POLICY.md` 已填 `@TomJerryGit`
- `PRIVACY.md` 已填联系邮箱
- `LICENSE` 已替换为完整 GPL-3.0 文本
- Release 已由 Actions 自动生成：https://github.com/TomJerryGit/qianyu/releases/tag/v0.9.0
- 仍需：提交 SignPath 申请。
