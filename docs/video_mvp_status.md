# 视频模式 MVP 状态（1.0 预览）

- **日期**：2026-10-17
- **状态**：可运行 MVP（内部 Alpha），不是完整 1.0。
- **文件**：`src/qianyu/ui/video_window.py`
- **架构**：与 spike 决策一致——mpv `wid` 渲染到原生子窗口，Qt 控制条放在画面**下方**；全屏使用 mpv OSC，不做覆盖式 Qt 控件。

---

## 1. 已实现

| 能力 | 实现 | 验证 |
|---|---|---|
| 打开本地文件 | 菜单/打开按钮/命令行/拖放 | `video_window_smoke.py` 打开 4K60 样本 |
| 打开 URL | URL 对话框 / 拖放 http(s)/rtsp/rtmp | 代码路径；网络流未实测 |
| 播放/暂停/停止/seek/音量/静音 | 控制条 + 快捷键 | 位置从 0.55 s seek 到 1.49 s |
| 全屏 | `showFullScreen` + mpv OSC | `FULLSCREEN True` |
| 硬件解码 | `hwdec=auto-safe`、`gpu-api=d3d11` | `hwdec-current=d3d11va` |
| 4K | 3840×2160 输出 | `SIZE 3840 2160` |
| 字幕 | 外挂 SRT/ASS/SSA，字幕轨下拉 | 加载 `.ass` 后 `SUBS 1` |
| 音轨/字幕轨选择 | `aid` / `sid` 下拉 | 代码路径 |
| 截图 | `screenshot-to-file`（含字幕） | `SHOT True True`（文件已生成） |
| 续播 | 按路径记录位置，打开时 seek 到记录 | `SAVED 6.0` → 重开 `RESUME_POSITION 6.7` |
| 队列/文件夹连播 | 打开文件时扫描同目录视频，按自然序排队；上一段/下一段/播完自动下一段 | `QUEUE 2`，next/pre 正确 |
| 章节 | `chapter-list` 观察器 + 章节下拉 | `CHAPTERS 2 VISIBLE True`，跳转 6.2 s |
| 书签 | 按文件记录，菜单添加/跳转/清除 | `BOOKMARK_POS 4.4` |
| 比例/旋转/去隔行 | `video-aspect-override`、`video-rotate`、`deinterlace` | 16:9、90°、去隔行均生效 |
| 倍速 | `speed` + 0.5×–2× 下拉 | `SPEED 1.5` |
| 逐帧/A-B | `frame-step`/`frame-back-step`，`ab-loop-a/b` | 5.000→5.033 s；A/B 5.03/7.0，清除 `no/no` |
| V18 字幕样式记忆 | 字体/字号/颜色/描边/延迟/位置/粗斜体 + `sub-ass-override=scale` | `SUB_SIZE 42`、`SUB_DELAY 0.5`、`SUB_ALIGN top` |
| V19 色彩调整 | `brightness/contrast/saturation/gamma` + 对话框 | `10/20/-5/5` 生效 |
| V20 音频延迟 | `audio-delay` + “音频”菜单 | `AUDIO_DELAY 0.25` |
| URL 流 | 本地 HTTP + 真实远程 HLS | 本地 11.97 s；远程 1080p/4K 见下 |
| V06 字幕编码 | `sub-codepage`：自动/UTF-8/GBK/GB18030/BIG5/UTF-16 | `SUB_CODEPAGE gbk` |
| V12 OSD | mpv `show-text` 操作提示；全屏用 OSC | 速度/比例/旋转/A-B/延迟均显示 |
| V12 鼠标手势 | mpv `input-default-bindings=yes`、`input-vo-keyboard=no`（滚轮/右键/双击由 mpv 处理，Qt 保留键盘） | 属性 `True/False` 生效；真实鼠标未自动化 |
| V12 全屏手势 | 顶层半透明 `GestureOverlay`：单击暂停、横滑 ±10 s、竖滑音量、双击退出全屏 | `TAP_PAUSE True`、`SWIPE 0.57→10.57`、`DBLCLICK False` |
| V12 窗口手势（可选） | “画面 → 窗口手势层”开关；顶层 overlay 仅覆盖视频画面，窗口失活即隐藏 | `WINDOWED_OVERLAY True`、`TAP_PAUSE True`、`SWIPE 0.0→10.03` |
| V17 HDR 控制 | `tone-mapping`/`target-peak`/`hdr-compute-peak`/`target-colorspace-hint` | `spline/500/False/False` 生效；HDR10 元数据样本已生成并验证，真实 HDR 显示未验 |
| 拖放 | 本地文件/网络 URL | 代码路径 |

**实测输出**：

