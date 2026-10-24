# Jellyfin 真实联调

## 当前状态

- Jellyfin 客户端：已实现并通过 **mock 协议测试**；
- 本地 Jellyfin Server：**尚未安装完成**；
- 原因：官方 Windows 包约 **199 MB**，当前网络镜像约 20–30 KB/s，下载时间不可接受。

Mock 测试结果：

```json
{
  "login": true,
  "songs": 1,
  "albums": 1,
  "album_songs": 1,
  "stream": true
}
```

脚本：

```
D:\qianyu\tools\jellyfin_mock_integration.py
```

## 安装真实 Jellyfin

官方 Windows 包：

```
https://repo.jellyfin.org/files/server/windows/latest-stable/amd64/jellyfin_12.3-amd64.zip
```

镜像：

```
https://sgp1.mirror.jellyfin.org/files/server/windows/stable/v12.3/amd64/jellyfin_12.3-amd64.zip
```

步骤：

1. 下载 ZIP；
2. 解压到 `D:\qianyu\tools\jellyfin-server`；
3. 运行 `jellyfin.exe`；
4. 浏览器打开 `http://127.0.0.1:8096`；
5. 完成首次设置：管理员账号、媒体库（音乐目录）；
6. 等待扫描完成。

## 配置 QianYu

```
设置 → 远程媒体库 → Jellyfin
服务器：http://127.0.0.1:8096
用户名：管理员用户名
密码：管理员密码
```

## 真实服务器验证脚本

```powershell
$env:JELLYFIN_URL = "http://127.0.0.1:8096"
$env:JELLYFIN_USER = "qianyu"
$env:JELLYFIN_PASSWORD = "你的密码"
python tools\jellyfin_real_test.py
```

期望：

```json
{
  "login": true,
  "albums": 1,
  "album_songs": 2,
  "stream_bytes": 4096,
  "ok": true
}
```

## 应用内验证

```
在线 → 远程专辑… → Jellyfin → 加载专辑
在线 → 统一搜索… → 搜索曲名
```

## 说明

- 真实 Jellyfin 服务器尚未跑通；
- Navidrome（Subsonic）真实联调已通过；
- Jellyfin API 代码路径已由 mock 覆盖；
- 下载完成后可直接运行 `jellyfin_real_test.py` 完成真实验证。
