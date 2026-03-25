#!/usr/bin/env python3
"""
分析多个 token 样本，尝试找到生成规律
"""
import base64
from datetime import datetime

# 从你的抓包中收集的 token 样本
samples = [
    ("VTJGc2RHVmtYMTh6UW5SRTRSaFI0a1NMWnVBVVNBUjRHNlRYczN2UnUybXFBampYYVB3dG9EQTNiS0ZXeG1hRHUxWjhNWjZBaW1FYVp1ODNsekRYRlE9PSMxNzc0MDc2NjQxNTkw", "record_online_time"),
    ("VTJGc2RHVmtYMThTZ3FPeEtnSytHMGVtVFRkdUg1M3RVMitnQ00wSkh4aTRZOU1VTnpXZms0cDdFeW8xZkhrUUQyckZIaWdaNjFrMDNkSy9NUHhxRXc9PSMxNzc0MDc2NjQzMDY0", "related_recommend"),
    ("VTJGc2RHVmtYMS92TldMTHJYQXg3RGhLS2ZxQjJzdUNLSWdJcDBGMWplZklwUFVGSU9jdmEyQWdRSWJjSVpmc1BpV1doajNvUCsrS0k0WFQxRHBEdWc9PSMxNzc0MDc2NjQxNjEz", "course?id=41"),
    ("VTJGc2RHVmtYMS8rVlVzdXJNRmRvaU9yQlR6aDFHQUU3eld3MzhCaGk2OTlCN2VSWVR2M2RLdUwyWnF6RjVmWFY1UThsMldTWG54Q08vNHRBbFNnTlE9PSMxNzc0MDc2NjQyMDkx", "member"),
    ("VTJGc2RHVmtYMStHWE5RckNFTzB0TmliNVdkK3p4M2JyY3dJcXdXaGJhT1lhbHdESzVUcDZidndVbW5CQlJNVDZsWmFabzNtZFlCOC9HTVVMYlBPRHc9PSMxNzc0MDc2NjQzMDMw", "lesson list"),
]

print("=" * 80)
print("Token 样本分析")
print("=" * 80)

for i, (token, api) in enumerate(samples, 1):
    print(f"\n样本 {i}: {api}")
    print(f"Token: {token[:40]}...")

    # 解码
    layer1 = base64.b64decode(token).decode('utf-8')
    parts = layer1.split('#')
    encrypted = parts[0]
    timestamp = int(parts[1])

    dt = datetime.fromtimestamp(timestamp / 1000)

    print(f"时间戳: {timestamp} → {dt}")
    print(f"加密部分长度: {len(encrypted)}")

    # 解密加密部分
    encrypted_bytes = base64.b64decode(encrypted)
    salt = encrypted_bytes[8:16]
    print(f"盐值 (hex): {salt.hex()}")

print("\n" + "=" * 80)
print("观察结论")
print("=" * 80)
print("""
1. 每个请求的时间戳不同（相差 1-2 秒）
2. 每个请求的盐值不同
3. 加密部分长度相近（都在 88 字符左右）

这说明：
→ Token 是在前端实时生成的
→ 每次都使用随机盐值
→ 密钥一定在小程序代码中

下一步：
必须获取小程序源代码才能找到密钥
""")
