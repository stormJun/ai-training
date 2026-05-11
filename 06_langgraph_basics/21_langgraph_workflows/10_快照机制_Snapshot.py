# %%
from typing import Annotated, Sequence
from pydantic import BaseModel, Field
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver  # ←← 

# === 1. 定义状态 Schema (Pydantic) ===
class AgentState(BaseModel):
    messages: Annotated[Sequence[str], operator.add] = Field(default_factory=list)
    step_count: int = 0


# === 2. 节点函数 ===
def node1(state: AgentState) -> dict:
    print(f"[Node1] 当前 step_count: {state.step_count}")
    new_message = f"Hello from node1 at step {state.step_count + 1}"
    return {
        "messages": [new_message],
        "step_count": state.step_count + 1,
    }


def node2(state: AgentState) -> dict:
    print(f"[Node2] 当前 step_count: {state.step_count}")
    new_message = f"Goodbye from node2 at step {state.step_count + 1}"
    return {
        "messages": [new_message],
        "step_count": state.step_count + 1,
    }


# === 3. 构建图 ===
builder = StateGraph(AgentState)

builder.add_node("node1", node1)
builder.add_node("node2", node2)

builder.add_edge(START, "node1")
builder.add_edge("node1", "node2")
builder.add_edge("node2", END)

# 编译时必须传入 checkpointer
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)  # ←← 启用 checkpointer

# === 4. 执行图并传入 config（包含 thread_id）===
config = {"configurable": {"thread_id": "123"}}
result = graph.invoke(
    {"messages": ["Initial input"], "step_count": 0},
    config=config
)

print("\n 最终输出:")
print(result)

# === 5. 获取状态历史（快照）===
print("\n 状态变更历史（快照）:")
state_history = list(graph.get_state_history(config))
for state in state_history:
    print(state)

# %% [markdown]
# 可以根据检查点 ID 回到任意一个状态，并从那里重新启动 Agent

# %%
config = {"configurable":{'thread_id': '123',  'checkpoint_id': '1f090bb7-f882-6a9b-8001-220d0d477fdb'}}

checkpoint_snapshot = graph.get_state(config)

graph.invoke({"messages": ["Initial input"], "step_count": 0}, config=config)

# %%
# !pip install -qU redis aioredis

# %%
import re
from typing import Annotated, Sequence, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver


# 1. 定义状态
class GraphState(TypedDict):
    messages: Annotated[Sequence, add_messages]
    retry_count: int


# 2. 输入校验函数
def is_valid_order_id(text: str) -> bool:
    return bool(re.fullmatch(r"\d{10,12}", text))


def validate_input(state: GraphState) -> Literal["valid", "invalid"]:
    last_message = state["messages"][-1]
    user_input = last_message.content.strip()
    if is_valid_order_id(user_input):
        return "valid"
    return "invalid"


# 3. 节点函数
def receive_input(state: GraphState):
    user_input = state["messages"][-1].content.strip()
    return {"order_id": user_input}


def query_order(state: GraphState):
    order_id = state["messages"][-1].content.strip()
    print(f"查询订单: {order_id}")
    return {
        "messages": ["订单状态: 已发货"],
        "status": "success"
    }


def handle_invalid(state: GraphState):
    retry = state.get("retry_count", 0)
    if retry >= 2:
        reply = "输入错误次数过多，会话结束。"
        return {"messages": [reply], "retry_count": retry + 1}
    
    reply = "订单号不合法，请输入10到12位数字。"
    return {"messages": [reply], "retry_count": retry + 1}


# 4. 构建图
builder = StateGraph(GraphState)

builder.add_node("receive_input", receive_input)
builder.add_node("query_order", query_order)
builder.add_node("handle_invalid", handle_invalid)

# 条件跳转
builder.add_conditional_edges(
    START,
    validate_input,
    {
        "valid": "query_order",
        "invalid": "handle_invalid"
    }
)

# 如果无效，最多重试2次
builder.add_conditional_edges(
    "handle_invalid",
    lambda s: "receive_input" if s["retry_count"] < 2 else END
)

builder.add_edge("receive_input", "query_order")
builder.add_edge("query_order", END)

# 编译图，使用 MemorySaver 记录状态历史
memory_saver = MemorySaver()
app = builder.compile(checkpointer=memory_saver)


# 5. 测试运行
config = {"configurable": {"thread_id": "123"}}

# 第一次：非法输入
app.invoke(
    {"messages": ["abc123"]},
    config=config
)

# 查看状态历史
history = app.get_state_history(config)
for snapshot in history:
    print("Messages:", snapshot.values["messages"])
    print("Retry count:", snapshot.values.get("retry_count", 0))
    print("---")

# %%
from typing import Annotated, Sequence
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END, add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# %%
import os
class GraphState(TypedDict):
    messages: Annotated[Sequence, add_messages]
    current_model: str

# 主模型（故意设错 API Key 来模拟调用失败）
primary_model = ChatOpenAI(
    model="gpt-4",
    api_key="invalid_key_for_test",  # 强制报错
    temperature=0.7,
    timeout=5.0
)

# 备用模型（使用你真实的 API Key）
backup_model = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),  # 替换为你的有效 key
    temperature=0.7,
    timeout=10.0
) 

# %%
def call_llm(state):
    messages = state["messages"]
    used_model = ""
    response_message = None

    # 尝试主模型
    try:
        print("尝试调用主模型 (gpt-4)...")
        response = primary_model.invoke(messages)
        response_message = response
        used_model = "gpt-4"
    except Exception as e:
        print(f"主模型失败: {type(e).__name__}: {str(e)}")
        print("切换到备用模型 (gpt-3.5-turbo)")

        # 尝试备用模型
        try:
            response = backup_model.invoke(messages)
            response_message = response
            used_model = "gpt-3.5-turbo"
        except Exception as e2:
            print(f"备用模型也失败: {str(e2)}")
            return {
                "messages": [AIMessage(content="服务暂时不可用，请稍后再试。")],
                "current_model": "none"
            }

    return {
        "messages": [AIMessage(content=response_message.content)],
        "current_model": used_model
    }

builder = StateGraph(GraphState)
builder.add_node("call_llm", call_llm)
builder.add_edge(START, "call_llm")
builder.add_edge("call_llm", END)

# 启用检查点，用于后续查看状态历史
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

# %%
# 测试

config = {"configurable": {"thread_id": "test_001"}}

inputs = {
    "messages": [HumanMessage(content="解释一下什么是机器学习")],
    "current_model": ""
}

result = app.invoke(inputs, config=config)

# %%
print("最终使用的模型:", result["current_model"])

for msg in result["messages"]:
    if isinstance(msg, AIMessage):
        print("AI 回复:")
        print(msg.content)
