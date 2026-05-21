# LangGraph 入门示例

这份材料只做两件事：

1. 先用 `create_react_agent(...)` 跑通一个最小 Agent
2. 再用 `StateGraph` 手写一个最小聊天图

配套脚本见同目录的 `07_LangGraph_入门示例.py`。

## 运行前提

- 已安装 `langgraph`
- 已安装 `langchain-community`
- 已配置 `DASHSCOPE_API_KEY`

如果你在当前专题里学习，优先在项目自己的环境里运行，不要直接在全局 Python 环境里试。

## 第一部分：最小 Agent

这一段的目标不是讲图结构，而是先让你看到：

- LangGraph 可以直接基于现成 Agent 工厂运行
- 模型、工具、提示词拼起来后，就能得到一个可流式输出的 Agent

核心代码：

```python
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatTongyi

llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
)

agent = create_react_agent(
    model=llm,
    tools=[],
    prompt="You are a helpful assistant.",
)
```

然后用流式方式调用：

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "你是谁？"}]},
    stream_mode="messages",
):
    print(chunk)
```

这里先记住一个结论就够了：

> 你不一定要先自己搭 `StateGraph`，也可以先用 LangGraph 预置的 Agent 能力感受整体运行方式。

## 第二部分：手写最小 StateGraph

当你开始自己搭图时，最先要理解的是“状态”。

下面这个状态只有一个字段 `messages`：

```python
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
```

这里的重点不是 `TypedDict`，而是：

- 图里的每个节点都读这个状态
- 节点返回的是“状态更新”
- `add_messages` 表示新消息要追加，而不是覆盖

接着定义图和节点：

```python
graph_builder = StateGraph(State)


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile()
```

这时候就有了一张最小图：

```text
START -> chatbot -> END
```

## 运行方式

最简单的流式打印函数：

```python
def stream_graph_updates(user_input: str):
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]}
    ):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)
```

再包一层交互循环：

```python
while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        break
    stream_graph_updates(user_input)
```

## 这份示例真正要你学会什么

- `create_react_agent(...)` 是最快的入门入口
- `StateGraph(State)` 是自己搭图的起点
- 节点本质上就是：`读取 state -> 返回 state 更新`
- `messages` 这种会累积的数据，通常要配 reducer，例如 `add_messages`

## 建议下一步

看完这份，再继续看：

- `08_LangGraph_核心概念_状态与节点.md`

那一份会更系统地讲状态、节点、边这些概念。
