# %% [markdown]
# ## 1. 图的节点工作过程
#
# 节点之间通过消息传递进行通信。
#
# 一个节点完成工作以后，会向邻居节点发送消息。收到消息的节点，会进行相应的处理。节点的工作过程在一个超步中完成以下步骤：
#
# 1. 初始状态为所有节点都处于`inactive`状态。
# 2. 每个节点在每个超步中，根据自身状态和收到的消息，计算出新的状态。
# 3. 节点在`active`状态下，完成自己的工作，之后会向邻居节点发送消息。
# 4. 超步结束，如果没有新的消息产生，那么整个图的计算就结束了。节点会举手进入到`vote to halt`状态，等待其他节点也举手，进入`halted`状态，表示整个图计算结束。
# 5. 系统将举手的节点，标记为休息状态。
# 6. 节点最终回到初始的`inactive`状态。
# 7. 最终，当所有的节点都进入`halted`状态时，整个图计算结束。
#
# 注意：
# 1. 在使用图之前，需要对图进行编译（验证图结构、构建 CompiledGraph 对象、验证 CompiledGraph 对象）。

# %% [markdown]
# ## 2. 状态
#
# 状态包含两个关键部分，一个是模式 Schema ， 一个是规约函数 reducer。Schema 定义了状态的数据结构，而 reducer 则定义了如何根据输入更新状态。
#
# Schema 定义了数据的结构和类型，可以用 TypedDict 和 Pydantic 来定义。
#
# ```python
# from typing import Annotated, Sequence
# from typing_extensions import TypedDict
# import operator
#
# from langgraph.graph import StateGraph, START, END
# from pydantic import BaseModel, Field
#
#
# # 定义状态 Schema 使用 Pydantic
# class AgentState(BaseModel):
#     messages: Annotated[Sequence[str], operator.add] = Field(default_factory=list)
#     user_input: str = ""
#     tool_calls: list = Field(default_factory=list)
#     final_response: str = ""
#
#
# # 定义状态 Schema 使用 TypedDict
# class GraphState(TypedDict):
#     messages: Annotated[Sequence[str], operator.add]
#     user_input: str
#     tool_calls: list
#     final_response: str
# ```
#
# LangGraph 的图支持三种类型的状态模式，分别是：
#
# 1. 共享模式：共享模式的状态会被所有节点共享。共享模式的状态 Schema 必须是可哈希的。
# 2. 私有模式：私有模式的状态不会被其他节点共享。私有模式的状态 Schema 可以是可变对象。
# 3. 内部模式：内部模式的状态不会被其他节点共享。内部模式的状态 Schema 必须是可哈希的。
#
# 规约函数 reducer 指定如何将节点的更新应用到状态上。每个状态键都有独立的规约函数，如果不指定，默认是覆盖更新。

# %% [markdown]
# ## 3. 节点
#
# 节点支持同步和异步，本质上是 Python 函数。
#
# 但是第一个位置参数必须是状态`state`，第二个位置参数是可选的配置`config`。
#
# 节点会被自动转换为 RunableLamaba 对象，支持批处理和异步操作。
#
# 节点返回值会作为状态更新， 只需包含要更新的字段。
#
# ```Python
# from typing import Annotated, Sequence
# from typing_extensions import TypedDict
# import operator
#
# from langgraph.graph import StateGraph, START, END
#
#
# # 定义状态 Schema 使用 TypedDict
# class GraphState(TypedDict):
#     messages: Annotated[Sequence[str], operator.add]
#     user_input: str
#     tool_calls: list
#     final_response: str
#
#
# # 节点函数
# def handle_user_input(state: GraphState) -> dict:
#     return {"user_input": state["messages"][-1] if state["messages"] else ""}
#
#
# def generate_response(state: GraphState) -> dict:
#     response = f"AI 回复: 收到你的消息: {state['user_input']}"
#     return {
#         "messages": [response],
#         "final_response": response,
#     }
#
#
# # 构建图
# builder = StateGraph(GraphState)
#
# builder.add_node("input", handle_user_input)
# builder.add_node("llm", generate_response)
#
# builder.add_edge(START, "input")
# builder.add_edge("input", "llm")
# builder.add_edge("llm", END)
#
# # 编译图
# graph = builder.compile()
#
# # 运行
# result = graph.invoke({
#     "messages": ["Hello from TypedDict!"],
#     "user_input": "",
#     "tool_calls": [],
#     "final_response": ""
# })
#
# print(result["final_response"])
# # 输出: AI 回复: 收到你的消息: Hello from TypedDict!
# ```

# %% [markdown]
# ## 4. 边
#
# 边定义了数据的连接关系，是数据流动的通道。边有四种类型：
#
# 1. 普通边
# 2. 条件边
# 3. 入口边
# 4. 条件入口边
#
# ### 4.1  普通边
#
# 普通边是最常见的边，它表示两个节点之间的直接连接关系。
#
# ```python
# builder.add_edge("node1", "node2")
# ```
#
# ### 4.2 条件边
#
# 条件边表示节点之间的连接需要满足特定的条件，比如下面代码中，只有当 `node1` 的值大于 `0` 时，才会建立 `node1` 和 `node2` 之间的连接。
#
# ```python
# def route_condition(state: State):
#     if state["score"] <= 60:
#         return "node4"
#     else:
#         return "node5"
#
# # 直接使用返回值作为下一个节点
# builder.add_edge("node3", condition=route_condition)
#
# # 使用映射字典定义下一个节点
# builder.add_edge(
#     "node3", 
#     condition=route_condition, 
#     { True: "node4", False: "node5" }
# )
# ```
#
# ### 4.3 入口边
# ```python
# builder.add_entry("node1")
# ```
#
# ### 4.4 条件入口边
# ```python
# def route_condition(state: State):
#     if state.get("is_login"):
#         return "node1"
#     return "node2"
#
# builder.add_conditional_entry(START, route_condition)
# ```

# %% [markdown]
# ## 5. 其他重要概念
#
# 1. 子图：子图是一种封装机制，允许将一个完整的图作为节点嵌入到另一个图中。这种机制是 MultiAgent 的核心。
# 2. 检查点：checkpoint 是图状态的快照，由 StateSnapshot 对象表示。
# 3. 会话： session 是用户与图之间的对话。在 Python 中用线程表示。每个 session 有唯一的会话 ID。
