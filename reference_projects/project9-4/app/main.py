import asyncio
import base64
import json
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.connection_manager import manager
from app.models import EventType
from app.omni_client import build_omni_client
from app.vad import SimpleEnergyVAD

app = FastAPI()


@app.websocket("/ws/{client_id}")
async def endpoint(websocket: WebSocket, client_id: str):
    """
    实时语音 WebSocket 端点。
    复用 project9 的 ConnectionManager,在其上加 VAD + 音频流水线 + barge-in。
    """
    await manager.connect(client_id, websocket)
    vad = SimpleEnergyVAD()
    audio_buf = bytearray()
    gen_task: Optional[asyncio.Task] = None
    session: dict = {}

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            t = msg.get("type")

            if t == EventType.SESSION_UPDATE:
                # 配置会话(音频格式、VAD、模态等)
                session.update(msg.get("session", {}))
                await manager.send_message(client_id, {
                    "type": EventType.SESSION_UPDATED, "session": session,
                })

            elif t == EventType.INPUT_AUDIO_APPEND:
                pcm = base64.b64decode(msg["audio"])
                audio_buf.extend(pcm)

                # barge-in:AI 正在说话时用户开口 -> 中断当前生成
                if vad.is_speech(pcm) and gen_task and not gen_task.done():
                    gen_task.cancel()
                    await manager.send_message(client_id, {"type": EventType.SPEECH_STARTED})

                # 自动模式(server_vad):VAD 检测到一句话结束 -> 触发生成
                if vad.utterance_end(pcm) and not (gen_task and not gen_task.done()):
                    pending, audio_buf = bytes(audio_buf), bytearray()
                    gen_task = asyncio.create_task(
                        generate_and_stream(client_id, pending, session))

            elif t == EventType.INPUT_AUDIO_COMMIT:
                # 手动模式:客户端显式提交 -> 触发生成(取消正在进行的)
                if gen_task and not gen_task.done():
                    gen_task.cancel()
                pending, audio_buf = bytes(audio_buf), bytearray()
                gen_task = asyncio.create_task(
                    generate_and_stream(client_id, pending, session))

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        if gen_task and not gen_task.done():
            gen_task.cancel()


async def generate_and_stream(client_id: str, audio_pcm: bytes, session: dict):
    """
    后台流式生成 + 推事件 -- project9 的 run_agent_and_stream 的实时语音版。
    把模型流式输出翻译成 response.audio.delta / response.audio_transcript.delta 事件。
    被 barge-in cancel 时推送 response.cancelled。
    """
    client = build_omni_client()
    try:
        await manager.send_message(client_id, {"type": EventType.RESPONSE_CREATE})
        async for chunk in client.stream(audio_pcm, session):
            if chunk.get("text"):
                await manager.send_message(client_id, {
                    "type": EventType.RESPONSE_TRANSCRIPT_DELTA, "delta": chunk["text"],
                })
            if chunk.get("audio"):
                await manager.send_message(client_id, {
                    "type": EventType.RESPONSE_AUDIO_DELTA,
                    "delta": base64.b64encode(chunk["audio"]).decode(),
                })
        await manager.send_message(client_id, {"type": EventType.RESPONSE_DONE})
    except asyncio.CancelledError:
        # barge-in 触发的正常中断
        await manager.send_message(client_id, {"type": EventType.RESPONSE_CANCELLED})
        raise
    except Exception as e:
        await manager.send_message(client_id, {"type": EventType.ERROR, "content": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
