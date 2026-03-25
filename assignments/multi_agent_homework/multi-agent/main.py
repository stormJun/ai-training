import asyncio
import datetime
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from .langgraph_app.graph import create_graph


TOOLS_SERVER = {
    "tools_server": {
        # MCP tool endpoint; ensure server is started separately.
        "url": "http://localhost:8000/mcp",
        "transport": "streamable_http",
    }
}


async def _run_pipeline(topic: str, style: str, length: int) -> Dict[str, Any]:
    """Connect to MCP server, build graph, and run the agent pipeline."""
    client = MultiServerMCPClient(TOOLS_SERVER)
    async with client.session("tools_server") as mcp_session:
        mcp_tools = await load_mcp_tools(mcp_session)
        app_graph = create_graph(mcp_tools)
        initial_state: Dict[str, Any] = {
            "topic": topic,
            "style": style,
            "length": length,
            "log": [f"# 多代理协作写作流程\n\n- 主题: {topic}\n- 风格: {style}\n- 目标字数: {length}"],
        }
        return await app_graph.ainvoke(initial_state)


def _save_output(topic: str, final_state: Dict[str, Any]) -> str:
    """Persist final article and stage logs into a timestamped markdown file."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"article_output_{timestamp}.md"
    output_path = Path(__file__).resolve().parent / output_filename

    final_article = final_state.get("final_article", "未生成最终文章。")
    log_sections = [
        final_state.get("log_research", ""),
        final_state.get("log_draft", ""),
        final_state.get("log_review", ""),
        final_state.get("log_polish", ""),
        "## 执行记录\n" + "\n".join(final_state.get("log", [])),
    ]
    process_log = "\n\n".join([part for part in log_sections if part])

    final_output = f"# 最终文章：{topic}\n\n{final_article}\n\n---\n\n{process_log}"
    output_path.write_text(final_output, encoding="utf-8")
    return str(output_path)


async def main_async() -> None:
    load_dotenv()
    topic = input("请输入文章主题（默认：帮我写一篇关于AI Agent的文章）：").strip() or "帮我写一篇关于AI Agent的文章"
    style = input("请输入期望的风格（默认：通俗易懂）：").strip() or "通俗易懂"
    length_raw = input("请输入期望字数（默认：800）：").strip()
    try:
        length = int(length_raw) if length_raw else 800
    except ValueError:
        length = 800

    print("\n================ 多代理写作开始 ================\n")
    print("提示：先在另一个终端运行 `python -m multi-agent.mcp_server.main` 启动 MCP 服务器。\n")
    try:
        final_state = await _run_pipeline(topic, style, length)
    except Exception as exc:
        print(f"❌ 运行失败：{exc}")
        print("请确认 MCP 服务器已启动，并检查网络与 API Key 配置（可选）。")
        return

    output_file = _save_output(topic, final_state)
    print("✅ 写作流程已完成！")
    print(f"📄 生成文件: {output_file}")


def main() -> None:
# 作业的入口写在这里。你可以就写这个文件，或者扩展多个文件，但是执行入口留在这里。
# 在根目录可以通过python -m multi-agent.main 运行
    # Single entrypoint to keep CLI behavior consistent.
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
