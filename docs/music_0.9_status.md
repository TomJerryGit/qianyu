# 0.9 音乐版：首个可运行切片状态

- **日期**：2026-10-17
- **状态**：**可运行原型（internal alpha）**，不是“可推荐”的 Beta。
- **代码位置**：`src/qianyu/`；开发启动：`python run_dev.py`
- **依赖**：PySide6 6.8.3（发布默认，Python 3.11）、python-mpv、mutagen、cryptography；PyQt5 保留为 Python 3.8 回退（见 `requirements-pyside6.txt` / `requirements-0.9.txt`）

---

## 1. 已经跑通的能力

| 能力 | 实现 | 验证 |
|---|---|---|
| libmpv 播放内核 | `engine/mpv_engine.py` | 播放 3 s WAV，position/duration/seek 正确；单元测试通过 |
| mpv 队列/无缝切换 | `set_queue()` + `playlist-pos` 观察 | 两首 2 s 曲目自动前进到 index=1；见 `test_queue_advances_without_reload` |
| 本地媒体库 | `library.py`（SQLite + mutagen） | 扫描 3 个 WAV：added=3；标签读取；按标题/艺术家/专辑搜索 |
| CUE/整轨 | `core/cue.py` + `ui/cue_dialog.py` + 引擎 `start/end` 队列 | 单/多文件 CUE 解析、连续播放、虚拟曲目入库/封面网格 |
| 收藏/最近播放 | 媒体库筛选 + 右键收藏 | SQLite `favorite/play_count/last_played`，最近/最常/未播放/最近添加 |
| 批量标签 | `ui/batch_tag_dialog.py` | 多选后批量改艺术家/专辑，逐个写文件+DB |
| 网络电台 | `core/radio.py` + `ui/radio_dialog.py` | Radio Browser 搜索/国家筛选，收藏/最近/导入导出，ICY 当前曲目，断流重连 |
| 播客 | `core/podcast.py` + `ui/podcast_dialog.py` | iTunes 搜索 + RSS 单集解析，mpv 播放 |
| 播客缓存 | `core/podcast_cache.py` + 播客对话框 | 单集下载/队列/离线播放/上限，默认 2 GB |
| ListenBrainz | `core/scrobble.py` + 设置 | 可选 Scrobbling，50%/4 分钟阈值，默认关闭 |
| 远程媒体库 | `core/subsonic.py` + `ui/remote_dialog.py` | Navidrome/Subsonic 搜索与串流 |
| Jellyfin | `core/jellyfin.py` | 登录、Audio 搜索、串流 |
| 统一搜索 | `ui/unified_search.py` | 本地 + Subsonic + Jellyfin |
| 远程专辑/队列/封面 | `ui/remote_album_dialog.py` + `core/cover_cache.py` | 专辑浏览、整张入队、eof 下一首、封面缓存 |
| 凭据加密 | `core/secure_store.py` | Windows DPAPI 加密 token/密码 |
| 经典电台 UI | `ui/radio_window.py` | 台式收音机窗口、调谐、预设、ICY |
| 经典音乐 UI | `ui/now_playing.py` + `ui/spectrum.py` | 全屏封面/歌词、真实本地频谱、歌手写真、经典金属主题 |
| 频谱分析 | `core/spectrum_analyzer.py` | FFmpeg PCM + Goertzel，本地文件 |
| WASAPI loopback | `core/wasapi_loopback.py` | 系统输出采集，流媒体实时频谱 |
| 网络流 | 主菜单“在线 → 打开网络流…” | HTTP/HTTPS 音频/视频流 |
| 音频指纹去重 | `core/fingerprint.py`（fpcalc/Chromaprint + PCM 包络回退） | 可选深度去重，相似度 ≥90%；无 fpcalc 时用内置离线包络指纹 |
| 在线封面 | `core/metadata.py` + 右键“获取在线封面” | 封面存档，写回封面字段 |
| 在线歌词 | `core/online.py` + “在线歌词”按钮 | LRCLIB 同步歌词，保存 `.lrc` 后本地加载 |
| 在线元数据 | `core/metadata.py` + 标签编辑“在线补全” | MusicBrainz 查询，预览后写标签；离线/失败静默回退 |
| 标签编辑 | `ui/tag_dialog.py` + `core/tagging.py` | ID3/easy 标签写入；媒体库同步更新；WAV 明确拒绝 |
| 重复检测 | `Library.find_duplicates()` + `ui/duplicate_dialog.py` | 元数据候选 + 文件指纹确认；从库移除不删文件 |
| 大库表格 | `ui/track_model.py`（QTableView + QAbstractTableModel） | 只渲染可见行，1 万曲不再重建 4 万个 item |
| 专辑/艺术家视图 | `ui/album_view.py` | 封面网格、专辑/艺术家分组、双击过滤并播放 |
| 队列抽屉 | 主界面“收起队列” | 隐藏播放队列，给媒体库/歌词更多空间 |
| 正在播放页 | `ui/now_playing.py` | 全屏大封面、模糊背景、歌词同步、上一首/下一首/暂停/关闭 |
| 主题取色 | `ui/theme_color.py` | 从封面提取主色，替换 QSS 强调色 |
| 封面 | 同名 `cover.jpg`/内嵌图片 → 正在播放 168×168 | 扫描后 `Track.cover` 指向封面；UI 显示 |
| 播放列表 | `core/models.py` + `core/playlist.py` | 去重、上一首/下一首、单曲循环、JSON 原子持久化、拖拽排序、多选删除 |
| 歌词 | `core/lyrics.py` + `ui/desktop_lyrics.py` | LRC 多时间标签/offset/UTF-8/GBK/UTF-16；当前行高亮；桌面歌词窗口 |
| 均衡器 | `ui/eq_dialog.py` | 10 段 -12…+12 dB、8 个预设、启用/旁路；复用 spike 验证的 FFmpeg equalizer 链 |
| 主界面 | `ui/main_window.py` | 媒体库表格、播放列表、封面、歌词、进度条（0–1000）、音量、静音、快捷键、菜单 |
| 系统集成 | 托盘 + 单实例 + 命令行打开 + 文件关联（按用户） | 关闭到托盘、二次启动唤回、`qianyu file.flac`、工具菜单注册关联 |
| 皮肤 | `ui/theme/dark.qss` / `light.qss` | 视图菜单切换；深/浅两套 |
| 迷你模式 | `ui/mini_player.py` | 无边框置顶小窗、封面/标题/控制、双击还原 |
| 歌词偏移/关联/编辑 | 工具栏 + `lyrics_map` / `lyrics_offsets` / `lyrics_editor.py` | ±0.5 s、手动选择/保存 `.lrc`、备份 `.bak`、按曲目持久化 |
| 扫描取消 | `ScanThread.cancel()` | 扫描进度中可取消；按钮状态随任务切换 |
| 播放列表右键 | `_playlist_context_menu` | 播放、在文件夹中显示、复制路径、移除 |
| ReplayGain | 设置 + `engine.set_replaygain` | 关闭/按曲目/按专辑 |
| WASAPI 独占 | 设置 + `engine.set_audio_exclusive` | 选项已接入；真实独占/比特完美未验证 |
| 安装 | `packaging/install.ps1` | 按用户复制、快捷方式、可选关联；**dist6 真实安装→--smoke 0→卸载**验证通过 |
| 更新检查 | `update.py` + 帮助菜单 | manifest/版本比较/可选 Ed25519 签名/SHA-256；可退出运行安装包 |
| 日志/崩溃 | `logs.py` | 轮转日志、`faulthandler`、异常钩子、崩溃对话框、启动 breadcrumb |
| 设置 | `ui/settings_dialog.py` | 主题、关闭到托盘、全局媒体键、输出设备、ReplayGain、音乐文件夹 |
| 全局媒体键 | `platform/media_keys.py` | Windows `RegisterHotKey`（真实桌面/托盘可用时启用） |
| 无头验证 | `spike/ui_smoke.py` | 扫描→封面→播放→歌词→偏移→音量→进度→双主题→桌面歌词→迷你；截图 |
| 音频金标准 | `tests/unit/test_audio_quality.py` | gapless 4.0 s 无插入静音；EQ 1 kHz +8 dB 以上、200 Hz 偏差 <2 dB |
| 性能基线 | `spike/bench_library.py` | 1 万曲：查询 361 ms、搜索 **13.6 ms**（FTS5 trigram）、模型刷新 35 ms；100 首队列 4.7–15 s（负载敏感） |

