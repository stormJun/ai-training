"""
测试客户端:连 WebSocket -> 发假音频 -> commit -> 收事件。
验证 WS 层 + 事件协议 + 后台流式推送的完整链路(fake 后端,无需 GPU)。

测试 barge-in:在收到 response.audio_transcript.delta 期间,再用本脚本或另一客户端
向同一 client_id 发高能量 input_audio_buffer.append,观察 response.cancelled。
"""
import asyncio
import base64
import json
import math
import struct

import websockets

CLIENT_ID = "user_test_001"
WS_URL = f"ws://localhost:8000/ws/{CLIENT_ID}"


def fake_speech_audio(n: int = 1600) -> bytes:
    """模拟"说话"音频:高能量正弦波(触发 VAD is_speech=True)。"""
    return b"".join(
        struct.pack("<h", int(20000 * math.sin(2 * math.pi * 440 * i / 16000)))
        for i in range(n)
    )


async def main():
    async with websockets.connect(WS_URL) as ws:
        print(f"已连接 {CLIENT_ID}")

        # 1. 配置会话
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "server_vad"},
            },
        }))

        # 2. 推几帧"说话"音频
        for _ in range(3):
            await ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(fake_speech_audio()).decode(),
            }))
            await asyncio.sleep(0.1)

        # 3. 手动提交触发生成
        await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        print("已 commit,监听回复...")

        # 4. 收事件
        while True:
            raw = await ws.recv()
            ev = json.loads(raw)
            t = ev.get("type")

            if t == "response.audio_transcript.delta":
                print(ev["delta"], end="", flush=True)
            elif t == "response.audio.delta":
                print(f"\n  [audio {len(ev['delta'])} chars]", end="")
            elif t == "response.done":
                print("\n\n[完成]")
                break
            elif t == "response.cancelled":
                print("\n[回复被取消(barge-in?)]")
                break
            elif t == "input_audio_buffer.speech_started":
                print("\n[barge-in: 检测到用户开口]")
            elif t == "error":
                print(f"\n[error] {ev.get('content')}")
                break
            else:
                print(f"\n[{t}]", ev)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已停止。")
