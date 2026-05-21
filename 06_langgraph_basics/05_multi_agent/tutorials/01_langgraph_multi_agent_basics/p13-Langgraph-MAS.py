# -*- coding: utf-8 -*-
"""
用于旅行预定的多智能体系统 (MAS)。

此系统包含一个航班预订代理和一个酒店预订代理，它们可以通过相互移交
来协同完成用户的综合预订请求。
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_ENV_FILES = [
    SCRIPT_DIR / ".env",
    PROJECT_ROOT / "27_multi_agent_frameworks/27_autogen_two_agent_chat/.env",
    PROJECT_ROOT / "01_langchain_basics/.env",
]
PLACEHOLDER_API_KEYS = {
    "",
    "your_api_key_here",
    "your_dashscope_api_key_here",
    "your-dashscope-api-key",
    "your_api_key",
    "your-api-key",
    "your-api-key-here",
    "your_openai_api_key_here",
    "your_key_here",
    "your_real_api_key_here",
    "your_dashscope_api_key",
    "your key here",
    "replace_me",
    "replace-with-your-key",
    "your_api_here",
}


def ensure_dependencies() -> None:
    """在当前 Python 环境中检查并安装示例所需依赖。"""
    try:
        import dotenv  # noqa: F401
        import langchain_community  # noqa: F401
        import langgraph  # noqa: F401

        print("依赖已安装，跳过安装步骤。")
    except ImportError:
        print(f"正在为当前解释器 ({sys.executable}) 安装依赖，这可能需要几分钟。")
        packages = [
            "langchain",
            "langchain-community",
            "langgraph",
            "python-dotenv",
            "langchain-core",
        ]
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
        print("依赖安装完成。")


ensure_dependencies()

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import AIMessage, ToolMessage, convert_to_messages
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command


def is_placeholder_api_key(value: str | None) -> bool:
    """判断 API Key 是否为空或明显占位值。"""
    if value is None:
        return True

    normalized = value.strip()
    if not normalized:
        return True

    return normalized.lower() in PLACEHOLDER_API_KEYS


def load_candidate_env_files(env_files: list[Path] | None = None) -> None:
    """按顺序加载候选 .env 文件，但不覆盖已有环境变量。"""
    for env_file in env_files or DEFAULT_ENV_FILES:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)


def resolve_dashscope_api_key(env_files: list[Path] | None = None) -> str:
    """解析当前脚本运行所需的 DashScope API Key。"""
    load_candidate_env_files(env_files)

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if is_placeholder_api_key(api_key):
        searched = "\n".join(f"- {path}" for path in (env_files or DEFAULT_ENV_FILES))
        raise RuntimeError(
            "未找到可用的 DASHSCOPE_API_KEY。请先设置环境变量，或在以下 .env 文件之一中配置真实密钥：\n"
            f"{searched}"
        )

    return api_key.strip()


def build_llm() -> ChatTongyi:
    """构建与当前环境兼容的 Qwen 聊天模型。"""
    return ChatTongyi(
        model="qwen-plus",
        dashscope_api_key=resolve_dashscope_api_key(),
        temperature=0.5,
    )


def bind_model_with_tools(model: ChatTongyi, tools: list):
    """绑定工具，并显式关闭并行 tool calls。"""
    return model.bind_tools(tools, parallel_tool_calls=False)


def pretty_print_message(message, indent: bool = False) -> None:
    """美化单条消息的打印输出。"""
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + chunk for chunk in pretty_message.split("\n"))
    print(indented)


def pretty_print_messages(update, last_message: bool = False) -> None:
    """美化并打印整个更新流中的消息。"""
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"来自子图 {graph_id} 的更新:")
        print()
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"来自节点 {node_name} 的更新:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label)
        print()

        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]

        for message in messages:
            pretty_print_message(message, indent=is_subgraph)
        print()


def summarize_completed_tool_messages(messages) -> list[str]:
    """提取已完成工具调用的摘要，供 handoff 时传给下一个代理。"""
    completed = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        content = str(message.content).strip()
        if not content:
            continue
        if content.startswith("成功转移到"):
            continue
        completed.append(content)
    return completed


def build_handoff_messages(
    messages,
    tool_call_id: str,
    agent_name: str,
) -> list:
    """
    构建合法的 handoff 消息对。

    只把触发 handoff 的最后一条 AIMessage 和对应 ToolMessage 交给父图，
    避免把未完成配对的历史 tool calls 一并带过去。
    """
    last_ai_message = next(
        message for message in reversed(messages) if isinstance(message, AIMessage)
    )
    completed_items = summarize_completed_tool_messages(messages)
    summary_lines = [f"成功转移到 {agent_name}。"]
    if completed_items:
        summary_lines.append("已完成事项：")
        summary_lines.extend(f"- {item}" for item in completed_items)
    summary_lines.append(f"当前请继续处理 {agent_name} 负责的剩余事项。")
    summary_lines.append("不要重复处理已完成事项。")
    transfer_message = ToolMessage(
        content="\n".join(summary_lines),
        tool_call_id=tool_call_id,
    )
    return [last_ai_message, transfer_message]


def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """
    创建一个将控制权移交给指定代理的特殊工具。

    当代理调用该工具时，工具不会返回简单字符串，而是返回 `Command`，
    用来驱动 LangGraph 跳转到目标代理节点。
    """

    name = f"transfer_to_{agent_name}"
    description = description or f"转移到 {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        return Command(
            goto=agent_name,
            update={
                "messages": build_handoff_messages(
                    messages=state["messages"],
                    tool_call_id=tool_call_id,
                    agent_name=agent_name,
                )
            },
            graph=Command.PARENT,
        )

    return handoff_tool


transfer_to_hotel_assistant = create_handoff_tool(
    agent_name="hotel_assistant",
    description="将用户转接给酒店预订助理。",
)
transfer_to_flight_assistant = create_handoff_tool(
    agent_name="flight_assistant",
    description="将用户转接给航班预订助理。",
)


def book_hotel(hotel_name: str) -> str:
    """模拟预订酒店的操作。"""
    return f"已成功预订 {hotel_name} 的住宿。"


def book_flight(from_airport: str, to_airport: str) -> str:
    """模拟预订航班的操作。"""
    return f"已成功预订从 {from_airport} 到 {to_airport} 的航班。"


def build_multi_agent_graph():
    """构建航班代理和酒店代理协作的多智能体图。"""
    qwen_llm = build_llm()
    flight_tools = [book_flight, transfer_to_hotel_assistant]
    hotel_tools = [book_hotel, transfer_to_flight_assistant]

    flight_assistant = create_react_agent(
        model=bind_model_with_tools(qwen_llm, flight_tools),
        tools=flight_tools,
        prompt=(
            "你是一位专业的航班预订助理。你的任务是帮助用户预订航班。"
            "如果用户还需要预订酒店，请使用 transfer_to_hotel_assistant "
            "工具将他们转接给酒店助理。"
        ),
        name="flight_assistant",
    )

    hotel_assistant = create_react_agent(
        model=bind_model_with_tools(qwen_llm, hotel_tools),
        tools=hotel_tools,
        prompt=(
            "你是一位专业的酒店预订助理。你的任务是帮助用户预订酒店。"
            "如果用户还需要预订航班，请使用 transfer_to_flight_assistant "
            "工具将他们转接给航班助理。"
        ),
        name="hotel_assistant",
    )

    return (
        StateGraph(MessagesState)
        .add_node(flight_assistant)
        .add_node(hotel_assistant)
        .add_edge(START, "flight_assistant")
        .compile()
    )


def main() -> int:
    """执行多智能体旅行预订示例。"""
    try:
        multi_agent_graph = build_multi_agent_graph()
    except RuntimeError as exc:
        print(exc)
        return 1

    for chunk in multi_agent_graph.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "请帮我预订一张从波士顿(BOS)到纽约(JFK)的机票，"
                        "以及在麦克基特里克酒店(McKittrick Hotel)的住宿。"
                    ),
                }
            ]
        },
        subgraphs=True,
    ):
        pretty_print_messages(chunk)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