**本轮（Round 1）新增**：mpv playlist 队列（gapless 基础）、封面提取、播放列表拖拽/多选、托盘、单实例、命令行打开、深浅主题、桌面歌词。**单测从 11 增至 15，全部通过。**

**Round 2 新增**：文件关联（按用户，工具菜单）、迷你播放器、歌词偏移/手动关联、媒体库虚拟化、性能基线脚本。**单测增至 17。**

**Round 3 新增**：日志/崩溃转储/启动 breadcrumb（`logs.py`）、源码 `--smoke` 初始化验证；spike 补 **HEVC `d3d11va` 硬解**与 **合成 PQ/BT.2020 色调映射**证据；打包产物重建中。

**Round 4 新增**：设置对话框（主题/托盘/媒体键/输出设备/库目录）、Windows 全局媒体键、崩溃提示框、Inno Setup 安装脚本与 `packaging/build.ps1`；打包 `--smoke` 已在 offscreen/windows 退出 0。

**Round 5 新增**：扫描取消、歌词编辑器（备份 `.bak`）、播放列表右键菜单、ReplayGain 设置；死代码/导入清理与 UTF-8 冒烟输出修复。

**Round 6 新增**：WASAPI 独占设置、按用户 `install.ps1`（无需 Inno，复制/卸载已用临时源验证）、安装文档；设置继续扩展。

