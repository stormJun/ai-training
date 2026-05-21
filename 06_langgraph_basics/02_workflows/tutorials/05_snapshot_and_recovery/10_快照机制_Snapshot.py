"""LangGraph 快照机制示例。

这个脚本包含 3 个部分：
1. 最小快照与状态历史
2. 输入校验 + 重试的状态历史
3. 主模型失败后切换备用模型，并记录最终使用模型
"""

from __future__ import annotations

import operator
import os
import re
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SimpleAgentState(BaseModel):
    """最小快照示例的状态。"""

    messages: Annotated[list[str], operator.add] = Field(default_factory=list)
    step_count: int = 0


def node1(state: SimpleAgentState) -> dict:
    """第一步节点。"""
    print(f"[node1] 当前 step_count: {state.step_count}")
    return {
        "messages": [f"Hello from node1 at step {state.step_count + 1}"],
        "step_count": state.step_count + 1,
    }


def node2(state: SimpleAgentState) -> dict:
    """第二步节点。"""
    print(f"[node2] 当前 step_count: {state.step_count}")
    return {
        "messages": [f"Goodbye from node2 at step {state.step_count + 1}"],
        "step_count": state.step_count + 1,
    }


def build_simple_snapshot_graph():
    """构建最小快照示例图。"""
    builder = StateGraph(SimpleAgentState)
    builder.add_node("node1", node1)
    builder.add_node("node2", node2)
    builder.add_edge(START, "node1")
    builder.add_edge("node1", "node2")
    builder.add_edge("node2", END)
    return builder.compile(checkpointer=MemorySaver())


def run_simple_snapshot_demo():
    """运行最小快照示例，并返回中间 checkpoint_id。"""
    print("\n=== Demo 1: 最小快照历史 ===")
    graph = build_simple_snapshot_graph()
    config = {"configurable": {"thread_id": "123"}}

    result = graph.invoke(
        {"messages": ["Initial input"], "step_count": 0},
        config=config,
    )

    print("\n最终输出:")
    print(result)

    print("\n状态变更历史（快照）:")
    state_history = list(graph.get_state_history(config))
    for snapshot in state_history:
        print(snapshot)

    checkpoint_id = None
    if len(state_history) >= 2:
        checkpoint_id = state_history[1].config["configurable"]["checkpoint_id"]

    return graph, checkpoint_id


def run_resume_from_checkpoint_demo(graph, checkpoint_id: str | None):
    """从指定 checkpoint 恢复执行。"""
    print("\n=== Demo 2: 从检查点恢复 ===")
    if not checkpoint_id:
        print("没有可用的 checkpoint_id，跳过恢复示例。")
        return

    config = {
        "configurable": {
            "thread_id": "123",
            "checkpoint_id": checkpoint_id,
        }
    }
    checkpoint_snapshot = graph.get_state(config)
    print("恢复前的检查点状态:")
    print(checkpoint_snapshot)

    resumed_result = graph.invoke(
        {"messages": ["Initial input"], "step_count": 0},
        config=config,
    )
    print("恢复执行后的结果:")
    print(resumed_result)


class ValidationGraphState(TypedDict):
    """输入校验示例的状态。"""

    messages: Annotated[list, add_messages]
    retry_count: int


def is_valid_order_id(text: str) -> bool:
    """订单号必须是 10 到 12 位数字。"""
    return bool(re.fullmatch(r"\d{10,12}", text))


def validate_input(state: ValidationGraphState) -> Literal["valid", "invalid"]:
    """根据用户最后一条消息做校验。"""
    last_message = state["messages"][-1]
    user_input = last_message.content.strip()
    return "valid" if is_valid_order_id(user_input) else "invalid"


def receive_input(state: ValidationGraphState):
    """接收输入。"""
    user_input = state["messages"][-1].content.strip()
    return {"order_id": user_input}


def query_order(state: ValidationGraphState):
    """模拟订单查询。"""
    order_id = state["messages"][-1].content.strip()
    print(f"查询订单: {order_id}")
    return {
        "messages": ["订单状态: 已发货"],
        "status": "success",
    }


