# 发布完整性与可审计性

## Release 资产

每个 QianYu Release 包含：

| 资产 | 用途 |
|---|---|
| `QianYu.exe` | 主程序 |
| `QianYu-0.9.0-setup.exe` | Inno 安装包 |
| `QianYu-0.9.0-portable.zip` | 便携版 |
| `SHA256SUMS.txt` | 全部资产校验和 |
| `sbom.json` | CycloneDX 1.5 软件物料清单 |
| `THIRD_PARTY_LICENSES.md` | 第三方组件/许可证清单 |
| `libmpv-2.dll` | 固定版本 libmpv |

## 验证步骤

```powershell
python tools\verify_release.py dist
```

期望：

```
OK QianYu.exe
OK QianYu-0.9.0-setup.exe
OK sbom.json
OK THIRD_PARTY_LICENSES.md
verified 4/4 assets
```

## SBOM

生成：

```powershell
python tools\release_metadata.py --output dist\release-meta
```

覆盖：

- PySide6；
- python-mpv；
- mutagen；
- Pillow；
- pypinyin；
- imageio-ffmpeg；
- libmpv；
- FFmpeg。

SBOM 和许可证清单由发布 workflow 自动生成并上传。

## 未签名说明

QianYu 不使用 SignPath，当前构建未做 Authenticode 签名。  
完整性和来源依靠：

- GitHub Release；
- 源 tag；
- SHA-256；
- SBOM/许可证清单；
- 可选 Ed25519 更新 manifest。

详见 [unsigned_distribution.md](unsigned_distribution.md) 和 [security.md](security.md)。
