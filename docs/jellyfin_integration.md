# Jellyfin 真实联调

日期：2026-10-24  
服务器：Jellyfin 12.3.0（Windows amd64，官方 ZIP）  
客户端：QianYu `JellyfinClient`  
协议：Jellyfin HTTP API

## 测试方式

脚本：

```powershell
python tools\jellyfin_integration.py
```

流程：

1. 启动临时 Jellyfin 服务器（127.0.0.1:8096）；
2. 等待 Startup Wizard API；
3. 创建管理员 `qianyu`；
4. 完成启动向导；
5. 添加音乐库；
6. 生成带 ID3 标签的测试 MP3；
7. 等待扫描；
8. 登录、搜索、专辑、专辑曲目、音频串流；
9. 关闭服务器。

## 实测结果

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

日志：

```
PUBLIC_READY
STARTUP_READY
CONFIG 204
FIRST_USER 200 {'Name': 'PL'}
USER 204
REMOTE 204
COMPLETE 204
RAW_LOGIN 200
LOGIN token=True
LIBRARY 204
REFRESH 204
SEARCH 1 ALBUMS 1
ALBUM_SONGS 1
COVER True 319
RESULT {"login": true, "songs": 1, "albums": 1, "album_tracks": 1,
         "cover": true, "cover_bytes": 319,
         "stream": true, "stream_bytes": 4096}
SERVER_STOPPED
```

封面测试使用带内嵌封面的 MP3，并等待 Jellyfin 异步生成 ImageTag 后重试，最终成功读取 319 字节 JPEG。

## 联调发现并修复的问题

Jellyfin 12.3 不再只接受：

```
X-Emby-Authorization
```

还需要在标准 `Authorization` 头中携带 token：

```
Authorization: MediaBrowser Client="QianYu", Device="Windows",
  DeviceId="...", Version="0.9.0", Token="..."
```

已修改：

```
src/qianyu/core/jellyfin.py
```

并新增回归测试：

```
tests/unit/test_jellyfin.py::test_authorization_includes_token
```

## 结论

QianYu 的 Jellyfin 客户端已通过真实 Jellyfin 12.3：

- 启动向导；
- 管理员登录；
- 音乐库扫描；
- 搜索；
- 专辑列表；
- 专辑曲目；
- 封面（319 字节 JPEG）；
- 音频串流。

## 在应用中连接本地 Jellyfin

测试服务器可手动启动：

```powershell
D:\qianyu\tools\start_jellyfin.cmd
```

然后应用设置：

```
设置 → 远程媒体库 → Jellyfin
服务器：http://127.0.0.1:8096
用户名：qianyu
密码：qianyu-test-pass
```

测试数据：

```
Test Artist / Test Album / Test Song
```

## CI

`.github/workflows/jellyfin-integration.yml`：

- 修改 Jellyfin 客户端、联调脚本或 workflow 时自动运行，也支持手动触发；
- 下载固定版本 Jellyfin；
- 校验 SHA-256；
- 运行真实启动向导/登录/搜索/专辑/串流测试；
- 上传日志和 JSON。

最新结果：

```
run:    40187787028
commit: 413de99
result: success
```

本地脚本：

```powershell
python tools\jellyfin_integration.py
```

## 说明

- 真实 Jellyfin 服务器已跑通；
- Navidrome（Subsonic）真实联调也已通过；
- 测试音乐由 Jellyfin 自带 ffmpeg 生成，带 ID3 标签与封面；
- 下载的 Jellyfin ZIP 保存在 `tools/jellyfin.zip`。
