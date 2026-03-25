#!/usr/bin/env python3
"""
VTJ Token 自动获取方案
基于 mitmproxy 的自动拦截脚本
"""
from mitmproxy import http
from mitmproxy import ctx
import json
import re
from datetime import datetime
from pathlib import Path

class TokenInterceptor:
    """拦截并保存 VTJ token"""

    def __init__(self):
        self.token_file = Path(__file__).parent / '.vtj_token_cache.json'
        self.api_patterns = [
            r'/api/lesson',
            r'/api/v1/room/stream_info',
            r'/api/auth/',
            r'/api/user/',
        ]

    def request(self, flow: http.HTTPFlow) -> None:
        """拦截请求，提取 token"""
        # 检查是否匹配目标 API
        if not any(re.search(pattern, flow.request.pretty_url) for pattern in self.api_patterns):
            return

        # 提取 URL 参数中的 token
        url = flow.request.pretty_url
        token_match = re.search(r'[?&]token=([^&]+)', url)

        if token_match:
            token = token_match.group(1)
            if token.startswith('VTJ'):
                self._save_token(token, url)
                ctx.log.info(f"✓ 捕获到 VTJ token: {token[:20]}...")

    def _save_token(self, token: str, source_url: str):
        """保存 token 到缓存文件"""
        data = {
            'token': token,
            'captured_at': datetime.now().isoformat(),
            'timestamp': datetime.now().timestamp(),
            'source_url': source_url
        }

        # 写入文件
        self.token_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        ctx.log.info(f"✓ Token 已保存到: {self.token_file}")

        # 同时保存到历史记录
        history_file = self.token_file.parent / '.vtj_token_history.jsonl'
        with history_file.open('a') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')


addons = [TokenInterceptor()]
