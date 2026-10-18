# SignPath Foundation 申请清单（QianYu）

申请入口：https://signpath.org/apply  
条件：https://signpath.org/terms

## 申请前必须完成

- [ ] GitHub 仓库公开
- [ ] 根目录 `LICENSE`（GPL-3.0-only）
- [ ] `CODE_SIGNING_POLICY.md` 填好真实 GitHub 用户名
- [ ] `PRIVACY.md` 填好公开联系邮箱
- [ ] 至少一个正式 Release（exe + 安装包）
- [ ] README 有功能、构建、下载说明
- [ ] GitHub 和 SignPath 开启 MFA
- [ ] 所有构建来自公开 CI（`.github/workflows/release.yml`）
- [ ] 不包含专有组件/商业双许可

## 申请信息模板

```text
Project: QianYu
Repository: https://github.com/<user>/qianyu
License: GPL-3.0-only
Latest release: https://github.com/<user>/qianyu/releases/tag/v0.9.0

QianYu is an open-source Windows local music/video player built with
Python, PySide6, libmpv and Inno Setup. It is actively maintained.

Build: GitHub Actions on windows-latest, PyInstaller + Inno Setup.
Artifacts to sign:
- QianYu.exe
- QianYu-0.9.0-setup.exe

Code signing policy: https://github.com/<user>/qianyu/blob/main/CODE_SIGNING_POLICY.md
Privacy policy: https://github.com/<user>/qianyu/blob/main/PRIVACY.md
```

## 申请后

SignPath 通过后提供：

- Organization ID
- Project slug
- Signing policy slug
- Artifact configuration slug
- API token

然后在 GitHub 仓库设置：

- Secret: `SIGNPATH_API_TOKEN`
- Variables: `LIBMPV_URL`, `LIBMPV_SHA256`

把 `release.yml` 的“upload unsigned”步骤替换为 SignPath 签名请求，人工批准后下载已签名产物。

## 当前仓库缺口

- 还没有真实 GitHub 仓库 URL；
- `CODE_SIGNING_POLICY.md` 里是 `@YOUR_GITHUB_USERNAME`；
- `PRIVACY.md` 联系邮箱待填；
- `LICENSE` 目前是 GPL-3.0 声明 + 官方链接，公开前应补完整 GPL 文本；
- `LIBMPV_URL`/`LIBMPV_SHA256` 未配置；
- 尚无正式 Release。
