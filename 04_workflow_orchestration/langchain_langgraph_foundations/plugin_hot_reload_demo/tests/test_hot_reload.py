from __future__ import annotations

import asyncio
import importlib
import shutil
from pathlib import Path

import httpx

from plugin_hot_reload_demo.api import create_app
from plugin_hot_reload_demo.graph_manager import GraphManager
from plugin_hot_reload_demo.plugin_manager import PluginManager


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "src" / "plugin_hot_reload_demo" / "plugins"
GREETING_FILE = PLUGIN_DIR / "greeting.py"
ORIGINAL_GREETING = """from plugin_hot_reload_demo.models import PluginSpec\n\n\ndef greet(query: str) -> str:\n    return f\"greeting-v1:{query}\"\n\n\nPLUGIN = PluginSpec(name=\"greeting\", description=\"Greeting plugin\", handler=greet)\n"""
UPDATED_GREETING = """from plugin_hot_reload_demo.models import PluginSpec\n\n\ndef greet(query: str) -> str:\n    return f\"greeting-v2:{query}\"\n\n\nPLUGIN = PluginSpec(name=\"greeting\", description=\"Greeting plugin\", handler=greet)\n"""


def write_greeting_plugin(content: str) -> None:
    GREETING_FILE.write_text(content, encoding="utf-8")
    pycache_dir = PLUGIN_DIR / "__pycache__"
    if pycache_dir.exists():
        shutil.rmtree(pycache_dir)
    importlib.invalidate_caches()


def reset_greeting_plugin() -> None:
    write_greeting_plugin(ORIGINAL_GREETING)


async def request_json(app, method: str, path: str, payload: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, json=payload)


def test_plugin_manager_loads_default_plugins() -> None:
    reset_greeting_plugin()
    manager = PluginManager("plugin_hot_reload_demo.plugins")

    names = [plugin.name for plugin in manager.get_plugins()]

    assert "greeting" in names
    assert "invoice" in names


def test_reload_builds_new_graph_but_old_graph_keeps_old_behavior() -> None:
    reset_greeting_plugin()
    manager = PluginManager("plugin_hot_reload_demo.plugins")
    graph_manager = GraphManager(manager)
    old_graph = graph_manager.get_graph()

    old_result = graph_manager.invoke_with_graph(old_graph, "hello")
    assert old_result == "greeting-v1:hello"

    write_greeting_plugin(UPDATED_GREETING)
    graph_manager.reload_graph()
    new_graph = graph_manager.get_graph()

    new_result = graph_manager.invoke_with_graph(new_graph, "hello")
    assert new_result == "greeting-v2:hello"

    old_result_after_reload = graph_manager.invoke_with_graph(old_graph, "hello")
    assert old_result_after_reload == "greeting-v1:hello"


def test_api_exposes_health_chat_and_reload() -> None:
    reset_greeting_plugin()
    app = create_app()

    health = asyncio.run(request_json(app, "GET", "/health"))
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    chat_before = asyncio.run(request_json(app, "POST", "/chat", {"query": "hello"}))
    assert chat_before.status_code == 200
    assert chat_before.json()["response"] == "greeting-v1:hello"

    write_greeting_plugin(UPDATED_GREETING)
    reload_resp = asyncio.run(request_json(app, "POST", "/reload"))
    assert reload_resp.status_code == 200

    chat_after = asyncio.run(request_json(app, "POST", "/chat", {"query": "hello"}))
    assert chat_after.status_code == 200
    assert chat_after.json()["response"] == "greeting-v2:hello"
