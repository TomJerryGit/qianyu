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

## 3. 发布 v0.9.0 Release

Release 资产建议：

- `QianYu-0.9.0-setup.exe`
- `QianYu-0.9.0-portable.zip`
- `libmpv-2.dll`（作为 release asset，不放进仓库）
- `SHA256SUMS.txt`

## 4. 配置 Actions 变量

仓库 Settings → Secrets and variables → Actions → Variables：

```
LIBMPV_URL    = https://github.com/TomJerryGit/qianyu/releases/download/v0.9.0/libmpv-2.dll
LIBMPV_SHA256 = 44af8b7f5ff45cf50db49b9866fe9238e84c4d935122576c4c6f7ce859226e8a
```

`release.yml` 会下载并校验 libmpv；未配置时构建会明确失败。

## 5. 申请 SignPath

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

## 当前状态

- 仓库已创建并推送：https://github.com/TomJerryGit/qianyu
- `CODE_SIGNING_POLICY.md` 已填 `@TomJerryGit`
- `PRIVACY.md` 已填联系邮箱
- `LICENSE` 已替换为完整 GPL-3.0 文本
- 仍需：Release 资产、`LIBMPV_URL`/`LIBMPV_SHA256`、SignPath 申请。
