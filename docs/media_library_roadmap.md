# 媒体库生产化路线（CUE / 在线元数据）

当前已完成：FTS5 搜索、标签编辑、重复检测、封面网格、队列抽屉、全屏播放页、**单/多文件 CUE/整轨连续播放与入库**、**MusicBrainz 元数据**、**LRCLIB 在线歌词**、**Cover Art Archive 在线封面**。

仍待：Chromaprint/`fpcalc` 二进制的准确率验收；无 fpcalc 时使用内置 PCM 包络指纹（可识别转码副本，弱于 Chromaprint）。

---

## 1. CUE / 整轨（单文件已落地）

**问题**：APE/FLAC 整轨 + `.cue` 是本地无损库的常见形态；当前只能整轨播放，不能按曲目切分。

**状态**：单/多文件 CUE 已解析、入库为虚拟曲目并进入 mpv 队列（`start/end`），支持整轨连续播放和封面网格。

**设计**：

1. `core/cue.py` 解析：
   - `FILE`、`TRACK nn AUDIO`、`TITLE`、`PERFORMER`、`INDEX 00/01`；
   - 计算每轨 `start/end`（下一轨 INDEX 或音频总时长）。
2. 虚拟曲目模型：
   - `CueTrack(path, start, end, title, artist, album, track_no)`；
   - 不复制/不切割音频文件。
3. 播放队列扩展：
   - `PlayableItem(path, start=None, end=None)`；
   - mpv 用 `loadfile`/队列条目的 `start`/`end` 选项，或播放时 seek + 监听 `time-pos` 到 end 后 next；
   - 需要验证 mpv 0.41 的 `loadfile` options 语法。
4. 扫描：
   - `.cue` 与音频同目录时生成虚拟曲目；
   - 歌曲 path 用稳定 ID（如 `file.flac#cue:03`），数据库增加 `cue_path/start/end` 列；
   - 标签/封面沿用整轨文件。
5. UI：
   - 专辑网格显示 CUE 专辑；
   - 曲目表显示 01/02…；
   - 双击播放对应区间。

**风险**：mpv 队列区间结束检测、seek 精度、CUE 编码（GBK/UTF-8）、多文件 CUE。

---

## 2. 在线元数据 / 封面 / 歌词

**状态**：MusicBrainz 元数据 + LRCLIB 歌词 + Cover Art Archive 封面已接入。

**目标**：减少手工整理，不强制联网。

**方案**：

- 元数据：MusicBrainz recording/release 搜索（User-Agent、限速 1 req/s）；
- 封面：Cover Art Archive（按 release MBID）；
- 歌词：LRCLIB 等公开 API，或用户配置源；
- 全部 **opt-in**，本地缓存到 `covers/`、`lyrics/`；
- 标签编辑对话框加“在线补全”按钮，先预览再写入；
- 失败/离线时静默回退本地标签，不阻塞 UI。

**风险**：API 可用性/限速、中文匹配准确率、版权/许可、隐私（不上传文件，只发 artist/title）。

---

## 3. 重复检测增强

已实现“元数据候选 + 文件指纹”。后续可加：

- 音频指纹（Chromaprint/AcoustID）识别不同码率/转码重复；
- 相似标题模糊匹配；
- 批量保留最高码率/最大文件；
- 回收站/备份，而不是只从库移除。

---

## 4. 建议顺序

1. CUE 解析 + 虚拟曲目（播放区间）；
2. 在线元数据/封面（MusicBrainz + CAA，opt-in）；
3. 音频指纹去重；
4. 标签批量编辑/重命名模板。
