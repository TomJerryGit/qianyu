# 性能预算与验收指标

## 目标

| 指标 | 目标 |
|---|---|
| 冷启动（p95） | ≤ 2.0 s |
| 热启动（p95） | ≤ 1.0 s |
| 10k 曲库搜索（p95） | ≤ 50 ms |
| 100k 曲库搜索（p95） | ≤ 150 ms |
| 10k 曲模型刷新 | ≤ 100 ms |
| 空闲内存 | ≤ 300 MB |
| 8 小时内存增长 | ≤ 20 MB |
| 音频播放 CPU（idle） | ≤ 5% |
| 全屏页滚动/动画 | ≥ 55 FPS |
| 频谱首帧 | ≤ 1.5 s |
| 封面加载 | 不阻塞 UI；缓存命中 ≤ 50 ms |

## 当前基线

- 10k 曲搜索：约 17.7–28 ms；
- 10k 模型刷新：约 64 ms；
- 100 首短 WAV 队列：约 4.7 s（4×）；
- 8 小时浸泡：RSS 77.7 → 76.2 MB；
- 冷启动/新 smoke：100/100 通过；
- 覆盖率：约 26%（当前 CI 门禁 20%，1.0 目标 40%）。

## 建议测量方式

```powershell
# 现有基准
QT_QPA_PLATFORM=offscreen python spike/bench_library.py

# 频谱
python tools/spectrum_stream_test.py

# WASAPI 环境探测
python tools/wasapi_probe.py
```

建议后续加入：

- 启动计时（进程开始 → 主窗口可交互）；
- 搜索 p50/p95（1k 词样本）；
- FFmpeg 频谱进程数/CPU；
- 全屏页帧时间；
- 内存 RSS 定时采样；
- 结果写入 `spike/out/perf.json`，CI 与基线对比。

## 优化优先级

1. 全屏背景模糊（`QGraphicsBlurEffect`）缩放/缓存；
2. 封面解码与缩略图缓存；
3. 拼音后台回填（已持久化）；
4. FFmpeg 频谱进程复用/超时；
5. 搜索模型刷新批处理；
6. 远程封面缓存上限与清理。
