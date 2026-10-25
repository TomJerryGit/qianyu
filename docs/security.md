# 安全威胁模型与基线

## 1. 资产

- 用户本地媒体库和播放列表；
- Windows DPAPI 保护的远程服务器凭据；
- 更新 manifest / 发布资产；
- 日志与崩溃转储；
- 用户配置、播放历史和收藏。

## 2. 信任边界

```
用户输入 ──> 文件路径 / URL / 标签 / 歌词 / 字幕
网络 ─────> Radio Browser / 播客 RSS / 封面 / 歌词 / 远程媒体库
磁盘 ─────> SQLite / 配置 / 缓存 / 媒体文件
更新 ─────> manifest / Release / 安装包
```

## 3. 主要威胁与现有控制

| 威胁 | 现有控制 | 剩余风险 |
|---|---|---|
| 恶意媒体文件解析 | libmpv/FFmpeg/mutagen 独立进程或成熟库；不自动执行媒体内嵌脚本 | 解析器 0-day |
| 恶意远程服务器 | TLS 校验；响应大小/超时限制；不信任字段 | 服务端伪造元数据 |
| `file://` / 非 HTTP URL | `core.net.safe_http_url` 只允许 http/https，拒绝内嵌凭据 | 本地主机 SSRF（本地 Jellyfin/Navidrome 为预期） |
| 封面/播客无限下载 | 8 MB 封面上限、1 GB 播客上限、超时 | 镜像大文件 |
| 凭据泄露 | DPAPI 加密；不写日志；不进入导出 | 本机恶意进程 |
| 日志/崩溃泄露隐私 | 不记录 token/password；崩溃文件本地 | 用户主动上传 |
| 更新被替换 | Release SHA-256；可选 Ed25519 manifest 签名 | 未签名安装包 / 私钥保管 |
| 依赖供应链 | 固定版本、CI、即将加入 SBOM/审计 | 上游 0-day、PyPI 投毒 |

## 4. 安全建设优先级

### P0
- 依赖审计（pip-audit）、SBOM、秘密扫描；
- 远程 URL 限制与响应大小限制；
- 许可证/来源审计；
- 更新 manifest 校验与回滚演练；
- 不在日志中输出凭据。

### P1
- 媒体/CUE/RSS 输入 fuzz；
- 依赖自动更新与人工审核；
- 崩溃报告 opt-in 与脱敏；
- 安全发布检查清单。

### P2
- 可选 Authenticode 证书；
- 外部安全审计；
- 安全公告与 CVE 响应流程。

## 5. 报告

见 [SECURITY.md](../SECURITY.md)。
