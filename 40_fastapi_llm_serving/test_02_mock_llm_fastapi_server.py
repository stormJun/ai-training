from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import httpx


MODULE_PATH = Path(__file__).with_name("02_mock_llm_fastapi_server.py")


def load_app():
    spec = importlib.util.spec_from_file_location("mock_llm_fastapi_server", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def run_request(method: str, path: str, **kwargs):
    async def _run():
        transport = httpx.ASGITransport(app=load_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(_run())


def test_health_endpoint():
    response = run_request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_endpoint():
    response = run_request("GET", "/models")

    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    assert "mock-qwen" in body["models"]


def test_chat_endpoint():
    response = run_request(
        "POST",
        "/chat",
        json={"message": "你好", "temperature": 0.2, "max_tokens": 128},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "mock-qwen"
    assert body["reply"]
    assert body["usage"]["prompt_tokens"] > 0
    assert body["usage"]["completion_tokens"] > 0


def test_chat_stream_endpoint():
    response = run_request(
        "POST",
        "/chat/stream",
        json={"message": "请解释一下 FastAPI", "temperature": 0.1, "max_tokens": 64},
    )
    chunks = [line for line in response.text.splitlines() if line]

    assert response.status_code == 200
    assert any("data: " in chunk for chunk in chunks)
    assert any('"done": true' in chunk.lower() for chunk in chunks)
