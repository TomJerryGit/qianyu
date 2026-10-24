# Navidrome 真实联调记录

日期：2026-10-24  
服务器：Navidrome 0.64.2（Windows amd64，官方 Release）  
客户端：QianYu `SubsonicClient`  
协议：Subsonic API（Navidrome 兼容）

## 测试方式

本地临时启动一个 Navidrome 实例：

```powershell
python tools\navidrome_integration.py
```

脚本在独立数据目录中：

1. 启动 `navidrome.exe`（127.0.0.1:4534）；
2. 调用 `/auth/createAdmin` 创建测试管理员；
3. 等待媒体库扫描完成；
4. 使用 QianYu 的 `SubsonicClient` 执行：
   - `ping`
   - `search3` / `search_songs`
   - `getAlbumList2` / `albums`
   - `getAlbum` / `album_songs`
   - `stream` 读取 4 KB；
5. 关闭服务器。

## 实测结果

```json
{
  "ready": true,
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

日志：

```
READY http://127.0.0.1:4534
ADMIN created 200
PING True
SEARCH 1
SONG single_tone | [Unknown Artist] | [Unknown Album]
ALBUMS 1
ALBUM_SONGS 2
RESULT {"ready": true, "ping": true, "songs": 1, "albums": 1, "album_tracks": 2, "stream": true, "stream_bytes": 4096}
SERVER_STOPPED
```

## 结论

QianYu 的 Subsonic 客户端已通过真实 Navidrome 的：

- 认证；
- ping；
- 搜索；
- 专辑列表；
- 音频串流读取；
- 封面 `getCoverArt` 读取（511 字节 JPEG）。

这不是 mock 测试，而是真实 Navidrome 进程。

## CI

`.github/workflows/navidrome-integration.yml` 在 `windows-latest` 上：

1. 下载固定版本 Navidrome 0.64.2；
2. 校验 SHA-256；
3. 解压；
4. 运行 `tools/navidrome_integration.py`；
5. 上传日志和 JSON。

触发条件：`workflow_dispatch`、修改 `subsonic.py`、修改联调脚本或 workflow。

本地也可以直接运行同一脚本：

```powershell
python tools\navidrome_integration.py
```

## CI 结果

```
workflow: navidrome-integration
commit:   6668e03
run:      40104142606
result:   success
```

CI 日志与 `navidrome_integration.json` 作为 artifact 上传。

## 说明

- 测试使用临时端口/临时数据目录，不修改用户现有 Navidrome 数据；
- 服务器在测试结束后停止；
- 应用内还需在 `设置 → 远程媒体库` 填写你自己的 URL/用户名/密码；
- Jellyfin 仍只有 mock/客户端代码测试，尚未在真实 Jellyfin 服务器上验证。