**Round 7 新增**：4K60 H.264 硬解实测（`d3d11va`、`display-resample`、2 s 0 丢帧）；发现默认 `video-sync=audio` 在无音轨时会掉帧，已写回 spike 决策。

**Round 8 新增**：用 `install.ps1` 对 dist6 做真实安装→启动冒烟→卸载全链路验证；补充 4K60/HEVC 硬解产物与报告。

**Round 9 新增**：音频金标准自动化测试（gapless 拼接 + EQ 频响），单测增至 23；开始 1.0 视频模式 MVP。

**Round 10 新增**：更新检查骨架（manifest/版本比较/SHA-256 下载）、设置中的更新源、帮助菜单“检查更新…”。

**Round 11 新增**：视频 V13 队列/文件夹连播、V14 章节下拉、V15 书签；视频冒烟覆盖 next/prev、章节跳转、书签跳转。

**Round 12 新增**：视频 V08 比例/旋转/去隔行、V09 倍速、V16 逐帧/A-B；视频冒烟覆盖 1.5×、16:9、90°、5.000→5.033 帧步进、A/B 设置与清除。

**Round 13 新增**：视频 V18 字幕样式记忆、V19 色彩调整、V20 音频延迟；本地 HTTP 服务验证 URL 流（11.97 s / 1280×720）。

**Round 14 新增**：V06 字幕编码、V12 操作 OSD、V17 HDR 参数控制；真实远程 HLS 1080p/4K 验证（1920×1080 / 3840×2160，`d3d11va`）。

**Round 15 新增**：V12 mpv 鼠标绑定（滚轮/右键/双击）、Ed25519 更新清单签名、`packaging/sign.ps1`、Inno 6.7.3 安装包编译。

**Round 16 新增**：PySide6 运行时迁移跑通（Python 3.11 venv + PySide6 6.12 + `qianyu.qt` shim）；UI/视频冒烟在 PySide6 下通过；默认仍 PyQt5，打包尚未切换。

**Round 17 新增**：PySide6 打包/default 切换完成（6.8.3，`dist-pyside6`，`--smoke` 两平台 0，install.ps1 安装/卸载通过）；PySide6 安装包重建。

**Round 18 新增**：用 imageio-ffmpeg/libx265 自产 4K60/1080p60 HEVC Main10 HDR10 样本；验证 `bt2020/pq/max-luma 1000/max-cll 1000/400`，发现本机 GPU 无 HEVC 10-bit 硬解（软件远低于实时）。

**Round 19 新增**：V12 全屏顶层手势层（单击暂停/横滑 seek/竖滑音量/双击退出），冒烟通过；确认顶层 Qt 窗口可覆盖 `wid` 视频。

**Round 20 新增**：V12 可选窗口手势层（仅覆盖视频画面、失活隐藏），PyQt5/PySide6 冒烟通过。

**Round 21 新增**：性能/UI 提升——搜索 160 ms 防抖、封面 LRU 缓存、播放列表批量刷新、媒体库统计/空状态、分区标题、表格/列表 hover/选中样式、主按钮与深/浅主题细节。

