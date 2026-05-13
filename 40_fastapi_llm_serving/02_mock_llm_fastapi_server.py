"""本地可运行的 mock LLM FastAPI 服务。

这个示例不依赖 Ollama 或外部模型服务，但接口形状已经接近一个真实的
AI 对话服务，适合放在 hello world 和真实代理服务之间作为过渡。
"""

from __future__ import annotations

import json
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


app = FastAPI(title="Mock LLM FastAPI Demo", version="0.1.0")

SUPPORTED_MODELS = ["mock-qwen", "mock-deepseek", "mock-assistant"]


class ChatRequest(BaseModel):
    """聊天请求模型。"""

    message: str = Field(min_length=1, description="用户输入内容")
    model: str = Field(default="mock-qwen", description="模拟模型名称")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=256, ge=1, le=4096, description="最大输出长度")
    style: Literal["concise", "teacher", "friendly"] = Field(
        default="concise", description="回复风格"
    )


class ChatResponse(BaseModel):
    """非流式聊天响应模型。"""

    request_id: str
    model: str
    reply: str
    usage: dict[str, int]


# 在动态加载模块（例如测试用 importlib）时，Pydantic 可能需要显式重建模型。
ChatRequest.model_rebuild()
ChatResponse.model_rebuild()


def ensure_supported_model(model: str) -> None:
    if model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model: {model}. Available: {SUPPORTED_MODELS}",
        )


def build_mock_reply(request: ChatRequest) -> str:
    """根据请求构造一段模拟回复。"""
    prefix_by_style = {
        "concise": "简要回答",
        "teacher": "老师模式讲解",
        "friendly": "友好回答",
    }
    prefix = prefix_by_style[request.style]
    return (
        f"{prefix}：你刚才问的是“{request.message}”。"
        f" 当前使用模型 {request.model}，temperature={request.temperature}。"
        " 这是一段本地 mock 回复，用来演示 FastAPI 中 AI 服务接口的基本形状。"
    )


def estimate_usage(prompt: str, completion: str) -> dict[str, int]:
    """用非常粗糙的字符长度近似 token 使用量，方便教学。"""
    return {
        "prompt_tokens": max(1, len(prompt) // 2),
        "completion_tokens": max(1, len(completion) // 2),
        "total_tokens": max(1, len(prompt) // 2) + max(1, len(completion) // 2),
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to the mock LLM FastAPI demo",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "models": "/models",
            "chat": "/chat",
            "chat_stream": "/chat/stream",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/models")
async def models():
    return {"models": SUPPORTED_MODELS}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    ensure_supported_model(request.model)
    reply = build_mock_reply(request)
    usage = estimate_usage(request.message, reply)
    return ChatResponse(
        request_id=str(uuid.uuid4()),
        model=request.model,
        reply=reply,
        usage=usage,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    ensure_supported_model(request.model)
    reply = build_mock_reply(request)

    async def generate():
        # 用词级切分来模拟模型逐段输出。
        for word in reply.split():
            chunk = {"delta": word + " "}
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(generate(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
