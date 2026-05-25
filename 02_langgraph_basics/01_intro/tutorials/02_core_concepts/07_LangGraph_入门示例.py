"""LangGraph 入门示例。

这份脚本分成两段：
1. 先运行一个最小的预置 Agent
2. 再手写一个最小的 StateGraph 聊天图
"""

from __future__ import annotations

import os
from typing import Annotated

from langchain_community.chat_models import ChatTongyi
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict


def build_llm() -> ChatTongyi:
    """构建通义千问聊天模型。"""
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("请先设置 DASHSCOPE_API_KEY 再运行此示例。")

    return ChatTongyi(
        model_name="qwen-turbo",
        temperature=0.7,
        streaming=True,
    )


def run_prebuilt_agent_demo(llm: ChatTongyi) -> None:
    """运行最小预置 Agent 示例。"""
    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt="You are a helpful assistant.",
    )

    print("=== Prebuilt Agent Demo ===")
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": "你是谁？"}]},
        stream_mode="messages",
    ):
        print(chunk)
        print()


class State(TypedDict):
    """图状态。"""

    messages: Annotated[list, add_messages]


def build_chatbot_graph(llm: ChatTongyi):
    """构建最小聊天图。"""

    def chatbot(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    return graph_builder.compile()


def stream_graph_updates(graph, user_input: str) -> None:
    """流式打印图输出。"""
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]}
    ):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


def run_interactive_demo(graph) -> None:
    """运行交互式聊天循环。"""
    print("=== StateGraph Chat Demo ===")
    print("输入 quit / exit / q 退出。")

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye!")
                break
            stream_graph_updates(graph, user_input)
        except EOFError:
            demo_question = "What do you know about LangGraph?"
            print("User:", demo_question)
            stream_graph_updates(graph, demo_question)
            break


def main() -> None:
    llm = build_llm()
    run_prebuilt_agent_demo(llm)
    graph = build_chatbot_graph(llm)
    run_interactive_demo(graph)


if __name__ == "__main__":
    main()
