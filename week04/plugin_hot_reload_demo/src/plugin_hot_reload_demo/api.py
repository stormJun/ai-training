"""FastAPI entrypoint for the plugin hot reload demo."""

from __future__ import annotations

from fastapi import FastAPI

from .graph_manager import GraphManager
from .models import ChatRequest, ChatResponse
from .plugin_manager import PluginManager


def create_app() -> FastAPI:
    """Create the demo API."""

    plugin_manager = PluginManager("plugin_hot_reload_demo.plugins")
    graph_manager = GraphManager(plugin_manager)

    app = FastAPI(title="Plugin Hot Reload Demo", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "plugins": [plugin.name for plugin in plugin_manager.get_plugins()],
        }

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return ChatResponse(response=graph_manager.invoke(request.query))

    @app.post("/reload")
    def reload_plugins() -> dict[str, object]:
        graph_manager.reload_graph()
        return {
            "status": "ok",
            "plugins": [plugin.name for plugin in plugin_manager.get_plugins()],
        }

    return app


app = create_app()
