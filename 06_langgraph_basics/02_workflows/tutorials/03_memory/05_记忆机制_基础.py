"""长期记忆基础示例。

这个脚本演示如何把 Redis 作为外部长期记忆层，与一个最小 LangGraph 对话图结合起来。
"""

from __future__ import annotations

import json
from typing import Annotated

import redis
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class GraphState(TypedDict):
    """图状态，只保存当前对话消息。"""

    messages: Annotated[list[AnyMessage], add_messages]


llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
)


class LongTermMemory:
    """基于 Redis 的最小长期记忆封装。"""

    def __init__(self, session_id: str, url: str = "redis://localhost:6379/0"):
        self.session_id = session_id
        self.key = f"memory:{session_id}"
        try:
            self.redis_client = redis.from_url(url)
            self.redis_client.ping()
        except Exception as exc:
            print(f"Redis 连接失败: {exc}")
            self.redis_client = None

    def save_memory(self, memory_type: str, content: str) -> None:
        """保存一条用户或助手消息。"""
        if not self.redis_client:
            return

        try:
            memory_data = {"type": memory_type, "content": content}
            self.redis_client.lpush(self.key, json.dumps(memory_data))
            print(f"记忆已保存: {content[:30]}...")
        except Exception as exc:
            print(f"保存记忆失败: {exc}")

    def get_memory(self, limit: int = 10) -> list[AnyMessage]:
        """读取最近若干条历史消息。"""
        if not self.redis_client:
            return []

        try:
            items = self.redis_client.lrange(self.key, 0, limit - 1)
            memories: list[AnyMessage] = []
            for item in reversed(items):
                data = json.loads(item)
                if data["type"] == "human":
                    memories.append(HumanMessage(content=data["content"]))
                elif data["type"] == "ai":
                    memories.append(AIMessage(content=data["content"]))
            return memories
        except Exception as exc:
            print(f"获取记忆失败: {exc}")
            return []

    def clear_memory(self) -> None:
        """删除当前会话的长期记忆。"""
        if not self.redis_client:
            return

        try:
            self.redis_client.delete(self.key)
            print(f"已清除会话 {self.session_id} 的记忆")
        except Exception as exc:
            print(f"清除记忆失败: {exc}")


current_thread_id: str | None = None


def chat_node(state: GraphState):
    """读取长期记忆，拼接上下文，生成回复，并把回复写回长期记忆。"""
    global current_thread_id

    thread_id = current_thread_id or "default"
    memory = LongTermMemory(session_id=thread_id)
    user_message = state["messages"][-1]

    if isinstance(user_message, HumanMessage):
        memory.save_memory("human", user_message.content)

    historical_messages = memory.get_memory(limit=10)
    all_messages = historical_messages + [user_message] if historical_messages else [user_message]

    print(f"使用 {len(all_messages)} 条消息作为上下文")
    response = llm.invoke(all_messages)
    print(f"AI 回复: {response.content}")

    memory.save_memory("ai", response.content)
    return {"messages": [response]}


builder = StateGraph(GraphState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

app = builder.compile(checkpointer=MemorySaver())


def show_memory(thread_id: str) -> None:
    """打印指定会话的历史记忆。"""
    memory = LongTermMemory(session_id=thread_id)
    messages = memory.get_memory(limit=20)

    print(f"\n=== 会话 '{thread_id}' 的记忆 ===")
    if not messages:
        print("无记录")
        return

    for index, message in enumerate(messages, 1):
        role = "用户" if isinstance(message, HumanMessage) else "助手"
        print(f"{role} {index}: {message.content}")


def delete_memory(thread_id: str) -> None:
    """删除指定会话的长期记忆。"""
    memory = LongTermMemory(session_id=thread_id)
    memory.clear_memory()


def test_long_term_memory() -> None:
    """用两个不同 thread_id 演示长期记忆的隔离效果。"""
    global current_thread_id

    print("开始测试长期记忆系统")

    print("\nAlice 第一次对话:")
    current_thread_id = "alice"
    app.invoke(
        {"messages": [HumanMessage(content="我是Alice，我喜欢读书")]},
        config={"configurable": {"thread_id": "alice"}},
    )

    print("Alice 第二次对话:")
    current_thread_id = "alice"
    app.invoke(
        {"messages": [HumanMessage(content="我刚才说喜欢什么？")]},
        config={"configurable": {"thread_id": "alice"}},
    )

    print("\nBob 第一次对话:")
    current_thread_id = "bob"
    app.invoke(
        {"messages": [HumanMessage(content="我是Bob，我喜欢运动")]},
        config={"configurable": {"thread_id": "bob"}},
    )

    print("Bob 第二次对话:")
    current_thread_id = "bob"
    app.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config={"configurable": {"thread_id": "bob"}},
    )

    show_memory("alice")
    show_memory("bob")

    print("\n清除 Alice 的记忆")
    delete_memory("alice")
    show_memory("alice")


if __name__ == "__main__":
    test_long_term_memory()
