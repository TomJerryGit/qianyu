# 安全审计 triage 记录

日期：2026-10-25

## 1. 已完成的阻断项

| 检查 | 状态 |
|---|---|
| 秘密扫描 `tools/scan_secrets.py` | ✅ 0 findings，CI 阻断 |
| OSV 依赖审计 `tools/osv_audit.py` | ✅ 0 findings，CI 阻断 |
| URL scheme / 响应大小守卫 | ✅ `core/net.py` |
| 安装/发布 SHA-256 校验 | ✅ `tools/verify_release.py` |
| SBOM / 许可证清单 | ✅ Release 自动生成 |

## 2. pip-audit / Bandit 报告

GitHub Actions 的 `security-reports` artifact 需要仓库 admin 权限下载，
当前执行环境无法直接取回 `pip-audit.json` / `bandit.json`。

已保留安全 CI 的 report-only 步骤，待有权限时下载并逐项 triage。

## 3. 代码审查中的 Bandit 类别

| 类别 | 位置 | 初判 | 处理 |
|---|---|---|---|
| B404 import subprocess | fingerprint / spectrum / now_playing | FFmpeg 子进程 | 固定可执行路径；不使用 shell |
| B603 subprocess | 同上 | 参数列表，无 `shell=True` | 接受；后续加路径校验 |
| B310 urllib.urlopen | online/metadata/radio/podcast/update | 部分 URL 来自公开 API/用户配置 | 新代码已走 `safe_http_url`；旧模块逐步迁移 |
| B110 try/except pass | 多个网络/缓存路径 | 失败静默以保持播放 | 接受但记录日志 |
| B101 assert | 测试 | 仅测试 | 忽略 |
| B506 yaml.load | 未使用 | — | 无 |

## 4. 下一步阻断升级

1. 下载 artifact；
2. 把高危/可利用项修复；
3. 对误报添加 `# nosec` 注释并注明原因；
4. 将 `pip-audit --strict` 与 `bandit -ll` 设为阻断；
5. 保留 SBOM/许可证 artifact。

## 5. 目前风险结论

```
依赖漏洞：OSV 0
秘密泄露：0
URL/大小限制：新路径已覆盖
签名：未签名，依赖 SHA256/SBOM
真实桌面：待兼容矩阵
```
