# 发布就绪检查（0.9 / 1.0 视频）

- **日期**：2026-10-18
- **当前产物**：PySide6 6.8.3 / Python 3.11，`dist-pyside6/QianYu/QianYu.exe`
- **安装包**：`dist/installer/QianYu-0.9.0-setup.exe`（61.2 MB，未签名）
- **结论**：0.9 音乐版 + 视频 MVP 可进入 Beta；1.0 视频对外发布仍被 **HDR 显示验收、HEVC 10-bit 硬件矩阵、Authenticode** 三项阻塞。

---

## 1. 门槛表

| 门槛 | 状态 | 证据 / 说明 |
|---|---|---|
| 24 个单测 | ✅ | `tests/unit/*`，含 gapless/EQ/更新签名 |
| PySide6 `--smoke` | ✅ | dist-pyside6，offscreen/windows 均 0 |
| PySide6 UI 冒烟 | ✅ | 扫描/播放/歌词/桌面歌词/迷你/设置/歌词编辑 |
| PySide6 打包托盘 | ✅ | 根因是托盘 `QMenu` 未保存 Python 引用、GC 后悬空；已保存 `self._tray_menu`，打包版 `--smoke` 0 |
| 视频 4K H.264 | ✅ | 3840×2160@60、`d3d11va`、`display-resample` 0 丢帧 |
| 视频 4K60 HEVC | 🟡 样本可解 | HDR10 元数据通过；本机 GPU 无 HEVC 10-bit 硬解，软件远低于实时 |
| HDR10 元数据 | ✅ | `yuv420p10`、`bt.2020`、`pq`、`max-luma 1000`、`max-cll 1000/400` |
| HDR 显示器验收 | ❌ 阻塞 | 无 HDR 显示器；需实机看色调映射/高光/黑位 |
| `install.ps1` 安装/卸载 | ✅ | PySide6 包真实安装 → `--smoke` 0 → 卸载 |
| Inno 安装/卸载 | 🟡 逻辑已验，真实桌面待验 | sandbox 变体完成安装→`--smoke` 0→卸载；生产包改为 `CreateUninstallRegKey=no` + HKCU best effort 卸载项，注册表被拒不再回滚 |
| Authenticode | ❌ 阻塞 | 无证书/PFX；自签名证书存储权限被拒 |
| V12 触控/手势 | ✅ 全屏 + 可选窗口手势 | 全屏默认手势层；窗口模式可在“画面 → 窗口手势层”开启；窗口内自定义皮肤仍 1.2 |

---

## 2. 真实桌面安装验收步骤

1. 在普通用户桌面运行 `dist\installer\QianYu-0.9.0-setup.exe`；
2. 选择安装目录，完成安装；
3. 检查开始菜单/桌面快捷方式（如勾选）；
4. 启动应用，确认：
   - 音乐扫描/播放；
   - 视频打开 4K H.264；
   - 托盘图标、关闭到托盘；
   - 文件关联（如勾选）。
5. 控制面板/设置中卸载，确认：
   - 程序目录删除；
   - 快捷方式删除；
   - 文件关联清理（`--unregister-associations`）。
6. 记录安装日志（`/LOG=...`）与截图。

> 沙箱失败点曾是卸载信息注册表写入；生产包已改为 best effort，不再因注册表拒绝回滚，最终仍需真实桌面验收。

---

## 3. HDR 显示器验收清单

准备：

- HDR10 显示器（Windows HDR 已开启）；
- `spike/fixtures/test_4k60_hevc_hdr.mp4`；
- 对比 SDR 模式与 HDR 模式。

检查：

- [ ] Windows 显示设置显示 HDR 已开启；
- [ ] 播放时 `video-params` 为 `bt.2020/pq/10-bit`；
- [ ] 高光不过曝、暗部有细节；
- [ ] 切换 `tone-mapping`（bt.2390 / spline / clip）画面有可辨差异；
- [ ] 4K60 播放不卡顿（需要支持 HEVC 10-bit 硬解的 GPU）；
- [ ] 截图记录 `hdr10_hevc.png` 与实机照片。

本机限制：GPU 无 HEVC 10-bit 硬解，4K60 软解不可实时；因此该项必须在参考机执行。

---

## 4. HEVC 10-bit 硬件矩阵

需要至少三台参考机：

| 平台 | 检查 |
|---|---|
| Intel iGPU（11 代+） | `hwdec-current=d3d11va`、4K60 0 丢帧 |
| NVIDIA（GTX 16/RTX+） | `d3d11va`/`nvdec`、4K60 0 丢帧 |
| AMD（RDNA+） | `d3d11va`、4K60 0 丢帧 |

命令：

```powershell
python spike\mpv_video_hwdec.py
# 看 out/hwdec_report.json 的 hevc_hdr.status / hwdec-current
```

当前本机结果：`status=software_decode`，所有 `hwdec` 变体均 `no`。

---

## 5. Authenticode 签名

1. 获取 EV/OV 代码签名证书（PFX）；
2. 运行：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
  -Pfx C:\secure\qianyu.pfx -Password <password>
```

3. 验证：

```powershell
Get-AuthenticodeSignature dist\installer\QianYu-0.9.0-setup.exe
```

4. 同时签名 `QianYu.exe` 与安装包；
5. 更新 manifest 仍用 Ed25519 公钥（`docs/update_signing.md`）。

本机自签名被证书存储权限拒绝，无法完成；生产证书到位后按上述执行。

---

## 6. V12 触控手势（已做全屏版）

`wid` 原生子窗口会盖住 Qt **子控件**，但**独立顶层窗口**可以覆盖（overlay spike 已验证）。当前实现：

- 全屏时启用顶层半透明 `GestureOverlay`：单击暂停/横滑 ±10 s/竖滑音量/双击退出；
- 窗口模式可在“画面 → 窗口手势层”开启，overlay 只覆盖视频画面，窗口失活即隐藏；
- 关闭 mpv OSC，避免重复；
- 1.2 可用 render API/`QOpenGLWidget` 把窗口内覆盖与皮肤统一。

---

## 7. 发布建议

- **0.9 Beta 可以发布**：音乐功能、PySide6 包、安装脚本、24 单测、视频 MVP 均可用；
- **1.0 视频对外发布暂缓**，直到：
  1. HDR 显示器验收完成；
  2. 至少三平台 HEVC 10-bit 硬解/4K60 数据；
  3. Authenticode 签名完成；
  4. Inno 安装/卸载真实桌面通过。

### 仅有本机时的决策

如果只有这一台电脑：

- **HDR 显示器验收**与**HEVC 10-bit 硬件矩阵**无法在本机完成，应作为“已知限制”发布，而不是继续阻塞开发；
- Inno 已用注册表无关的 sandbox 变体验证安装→启动→卸载全链路；生产包改为 `CreateUninstallRegKey=no` + HKCU best effort，真实桌面待验；
- Authenticode 需要外部证书；没有证书时只能发布未签名包，并在下载页标注 SHA-256；
- V12 触控手势明确延后到 1.2，不在 1.0 `wid` 方案内继续投入。

因此建议：**0.9 Beta 按当前产物发布；1.0 视频标记为“软件 HDR-ready / 硬件验收待补”。**
