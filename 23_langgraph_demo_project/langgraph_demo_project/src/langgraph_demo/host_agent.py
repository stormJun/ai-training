"""Master agent that routes between subagents and aggregates results."""

from __future__ import annotations

import argparse
import asyncio
from typing import TypedDict

import httpx
from langgraph.graph import END, START, StateGraph

from .analysis_agent import run_analysis_agent
from .models import AgentResponse
from .stock_agent import run_stock_agent


STOCK_URL = "http://127.0.0.1:8011/invoke"
ANALYSIS_URL = "http://127.0.0.1:8012/invoke"


class HostState(TypedDict, total=False):
    """State carried inside the host graph."""

    query: str
    mode: str
    route: str
    stock_response: AgentResponse | None
    analysis_response: AgentResponse | None
    final_answer: str


def route_query(state: HostState) -> HostState:
    """Decide which subagent(s) should handle the query."""

    query = state["query"]
    indicators = ["对比", "分析", "投资", "哪家", "组合", "值得关注"]
    route = "analysis" if any(token in query for token in indicators) else "stock"
    if ("先" in query or "再" in query) and route == "analysis":
        route = "both"
    return {"route": route}


async def call_remote_service(url: str, query: str) -> AgentResponse:
    """Invoke a remote FastAPI subagent."""

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json={"query": query})
        response.raise_for_status()
        return AgentResponse.model_validate(response.json())


def dispatch_local(state: HostState) -> HostState:
    """Run the matching subagent locally."""

    route = state["route"]
    updates: HostState = {}
    if route in {"stock", "both"}:
        updates["stock_response"] = run_stock_agent(state["query"])
    if route in {"analysis", "both"}:
        updates["analysis_response"] = run_analysis_agent(state["query"])
    return updates


def dispatch_remote(state: HostState) -> HostState:
    """Run the matching subagent(s) over HTTP."""

    async def _run() -> HostState:
        route = state["route"]
        updates: HostState = {}
        if route in {"stock", "both"}:
            updates["stock_response"] = await call_remote_service(STOCK_URL, state["query"])
        if route in {"analysis", "both"}:
            updates["analysis_response"] = await call_remote_service(ANALYSIS_URL, state["query"])
        return updates

    return asyncio.run(_run())


def pick_dispatch(state: HostState) -> str:
    """Pick local or remote dispatch mode."""

    return "dispatch_remote" if state.get("mode") == "remote" else "dispatch_local"


def synthesize(state: HostState) -> HostState:
    """Build the final host answer."""

    parts = [f"Host Agent 路由结果：{state['route']}"]
    stock_response = state.get("stock_response")
    analysis_response = state.get("analysis_response")
    if stock_response:
        parts.append(f"[Stock Subagent] {stock_response.summary}")
        parts.append(stock_response.detail)
    if analysis_response:
        parts.append(f"[Analysis Subagent] {analysis_response.summary}")
        parts.append(analysis_response.detail)
    return {"final_answer": "\n\n".join(parts)}


def build_host_agent():
    """Compile the host graph."""

    graph = StateGraph(HostState)
    graph.add_node("route_query", route_query)
    graph.add_node("dispatch_local", dispatch_local)
    graph.add_node("dispatch_remote", dispatch_remote)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "route_query")
    graph.add_conditional_edges(
        "route_query",
        pick_dispatch,
        {
            "dispatch_local": "dispatch_local",
            "dispatch_remote": "dispatch_remote",
        },
    )
    graph.add_edge("dispatch_local", "synthesize")
    graph.add_edge("dispatch_remote", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


HOST_AGENT = build_host_agent()


def run_host_agent(query: str, mode: str = "direct") -> str:
    """Execute the master agent."""

    result = HOST_AGENT.invoke({"query": query, "mode": mode})
    return result["final_answer"]


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Run the LangGraph host agent.")
    parser.add_argument("--query", required=True, help="Question to send to the host agent.")
    parser.add_argument(
        "--mode",
        choices=["direct", "remote"],
        default="direct",
        help="Whether the host agent calls local functions or remote FastAPI services.",
    )
    args = parser.parse_args()
    print(run_host_agent(args.query, mode=args.mode))


if __name__ == "__main__":
    main()
