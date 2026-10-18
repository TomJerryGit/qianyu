# 浅语影音 0.9.0 Beta 发布说明

- **日期**：2026-10-18
- **包**：PySide6 6.8.3 / Qt 6 / Python 3.11
- **定位**：音乐版 0.9 Beta + 视频模式 MVP（1.0 预览）

## 已包含

- 本地媒体库：SQLite + mutagen，扫描/增量/搜索/标签/封面；FTS5 trigram 搜索、1 万曲 13.6 ms；标签编辑、批量标签、重复检测（移库不删文件）、可选 Chromaprint/PCM 包络深度去重、MusicBrainz 在线补全、在线封面/歌词、单/多文件 CUE 入库与整轨连续播放、收藏/最近/最常/未播放筛选；
- 播放：libmpv，队列无缝切歌、EQ、ReplayGain、WASAPI 独占；
- 播放列表：拖拽、多选、右键、JSON 持久化；
- 歌词：LRC/多时间标签/偏移/关联/编辑/桌面歌词；
- 界面：深/浅主题、迷你播放器、托盘、全局媒体键、设置；分区标题/统计/空状态，搜索防抖与封面缓存；专辑/艺术家封面网格、队列抽屉、全屏正在播放页、封面主色强调色；
- 视频 MVP：本地/URL、4K/硬解、字幕/编码/样式、音轨/字幕轨、截图、续播、文件夹队列、章节、书签、比例/旋转/倍速/逐帧/A-B、色彩/HDR 参数、音频延迟、全屏手势层；
- 安装：`install.ps1`（按用户）+ Inno 安装包；
- 更新：manifest 版本检查、可选 Ed25519 签名、SHA-256 校验、下载后运行安装包。

## 验证

- 33 个单元测试通过（核心/媒体库/引擎/更新/音频金标准/标签去重/在线元数据/CUE 多文件与区间播放/指纹）；
- PySide6 `--smoke` offscreen/windows 均 0；
- UI 冒烟：扫描/播放/歌词/桌面歌词/迷你/设置/歌词编辑；
- 视频冒烟：4K H.264（`d3d11va`、0 丢帧）、字幕、截图、续播、队列、章节、书签、比例/倍速/逐帧/A-B、色彩、音频延迟、全屏手势；
- 安装：`install.ps1` 安装/启动/卸载；Inno sandbox 变体安装/启动/卸载；
- 音频：gapless 4.0 s、EQ 1 kHz +8 dB 以上。

## 已知限制

1. **HDR 显示器验收未做**：HDR10 元数据/10-bit HEVC 样本已验证，但本机无 HDR 显示器。
2. **HEVC 10-bit 硬解**：本机 GPU 不支持，4K60 HEVC 只能软件解码。
3. **Authenticode**：安装包未签名；无 `signtool`/证书。提供 `SHA256SUMS.txt` 作为完整性校验。
4. **Inno 生产安装**：沙箱写卸载注册表被拒；真实桌面安装需再验。
5. **V12 窗口内覆盖/皮肤**：全屏手势层已做；窗口内自定义覆盖留 1.2 render API。

## 文件

- `dist-pyside6/QianYu/QianYu.exe`
- `dist/installer/QianYu-0.9.0-setup.exe`
- `dist/installer/SHA256SUMS.txt`
- `QianYu_run.bat`
- 文档：`docs/music_0.9_status.md`、`docs/video_mvp_status.md`、`docs/release_readiness.md`