**Round 22 新增**：专辑/艺术家封面网格（双击过滤播放）、队列抽屉、全屏正在播放页（大封面/模糊背景/歌词同步）、封面主色强调色、视频控制条分组分隔。

**Round 23 新增**：SQLite FTS5 trigram 搜索（1 万曲搜索 13.6 ms）、批量扫描时暂停/重建 FTS 触发器、`mmap/cache/temp_store` 调优；封面网格/队列/正在播放页进入 UI 冒烟。

**Round 24 新增**：标签编辑对话框 + ID3/easy 标签写入；重复曲目检测（元数据候选 + 文件指纹）与只移库不删文件；单测增至 26。

**Round 25 新增**：MusicBrainz 在线元数据补全（标签编辑对话框内，预览后保存）；单测增至 27。

**Round 26 新增**：CUE 单文件整轨解析 + mpv `start/end` 队列连续播放（引擎区间测试通过）；LRCLIB 在线歌词；单测增至 29。

**Round 27 新增**：多文件 CUE + CUE 虚拟曲目入库（封面网格/搜索/双击播放）、Cover Art Archive 在线封面；单测增至 30。

**Round 28 新增**：可选 Chromaprint/fpcalc 音频指纹深度去重；`packaging/release.ps1` 生成便携 ZIP、release.json、校验和；单测增至 32。

**Round 29 新增**：收藏/最近播放筛选与播放计数；媒体库标题星标；单测增至 33。

**Round 30 新增**：最近添加/最常播放/未播放智能筛选；多选批量编辑艺术家/专辑。

**Round 31 新增**：Radio Browser 网络电台搜索/播放、收藏与网络流地址播放；单测增至 36。

**Round 32 新增**：iTunes 播客搜索 + RSS 单集解析/播放、订阅与已听标记、单集续播记忆；单测增至 40。

**Round 33 新增**：播客单集下载缓存、顺序下载队列、离线播放、缓存上限设置；单测增至 42。

**Round 34 新增**：可选 ListenBrainz Scrobbling、50%/4 分钟阈值、token 本地保存；单测增至 47。

**Round 35 新增**：电台最近收听/收藏导入导出/ICY 当前曲目/断流重连；版权与在线内容合规文档、SPDX 头、安装包版权元数据。

**Round 36 新增**：Subsonic/Navidrome 远程媒体库搜索与串流；单测增至 50。

**Round 37 新增**：Windows DPAPI 加密 ListenBrainz token/远程密码；经典电台窗口；单测增至 52。

**Round 38 新增**：经典音乐全屏页动态频谱、歌手写真（本地/Deezer）、经典金属主题；单测增至 54。

**Round 39 新增**：Jellyfin 登录/搜索/串流；本地 + Subsonic + Jellyfin 统一搜索；单测增至 57。

**Round 40 新增**：远程专辑浏览、整张入队、远程播放队列、封面缓存；单测增至 61。

**Round 41 新增**：经典金属主题下的视频底部遥控器风格控制栏。

**Round 42 新增**：本地文件真实频谱（FFmpeg PCM + Goertzel）；流媒体回退装饰频谱；单测增至 63。

**Round 43 新增**：WASAPI loopback 系统输出采集，流媒体实时频谱；单测增至 65。

**Round 44 新增**：内置精选公开电台（SomaFM/Radio Paradise/FIP/KEXP/NPR 等），收藏/最近；单测增至 66。

**Round 45 新增**：电台/播客/远程多源统一搜索、本地模糊搜索、主流平台官方搜索深链；单测增至 69。

**Round 46 新增**：拼音搜索（全拼/首字母）、搜索相关性排序（标题/艺术家/收藏/播放次数）；单测增至 70。

**Round 47 新增**：电台分类/国家浏览、精选电台按分类过滤；Radio Browser 标签查询。

**Round 48 新增**：拼音索引持久化（tracks.pinyin + 后台回填），拼音搜索不再每次全库计算；单测增至 71。

**Round 49 新增**：移除 SignPath 依赖；改为未签名分发 + SHA256/源 tag 校验，保留未来自有 Authenticode 证书选项。

**Round 50 新增**：搜索词高亮、首次启动兴趣频道并自动生成精选电台收藏；单测增至 74。

**Round 51 新增**：远程媒体库“测试连接”按钮，便于本地 Navidrome/Subsonic 联调。

