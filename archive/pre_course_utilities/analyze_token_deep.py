#!/usr/bin/env python3
"""
深度分析 VTJ token - 发现了 AES 加密！
"""
import base64

token = "VTJGc2RHVmtYMTlQTkhSOHpKTzdXTkgxc0pTakVZbmcxUFRWSjYzZC9DUXBFSURxZ0tncXNKM3ppcjhaVjB2NTZBT1dicVNRMkRwcXhKcUhvQ2tBZUE9PSMxNzc0MDc0OTY2NDEx"

# 第一层 Base64 解码
layer1 = base64.b64decode(token)
print("=" * 80)
print("第一层解码（Base64）:")
print("=" * 80)
print(f"原始: {token[:50]}...")
print(f"解码: {layer1}")
print()

# 分离加密部分和时间戳
parts = layer1.decode('utf-8').split('#')
encrypted_part = parts[0]
timestamp = parts[1] if len(parts) > 1 else None

print("=" * 80)
print("结构分析:")
print("=" * 80)
print(f"加密部分: {encrypted_part}")
print(f"时间戳: {timestamp}")
print()

# 第二层 Base64 解码（加密部分）
layer2 = base64.b64decode(encrypted_part)
print("=" * 80)
print("第二层解码（加密数据）:")
print("=" * 80)
print(f"原始: {encrypted_part}")
print(f"解码 (hex): {layer2.hex()}")
print(f"解码 (前16字节): {layer2[:16]}")
print(f"解码 (尝试UTF-8): {layer2[:16]}")
print()

# 检查是否是 "Salted__" 开头 (OpenSSL AES 加密标准格式)
if layer2.startswith(b'Salted__'):
    print("=" * 80)
    print("🎯 重大发现！")
    print("=" * 80)
    print("✓ 这是 OpenSSL/CryptoJS AES 加密格式！")
    print("✓ 'Salted__' 是标准的 AES-CBC 加密前缀")
    print()
    print("加密结构:")
    print("  - 前8字节: 'Salted__' (魔术字符串)")
    print(f"  - 8-16字节: {layer2[8:16].hex()} (盐值 Salt)")
    print(f"  - 16字节后: {layer2[16:].hex()[:40]}... (加密的实际数据)")
    print()
    print("=" * 80)
    print("解密需要的信息:")
    print("=" * 80)
    print("❌ 需要密钥（password/secret key）- 存储在服务端或小程序代码中")
    print("❌ 加密算法：很可能是 AES-256-CBC")
    print("✓ 已知盐值：", layer2[8:16].hex())
    print("✓ 已知时间戳：", timestamp)
    print()

print("=" * 80)
print("Token 生成流程（推测）:")
print("=" * 80)
print("""
服务端流程：
1. 准备明文数据（可能包含：userId, courseId, lessonId, expireTime 等）
2. 使用 AES-256-CBC 加密明文（密钥在服务端配置）
3. 加密结果格式：Salted__ + 盐值 + 密文
4. Base64 编码加密结果
5. 拼接时间戳：base64_encrypted + "#" + timestamp
6. 再次 Base64 编码整体
7. 返回给客户端作为 token

客户端（小程序）流程：
1. 调用某个 API 获取 token（可能是 /api/lesson 或专门的认证接口）
2. 收到 VTJ... token
3. 在后续请求中作为参数传递

验证流程：
1. 服务端收到 token
2. Base64 解码两层
3. 检查时间戳是否过期
4. 使用密钥解密 AES 部分
5. 验证解密后的数据（用户权限、课程权限等）
""")

print("=" * 80)
print("🔍 寻找密钥的方法:")
print("=" * 80)
print("""
方法 1：反编译小程序包（推荐尝试）
  - 如果密钥在前端，可以从小程序代码中找到
  - 工具：wxappUnpacker, 微信开发者工具
  - 位置：app.js, config.js, utils/crypto.js 等文件

方法 2：抓包找前置接口（最实用）
  - Token 不是凭空出现的，一定有个接口返回它
  - 查找规律：
    * 打开课程页面时的请求
    * 点击播放前的请求
    * 可能的接口名：/api/auth/token, /api/user/access_token, /api/lesson 等
  - 只要找到这个接口，就能自动获取 token

方法 3：使用登录态换取（如果有登录接口）
  - 已知你们有 minicheckaccount 登录 token
  - 可能可以用登录 token 换取 VTJ token
  - 查找是否有 /api/auth/exchange 之类的接口

方法 4：自动化持续抓包（最可靠）
  - 使用 mitmproxy 监听微信小程序流量
  - 自动提取并保存最新的 VTJ token
  - 脚本使用时自动读取最新 token
""")
