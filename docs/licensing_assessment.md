# 原生组件许可证与编解码器专利评估

> 本文件是工程风险清单，不构成法律意见。发布前建议由法律/合规人员确认。

## 1. 组件

| 组件 | 版本/来源 | 许可证 | 分发注意 |
|---|---|---|---|
| QianYu 代码 | 本仓库 | GPL-3.0-only | 提供完整源码/Source Offer |
| PySide6-Essentials | 6.8.3 PyPI | LGPL-3.0 / GPL-3.0 / commercial | 动态链接；保留 LGPL 声明与替换能力 |
| PyQt5 回退 | 仅 Python 3.8 | GPL-3.0 / commercial | 发布包默认不使用；如分发 GPL 兼容 |
| python-mpv | PyPI | GPL-2.0-or-later | 与项目 GPL-3.0 兼容性需确认 |
| libmpv | shinchiro 固定构建 | GPL-2.0-or-later / LGPL-2.1-or-later | 记录构建配置与源码获取方式 |
| FFmpeg | imageio-ffmpeg 内置构建 | LGPL/GPL build-dependent | 记录构建选项；提供对应源码/许可 |
| mutagen | PyPI | GPL-2.0-or-later | 标签解析 |
| Pillow | PyPI | MIT-CMU | 图片处理 |
| pypinyin | PyPI | MIT | 拼音搜索 |
| imageio-ffmpeg | PyPI | BSD-2-Clause | 内置 FFmpeg 的额外许可 |

## 2. 编解码器专利

FFmpeg/mpv 的**软件许可证**与**编解码器专利**是两件事：

- H.264/AVC、H.265/HEVC、AAC、MP3 等可能涉及专利池；
- 开源项目通常不提供专利许可；
- 商业分发/预装到硬件可能需要单独授权；
- 仅播放用户本地文件的桌面软件风险较低，但不应把“无专利风险”写进宣传。

建议：

1. 发布说明只声明软件许可证；
2. 不声称“所有编解码器已获专利授权”；
3. 如未来商业发行，咨询专利律师；
4. 保留 FFmpeg/libmpv 构建配置与来源。

## 3. 在线内容

| 内容 | 当前做法 | 风险 |
|---|---|---|
| 网络电台 | 播放公开流 | 流内容版权归电台 |
| 播客 | RSS + 个人离线缓存 | 仅个人使用；不转播 |
| 封面/歌手图 | 在线获取并本地显示 | 版权归原权利人；不重新分发 |
| 歌词 | LRCLIB 等来源 | 仅显示；不打包进发行版 |
| 平台深链 | 打开官方页面 | 不抓流/不绕 DRM |

详见 [online_compliance.md](online_compliance.md)。

## 4. 发布前清单

- [ ] License/SBOM 与 Release 一起上传
- [ ] Source Offer 指向对应 tag
- [ ] libmpv/FFmpeg 来源与构建配置记录
- [ ] 不含商业字体/图标/测试媒体
- [ ] 未删除 GPL/LGPL 声明
- [ ] 未把未签名包描述为“可信发布者”
- [ ] 编解码器专利声明措辞审阅
