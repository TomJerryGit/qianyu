# libmpv Spike 报告（音视频可行性 + 视频 UI 架构决策）

- **日期**：2026-10-18
- **目标**：验证 libmpv 能否同时支撑音乐与视频两条产品线，并据此定下视频 UI 架构。
- **环境**：Windows 10 19045 / Python 3.8.9 / PyQt5 5.15.11（Qt 5.15.2）/ libmpv **v0.41.0-60-g85bf9f4ff**（`D:\qianyu\libmpv-2.dll`，111.7 MB）/ python-mpv 1.0.6 / 声卡：Conexant SmartAudio HD（WASAPI）。
- **结论**：**libmpv 通过音视频可行性验证；1.0 视频 UI 采用 `wid` 嵌入 + 画面下方独立控制条 + 全屏 mpv OSC，不做 Qt 覆盖式控件；render API 自定义覆盖留到 1.2。**

---

## 1. 验证范围与结论摘要

| 能力 | 结果 | 证据 |
|---|---|---|
| 音频无缝播放（gapless） | ✅ 通过 | 4.000 s 连续输出；拼接处 RMS 0.2475，与正弦理论值一致；最长“静音”仅 0.02 ms（1 个采样） |
| 10 段 EQ（FFmpeg equalizer） | ✅ 通过 | 1 kHz 提升 **+11.8 dB**，200 Hz 仅 **+0.66 dB**（目标 +12 dB） |
| 输出设备枚举/切换 | ✅ 通过 | 枚举 3 个设备；播放中切到 WASAPI 扬声器与 OpenAL；输出参数 48 kHz/2ch/float |
| 4K 解码 | ✅ H.264 4K60；🟡 HEVC 4K60 仅软件 | 4K60 H.264 `d3d11va`、2 s 0 丢帧；4K60 HEVC 10-bit 样本可解，但本机 GPU 无 HEVC 硬解，软件解码远低于实时 |
| ASS 字幕 | ✅ 通过 | 中文/英文/日文正常渲染；样式、描边、位置、`\fad` 生效 |
| `wid` 嵌入 Qt | ✅ 通过 | `current-vo=gpu/gpu-next`，视频输出 3840×2160，OSD 尺寸 1280×720 |
| 硬件解码 | ✅ 360p HEVC + 4K60 H.264；❌ HEVC 10-bit | `hwdec-current=d3d11va`；HEVC 10-bit HDR 样本 `hwdec-current=no` |
| HDR 色调映射 | ✅ HDR10 元数据样本通过；❌ HDR 显示未验证 | 自产 4K/1080p HEVC Main10 HDR10：`bt.2020/pq/10-bit`、`max-luma=1000`、`max-cll=1000/400`；无 HDR 显示器 |
| render API（软件） | ✅ 通过 | 640×360、1280×720 帧捕获成功，字幕随帧渲染 |

---

## 2. 音频 Spike

### 2.1 方法与夹具

- 生成两段 2 s、440 Hz、相位连续的 WAV（`gapless_a/b.wav`），拼接应为连续正弦。
- 用 `ao=pcm` + `ao-pcm-waveheader=yes` 把实际输出写成 WAV，再分析：
  - 总时长是否 4.000 s；
  - 拼接点（2.0 s）局部 RMS/峰值；
  - 全片最长“近零”连续段。
- EQ：5 s 白噪声，分别在 `af` 为空与 `equalizer=f=1000:t=q:w=1:g=12` 下录制，做 FFT 频带能量对比。
- 设备：`audio-device-list` 枚举；播放中切换到 `wasapi/{GUID}` 与 `openal`，读取 `audio-out-params`。

### 2.2 结果

```json
{
  "gapless": {
    "duration_s": 4.0,
    "longest_silence_ms": 0.02,
    "splice_peak": 0.35,
    "splice_rms": 0.2475
  },
  "eq": {
    "delta_1k_db": 11.8,
    "delta_200_db": 0.66,
    "sample_rate": 48000
  },
  "devices": {
    "devices": ["auto", "wasapi/{f22b9318-...}", "openal"],
    "audio_out_params": {"samplerate": 48000, "channel-count": 2, "format": "float"},
    "switched_to": "wasapi/{f22b9318-...}",
    "switched_openal": "openal"
  }
}
```

**判读**：

