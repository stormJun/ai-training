import asyncio
import base64
import math
import os
import struct
from typing import AsyncIterator


class OmniClient:
    """模型客户端接口:音频进,流式出文本 + 音频。"""

    async def stream(self, audio_pcm: bytes, session: dict) -> AsyncIterator[dict]:
        """yield {"text": ...} 和/或 {"audio": bytes}。"""
        raise NotImplementedError


class FakeOmniClient(OmniClient):
    """
    假后端(无需 GPU/模型)。
    生成假的文本流 + 正弦波音频流,用于验证 WS 层 / 事件协议 / VAD / barge-in 的完整链路。
    """

    async def stream(self, audio_pcm: bytes, session: dict) -> AsyncIterator[dict]:
        text = "这是自部署实时语音 agent 的假回复。接入 vLLM + Qwen3-Omni 后,这里会替换为模型的真实流式输出。"
        # 逐段吐文本(模拟 token 流)
        for i in range(0, len(text), 4):
            yield {"text": text[i : i + 4]}
            await asyncio.sleep(0.03)
        # 吐几段假音频(440Hz 正弦波 PCM16,16kHz 单声道)
        audio = self._fake_audio(800)  # ~50ms
        for _ in range(5):
            yield {"audio": audio}
            await asyncio.sleep(0.03)

    @staticmethod
    def _fake_audio(n_samples: int) -> bytes:
        return b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 16000)))
            for i in range(n_samples)
        )


class VLLMOmniClient(OmniClient):
    """
    真后端:调 vLLM 起的 Qwen3-Omni 流式服务(OpenAI 兼容 / SSE)。

    前置:
        vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --quantization awq --port 8001

    注意:本类为示意结构。不同 vLLM 版本对「音频输入」与「流式音频输出」的 API 略有差异,
    需对照 vLLM 文档调整请求体与响应解析(尤其是音频输出 delta 的字段)。
    """

    def __init__(self, base_url: str = "http://localhost:8001",
                 model: str = "Qwen/Qwen3-Omni-30B-A3B-Instruct"):
        self.base_url = base_url
        self.model = model

    async def stream(self, audio_pcm: bytes, session: dict) -> AsyncIterator[dict]:
        import json
        import httpx

        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64.b64encode(audio_pcm).decode(),
                                "format": "pcm16",
                            },
                        }
                    ],
                }
            ],
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/v1/chat/completions", json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0]["delta"]
                    if delta.get("content"):
                        yield {"text": delta["content"]}
                    # TODO: 按 vLLM/Qwen3-Omni 的流式音频格式解析音频 delta 并 yield {"audio": ...}


def build_omni_client() -> OmniClient:
    """按环境变量 OMNI_BACKEND 选择后端,默认 fake(无需 GPU)。"""
    if os.environ.get("OMNI_BACKEND", "fake").lower() == "vllm":
        return VLLMOmniClient(
            base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8001"),
            model=os.environ.get("VLLM_MODEL", "Qwen/Qwen3-Omni-30B-A3B-Instruct"),
        )
    return FakeOmniClient()
