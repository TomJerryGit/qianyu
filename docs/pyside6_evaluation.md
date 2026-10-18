# PySide6 迁移评估（0.9 → 1.0）

- **日期**：2026-10-17
- **当前**：PyQt5 5.15.11 / Qt 5.15.2（GPLv3 或商业许可）
- **目标**：PySide6 / Qt 6（LGPLv3），或购买 PyQt 商业授权
- **结论**：**运行时迁移已跑通**（Python 3.11 venv + PySide6 6.8.3 + Qt shim）；打包/default 切换正在收尾。

---

## 0. 实施进展（2026-10-18）

已完成：

- 新增 `src/qianyu/qt.py`：默认按 Python 版本自动选择（3.9+ 优先 PySide6，3.8 用 PyQt5），可用 `QIANYU_QT` 强制；
- 所有 UI/平台模块改为从 `qianyu.qt` 导入；
- 创建 `tools/venv311`（Python 3.11.9），安装 PySide6-Essentials **6.8.3**、python-mpv、mutagen、Pillow；
- `QIANYU_QT=PySide6` 下：
  - `run_dev.py --smoke` 退出 0；
  - `spike/ui_smoke.py` 全流程通过（扫描/播放/歌词/桌面歌词/迷你/设置/歌词编辑）；
  - `spike/video_window_smoke.py` 通过（4K、`d3d11va`、字幕、截图、续播）。
- PySide6 6.8.3 的 PyInstaller 包已构建（`dist-pyside6`），`--smoke` offscreen/windows 均退出 0；`install.ps1` 安装后启动/卸载通过；Inno 安装包已基于该包重建。
- 打包托盘 `0xC0000005` 已修复：根因是 `QMenu` 局部变量被 GC、`QSystemTrayIcon` 持有悬空指针；保存 `self._tray_menu` 后打包版托盘正常。
- `MpvEngine.shutdown()` 改为带 3 s 超时的 daemon 线程，避免 Qt 事件线程在退出时阻塞。

仍待做：

- PyInstaller **PySide6 打包**已完成（`dist-pyside6`，6.8.3）；
- 默认依赖/启动已切到 PySide6（Python 3.11 自动选择；3.8 保留 PyQt5 回退）；
- PySide6 安装包已重建；真实桌面安装/卸载仍需执行；
- LGPL 第三方清单/合规审核。

---

## 1. 为什么必须处理

PyQt5 是 GPLv3/商业双许可。若对外分发闭源安装包：

- 走 GPL：需要按 GPL 提供完整对应源码；
- 走商业：购买 Riverbank/PyQt 商业授权；
- 走 PySide6：LGPLv3，可闭源动态链接，但需履行 LGPL 义务（允许替换库、声明、提供 relinkable 方式）。

libmpv 也需使用 LGPL 构建并动态链接；两者叠加后，PySide6 + LGPL libmpv 是最干净的商业路径。

---

## 2. 代码影响面

当前代码使用 PyQt5 的部位：`ui/`（主窗口/视频/设置/歌词/迷你/EQ/模型/主题）、`platform/media_keys.py`、`utils` 少量。播放内核是 libmpv，不依赖 Qt Multimedia。

| 差异 | 影响文件 | 处理 |
|---|---|---|
| `from PyQt5...` → `from PySide6...` | 所有 UI/平台文件 | 机械替换 + 导入检查 |
| `pyqtSignal` → `Signal`，`pyqtSlot` → `Slot` | `main_window`、`video_window`、`desktop_lyrics`、`engine` bridge | 别名或替换 |
| `QAction` 从 QtWidgets → QtGui | `main_window`、`video_window` | 改导入 |
| `QShortcut` 从 QtWidgets → QtGui（Qt6） | `main_window`、`video_window` | 改导入 |
| `exec_()` → `exec()` | 所有对话框/应用 | 替换 |
| 枚举作用域（`Qt.AlignCenter` → `Qt.AlignmentFlag...`；`QDialog.Accepted` → `QDialog.DialogCode.Accepted`） | 多处 UI | 逐处修 |
| `QDesktopServices`/`QUrl`/`QSystemTrayIcon` | 基本不变 | 回归 |
| `QMediaPlayer`/`QVideoWidget` | 旧 0.x 代码，不再使用 | 不迁移 |
| 样式表 QSS | 主题文件 | 视觉回归；Qt6 对部分属性更严格 |

**不需要迁移**：libmpv/ctypes、SQLite、mutagen、播放队列、歌词解析、更新逻辑。

---

## 3. 工作量与步骤

### 3.1 推荐步骤

1. **升级 Python**：PySide6 6.x 需要 Python ≥3.9（当前 3.8.9 已 EOL）。先升 3.11/3.12。
2. **建兼容层** `qianyu/qt.py`：
   - 优先 `PySide6`，回退 `PyQt5`；
   - 统一导出 `QtCore/QtGui/QtWidgets` 常用类、`Signal/Slot`、`QAction`、`QShortcut`、`exec_app`。
3. **替换导入**：UI 文件只从 `qianyu.qt` 导入；引擎/领域层不依赖 Qt。
4. **修枚举/`exec_`/`QAction`/`QShortcut`**：按上表逐处。
5. **测试**：18+ 单测、UI 冒烟、video window smoke、打包 `--smoke`。
6. **打包**：PyInstaller PySide6 hook；体积预计 +30–60 MB；验证 `libmpv` 加载、平台插件、主题。
7. **视觉回归**：深/浅主题、DPI、对话框、桌面歌词、迷你窗。

### 3.2 工时估算

| 工作 | 人天 |
|---|---:|
| Python 3.11 升级 + 依赖重装 | 0.5 |
| 兼容层 + 导入替换 | 1 |
| 枚举/`exec_`/QAction/QShortcut 修复 | 1–2 |
| 单测/UI/视频/打包回归 | 2–3 |
| 许可证声明/第三方清单 | 0.5 |
| **合计** | **5–7 人天** |

---

## 4. 风险

| 风险 | 缓解 |
|---|---|
| Qt6 枚举/API 差异导致运行时错误 | 兼容层 + 全量 UI 冒烟 |
| QSS 视觉差异 | 截图回归；必要时微调 |
| PySide6 打包体积/插件缺失 | PyInstaller hook + `--smoke` |
| Python 3.8 → 3.11 依赖兼容 | 锁版本；先跑纯逻辑测试 |
| LGPL 合规 | 动态链接、提供替换方式、第三方许可清单 |
| 迁移期间功能回归 | 分支迁移，保持 PyQt5 可回退 |

---

## 5. 建议

- **1.0 发布前必须完成**；0.9 内部开发可继续用 PyQt5。
- 如果时间紧，购买 PyQt 商业授权也是一条合法路径，但成本与长期维护需评估。
- 迁移完成后，把 `PySide6` 写入 `pyproject` 依赖，移除 PyQt5。
- 在 CI 中同时跑 PySide6 + offscreen 冒烟，避免回退。

---

## 6. 验收清单

- [ ] Python 3.11/3.12
- [ ] PySide6 导入无警告
- [ ] 18+ 单测通过
- [ ] 主界面/歌词/设置/迷你/视频窗口冒烟
- [ ] 深/浅主题截图回归
- [ ] PyInstaller `--smoke` 两平台退出 0
- [ ] LGPL/第三方许可清单
- [ ] 卸载 PyQt5 后应用仍可运行