**Round 52 新增**：真实 Navidrome 0.64.2 联调通过（ping/搜索/专辑/串流），见 `docs/navidrome_integration.md`。

**Round 53 新增**：远程专辑筛选/刷新、专辑计数与空结果提示。

**Round 54 新增**：Jellyfin mock 协议联调（登录/搜索/专辑/串流）；真实服务器安装受 199 MB 下载速度限制，待完成。

**Round 55 新增**：远程专辑封面异步加载、专辑信息预览；Navidrome 真实联调 CI 已通过（run 40104142606）。

**Round 56 新增**：真实 Jellyfin 12.3 联调通过（启动向导/登录/搜索/专辑/曲目/串流）；修复 Jellyfin 12.3 `Authorization` token 头；单测增至 75。

**Round 57 新增**：远程专辑封面 UI 测试、Jellyfin 真实联调 CI 工作流（手动/路径触发）；单测增至 77。

**Round 58 新增**：Jellyfin 真实联调 CI 已通过（run 40187787028）；修复 CI 脚本硬编码路径。

**Round 59 新增**：Jellyfin `album_cover_url` 与封面探测；真实服务器测试素材未生成 ImageTag，封面探测非阻塞；单测增至 78。

**Round 60 新增**：FFmpeg 渐进式频谱（本地/HTTP 流，无需音频设备），Jellyfin 内嵌封面真实联调通过（319 字节）；单测增至 79。

**Round 61 新增**：网络 URL/响应大小安全守卫、秘密扫描、安全 CI 与威胁模型；单测增至 82。

**Round 62 新增**：Release SBOM/许可证清单、SHA256 校验器、OSV 依赖审计、覆盖率 CI；单测增至 84。

**Round 63 新增**：覆盖率阈值、性能门禁、原生组件许可证评估、真实桌面兼容矩阵。

**Round 64 新增**：UI smoke 纳入覆盖率统计，单元 + smoke 合计约 48%，CI 覆盖率门禁提升到 40%。

**Round 31 新增**：Radio Browser 网络电台搜索/播放、网络流地址播放；单测增至 35。

**实测数据（`spike/ui_smoke.py`）**：

```
SCAN added=3 errors=0
COVER ...\music\cover.jpg
ROWS 3
SLIDER_MAX 1000
POSITION 0.51 DURATION 2.0
PROGRESS_SET 500
VOLUME 50
LYRICS_AFTER 3 NOW_AFTER single_tone
LYRICS_OFFSET 偏移 +500 ms
DESKTOP_LYRICS True 第一行歌词
MINI True single_tone
```

**性能基线（`spike/bench_library.py`）**：

```json
{
  "library": {"rows": 10000, "insert_10k_ms": 358.0, "tracks_query_ms": 369.9,
               "search_ms": 17.7, "model_refresh_ms": 64.1},
  "queue": {"tracks": 100, "reached_99": true, "elapsed_s": 4.71}
}
```

> 100 首耗时随系统负载/倍速生效波动；CI 串行检查时曾测到约 17 s，但均到达 index 99。

---

## 2. 与“可推荐”的差距

### P0（0.9 Beta 前必须补）

| 项 | 现状 | 目标 |
|---|---|---|
| 设置持久化 | 音量/窗口/主题/列表/歌词偏移/ReplayGain/输出设备 | 歌词字体、快捷键、关闭行为 |
| 崩溃/日志 | 日志/崩溃框已接入；无上报 | 上报、隐私开关 |
| 安装器/签名/更新 | Inno 6.7.3 已安装并编译 `dist\installer\QianYu-0.9.0-setup.exe`；manifest 可选 Ed25519；安装包未 Authenticode 签名 | 安装包代码签名、自动替换、安装烟测 |

### P1（1.0 前）

- CUE/整轨、WASAPI 独占、DSD/多声道、设备热插拔。
- 标签编辑（原子写、备份）、重复检测、丢失文件处理。
- SMTC/任务栏缩略图按钮。
- 多语言、可访问性、高 DPI 截图回归。
- PySide6 迁移（解决 PyQt5 GPL 分发）或购买商业授权。
- 安装器、签名、自动更新、遥测（opt-in）。

---

## 3. 四周迭代计划（0.9 Beta）

### Sprint 1（第 1–2 周）：播放与库的“可信”

