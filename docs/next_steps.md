# 下一步工作安排

更新：2026-10-18  
仓库：https://github.com/TomJerryGit/qianyu  
当前 Release：https://github.com/TomJerryGit/qianyu/releases/tag/v0.9.0

## 当前状态

- SignPath 申请：已提交，等待审核（邮箱 1265338136@qq.com）
- 内存：30 分钟预热后增长 0.0 MB，已收敛
- 冷启动：旧 `--smoke` 硬退出的偶发 `0xC0000005` 已定位为测试工具竞态；真实事件循环 100/100 无崩溃，新 smoke 50/50 无崩溃
- 功能：冻结，不新增
- 签名：等 SignPath

## P0 — 本周必须推进

### 1. SignPath 审核跟进（用户）

- 每天检查邮箱/垃圾邮件；
- 7–10 个工作日后无回复，再向 support@signpath.io 跟进；
- 不要重复提交申请；
- 不移动 `v0.9.0` tag，不删除 Release。

**通过标准**：收到通过/拒绝/补充材料邮件，并记录结论。

### 2. IME 崩溃定位（开发）

当前结论：旧 `--smoke` 的 `os._exit` 与 IME 初始化竞争，是测试工具竞态；真实事件循环 100 次无崩溃，新 smoke 50 次无崩溃。

仍需：

1. 微软拼音对照（脚本已准备，需手动切换默认输入法）；
2. 干净 venv 测试较新的 PySide6/Qt；
3. 8 小时浸泡复测；
4. 若真实用户仍报告启动崩溃，再抓 Windows Error Reporting dump。

**通过标准**：100 次真实事件循环 + 8 小时浸泡 0 崩溃。

### 3. 签名 CI 准备（开发，等 SignPath）

通过后需要四个值：

- Organization ID
- Project slug
- Signing policy slug
- Artifact configuration slug

收到后：

1. 配 `SIGNPATH_API_TOKEN` 到 GitHub Secret；
2. 修改 `release.yml`：
   - 上传 `QianYu.exe` + installer；
   - 提交签名请求；
   - 等待人工批准；
   - 下载已签名产物；
   - 更新 Release 资产；
3. 验证：
   ```powershell
   Get-AuthenticodeSignature dist\installer\QianYu-0.9.0-setup.exe |
     Format-List Status, SignerCertificate, TimeStamperCertificate
   ```
   期望 `Status=Valid`，签名者 `CN=SignPath Foundation`。

**通过标准**：签名安装包可安装、启动、卸载，且 `Status=Valid`。

## P1 — 审核等待期

### 4. 8 小时浸泡（开发）

- 用当前构建重跑 `spike/soak_8h.py`；
- 目标：预热后 8 小时 RSS 增长 < 20 MB，无崩溃；
- 记录 `spike/out/soak_8h.json`。

### 5. 仓库信誉材料（用户 + 开发）

- GitHub About 填描述和 topics；
- README 加 2–3 张真实截图；
- Release notes 写清功能、限制、校验值；
- 不刷 star、不伪造下载量。

## P2 — 稳定性通过后

只有在 100 次冷启动 + 8 小时浸泡通过后才恢复：

- 批量标签/智能列表增强；
- CUE 多文件细节；
- 在线封面/歌词重试缓存；
- 视频控制条折叠；
- 10k 首屏继续优化。

## 里程碑

| 里程碑 | 条件 |
|---|---|
| M1 SignPath 结果 | 收到审核邮件 |
| M2 启动稳定 | 100 次冷启动 0 崩溃 |
| M3 签名发布 | 安装包 `Status=Valid` |
| M4 1.0 | M2 + M3 + 8 小时浸泡 + 真实安装卸载 |

## 不要做

- 不要用自签名冒充生产签名；
- 不要为了通过审核伪造用户量/媒体报道；
- 不要在崩溃未定位时继续堆功能；
- 不要移动或删除已提交的 Release tag。
