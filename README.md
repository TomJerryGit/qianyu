# 浅语影音 0.9

本地音乐/视频播放器，GPL-3.0-only 开源。

基于 **libmpv** 的 Windows 音乐/视频播放器。**1.0 发布包默认使用 PySide6/Qt6（LGPL）**；Python 3.8 的 PyQt5 构建保留为兼容回退。

## 0.9 已实现

- 本地媒体库：SQLite + mutagen，扫描/增量/搜索/标签/封面（同名封面或内嵌）。
- 播放：libmpv，mpv playlist 队列（无缝切歌的基础）、播放/暂停/停止/seek/音量/静音。
- 播放列表：增删、多选、拖拽排序、右键菜单、JSON 持久化。
- 歌词：LRC（多时间标签、offset、UTF-8/GBK/UTF-16），当前行高亮，桌面歌词窗口，编辑/关联。
- 均衡器：10 段 -12…+12 dB、8 个预设、启用/旁路；ReplayGain 关闭/曲目/专辑。
- 系统集成：托盘、单实例、命令行打开文件、按用户注册音频文件关联、迷你播放器、全局媒体键。
- 设置：主题、关闭到托盘、媒体键开关、输出设备、ReplayGain、音乐文件夹。
- 歌词：偏移 ±0.5 s、手动关联、按曲目记忆；桌面歌词。
- 两套主题（深/浅），封面主色强调色。
- **媒体库视图**：列表 + 专辑/艺术家封面网格；播放队列可收起；全屏正在播放页。
- **视频模式 MVP**：本地/URL、拖放、传输控制、全屏、硬解、字幕/编码/样式、音轨/字幕轨、截图、续播、文件夹队列、章节、书签、比例/旋转/倍速/逐帧/A-B、色彩调整、HDR 参数、音频延迟、mpv 鼠标手势、全屏/可选窗口手势层（1.0 预览）。
- 更新检查：manifest 版本比较 + 可选 Ed25519 签名 + SHA-256 校验下载；下载后可退出并运行安装包（自动替换待做）。
- 日志/崩溃：轮转日志、`faulthandler`、异常钩子与崩溃提示。
- **在线**：网络电台搜索/播放（Radio Browser）、HTTP/HTTPS 网络流、在线歌词/封面/元数据补全。
- 工程：35 个单元测试、无头 UI 冒烟、1 万曲/100 首基准、GitHub Actions 骨架。

## 运行

```powershell
python -m pip install -r requirements-0.9.txt
python run_dev.py
```

也可以直接：

```powershell
python -m pip install -e .
qianyu "D:\Music\song.flac"
```

> 需要 `libmpv-2.dll` 位于项目根目录（或设置 `QIANYU_MPV_DLL`）。

## 测试

```powershell
# 不依赖 Qt/libmpv 的纯逻辑测试
python -m unittest tests.unit.test_core tests.unit.test_library -v

# 引擎测试（需要 libmpv 与 spike 夹具）
python -m unittest tests.unit.test_engine -v

# 无头 UI 冒烟（需要 PyQt5）
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
python spike\ui_smoke.py

# 视频窗口冒烟（需要真实 Windows 窗口与 4K 样本）
$env:QT_QPA_PLATFORM='windows'
python spike\video_window_smoke.py
python spike\video_queue_smoke.py
python spike\video_controls_smoke.py
python spike\video_style_smoke.py
python spike\video_url_smoke.py
python spike\video_hls_smoke.py
python spike\video_gesture_smoke.py
python spike\video_windowed_overlay_smoke.py

# 重新生成 HDR10/HEVC 样片（需要 imageio-ffmpeg，tools/venv311 已安装）
tools\venv311\Scripts\python.exe spike\make_hdr_hevc.py

# 1 万曲 + 100 首队列基准
python spike\bench_library.py
```

## PySide6 运行（迁移验证）