- 总时长精确 4.000 s，拼接点 RMS 等于 0.35/√2≈0.2475，说明没有插入静音；最长近零段 0.02 ms 只是正弦过零的一个采样，**gapless 成立**。
- EQ 实测 +11.8 dB（目标 +12 dB），带外仅 +0.66 dB，**滤波器链可用**。
- 设备可枚举、可在播放中切换；WASAPI 输出为 48 kHz/2ch/float，满足音乐场景。
- 未验证：WASAPI 独占/比特完美、DSD、多声道、设备热插拔（拔耳机）——列入 0.9/1.0 回归。

> 原始数据：[`out/audio_report.json`](out/audio_report.json)

---

## 3. 视频 Spike

### 3.1 4K 解码

- 3840×2160 PNG（渐变 + 文字），`vo=null`。
- `width=3840`、`height=2160`、`video-params` 为 `rgb24`，`video-out-params` 为 `gbrp`。
- **结论**：4K 解码与缩放路径通；但 PNG 不等于 4K HEVC/10-bit，硬解与 4K60 性能仍未验证。

### 3.2 ASS 字幕

- 使用 mpv 的 `lavfi` 合成视频（`av://lavfi:testsrc2=size=1280x720:rate=30:duration=10`），外挂 `overlay.ass`。
- `track-list` 中字幕轨 `selected=true`；`sub-text` 返回“ASS subtitle: 中文 / English / 日本語”。
- 截图与软件渲染均显示中文/英文/日文、描边、底部定位、淡入淡出。
- **关键坑**：图像 demuxer 的 `duration=0`，ASS 事件不会被激活（`sub-text=null`）；字幕验证必须用带时间轴的视频源。

![ASS 字幕（mpv 截图）](out/lavfi_ass.png)

### 3.3 `wid` 嵌入 Qt

- 创建真实 Windows Qt 窗口（`QT_QPA_PLATFORM=windows`），把 `winId()` 传给 mpv `wid`。
- `vo=gpu` 与 `vo=gpu-next` 均可用：`current-vo` 正确、`video-out-params` 为 1280×720、OSD 尺寸同步。
- **但出现 airspace**：Qt 控件无法覆盖在 mpv 原生子窗口之上。

### 3.4 Airspace 证据（本次 spike 的关键发现）

用两种方式抓同一个窗口：

| 抓取方式 | 结果 | 图片 |
|---|---|---|
| Win32 `PrintWindow(PW_RENDERFULLCONTENT)` | 能看到视频画面，**看不到 Qt 红色标签** | [airspace_printwindow.png](out/airspace_printwindow.png) |
| `QWidget.grab()` | 能看到 Qt 红色标签，**看不到视频** | [airspace_qt_grab.png](out/airspace_qt_grab.png) |

这说明：`wid` 模式下，mpv 的原生子窗口在 Z 序上覆盖 Qt 控件。半透明控制条、字幕面板、右键菜单、提示气泡都不能可靠地叠加在画面上。

![PrintWindow：视频在，Qt 控件不在](out/airspace_printwindow.png)

![QWidget.grab：Qt 控件在，视频不在](out/airspace_qt_grab.png)

#### 3.4.1 顶层 Qt overlay 探针（说明不是“绝对不可能”）

另做了一个 **无父级的顶层 Qt Tool 窗口**（半透明红色）覆盖在 mpv 窗口上：

- `QScreen.grabWindow(0)` 能看到红色 overlay 在视频/其他窗口之上；
- 说明 airspace 只限制 **Qt 子控件**，**独立顶层窗口**可以覆盖 `wid`；
- 但 `WindowStaysOnTopHint` 会全局置顶，覆盖其他应用；焦点/激活/多屏管理也更复杂。

结论：1.0 窗口模式仍采用“画面 + 下方控制条”，**全屏采用“顶层半透明手势层 + mpv OSC 关闭”**（单击暂停/横滑 seek/竖滑音量/双击退出）；1.2 再评估 render API 统一窗口内覆盖/皮肤。探针：[overlay_probe.py](overlay_probe.py)、[overlay_probe.png](out/overlay_probe.png)；手势冒烟：[video_gesture_smoke.py](video_gesture_smoke.py)。

### 3.5 硬件解码（HEVC / D3D11VA）

用 B 站公开 360p HEVC 样本（`fixtures/bili_hevc.mp4`，仅用于本地 spike）验证：

