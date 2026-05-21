# %% [markdown]
# ## 记忆
#
# Langgraph 的记忆分为短期记忆和长期记忆。
#
# 短期记忆是针对单个会话的，在会话中随时可以被调用。每次调用完图之后，会自动更新，然后在每个超步开始的时候读取。
#
# 长期记忆是跨会话线程的，可以在任何时间与任何线程中调用。

# %%
# 修复后的简化长期记忆管理

from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import HumanMessage, AIMessage
import json
import redis
from langchain_community.chat_models import ChatTongyi


# 状态定义
class GraphState(TypedDict):
    messages: Annotated[Sequence, add_messages]


# 大模型
llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True
)


# 长期记忆管理类
class LongTermMemory:
    def __init__(self, session_id: str, url: str = "redis://localhost:6379/0"):
        self.session_id = session_id
        self.key = f"memory:{session_id}"
        try:
            self.redis_client = redis.from_url(url)
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self.redis_client = None

    def save_memory(self, memory_type: str, content: str):
        """保存记忆"""
        if not self.redis_client:
            return
        try:
            memory_data = {
                "type": memory_type,
                "content": content
            }
            self.redis_client.lpush(self.key, json.dumps(memory_data))
            print(f"记忆已保存: {content[:30]}...")
        except Exception as e:
            print(f"保存记忆失败: {e}")

    def get_memory(self, limit: int = 10) -> list:
        """通过ID获取记忆"""
        if not self.redis_client:
            return []
        try:
            items = self.redis_client.lrange(self.key, 0, limit-1)
            memories = []
            for item in reversed(items):
                data = json.loads(item)
                if data["type"] == "human":
                    memories.append(HumanMessage(content=data["content"]))
                elif data["type"] == "ai":
                    memories.append(AIMessage(content=data["content"]))
            return memories
        except Exception as e:
            print(f"获取记忆失败: {e}")
            return []

    def clear_memory(self):
        """清除记忆"""
        if not self.redis_client:
            return
        try:
            self.redis_client.delete(self.key)
            print(f"已清除会话 {self.session_id} 的记忆")
        except Exception as e:
            print(f"清除记忆失败: {e}")


# 全局变量存储当前thread_id
current_thread_id = None

def chat_node(state: GraphState):
    global current_thread_id
    thread_id = current_thread_id or "default"
    
    # 初始化长期记忆
    memory = LongTermMemory(session_id=thread_id)
    
    # 获取当前用户消息
    user_message = state["messages"][-1]
    
    if isinstance(user_message, HumanMessage):
        # 保存用户消息到长期记忆
        memory.save_memory("human", user_message.content)
    
    # 获取历史记忆
    historical_messages = memory.get_memory(limit=10)
    
    # 构建对话上下文
    if historical_messages:
        all_messages = historical_messages + [user_message]
    else:
        all_messages = [user_message]
    
    print(f"使用 {len(all_messages)} 条消息作为上下文")
    
    # 调用模型生成回复
    response = llm.invoke(all_messages)
    print(f"AI回复: {response.content}")
    
    # 保存AI回复到长期记忆
    memory.save_memory("ai", response.content)
    
    return {"messages": [response]}


# 构建图
builder = StateGraph(GraphState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

from langgraph.checkpoint.memory import MemorySaver
app = builder.compile(checkpointer=MemorySaver())


# 辅助函数
def show_memory(thread_id: str):
    """显示指定ID的记忆"""
    memory = LongTermMemory(session_id=thread_id)
    messages = memory.get_memory(limit=20)
    
    print(f"\n=== 会话 '{thread_id}' 的记忆 ===")
    if not messages:
        print("无记录")
    else:
        for i, msg in enumerate(messages, 1):
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            print(f"{role} {i}: {msg.content}")


def delete_memory(thread_id: str):
    """删除指定ID的记忆"""
    memory = LongTermMemory(session_id=thread_id)
    memory.clear_memory()


# 测试长期记忆
def test_long_term_memory():
    global current_thread_id
    
    print("开始测试长期记忆系统")
    
    # Alice 的对话
    print("\nAlice 第一次对话:")
    current_thread_id = "alice"
    app.invoke(
        {"messages": [HumanMessage(content="我是Alice，我喜欢读书")]},
        config={"configurable": {"thread_id": "alice"}}
    )
    
    print("Alice 第二次对话:")
    current_thread_id = "alice"
    app.invoke(
        {"messages": [HumanMessage(content="我刚才说喜欢什么？")]},
        config={"configurable": {"thread_id": "alice"}}
    )
    
    # Bob 的对话
    print("\nBob 第一次对话:")
    current_thread_id = "bob"
    app.invoke(
        {"messages": [HumanMessage(content="我是Bob，我喜欢运动")]},
        config={"configurable": {"thread_id": "bob"}}
    )
    
    print("Bob 第二次对话:")
    current_thread_id = "bob"
    app.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config={"configurable": {"thread_id": "bob"}}
    )
    
    # 显示记忆
    show_memory("alice")
    show_memory("bob")
    
    # 清除Alice的记忆
    print("\n清除Alice的记忆")
    delete_memory("alice")
    show_memory("alice")


if __name__ == "__main__":
    test_long_term_memory()
