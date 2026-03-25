#!/usr/bin/env python3
"""
Token 管理器 - 读取/保存/验证 VTJ token
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import base64

class TokenManager:
    def __init__(self, cache_file='.vtj_token_cache.json'):
        self.cache_file = Path(__file__).parent / cache_file
        self.history_file = Path(__file__).parent / '.vtj_token_history.jsonl'

    def get_token(self):
        """获取当前有效的 token"""
        if not self.cache_file.exists():
            print("❌ 没有缓存的 token，请先设置", file=sys.stderr)
            print("💡 使用方法：python token_manager.py set 'VTJ...'", file=sys.stderr)
            return None

        data = json.loads(self.cache_file.read_text())
        token = data.get('token')

        # 检查 token 是否看起来有效
        if not token or not token.startswith('VTJ'):
            print("⚠️  缓存的 token 格式不正确", file=sys.stderr)
            return None

        # 解析时间戳（从 token 中提取）
        try:
            timestamp = self._extract_timestamp(token)
            if timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000)
                now = datetime.now()
                age_minutes = (now.timestamp() * 1000 - timestamp) / 60000

                if age_minutes > 20:
                    print(f"⚠️  Token 内嵌时间戳为 {dt}，已过去 {age_minutes:.0f} 分钟", file=sys.stderr)
                    print("💡 该时间戳不等于严格过期时间；若请求失败，请更新 token", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  无法解析 token 时间戳: {e}", file=sys.stderr)

        return token

    def set_token(self, token, source='manual'):
        """设置新的 token"""
        if not token.startswith('VTJ'):
            print("❌ Token 必须以 'VTJ' 开头", file=sys.stderr)
            return False

        data = {
            'token': token,
            'captured_at': datetime.now().isoformat(),
            'timestamp': datetime.now().timestamp(),
            'source': source
        }

        # 保存到缓存
        self.cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        # 保存到历史
        with self.history_file.open('a') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

        # 打印信息
        timestamp = self._extract_timestamp(token)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            print(f"✓ Token 已保存（内嵌时间戳: {dt}）")
        else:
            print(f"✓ Token 已保存")

        return True

    def _extract_timestamp(self, token):
        """从 token 中提取时间戳"""
        try:
            # 解码第一层 Base64
            layer1 = base64.b64decode(token)
            # 提取 # 后的时间戳
            parts = layer1.decode('utf-8').split('#')
            if len(parts) > 1 and parts[1].isdigit():
                return int(parts[1])
        except:
            pass
        return None

    def show_info(self):
        """显示当前 token 信息"""
        if not self.cache_file.exists():
            print("❌ 没有缓存的 token")
            return

        data = json.loads(self.cache_file.read_text())
        token = data.get('token', '')

        print("=" * 60)
        print("当前 Token 信息")
        print("=" * 60)
        print(f"Token 前缀: {token[:30]}...")
        print(f"保存时间: {data.get('captured_at', 'Unknown')}")
        print(f"来源: {data.get('source', 'Unknown')}")

        timestamp = self._extract_timestamp(token)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            age_minutes = (datetime.now().timestamp() * 1000 - timestamp) / 60000
            print(f"Token 内嵌时间戳: {dt}")
            print(f"距今: {age_minutes:.0f} 分钟")
            if age_minutes > 20:
                print("⚠️  时间较久，建议实际请求验证或更新 token")
            else:
                print("✓ 时间较新，但是否有效仍需实际请求验证")

        print("=" * 60)


def main():
    manager = TokenManager()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python token_manager.py get              # 获取当前 token")
        print("  python token_manager.py set 'VTJ...'     # 设置新 token")
        print("  python token_manager.py info             # 查看 token 信息")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'get':
        token = manager.get_token()
        if token:
            print(token)
    elif command == 'set':
        if len(sys.argv) < 3:
            print("❌ 请提供 token", file=sys.stderr)
            sys.exit(1)
        token = sys.argv[2]
        manager.set_token(token)
    elif command == 'info':
        manager.show_info()
    else:
        print(f"❌ 未知命令: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
