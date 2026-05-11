```python
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
```
**Output:**

```text
[Node1] 当前 step_count: 0
[Node2] 当前 step_count: 1

 最终输出:
{'messages': ['Initial input', 'Hello from node1 at step 1', 'Goodbye from node2 at step 2'], 'step_count': 2}

 状态变更历史（快照）:
StateSnapshot(values={'messages': ['Initial input', 'Hello from node1 at step 1', 'Goodbye from node2 at step 2'], 'step_count': 2}, next=(), config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f882-6a9c-8002-c61205ac2bf9'}}, metadata={'source': 'loop', 'step': 2, 'parents': {}}, created_at='2025-09-13T16:05:42.139970+00:00', parent_config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f882-6a9b-8001-220d0d477fdb'}}, tasks=(), interrupts=())
StateSnapshot(values={'messages': ['Initial input', 'Hello from node1 at step 1'], 'step_count': 1}, next=('node2',), config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f882-6a9b-8001-220d0d477fdb'}}, metadata={'source': 'loop', 'step': 1, 'parents': {}}, created_at='2025-09-13T16:05:42.139970+00:00', parent_config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f880-62b9-8000-c8e66e66edff'}}, tasks=(PregelTask(id='3c707d99-0376-3a98-d27d-5d98b7c7baae', name='node2', path=('__pregel_pull', 'node2'), error=None, interrupts=(), state=None, result={'messages': ['Goodbye from node2 at step 2'], 'step_count': 2}),), interrupts=())
StateSnapshot(values={'messages': ['Initial input'], 'step_count': 0}, next=('node1',), config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f880-62b9-8000-c8e66e66edff'}}, metadata={'source': 'loop', 'step': 0, 'parents': {}}, created_at='2025-09-13T16:05:42.138949+00:00', parent_config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f87d-6b68-bfff-88691867fd35'}}, tasks=(PregelTask(id='a62460d6-729d-42d1-473c-8a5e5724df02', name='node1', path=('__pregel_pull', 'node1'), error=None, interrupts=(), state=None, result={'messages': ['Hello from node1 at step 1'], 'step_count': 1}),), interrupts=())
StateSnapshot(values={'messages': []}, next=('__start__',), config={'configurable': {'thread_id': '123', 'checkpoint_ns': '', 'checkpoint_id': '1f090bb7-f87d-6b68-bfff-88691867fd35'}}, metadata={'source': 'input', 'step': -1, 'parents': {}}, created_at='2025-09-13T16:05:42.137943+00:00', parent_config=None, tasks=(PregelTask(id='ffeb084c-5a8e-a45c-25f2-a921c32ccc71', name='__start__', path=('__pregel_pull', '__start__'), error=None, interrupts=(), state=None, result={'messages': ['Initial input'], 'step_count': 0}),), interrupts=())
```
可以根据检查点 ID 回到任意一个状态，并从那里重新启动 Agent
```python
config = {"configurable":{'thread_id': '123',  'checkpoint_id': '1f090bb7-f882-6a9b-8001-220d0d477fdb'}}

checkpoint_snapshot = graph.get_state(config)

graph.invoke({"messages": ["Initial input"], "step_count": 0}, config=config)
```
**Output:**

```text
[Node1] 当前 step_count: 0
[Node2] 当前 step_count: 1
```

```text
{'messages': ['Initial input',
  'Hello from node1 at step 1',
  'Initial input',
  'Hello from node1 at step 1',
  'Goodbye from node2 at step 2'],
 'step_count': 2}
```
```python
!pip install -qU redis aioredis
```
```python
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
```
**Output:**

```text
查询订单: 订单号不合法，请输入10到12位数字。
Messages: [HumanMessage(content='abc123', additional_kwargs={}, response_metadata={}, id='3439bc1e-ac46-4499-838f-1a3c9aa2e227'), HumanMessage(content='订单号不合法，请输入10到12位数字。', additional_kwargs={}, response_metadata={}, id='a79cf0d3-3c31-4cd7-8e69-9d98500e8311'), HumanMessage(content='订单状态: 已发货', additional_kwargs={}, response_metadata={}, id='c4cf2943-f121-4bee-9639-fc9ed7e01919')]
Retry count: 1
---
Messages: [HumanMessage(content='abc123', additional_kwargs={}, response_metadata={}, id='3439bc1e-ac46-4499-838f-1a3c9aa2e227'), HumanMessage(content='订单号不合法，请输入10到12位数字。', additional_kwargs={}, response_metadata={}, id='a79cf0d3-3c31-4cd7-8e69-9d98500e8311')]
Retry count: 1
---
Messages: [HumanMessage(content='abc123', additional_kwargs={}, response_metadata={}, id='3439bc1e-ac46-4499-838f-1a3c9aa2e227'), HumanMessage(content='订单号不合法，请输入10到12位数字。', additional_kwargs={}, response_metadata={}, id='a79cf0d3-3c31-4cd7-8e69-9d98500e8311')]
Retry count: 1
---
Messages: [HumanMessage(content='abc123', additional_kwargs={}, response_metadata={}, id='3439bc1e-ac46-4499-838f-1a3c9aa2e227')]
Retry count: 0
---
Messages: []
Retry count: 0
---
```
```python
from typing import Annotated, Sequence
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END, add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
```
```python
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
```
```python
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
```
```python
# 测试

config = {"configurable": {"thread_id": "test_001"}}

inputs = {
    "messages": [HumanMessage(content="解释一下什么是机器学习")],
    "current_model": ""
}

result = app.invoke(inputs, config=config)
```
**Output:**

```text
尝试调用主模型 (gpt-4)...
主模型失败: AuthenticationError: Error code: 401 - {'error': {'message': '无效的令牌 (request id: 2025091400414229283963658964709)', 'type': 'v_api_error'}}
切换到备用模型 (gpt-3.5-turbo)
```
```python
print("最终使用的模型:", result["current_model"])

for msg in result["messages"]:
    if isinstance(msg, AIMessage):
        print("AI 回复:")
        print(msg.content)
```
**Output:**

```text
最终使用的模型: gpt-3.5-turbo
AI 回复:
机器学习是一种人工智能的分支，其目的是让计算机系统通过学习数据和模式来自动改进和适应，而不需要明确的编程指令。通过机器学习，计算机系统可以从大量的数据中识别模式和趋势，并利用这些信息来做出预测和决策。机器学习的应用范围非常广泛，包括语音识别、图像识别、自然语言处理、推荐系统等领域。在机器学习中，常用的算法包括监督学习、无监督学习和强化学习等。通过不断地训练和优化，机器学习算法可以不断提高性能和准确性，从而更好地应用于实际问题中。
```
