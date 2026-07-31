from typing import Dict

from fastapi import WebSocket


class ConnectionManager:
    """
    WebSocket 连接管理器(client_id -> WebSocket)。
    复用自 project9:管理活跃连接、按 client_id 单播、广播。
    生产多实例需升级为 Redis pub/sub 跨进程路由(见 project9-2 §7.2)。
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """接受并注册新连接。"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """移除断开的连接。"""
        self.active_connections.pop(client_id, None)

    async def send_message(self, client_id: str, message: dict):
        """向指定客户端单播 JSON 消息。"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict):
        """向所有客户端广播(本骨架未用到,保留)。"""
        for ws in self.active_connections.values():
            await ws.send_json(message)


# 全局单例
manager = ConnectionManager()
