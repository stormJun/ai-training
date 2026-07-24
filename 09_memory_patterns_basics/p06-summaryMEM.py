"""
摘要记忆（Summary Memory）示例

功能：
- 当 token 数超过阈值时，自动将旧消息压缩成摘要
- 用 [Memory Summary] 替换旧消息，保留系统提示 + 当前轮次 + 部分近期历史

依赖：
- langmem: 记忆管理库
- langgraph: 工作流框架
- langchain-openai 或 langchain-community

运行：
    cd 09_memory_patterns_basics
    uv sync
    source .venv/bin/activate
    export DASHSCOPE_API_KEY=your_key  # 或 export OPENAI_API_KEY=your_key
    python p06-summaryMEM.py
"""

from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from typing import Any
import os

# ============ 配置模型 ============
import os

# 检查 API Key
if os.environ.get("DASHSCOPE_API_KEY"):
    # 方式1: 使用通义千问
    from langchain_community.chat_models.tongyi import ChatTongyi
    model = ChatTongyi(
        model="qwen-max",
        temperature=0.7,
        streaming=True
    )
    MODEL_PROVIDER = "通义千问"
elif os.environ.get("OPENAI_API_KEY"):
    # 方式2: 使用 OpenAI
    from langchain_openai import ChatOpenAI
    model = ChatOpenAI(model="gpt-4o")
    MODEL_PROVIDER = "OpenAI"
else:
    print("=" * 60)
    print("⚠️  未检测到 API Key")
    print("=" * 60)
    print("\n请配置环境变量后再运行:")
    print("  方式1 (通义千问): export DASHSCOPE_API_KEY=your_key")
    print("  方式2 (OpenAI):   export OPENAI_API_KEY=your_key")
    print("\n示例:")
    print("  export DASHSCOPE_API_KEY=sk-xxxxx")
    print("  python p06-summaryMEM.py")
    print("=" * 60)
    exit(0)

# ============ 摘要记忆节点配置 ============
# 当 token 数超过 max_tokens 时，自动触发摘要
summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,  # token 计数器
    model=model,                                # 用于生成摘要的模型
    max_tokens=384,                             # token 阈值（超过此值触发摘要）
    max_summary_tokens=128,                     # 摘要最大 token 数
    output_messages_key="messages",             # 输出消息的 key
)

# ============ 定义状态 ============
class State(MessagesState):
    # 添加 context 字段，用于跟踪之前的摘要信息
    context: dict[str, Any] = {}

# ============ 创建简单工作流 ============
def call_model(state: State):
    """调用模型"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

# 创建工作流图
workflow = StateGraph(State)

# 添加节点
workflow.add_node("summarize", summarization_node)  # 摘要节点
workflow.add_node("agent", call_model)              # 模型调用节点

# 定义边
workflow.add_edge(START, "summarize")
workflow.add_edge("summarize", "agent")
workflow.add_edge("agent", END)

# 编译图
checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# ============ 运行示例 ============
if __name__ == "__main__":
    print("=" * 60)
    print("摘要记忆（Summary Memory）示例")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  - 模型提供商: {MODEL_PROVIDER}")
    print(f"  - Token 阈值: 384")
    print(f"  - 摘要最大 Token: 128")
    print("\n工作流程:")
    print("  START → summarize → agent → END")
    print("  (在 summarize 节点检测 token 数，超过阈值则生成摘要)")
    print("\n" + "=" * 60)

    # 配置：指定 thread_id 用于会话隔离
    config = {"configurable": {"thread_id": "demo-session-001"}}

    # 对话历史
    conversations = [
        "你好！我叫小明，我喜欢打篮球。",
        "今天北京天气怎么样？",
        "你还记得我叫什么名字吗？我喜欢什么？",
        "我想去上海旅游，那边天气如何？",
        "给我讲一个有趣的故事，关于一个小男孩和他的篮球梦。",
        "你觉得我适合当职业篮球运动员吗？",
        "上海有什么好玩的景点推荐吗？",
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"\n[第 {i} 轮对话]")
        print(f"用户: {user_input}")

        # 调用图
        result = graph.invoke(
            {"messages": [("user", user_input)]},
            config=config
        )

        # 获取最后一条助手消息
        last_message = result["messages"][-1]
        print(f"助手: {last_message.content}")

        # 显示当前 token 数
        current_messages = result["messages"]
        token_count = count_tokens_approximately(current_messages)
        print(f"当前 Token 数: {token_count}")

        # 如果触发过摘要，会有特殊的 system message
        if any("Memory Summary" in str(msg.content) or "summary" in str(type(msg)).lower()
               for msg in current_messages):
            print("✓ 已触发摘要压缩")

    # 最终状态总结
    print("\n" + "=" * 60)
    print("会话总结")
    print("=" * 60)

    final_state = graph.get_state(config)
    if final_state and 'messages' in final_state.values:
        messages = final_state.values['messages']
        token_count = count_tokens_approximately(messages)

        print(f"总消息数: {len(messages)}")
        print(f"总 Token 数: {token_count}")
        print(f"\n消息历史 (最近 10 条):")
        for i, msg in enumerate(messages[-10:], 1):
            msg_type = type(msg).__name__
            content_preview = str(msg.content)[:60] + "..." if len(str(msg.content)) > 60 else str(msg.content)
            print(f"  {i}. [{msg_type}]: {content_preview}")

        # 检查是否有摘要消息
        summary_count = sum(1 for msg in messages if "summary" in str(type(msg)).lower()
                           or "Memory Summary" in str(msg.content))
        if summary_count > 0:
            print(f"\n✓ 共生成了 {summary_count} 个摘要消息")

    print("\n" + "=" * 60)
    print("运行完成！")
    print("=" * 60)
    print("\n提示:")
    print("  - 摘要记忆会在 token 数超过阈值时自动触发")
    print("  - 旧消息会被压缩成摘要，保留关键信息")
    print("  - 适用于长对话场景，可以控制上下文大小")
    print("  - 配置真实 API Key 可以看到真实的摘要效果")
