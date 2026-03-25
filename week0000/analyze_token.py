#!/usr/bin/env python3
"""
分析 VTJ token 结构，尝试找到生成规律
"""
import base64
import json
import urllib.parse
from datetime import datetime

# 示例 token
sample_token = "VTJGc2RHVmtYMTlQTkhSOHpKTzdXTkgxc0pTakVZbmcxUFRWSjYzZC9DUXBFSURxZ0tncXNKM3ppcjhaVjB2NTZBT1dicVNRMkRwcXhKcUhvQ2tBZUE9PSMxNzc0MDc0OTY2NDEx"

def analyze_token(token):
    print(f"原始 token: {token}\n")
    print(f"Token 长度: {len(token)}\n")

    # 检查是否有分隔符
    if '#' in token:
        parts = token.split('#')
        print(f"发现分隔符 '#'，分割后有 {len(parts)} 部分:")
        for i, part in enumerate(parts):
            print(f"  部分 {i+1}: {part}")

        # 最后一部分可能是时间戳
        if parts[-1].isdigit():
            timestamp_ms = int(parts[-1])
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            print(f"\n  → 最后部分看起来是时间戳: {timestamp_ms}")
            print(f"  → 转换为日期: {dt}")
            print(f"  → 过期时间可能在: {datetime.fromtimestamp((timestamp_ms + 3600000) / 1000)} (假设1小时有效)")

        # 尝试解码第一部分
        print(f"\n尝试 Base64 解码第一部分:")
        try:
            decoded = base64.b64decode(parts[0])
            print(f"  ✓ 解码成功 (原始字节): {decoded}")
            try:
                decoded_str = decoded.decode('utf-8')
                print(f"  ✓ UTF-8 解码: {decoded_str}")
            except:
                print(f"  ✗ 无法 UTF-8 解码，可能是二进制数据")
                # 尝试看看是否有可打印字符
                printable = ''.join(chr(b) if 32 <= b < 127 else f'\\x{b:02x}' for b in decoded)
                print(f"  → 可打印部分: {printable[:200]}")
        except Exception as e:
            print(f"  ✗ Base64 解码失败: {e}")

    # 尝试整体 Base64 解码
    print(f"\n尝试整体 Base64 解码:")
    try:
        decoded = base64.b64decode(token)
        print(f"  ✓ 解码成功: {decoded}")
    except Exception as e:
        print(f"  ✗ 解码失败: {e}")

    # 尝试 URL 解码
    print(f"\n尝试 URL 解码:")
    try:
        decoded = urllib.parse.unquote(token)
        if decoded != token:
            print(f"  ✓ 发现 URL 编码: {decoded}")
        else:
            print(f"  → 没有 URL 编码")
    except Exception as e:
        print(f"  ✗ 解码失败: {e}")

if __name__ == '__main__':
    print("=" * 80)
    print("VTJ Token 结构分析")
    print("=" * 80 + "\n")

    analyze_token(sample_token)

    print("\n" + "=" * 80)
    print("分析结论")
    print("=" * 80)
    print("""
可能的 token 结构：
1. 前半部分：Base64 编码的加密数据（包含用户ID、课程ID等信息）
2. # 分隔符
3. 后半部分：时间戳（毫秒级，用于过期验证）

要自动生成 token，需要：
1. 找到小程序中生成 token 的接口（可能是 /api/auth/xxx 或 /api/lesson 等）
2. 或者抓包时同时保存 cookie/session，用登录态换取 token
3. 或者使用自动化工具持续监听并更新 token
    """)
