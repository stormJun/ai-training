#!/usr/bin/env python3
"""
尝试解密 VTJ token (如果知道密钥)
"""
import sys
import base64
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
import hashlib

def decrypt_token(token, password):
    """
    解密 VTJ token
    参数:
        token: VTJ... 格式的 token
        password: AES 密钥（从小程序代码中找到）
    """
    try:
        # 第一层 Base64 解码
        layer1 = base64.b64decode(token)

        # 分离加密部分和时间戳
        parts = layer1.decode('utf-8').split('#')
        encrypted_b64 = parts[0]
        timestamp = parts[1] if len(parts) > 1 else None

        print(f"时间戳: {timestamp}")

        # 第二层 Base64 解码（加密数据）
        encrypted = base64.b64decode(encrypted_b64)

        # 验证是否是 OpenSSL 格式
        if not encrypted.startswith(b'Salted__'):
            raise ValueError("不是有效的 OpenSSL/CryptoJS 加密格式")

        # 提取盐值和密文
        salt = encrypted[8:16]
        ciphertext = encrypted[16:]

        print(f"盐值 (hex): {salt.hex()}")

        # 使用 PBKDF2 推导密钥和 IV（OpenSSL 默认方法）
        # 密钥长度 32 字节 (AES-256)，IV 长度 16 字节
        key_iv = PBKDF2(
            password.encode('utf-8') if isinstance(password, str) else password,
            salt,
            dkLen=48,  # 32 (key) + 16 (IV)
            count=1,  # OpenSSL 默认迭代次数
            prf=lambda p, s: hashlib.md5(p + s).digest()
        )

        key = key_iv[:32]
        iv = key_iv[32:48]

        print(f"推导的密钥 (hex): {key.hex()}")
        print(f"推导的 IV (hex): {iv.hex()}")

        # AES-256-CBC 解密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = cipher.decrypt(ciphertext)

        # 去除 PKCS7 padding
        padding_len = plaintext[-1]
        if padding_len > 16 or padding_len == 0:
            raise ValueError("Padding 无效，密钥可能不正确")

        plaintext = plaintext[:-padding_len]

        return plaintext, timestamp

    except Exception as e:
        print(f"❌ 解密失败: {e}")
        return None, None


def try_common_keys(token):
    """尝试常见的密钥"""
    common_keys = [
        # 添加从小程序中找到的可疑字符串
        "ixunke",
        "ixunke.cn",
        "appni3brwoydrxr",
        "secret",
        "secret_key",
        "aes_key",
        "wx613cd6930dab2d0a",  # 小程序 AppID
    ]

    print("=" * 80)
    print("尝试常见密钥...")
    print("=" * 80)

    for key in common_keys:
        print(f"\n尝试密钥: '{key}'")
        result, timestamp = decrypt_token(token, key)
        if result:
            print(f"✓ 解密成功!")
            print(f"明文 (UTF-8): {result.decode('utf-8', errors='ignore')}")
            print(f"明文 (hex): {result.hex()}")
            return result

    return None


if __name__ == '__main__':
    sample_token = "VTJGc2RHVmtYMTlQTkhSOHpKTzdXTkgxc0pTakVZbmcxUFRWSjYzZC9DUXBFSURxZ0tncXNKM3ppcjhaVjB2NTZBT1dicVNRMkRwcXhKcUhvQ2tBZUE9PSMxNzc0MDc0OTY2NDEx"

    if len(sys.argv) > 1:
        # 使用命令行提供的密钥
        password = sys.argv[1]
        print(f"使用提供的密钥: '{password}'")
        result, timestamp = decrypt_token(sample_token, password)
        if result:
            print(f"\n✓ 解密成功!")
            print(f"明文 (UTF-8): {result.decode('utf-8', errors='ignore')}")
            print(f"明文 (hex): {result.hex()}")
        else:
            print("\n❌ 解密失败，密钥不正确")
    else:
        # 尝试常见密钥
        print("用法:")
        print(f"  python {sys.argv[0]} <密钥>")
        print(f"\n或者让脚本尝试常见密钥:\n")
        try_common_keys(sample_token)
