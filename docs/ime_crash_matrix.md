# IME 冷启动崩溃矩阵

日期：2026-10-18  
环境：Windows 10、Python 3.11 + PySide6 6.8.3、源码 `run_dev.py --smoke`

## 结果

| 条件 | 次数 | 0xC0000005 | 崩溃率 | 平均耗时 |
|---|---:|---:|---:|---:|
| 默认 Windows IME | 50 | 1 | 2% | 3616 ms |
| `QT_IM_MODULE=qt` | 50 | 0 | 0% | 3061 ms |
| `QT_IM_MODULE=windows` | 50 | 2 | 4% | 2682 ms |
| 默认 IME + 禁用托盘 | 50 | 3 | 6% | 2677 ms |
| offscreen（无 Windows IME） | 30 | 0 | 0% | 1535 ms |

默认/Windows/无托盘合计：

```
6 / 150 = 4%
```

## 崩溃特征

- 正常启动 1.5–3 s；
- 崩溃运行通常拖到 **6.5–7.5 s**，其中一次 13.5 s；
- 崩溃模块：`python311.dll`；
- 事件日志历史记录出现过 `SogouPY.ime`；
- 托盘不是原因：禁用托盘后仍有 3/50；
- offscreen 不加载 Windows IME，0/30。

## 关键发现：旧 `--smoke` 是硬退出测试

旧 smoke 路径：

```
show()
processEvents()
os._exit(0)
```

它不进入真正的事件循环，Windows IME 初始化与进程硬退出竞争，产生偶发
`0xC0000005`。

验证：

| 运行方式 | 次数 | 崩溃 |
|---|---:|---:|
| 真实事件循环 2.5 秒后正常退出 | 100 | **0** |
| 新 smoke：事件循环 2.5 秒后退出 | 50 | **0** |
| 旧 smoke：show 后立即 `os._exit` | 150 | **6–7%** |
| 进程内 `ImmDisableIME(0)` | 150 | **0** |

`ImmDisableIME` 进一步确认崩溃与 Windows IME 初始化有关；但正常事件循环下
100 次没有复现。

**当前 `--smoke` 已改为先跑 2.5 秒事件循环，再退出。**  
这不是生产崩溃修复，而是修掉了测试工具自身的竞态。

## 组件二分（默认搜狗 IME）

| 最小组件 | 次数 | 崩溃 |
|---|---:|---:|
| QLineEdit | 50 | 0 |
| + QTableView | 50 | 0 |
| + QListWidget | 50 | 0 |
| + QSystemTrayIcon/QMenu | 50 | 0 |
| + 深色 QSS | 50 | 0 |
| 以上全部 | 50 | 0 |
| MpvEngine（无窗口） | 50 | 0 |
| MpvEngine + QLineEdit 窗口 | 50 | 0 |

**简单 Qt 组件 0/300，mpv 0/100。**  
说明崩溃需要完整 MainWindow 的某些组合，而不是单独 QLineEdit、表格、托盘或 mpv。

## 结论

**强相关：Windows 原生 IME（当前为搜狗输入法）注入。**  
但最小组件与 mpv 组合都没有复现，暂无法直接作为 Qt/Sogou 的最小 bug 报告。

## 微软拼音矩阵

沙箱无法修改输入法（`Set-WinDefaultInputMethodOverride` 返回成功但注册表仍为搜狗；直接写 HKCU 被拒绝）。

准备脚本：

```powershell
# 先 Win+Space 切到微软拼音
python spike\ime_matrix_ms.py
```

脚本会检测当前 IME，若不是微软拼音则退出，不会误测。

## 下一步

1. 同一矩阵换 **微软拼音** 作为默认 IME，验证是否仍崩；
2. 在独立 venv 试 PySide6/Qt 更新版本（6.8.4/6.9），不动发布环境；
3. 若确认是搜狗：提交最小复现给 Qt/Sogou，并在 Release 标注已知问题；
4. 不把 Qt 输入模块切换作为默认修复；
5. 100 次冷启动 0 崩溃前不发布 1.0。