def handle_invalid(state: ValidationGraphState):
    """处理非法订单号并累加重试次数。"""
    retry = state.get("retry_count", 0)
    if retry >= 2:
        return {
            "messages": ["输入错误次数过多，会话结束。"],
            "retry_count": retry + 1,
        }

    return {
        "messages": ["订单号不合法，请输入10到12位数字。"],
        "retry_count": retry + 1,
    }


def build_validation_graph():
    """构建输入校验示例图。"""
    builder = StateGraph(ValidationGraphState)
    builder.add_node("receive_input", receive_input)
    builder.add_node("query_order", query_order)
    builder.add_node("handle_invalid", handle_invalid)

    builder.add_conditional_edges(
        START,
        validate_input,
        {
            "valid": "query_order",
            "invalid": "handle_invalid",
        },
    )
    builder.add_conditional_edges(
        "handle_invalid",
        lambda state: "receive_input" if state["retry_count"] < 2 else END,
    )
    builder.add_edge("receive_input", "query_order")
    builder.add_edge("query_order", END)
    return builder.compile(checkpointer=MemorySaver())


def run_validation_history_demo():
    """运行非法输入示例并打印状态历史。"""
    print("\n=== Demo 3: 输入校验与状态历史 ===")
    app = build_validation_graph()
    config = {"configurable": {"thread_id": "validation-demo"}}

    app.invoke({"messages": ["abc123"]}, config=config)

    history = app.get_state_history(config)
    for snapshot in history:
        print("Messages:", snapshot.values["messages"])
        print("Retry count:", snapshot.values.get("retry_count", 0))
        print("---")


class FallbackGraphState(TypedDict):
    """模型降级示例的状态。"""

    messages: Annotated[list, add_messages]
    current_model: str


primary_model = ChatOpenAI(
    model="gpt-4",
    api_key="invalid_key_for_test",
    temperature=0.7,
    timeout=5.0,
)

backup_model = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7,
    timeout=10.0,
)


def call_llm(state: FallbackGraphState):
    """优先调用主模型，失败后切换备用模型。"""
    messages = state["messages"]

    try:
        print("尝试调用主模型 (gpt-4)...")
        response = primary_model.invoke(messages)
        return {
            "messages": [AIMessage(content=response.content)],
            "current_model": "gpt-4",
        }
    except Exception as exc:
        print(f"主模型失败: {type(exc).__name__}: {exc}")
        print("切换到备用模型 (gpt-3.5-turbo)")

    try:
        response = backup_model.invoke(messages)
        return {
            "messages": [AIMessage(content=response.content)],
            "current_model": "gpt-3.5-turbo",
        }
    except Exception as exc:
        print(f"备用模型也失败: {exc}")
        return {
            "messages": [AIMessage(content="服务暂时不可用，请稍后再试。")],
            "current_model": "none",
        }


def build_fallback_graph():
    """构建主模型 / 备用模型降级示例图。"""
    builder = StateGraph(FallbackGraphState)
    builder.add_node("call_llm", call_llm)
    builder.add_edge(START, "call_llm")
    builder.add_edge("call_llm", END)
    return builder.compile(checkpointer=MemorySaver())


def run_model_fallback_demo():
    """运行主模型失败、备用模型接管的示例。"""
    print("\n=== Demo 4: 模型降级与快照 ===")
    app = build_fallback_graph()
    config = {"configurable": {"thread_id": "test_001"}}

    inputs = {
        "messages": [HumanMessage(content="解释一下什么是机器学习")],
        "current_model": "",
    }
    result = app.invoke(inputs, config=config)

    print("最终使用的模型:", result["current_model"])
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            print("AI 回复:")
            print(message.content)


def main():
    graph, checkpoint_id = run_simple_snapshot_demo()
    run_resume_from_checkpoint_demo(graph, checkpoint_id)
    run_validation_history_demo()
    run_model_fallback_demo()


if __name__ == "__main__":
    main()
