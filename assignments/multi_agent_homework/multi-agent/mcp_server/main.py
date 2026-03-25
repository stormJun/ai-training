import json
from typing import List, Dict, Any

from fastmcp import FastMCP
from duckduckgo_search import DDGS

from .prompts import PROMPTS

# FastMCP app exposes search/prompt tools to LangGraph agents.
mcp = FastMCP("Multi Agent Tools")


def _safe_search(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """Perform a DuckDuckGo search with graceful fallback."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(topic, max_results=max_results))
    except Exception as exc:  # pragma: no cover - network edge case
        return [
            {
                "title": "搜索暂不可用，使用内置提示",
                "href": "local://cache",
                "body": f"无法联网获取 '{topic}' 的最新结果，返回占位数据。详情：{exc}",
            }
        ]


@mcp.tool
def search(topic: str, max_results: int = 6) -> str:
    """根据主题进行网络搜索，返回 JSON 字符串结果。"""
    results = _safe_search(topic, max_results)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool
def get_prompt(agent_name: str) -> str:
    """返回指定代理的系统提示词。"""
    return PROMPTS.get(agent_name, "prompt not found")


def run() -> None:
    """Run MCP HTTP server for tools."""
    print("🚀 MCP server running at http://localhost:8000/mcp (streamable-http)")
    mcp.run(transport="streamable-http", port=8000)


if __name__ == "__main__":
    run()
