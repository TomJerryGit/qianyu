# 依赖审计记录

日期：2026-10-25

## 工具

- OSV 查询（PyPI 生态，无需额外依赖）；
- `pip-audit` / Bandit / pip-licenses / CycloneDX SBOM 由安全 CI 生成报告。

## 当前结果

```text
PySide6-Essentials 6.8.3: clean
python-mpv 1.0.8: clean
mutagen 1.48.1: clean
Pillow 13.0.0: clean
pypinyin 0.55.0: clean
imageio-ffmpeg 0.6.0: clean
OSV: 0 finding(s)
```

脚本：

```powershell
python tools\osv_audit.py
```

## 原生组件

| 组件 | 来源 | 许可证 | 备注 |
|---|---|---|---|
| libmpv | shinchiro 固定版本 | GPL/LGPL | 发布时下载并校验 SHA-256 |
| FFmpeg | imageio-ffmpeg 内置 | LGPL/GPL 取决于构建 | 不重新授权 |
| PySide6 | PyPI 6.8.3 | LGPL/GPL/commercial | 动态链接 |
| PyQt5 回退 | 仅 Python 3.8 | GPL/commercial | 发布包默认不使用 |

## 待办

- 在 Release 中附带 SBOM 与许可证清单（已加入 release workflow）；
- 对漏洞报告人工 triage；
- 依赖升级需跑完整测试与真实服务器联调；
- 编解码器专利风险需法律/商业评估，不由代码解决。
