# 更新签名与安装包

## 1. 当前实现

- `update.py` 支持 Ed25519 清单签名：
  - 签名对象：`canonical_manifest()`，即去掉 `signature` 字段后，按 key 排序、无空格的 UTF-8 JSON；
  - 公钥：Base64 raw Ed25519 public key，配置在 设置 → 更新公钥；
  - 未配置公钥时，应用会警告“只做 SHA-256 校验”，需用户确认；
  - 下载后仍校验 `sha256`。
- `main_window.py` 下载完成后可退出并运行 `.exe`/`.ps1` 安装包。
- **仍未做**：安装包自身的 Authenticode 签名、自动静默替换、回滚。

## 2. 生成密钥（离线）

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64

key = Ed25519PrivateKey.generate()
private = key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)
public = key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
print("PRIVATE_B64", base64.b64encode(private).decode())
print("PUBLIC_B64", base64.b64encode(public).decode())
```

私钥只放在离线签名机；应用只配置 `PUBLIC_B64`。

## 3. 签名 manifest

```python
import base64, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from qianyu.update import canonical_manifest

private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(PRIVATE_B64))
document = {
    "version": "0.9.1",
    "url": "https://example.com/qianyu/QianYu-0.9.1-setup.exe",
    "sha256": "<installer sha256>",
    "notes": "修复...",
}
payload = json.dumps(document, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
signature = private.sign(canonical_manifest(payload))
document["signature"] = base64.b64encode(signature).decode("ascii")
print(json.dumps(document, ensure_ascii=False, indent=2))
```

把输出保存为 `manifest.json`，上传 HTTPS。

## 4. 安装包签名（脚本已就绪，证书受限）

`packaging/sign.ps1` 支持：

```powershell
# 生产：PFX 代码签名证书
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -Pfx C:\secure\qianyu.pfx -Password <password>

# 开发：自签名（仅本机验证）
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -CreateSelfSigned -NoTimestamp
```

本机自签名测试被证书存储权限阻塞（`New-SelfSignedCertificate: Access denied`）；脚本与 PFX 路径已就绪，需要可用证书/权限。

生产也可用 `signtool.exe`：

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f cert.pfx /p <password> dist\installer\QianYu-0.9.0-setup.exe
```

签名后，更新器还应校验安装包 Authenticode，而不仅是 SHA-256。

## 5. 自动替换（仍未做）

安全流程应是：

1. 下载到临时目录；
2. 校验签名 + SHA-256；
3. 关闭主程序；
4. 启动安装器静默安装；
5. 失败回滚/保留旧版本。

当前只做到“退出并运行安装包”，由用户完成安装。
