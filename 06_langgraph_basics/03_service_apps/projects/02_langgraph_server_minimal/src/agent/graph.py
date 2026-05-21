"""LangGraph 单节点图的标准学习版示例。

本文件使用官方当前更推荐的写法：
1. 定义状态 `State`
2. 定义运行时上下文 `Context`
3. 编写节点函数
4. 创建 `StateGraph` builder
5. 添加节点与边
6. 编译得到可执行图
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


class Context(TypedDict):
    """Agent 的上下文参数。

    这些参数在调用图时通过 `context=` 传入，供节点在运行时读取。
    参考：
    https://docs.langchain.com/oss/python/langgraph/graph-api
    """
    my_configurable_param: str


@dataclass
class State:
    """Agent 的输入状态。

    用于定义传入数据的初始结构。
    参考：
    https://docs.langchain.com/oss/python/langgraph/graph-api
    """
    changeme: str = "example"


def call_model(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """处理输入并返回输出。

    通过 `runtime.context` 读取运行时上下文，生成新的状态字段。
    """
    context = runtime.context or {}
    return {
        "changeme": "output from call_model. "
        f"Configured with {context.get('my_configurable_param')}"
    }


# 1. 创建图的 builder，并声明状态结构与运行时上下文结构
builder = StateGraph(State, context_schema=Context)

# 2. 添加节点。这里显式命名为 `call_model`，便于学习和后续扩展
builder.add_node("call_model", call_model)

# 3. 添加边，完整展示 START -> 节点 -> END 的标准流程
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)

# 4. 编译为可执行图对象
graph = builder.compile(name="New Graph")
