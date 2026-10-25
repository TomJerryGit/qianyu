# 本地自动验收记录

日期：2026-10-25  
环境：Windows 10.0.19045 / Python 3.11 打包版 / PySide6 6.8.3

## 1. 便携安装 / 启动 / 卸载

安装到临时目录：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 `
  -Target D:\qianyu\tools\acceptance-install `
  -NoShortcuts -NoAssociations
```

启动 smoke：

```powershell
$env:QIANYU_NO_SINGLE_INSTANCE='1'
$env:QT_QPA_PLATFORM='offscreen'
D:\qianyu\tools\acceptance-install\QianYu.exe --smoke
```

结果：

```
EXIT 0
```

卸载：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\install.ps1 `
  -Uninstall -Target D:\qianyu\tools\acceptance-install
```

结果：

```
D:\qianyu\tools\acceptance-install 已删除
```

结论：便携安装/启动/卸载通过。

## 1.1 Inno 安装包静默验收

```powershell
QianYu-0.9.0-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS
  /DIR=D:\qianyu\tools\inno-acceptance /LOG=D:\qianyu\tools\inno-acceptance.log
```

结果：

```
INSTALL_EXIT 0
EXISTS True

SMOKE_EXIT 0

UNINSTALL_EXIT 0
```

卸载后目录内文件数为 0。  
结论：Inno 安装/启动/卸载通过。

## 2. 单元测试

```powershell
python -m unittest discover -s tests\unit
```

结果：

```
Ran 78 tests
OK
```

## 3. Navidrome 真实联调

```powershell
python tools\navidrome_integration.py
```

结果：

```json
{
  "ping": true,
  "songs": 1,
  "albums": 1,
  "album_tracks": 2,
  "stream": true,
  "stream_bytes": 4096,
  "cover": true,
  "cover_bytes": 511
}
```

CI：

```
navidrome-integration run 40104469671 success
```

## 4. Jellyfin 真实联调

```powershell
python tools\jellyfin_integration.py
```

结果：

```json
{
  "login": true,
  "songs": 1,
  "albums": 1,
  "album_tracks": 1,
  "cover": true,
  "cover_bytes": 319,
  "stream": true,
  "stream_bytes": 4096
}
```

Jellyfin 封面：带内嵌封面 MP3 + 异步 ImageTag 重试后成功读取 319 字节 JPEG。

CI：

```
jellyfin-integration run 40189202265 success
```

## 5. 频谱

### 5.1 WASAPI 桌面输出

```powershell
python tools\wasapi_probe.py
```

结果：

```
COCREATE 0x0
DEVICE 0x0
MIXFORMAT 0x0
FORMAT_TAG 65534 CHANNELS 2 RATE 48000
INITIALIZE 0x0
START 0x0
FRAMES_TOTAL 0
```

当前执行环境没有实际音频输出，WASAPI 捕获为 0。

### 5.2 FFmpeg 渐进式频谱（无需音频设备）

```powershell
python tools\spectrum_stream_test.py
```

结果：

```
LOCAL  SOURCE: 频谱：真实 · FFmpeg   LEVELS: 0.363
STREAM SOURCE: 频谱：实时 · 流分析   LEVELS: 0.363
LOCAL2 SOURCE: 频谱：真实 · FFmpeg   LEVELS: 0.363
```

结论：

- 本地文件和 HTTP 流均可实时输出真实频谱；
- 不依赖桌面音频设备；
- WASAPI 作为流分析失败时的回退；
- 真实桌面波形仍建议人工确认一次。

## 6. 结论

| 项 | 结果 |
|---|---|
| 便携安装/启动/卸载 | ✅ |
| 82 单测 | ✅ |
| Navidrome 真实联调 | ✅ |
| Navidrome CI | ✅ |
| Jellyfin 真实联调 | ✅ |
| Jellyfin CI | ✅ |
| 远程专辑/串流 | ✅ |
| Jellyfin 封面 | ✅ 319 字节 |
| 渐进式频谱 | ✅ 本地 + HTTP 流 |
| WASAPI 桌面频谱 | 🟡 环境无音频设备 |

剩余不是代码路径，而是真实桌面音频与 UI 交互验收。