```
DURATION 2.98
SIZE 3840 2160
HWDEC d3d11va
TRACKS 1
SUBS 1
POSITION 1.49
SHOT True True
FULLSCREEN True
RESUME_POSITION 6.7
CLOSED True
```

队列/章节/书签冒烟：

```
QUEUE 2 INDEX 0
NEXT 02-second.mp4 INDEX 1
PREV 01-first.mp4 INDEX 0
CHAPTERS 2 VISIBLE True
CHAPTER_POS 6.2
BOOKMARK_POS 4.4
CLOSED True
```

比例/倍速/逐帧/A-B 冒烟：

```
SPEED 1.5
ASPECT 1.7777777777777777
ROTATE 90
DEINTERLACE True
FRAME_STEP 5.0 -> 5.033
AB 5.033333333333333 7.0
AB_CLEAR no no
CLOSED True
```

全屏手势：

```
FULLSCREEN True OVERLAY True
TAP_PAUSE True
SWIPE_POS 0.57 -> 10.57
DBLCLICK_FULLSCREEN False
CLOSED True
```

窗口手势（可选，配置 `video_gesture_windowed=true` 或“画面 → 窗口手势层”）：

```
WINDOW_ACTIVE True
WINDOWED_OVERLAY True
TAP_PAUSE True
SWIPE_POS 0.0 -> 10.03
CLOSED True
```

字幕/色彩/音频延迟/URL 冒烟：

```
SUB_SIZE 42.0
SUB_COLOR #FFFFCC00
SUB_DELAY 0.5
SUB_ALIGN top
SUB_CODEPAGE gbk
HDR spline 500 False False
COLOR 10.0 20.0 -5.0 5.0
AUDIO_DELAY 0.25
URL_DURATION 11.97
URL_SIZE 1280 720
CLOSED True
```

真实远程 HLS：

```
1080p DURATION 634.58
1080p SIZE 1920 1080
1080p CODEC H.264
1080p HWDEC d3d11va
4K DURATION 141.04
4K SIZE 3840 2160
4K CODEC H.264
4K HWDEC d3d11va
CLOSED True
```

![视频窗口（Qt 只能截到控制条，视频在原生子窗口）](spike/out/video_window.png)

> 截图里画面是黑的，是 airspace 的直接表现：`QWidget.grab()` 抓不到 mpv 原生子窗口；实际播放由 `hwdec-current`/`width`/`height`/position 验证。

---

## 2. 与 1.0 核心 20 项的对应

| 覆盖 | 条目 |
|---|---|
| ✅ MVP 已覆盖 | V01–V05、V07–V11、V13–V20（V08 比例/旋转/去隔行、V09 倍速、V16 逐帧/A-B、V18 字幕样式、V19 色彩、V20 音频延迟） |
| 🟡 部分 | V06 编码选择已加，字体回退/ASS 样式冲突未验；V12 全屏顶层手势层已加（窗口模式仍为下方控制条）；V17 HDR 参数控制已加，真实 HDR10/HLG 样片/显示未验 |

---

## 3. 已知问题

1. 全屏默认启用顶层手势层（单击暂停/横滑 seek/竖滑音量/双击退出），mpv OSC 关闭；窗口模式仍用下方控制条。1.2 render API 可把两者统一。
2. 队列只覆盖“同目录自然排序”，没有手动排序/混合 URL 队列；上一段/下一段已接真实队列。
3. 字幕编码/延迟/样式 UI 已有；ASS 样式冲突/字体回退未系统验收。
4. 视频窗口未套用深色主题 QSS（主窗口样式表会作用到它，但控制条未单独美化）。
5. 未做多显示器/DPI/全屏切换的自动化回归。
6. HDR10 元数据/10-bit HEVC 已验；真实 HDR 显示器与 HEVC 10-bit 硬解仍缺。

---

## 4. 运行

```powershell
# 主程序：文件 → 打开视频…（Ctrl+Shift+O），或把视频拖入窗口
python run_dev.py

# 独立视频窗口冒烟（需要真实 Windows 窗口 + 4K 样本）
$env:QT_QPA_PLATFORM='windows'
python spike\video_window_smoke.py
```

---

## 5. 下一步

1. 真实 HDR10/HLG、4K60 HEVC 样片/显示器验收：已自产 HEVC Main10 HDR10 样本（`bt2020/pq/max-luma 1000`），但本机 GPU 无 HEVC 10-bit 硬解，4K60 只能软解；仍无 HDR 显示器。
2. V12 Qt 触控手势受原生子窗口限制；mpv 鼠标绑定已启用，跨平台触控需 render API/1.2。
3. 队列手动排序/混合 URL、章节缩略图。
4. 更新签名/自动替换、PySide6 迁移、Inno 安装包。