```
hwdec-current = d3d11va
video-out-params = {pixelformat: d3d11, hw-pixelformat: nv12, w: 640, h: 360, fps: 30}
decoder-frame-drop-count = 0
frame-drop-count = 0（复跑；首次启动阶段曾为 2）
```

说明 `hwdec=auto-safe` + `gpu-api=d3d11` 的硬解路径可用；4K60 仍需 4K HEVC 样片与参考 GPU。  
原始数据：[hwdec_report.json](out/hwdec_report.json)。

**4K60 H.264**（用 libmpv 编码模式自产，避免外部样本）：

```
width/height = 3840×2160, fps = 60.13
hwdec-current = d3d11va
display-fps = 60
frame-drop-count = 0 (2 s delta = 0)
decoder-frame-drop-count = 0
```

**关键**：无音频/纯视频样本必须用 `video-sync=display-resample`；默认 `audio` 会在无音轨时掉帧（本机 2 s 掉 77–81 帧）。视频模式默认应设置 `display-resample`。

### 3.6 HDR 色调映射（合成 PQ 源）

用 `vf=format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc` 把 SDR 测试图标记为 BT.2020/PQ：

```
video-out-params = {pixelformat: yuv420p10, primaries: bt.2020, gamma: pq,
                    max-pq-y: 0.990, avg-pq-y: 0.865}
vo = gpu-next, tone-mapping = bt.2390, target-colorspace-hint = yes
```

截图显示色调映射后的画面（[hdr_synthetic.png](out/hdr_synthetic.png)）。这验证了 **gpu-next + bt.2390 + 10-bit BT.2020/PQ 的输出链路**，但**不是**真实 HDR10/HLG 内容，也未在 HDR 显示器上验收。

### 3.7 HDR10 HEVC 样本（自产，非合成 vf）

用 `imageio-ffmpeg` 自带的 ffmpeg 7.1 + libx265 10-bit 生成：

- 3840×2160@60 / 1920×1080@60，3 s；
- `format=yuv420p10le` + `setparams=bt2020/pq`；
- x265：`hdr-opt=1`、`master-display=...L(10000000,1)`、`max-cll=1000,400`。

libmpv 读取结果：

```
video-codec = HEVC
video-params = {pixelformat: yuv420p10, primaries: bt.2020, gamma: pq,
                max-luma: 1000, max-cll: 1000, max-fall: 400}
hwdec-current = no
time-pos ≈ 0.02 s after 2 s  (software decode, far below realtime)
```

结论：

- **HDR10 元数据/10-bit HEVC 解码链路已验证**，比 3.6 的 `vf` 标记更接近真实内容；
- 本机 GPU **不支持 HEVC 10-bit 硬解**（`d3d11va` 对 H.264 有效，对 HEVC Main10 回退软件）；
- 4K60 HEVC 软件解码远低于实时，**不能作为 4K60 HEVC 性能验收**；
- 仍未在 HDR 显示器上验收色调映射。

样本：`fixtures/test_4k60_hevc_hdr.mp4`、`fixtures/test_1080p60_hevc_hdr.mp4`（已 gitignore）；截图：[hdr10_hevc.png](out/hdr10_hevc.png)。

### 3.8 render API（软件渲染）

- `vo=libmpv` + `mpv_render_context_create(api_type='sw')`，把帧渲染到 Python 持有的缓冲区。
- 640×360、1280×720 均成功；ASS 字幕随帧渲染。
- 需要给 python-mpv 1.0.6 打补丁，补上 `sw_size/sw_format/sw_stride/sw_pointer` 四个参数（type id 17–20）；当前绑定只内置 OpenGL 参数。
- **结论**：render API 路径在 Python 可行，但软件渲染是 CPU 路径，4K 不具产品性能；正式自定义覆盖 UI 应走 OpenGL FBO（`QOpenGLWidget`），工作量和 HDR 验证都更大。

![render API 软件渲染 + ASS](out/sw_video_ass_1.png)

---

## 4. 架构决策

### 4.1 决策：1.0 用 `wid` + 非覆盖式控制条

| 选项 | 决策 | 理由 |
|---|---|---|
| `wid` + 画面下方独立控制条（窗口模式） | ✅ **1.0 采用** | 无 airspace；实现快；视频/字幕/硬解/HDR 全由 mpv 负责 |
| 全屏用 mpv OSC | ✅ **1.0 采用** | 全屏无法放“下方控制条”；OSC 可自动隐藏/配色，先满足可用 |
| render API + `QOpenGLWidget` 覆盖控件 | ⏳ **1.2 评估** | 可实现完全自定义/皮肤；但 OpenGL FBO、HDR、4K 性能、Python 绑定都要额外验证 |
| 独立透明覆盖窗口 | ❌ 不采用 | 同步脆弱，多屏/全屏易穿帮 |

