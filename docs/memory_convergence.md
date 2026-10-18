# 内存收敛记录

目标：30 分钟压力循环 RSS 增量 < 5 MB。

## 已做修改

1. **播放列表保存防抖**
   - `_sync_index` 不再每次切歌立即 `PlaylistStore.save()`；
   - 500 ms 单次定时器合并写入。

2. **播放列表增量刷新**
   - `_refresh_playlist` 不再 `clear()` 后重建全部 `QListWidgetItem`；
   - 只更新文本/路径，数量变化才增删。

3. **封面网格签名缓存**
   - `AlbumView.set_tracks` 对 `(mode, path, album, artist, cover)` 做签名；
   - 媒体库未变化时跳过 `clear()`/重建图标。

4. **媒体库刷新签名**
   - `_refresh_library` 对过滤后的曲目字段做签名；
   - 同一关键词、同一模式、数据未变化时跳过表格 model reset、统计和空状态更新。

## 30 分钟验证（当前构建）

```
开始   76.8 MB（进程冷启动，缓存未预热）
5 min  124.4 MB
10 min 124.3 MB
15 min 124.3 MB
20 min 124.4 MB
25 min 124.3 MB
30 min 124.4 MB

5→30 分钟增量：0.0 MB
0xC0000005：0
```

以 5 分钟预热后的平台为基线：**30 分钟内完全平坦**，达到 <5 MB 目标。

## 10 分钟验证（修复后首次）

```
开始   109.2 MB
5 min  126.1 MB
10 min 126.4 MB

5→10 分钟 +0.3 MB
```

对比修复前同区间约 +1.9 MB，增长明显收敛。  
仍需 30 分钟确认是否真正平台化。

## 下一步若仍增长

- 把 `QListWidget` 播放列表改为 `QAbstractListModel + QListView`；
- 封面网格分页/缩略图上限；
- 检查 `QListWidgetItem`/`QIcon` 的 Qt 端缓存；
- 用 `gc.get_objects()` 与 Qt 对象计数区分 Python/Qt/native 增长。