已有一个 Python 3.11 venv：`tools/venv311`，安装了 PySide6 6.8.3（6.12 在 Windows 打包下存在托盘启动崩溃，已避开）。发布包默认 PySide6；Python 3.8 的 PyQt5 构建作为回退。

```powershell
$env:QT_QPA_PLATFORM='windows'
tools\venv311\Scripts\python.exe run_dev.py
tools\venv311\Scripts\python.exe spike\ui_smoke.py
```

`--smoke`、UI 冒烟、视频窗口 4K 冒烟均已通过；PySide6 PyInstaller 包已构建并验证。

## 打包 / 安装

```powershell
# 便携目录（PySide6 / Python 3.11）
& 'D:\qianyu\tools\venv311\Scripts\python.exe' -m PyInstaller --noconfirm packaging\qianyu-pyside6.spec

# 按用户安装（无需管理员；复制 + 快捷方式 + 可选文件关联）
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -Source dist-pyside6\QianYu

# 卸载
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -Uninstall

# 可选：Inno Setup 安装包（本机 tools\InnoSetup 已提供 iscc）
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -SkipApp -Installer
# 可选：无卸载注册表的沙箱测试安装包（验证安装/卸载链路）
& 'D:\qianyu\tools\InnoSetup\ISCC.exe' packaging\qianyu-sandbox.iss
# 输出：dist\installer\QianYu-0.9.0-sandbox-setup.exe
# 可选：签名（生产用 PFX；开发自签名）
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -Pfx C:\secure\qianyu.pfx -Password <password>
# 输出：dist\installer\QianYu-0.9.0-setup.exe
```

> 打包需要把 `libmpv-2.dll` 放在项目根目录。`dist-pyside6/QianYu/QianYu.exe --smoke` 在 offscreen/windows 均返回 0；`install.ps1` 已用 PySide6 包做真实安装/启动/卸载验证；Inno 安装包已基于 PySide6 编译（未签名，静默安装测试受沙箱限制）。

## 目录

```
src/qianyu/
  engine/        libmpv 封装（队列、事件、EQ、设备）
  core/          领域模型、播放列表、LRC
  library.py     SQLite 媒体库 + 标签/封面
  ui/            主窗口、均衡器、桌面歌词、主题
spike/           libmpv 音视频 spike 与报告
docs/            范围冻结、0.9 状态、路线图
tests/unit/      单元测试
```

## 关键文档

- [libmpv Spike 报告](spike/REPORT.md)
- [视频模式 MVP 状态](docs/video_mvp_status.md)
- [PySide6 迁移评估](docs/pyside6_evaluation.md)
- [更新签名与安装包](docs/update_signing.md)
- [发布就绪检查](docs/release_readiness.md)
- [媒体库生产化路线（CUE/在线元数据）](docs/media_library_roadmap.md)
- [生产发布链](docs/release_chain.md)
- [本地生产验收记录](docs/acceptance_2026-10-18.md)
- [下载页](DOWNLOAD.md)
- [在线功能路线](docs/online_features.md)
- [代码签名政策](CODE_SIGNING_POLICY.md)
- [SignPath Foundation 申请清单](docs/signpath_application.md)
- [GitHub 发布与 SignPath 步骤](docs/github_publish.md)
- [隐私政策](PRIVACY.md)
- [第三方组件与许可证](THIRD_PARTY_NOTICES.md)
- [许可证 GPL-3.0](LICENSE)
- [0.9.0 Beta 发布说明](docs/release_notes_0.9.md)
- [视频 1.0 核心 20 项冻结](docs/video_scope_1.0.md)
- [0.9 状态与差距](docs/music_0.9_status.md)
- [双模播放器路线图](浅语影音_双模播放器路线图.md)
- [全面分析报告](浅语影音_全面分析报告.md)

## 许可证注意

当前 0.9 原型使用 **PyQt5（GPLv3/商业双许可）**。对外分发前必须迁移到 PySide6（LGPL）或购买 PyQt 商业授权；libmpv 需使用 LGPL 构建。详见分析报告。
