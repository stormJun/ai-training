"""Graph builder that swaps compiled graphs after plugin reload."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .models import PluginSpec
from .plugin_manager import PluginManager


class GraphState(TypedDict, total=False):
    """State used by the LangGraph app."""

    query: str
    route: str
    response: str


class GraphManager:
    """Manage the current compiled graph and rebuild after plugin reload."""

    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self._graph = self._build_graph()

    def _build_graph(self):
        plugins = {plugin.name: plugin for plugin in self.plugin_manager.get_plugins()}
        graph = StateGraph(GraphState)

        def route_query(state: GraphState) -> GraphState:
            query = state["query"]
            route = "invoice" if "invoice" in query.lower() else "greeting"
            return {"route": route}

        graph.add_node("route_query", route_query)

        for plugin_name, plugin in plugins.items():
            graph.add_node(plugin_name, self._build_plugin_node(plugin))
            graph.add_edge(plugin_name, END)

        graph.add_edge(START, "route_query")
        graph.add_conditional_edges("route_query", self._pick_route, {name: name for name in plugins})
        return graph.compile()

    @staticmethod
    def _build_plugin_node(plugin: PluginSpec):
        def run_plugin(state: GraphState) -> GraphState:
            return {"response": plugin.handler(state["query"])}

        return run_plugin

    @staticmethod
    def _pick_route(state: GraphState) -> str:
        return state["route"]

    def get_graph(self):
        """Return the current compiled graph."""

        return self._graph

    def reload_graph(self):
        """Reload plugins and swap in a new graph."""

        self.plugin_manager.reload_plugins()
        self._graph = self._build_graph()
        return self._graph

    @staticmethod
    def invoke_with_graph(graph, query: str) -> str:
        """Run a specific graph instance."""

        result = graph.invoke({"query": query})
        return result["response"]

    def invoke(self, query: str) -> str:
        """Run the current graph instance."""

        return self.invoke_with_graph(self._graph, query)