**产品含义**：

- 1.0 的视频窗口是“画面 + 下方工具栏”，不是 PotPlayer 那种覆盖式皮肤控制条；
- 全屏时使用 mpv OSC（可配置颜色/自动隐藏），不承诺自定义视频皮肤；
- 视频区域的右键菜单放在画面外（工具栏/顶部菜单），避免被原生子窗口盖住；
- 1.2 再评估 render API 做“覆盖式控制条 + 视频皮肤”。

### 4.2 对路线图的影响

- 原路线图 §2.2 的“折中方案”与本次实测一致，升级为**已决策**。
- 视频 UI 的 Phase 2 工作量按“wid + 下方控制条 + OSC 全屏”估算；render API 从 1.0 范围移除。
- 1.0 视频渲染统一用 `vo=gpu-next`（HDR 色调映射更完整），`gpu` 作为兼容回退；两者均已验证可 `wid`。
- 视频模式默认 `video-sync=display-resample`：无音轨/纯视频样本在默认 `audio` 同步下会掉帧（本机 4K60 实测 2 s 掉 77–81 帧），改为 `display-resample` 后 0 丢帧。

---

## 5. 仍未验证 / 下一步

| 项 | 状态 | 下一步 |
|---|---|---|
| H.264/HEVC 硬解、4K60、10-bit | ✅ 4K60 H.264 + 360p HEVC；⚠️ HEVC 10-bit 软解 | 4K60 `display-resample` 0 丢帧；HEVC 10-bit HDR 样本 `hwdec-current=no`，软件远低于实时 |
| 真实 HDR10/HLG 色调映射 | ⚠️ HDR10 元数据样本通过；HDR 显示未验证 | 自产 HEVC Main10 HDR10（bt2020/pq/max-luma 1000/max-cll 1000/400）；需 HDR 显示器/HEVC 硬解 GPU |
| WASAPI 独占/比特完美 | 未验证 | 用 `ao=wasapi` + 独占选项，环回采集比对 PCM |
| 设备热插拔 | 未验证 | 播放中拔/插耳机、HDMI，观察暂停/切换/恢复 |
| render API OpenGL FBO | 未验证 | 1.2 前做 `QOpenGLWidget` + `opengl_fbo` spike，验证 4K/HDR/叠加 |
| 性能基线 | 部分 | 启动、首帧、seek、内存、4K 丢帧，纳入 CI 门禁 |

---

## 6. 复现

```powershell
# 1) 生成夹具（WAV/4K PNG/ASS）
python spike/media_gen.py

# 2) 音频：gapless / EQ / 设备
python spike/mpv_audio.py

# 3) 视频：4K / ASS / wid / render API / HDR 选项
$env:QT_QPA_PLATFORM='windows'
python spike/mpv_video.py

# 4) airspace 证据（PrintWindow vs QWidget.grab）
python spike/airspace_probe2.py

# 5) 硬解 + 合成 HDR 链路（需要 fixtures/bili_hevc.mp4）
$env:QT_QPA_PLATFORM='windows'
python spike/mpv_video_hwdec.py
```

产物在 `spike/out/`：

- `audio_report.json`、`video_report.json`、`airspace_report.json`
- `gapless_capture.wav`、`eq_flat.wav`、`eq_boost_1k.wav`
- `lavfi_ass.png`、`sw_video_ass_1.png`、`hdr_synthetic.png`、`hdr10_hevc.png`
- `airspace_printwindow.png`、`airspace_qt_grab.png`、`overlay_probe.png`、`hwdec_hevc.png`、`hwdec_4k60.png`
- **4K60 HEVC/HDR**：`fixtures/test_4k60_hevc_hdr.mp4`、`fixtures/test_1080p60_hevc_hdr.mp4`（自产，gitignore）
- `hwdec_report.json`

---

## 7. 一句话总结

**libmpv 的能力足够支撑“音乐 + 视频”双模；真正卡住体验的不是解码，而是 Windows 原生子窗口的叠加限制。1.0 用 `wid` + 下方控制条绕开它，把 render API 自定义覆盖留到 1.2。**