- ✅ mpv playlist 队列：预加载下一首、gapless 基础、`playlist-pos` 同步。
- ✅ 封面提取/缓存；正在播放显示。
- ✅ 播放列表拖拽排序、多选删除。
- ✅ 库扫描：进度；1 万曲查询/搜索/模型刷新基准（370/17.7/64 ms）。
- ✅ 100 首连续播放（4×，4.71 s，到达 index 99）。
- ⏳ 扫描取消、错误列表；混合格式/长时浸泡。

### Sprint 2（第 3–4 周）：歌词与桌面集成

- ✅ 桌面歌词窗口（无边框/置顶/拖拽/双行）。
- ✅ 托盘、单实例、命令行打开、按用户文件关联。
- ✅ 两套皮肤（暗/亮）。
- ✅ 迷你模式；歌词偏移/手动关联。
- ⏳ 全局媒体键；歌词编辑/编码选择；迷你窗口记忆位置。
- 验收：双击文件起播；关窗进托盘；歌词双屏正确。

### Sprint 3（第 5–6 周）：工程与发布

- PySide6 迁移评估/执行（或商业授权决策）。
- 日志/faulthandler/崩溃转储；安装器 + 签名；自动更新骨架。
- 性能门禁：启动、内存、扫描、搜索；CI（lint/单测/构建）。
- 验收：安装/卸载干净；崩溃可定位；性能达标。

### Sprint 4（第 7–8 周）：Beta 硬化

- 100 位真实用户；崩溃-free ≥99%；P0=0。
- 兼容矩阵：Win10/11、DPI、中文/长路径、只读目录、睡眠恢复。
- 文档/FAQ/已知限制；发布 0.9 Beta。
- 验收：Beta 退出条件全绿。

---

## 4. 当前已知问题（诚实清单）

1. **文件关联/托盘/单实例未在真实桌面验收**：沙箱禁止命名管道与注册表写入；代码已实现，需在真机点击“工具→注册文件关联”验证。
2. **封面只验证了同名 `cover.jpg`**：内嵌 APIC/FLAC picture/MP4 covr 的提取代码已写，但未用真实带封面的 MP3/FLAC 验证。
3. **PyQt5 GPL**：发布包默认已切 PySide6 6.8.3 / Python 3.11；PyQt5 仅保留 Python 3.8 回退。LGPL 合规清单仍待整理。
4. **Python 3.8**：本机 3.8.9，已 EOL；1.0 前升 3.11/3.12。
5. **测试覆盖有限**：84 个单测 + 1 个 UI 冒烟 + 1 个基准；有 gapless/EQ 金标准，但无浸泡/兼容矩阵。
6. **安装包/更新**：`install.ps1` 已用 PySide6 包完成真实安装/启动/卸载；Inno 6.7.3 已编译 `dist\installer\QianYu-0.9.0-setup.exe`（61.2 MB，PySide6/6.8.3）。生产安装器使用 `CreateUninstallRegKey=no` + HKCU best effort 卸载项，注册表被拒时安装不再回滚；真实桌面验收仍待做。manifest 支持 Ed25519，安装包本身未签名。
7. **性能基线有数据但未入门禁**：1 万曲搜索 17.7–28 ms、模型刷新 64 ms；100 首队列可完成，耗时受负载波动；尚未在 CI 设阈值。
8. **桌面歌词暂无锁定/鼠标穿透**；需要真机验证多屏。
9. **无缝队列只验证了 100 首短 WAV**：混合格式/长时浸泡/ReplayGain 尚未验证。
10. **全局媒体键未在真实桌面验证**：`RegisterHotKey` 只在托盘可用时启用；沙箱无法验收。

---

## 5. 如何运行

```powershell
# 发布默认：Python 3.11 + PySide6 6.8.3
tools\venv311\Scripts\python.exe -m pip install -r requirements-pyside6.txt

# 开发启动（自动把 src/ 加入 sys.path）；或双击 QianYu_run.bat
tools\venv311\Scripts\python.exe run_dev.py

# 无头冒烟
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
tools\venv311\Scripts\python.exe spike\ui_smoke.py

# 单元测试
python -m unittest tests.unit.test_core tests.unit.test_engine -v
```

---

## 6. 一句话

**0.9 的第一个可运行切片已经成立：能扫描、能播、能显示歌词、能调 EQ、能记住列表；但“可推荐”还差无缝队列、封面、桌面歌词、托盘/关联、皮肤和发布工程——按上面 4 个 Sprint 推进。**
