"""
手动实现的摘要记忆（Summary Memory）- 基于 WeKnora 的精简版

核心逻辑：
1. 触发条件：token > maxTokens * 0.5
2. 定位当前轮次：从后往前找最后一个 user 消息
3. 贪心保留近期历史：从尾部保留，越近越重要
4. LLM 摘要旧消息：失败则用纯文本兜底
5. 组装结果：[system] + [summary] + [近期历史] + [当前轮次]

运行：
    cd 09_memory_patterns_basics
    source .venv/bin/activate
    export DASHSCOPE_API_KEY=your_key
    python p06-summaryMEM-manual.py
"""

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.utils import count_tokens_approximately
from typing import List, Optional
import os


# ============================================================================
# 核心类：MemoryConsolidator
# ============================================================================

class MemoryConsolidator:
    """
    记忆压缩器 - 基于 WeKnora 的精简实现

    两级防线：
    1. LLM 智能摘要（首选）
    2. 纯文本兜底（LLM 失败时）
    """

    def __init__(
        self,
        model,                    # LLM 模型
        max_tokens: int = 4000,   # 上下文窗口大小
        threshold: float = 0.5,   # 触发阈值（0.5 = 50%）
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.threshold = threshold

    def should_consolidate(self, current_tokens: int) -> bool:
        """
        是否应该触发压缩

        原理：当 token 占用超过上下文窗口的 50% 就触发
        留出安全余量，避免 LLM 被截断
        """
        if self.max_tokens <= 0:
            return False
        trigger_at = int(self.max_tokens * self.threshold)
        return current_tokens > trigger_at

    def consolidate(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        核心压缩逻辑

        流程：
        1. 定位当前轮次（最后一个 user 消息）
        2. 分割：history（旧消息） + tail（当前轮次）
        3. 贪心保留近期历史
        4. LLM 摘要旧消息
        5. 组装结果

        输入：[sys, u1, a1, u2, a2, u3, a3]
        输出：[sys, summary, u2, a2, u3, a3]
        """
        # 边界守卫：消息太少，不压缩
        if len(messages) <= 3:
            return messages

        system_msg = messages[0]

        # Step 1: 定位当前轮次的边界
        # 从后往前找最后一个 role="user" 的消息
        last_user_idx = 0
        for i in range(len(messages) - 1, 0, -1):
            if isinstance(messages[i], HumanMessage):
                last_user_idx = i
                break

        if last_user_idx <= 1:
            return messages

        # Step 2: 分割消息
        # history: system 之后、当前 user 之前 → 旧历史
        # tail: 当前 user + 后续 assistant/tool → 当前轮次（必须完整保留）
        history = messages[1:last_user_idx]
        tail = messages[last_user_idx:]

        if len(history) < 2:
            return messages

        # Step 3: 计算保留预算
        # 目标 = 窗口 × 50% × 60% = 窗口的 30%
        target_tokens = int(self.max_tokens * self.threshold * 0.6)

        # 扣除不可压缩的部分
        tail_tokens = count_tokens_approximately(tail)
        budget = (
            target_tokens
            - count_tokens_approximately([system_msg])
            - tail_tokens
            - 500  # 预留给 summary 消息自身
        )

        if budget <= 0:
            # 预算不足，保留 0 条历史
            to_keep = []
            to_consolidate = history
        else:
            # Step 4: 贪心保留近期历史
            keep_from_end = self._find_keep_boundary(history, budget)
            to_consolidate = history[:len(history) - keep_from_end]
            to_keep = history[len(history) - keep_from_end:]

        if len(to_consolidate) == 0:
            return messages

        # Step 5: LLM 摘要旧消息
        summary = self._summarize_messages(to_consolidate)

        # Step 6: 组装结果
        # [system prompt] → [Memory Summary] → [近期历史] → [当前轮次]
        summary_msg = SystemMessage(
            content=f"[Memory Summary - {len(to_consolidate)} earlier messages consolidated]\n\n{summary}"
        )

        result = [system_msg, summary_msg] + to_keep + tail

        print(f"✓ 压缩完成:")
        print(f"  - 压缩了 {len(to_consolidate)} 条旧消息")
        print(f"  - 保留了 {len(to_keep)} 条近期历史")
        print(f"  - 当前轮次 {len(tail)} 条消息完整保留")
        print(f"  - 总消息数: {len(messages)} → {len(result)}")

        return result

    def _find_keep_boundary(self, history: List[BaseMessage], budget: int) -> int:
        """
        贪心策略：从尾部保留近期历史

        原理：
        - 越近的对话越重要
        - assistant(tool_calls) + tool(results) 必须成组保留
        """
        tokens = 0
        keep_count = 0
        i = len(history) - 1

        while i >= 0:
            msg = history[i]
            msg_tokens = count_tokens_approximately([msg])

            # 特殊处理：tool 消息必须和前面的 assistant 成组保留
            if isinstance(msg, ToolMessage):
                # 找到连续的 tool 消息 + 对应的 assistant
                group_tokens = msg_tokens
                group_size = 1
                j = i - 1
                while j >= 0 and isinstance(history[j], ToolMessage):
                    group_tokens += count_tokens_approximately([history[j]])
                    group_size += 1
                    j -= 1
                if j >= 0 and isinstance(history[j], AIMessage):
                    group_tokens += count_tokens_approximately([history[j]])
                    group_size += 1

                if tokens + group_tokens > budget:
                    break
                tokens += group_tokens
                keep_count += group_size
                i -= group_size
            else:
                if tokens + msg_tokens > budget:
                    break
                tokens += msg_tokens
                keep_count += 1
                i -= 1

        return keep_count

    def _summarize_messages(self, messages: List[BaseMessage]) -> str:
        """
        用 LLM 生成摘要

        失败时回退到纯文本兜底
        """
        try:
            # 构建 prompt
            prompt = self._build_summary_prompt(messages)

            # 调用 LLM（低温，事实性摘要）
            response = self.model.invoke(
                prompt,
                temperature=0.3,
                max_tokens=1000,
            )

            return response.content
        except Exception as e:
            print(f"⚠️  LLM 摘要失败: {e}")
            print("使用纯文本兜底...")
            return self._raw_archive(messages)

    def _build_summary_prompt(self, messages: List[BaseMessage]) -> str:
        """
        构建摘要 prompt
        """
        # 构建对话历史文本
        history_text = ""
        for msg in messages:
            role = type(msg).__name__.replace("Message", "")
            content = str(msg.content)[:500]  # 截断长消息
            if isinstance(msg, AIMessage) and msg.tool_calls:
                tools = [tc["name"] for tc in msg.tool_calls]
                history_text += f"**{role}** [called tools: {', '.join(tools)}]: {content}\n"
            elif isinstance(msg, ToolMessage):
                history_text += f"**Tool [{msg.name}]**: {content}\n"
            else:
                history_text += f"**{role}**: {content}\n"

        return f"""请为以下对话历史生成简洁摘要，保留：

1. 关键事实和决策
2. 工具执行结果
3. 用户的原始意图
4. 遇到的错误及解决方案

对话历史：

{history_text}

摘要（压缩到原文 30% 以下）："""

    def _raw_archive(self, messages: List[BaseMessage]) -> str:
        """
        纯文本兜底（LLM 失败时）

        截断更激进（每条 200 字符）
        """
        archive = "Raw conversation archive:\n\n"
        for msg in messages:
            role = type(msg).__name__.replace("Message", "")
            content = str(msg.content)[:200]
            archive += f"- {role}: {content}\n"
        return archive


# ============================================================================
# 精简版工作流
# ============================================================================

def manage_context_window(
    messages: List[BaseMessage],
    consolidator: MemoryConsolidator,
    max_tokens: int = 4000,
) -> List[BaseMessage]:
    """
    上下文管理入口函数

    两级防线：
    1. LLM 智能摘要（Consolidator）
    2. 暴力截断兜底（可选）
    """
    # 1. 计算 token 数
    current_tokens = count_tokens_approximately(messages)

    # 2. 检查是否需要压缩
    if not consolidator.should_consolidate(current_tokens):
        print(f"Token 数: {current_tokens}/{max_tokens} - 未超过阈值")
        return messages

    print(f"Token 数: {current_tokens}/{max_tokens} - 超过阈值，触发压缩...")

    # 3. 执行压缩
    messages = consolidator.consolidate(messages)

    return messages


# ============================================================================
# 运行示例
# ============================================================================

if __name__ == "__main__":
    # 检查 API Key
    HAS_API_KEY = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")

    if HAS_API_KEY:
        # 配置真实模型
        if os.environ.get("DASHSCOPE_API_KEY"):
            from langchain_community.chat_models.tongyi import ChatTongyi
            model = ChatTongyi(model="qwen-max", temperature=0.7)
            MODEL_PROVIDER = "通义千问"
        else:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model="gpt-4o")
            MODEL_PROVIDER = "OpenAI"
    else:
        # 模拟模式：使用简单的响应生成
        print("=" * 60)
        print("⚠️  未检测到 API Key - 使用模拟模式")
        print("=" * 60)
        print("\n配置真实 API Key 可以看到 LLM 生成的摘要效果")
        print("  export DASHSCOPE_API_KEY=your_key")
        print("\n" + "=" * 60 + "\n")
        MODEL_PROVIDER = "模拟模式 (Mock)"

        # 创建一个简单的模拟模型
        class MockModel:
            def invoke(self, prompt, **kwargs):
                # 模拟 LLM 返回摘要
                class MockResponse:
                    content = "用户询问了个人喜好和天气情况。助手回答了相关问题，并提供了篮球故事和旅游建议。"
                return MockResponse()

        model = MockModel()

    print("=" * 60)
    print("手动实现的摘要记忆（Summary Memory）")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  - 模型: {MODEL_PROVIDER}")
    print(f"  - 上下文窗口: 4000 tokens")
    print(f"  - 触发阈值: 50% (2000 tokens)")
    print(f"  - 目标压缩: 30% (1200 tokens)")
    print("\n" + "=" * 60)

    # 创建压缩器（降低阈值用于演示）
    consolidator = MemoryConsolidator(
        model=model,
        max_tokens=200,   # 降低上下文窗口，更容易触发
        threshold=0.5,     # 50% 触发
    )

    # 构建对话历史
    messages = [
        SystemMessage(content="你是一个有帮助的AI助手。"),
    ]

    # 模拟多轮对话
    conversations = [
        ("你好！我叫小明，我喜欢打篮球。", "你好小明！很高兴认识你，篮球是一项很棒的运动！"),
        ("今天北京天气怎么样？", "北京今天天气晴朗，温度适宜，非常适合户外运动。"),
        ("你还记得我叫什么吗？", "你叫小明，你喜欢打篮球！"),
        ("我想去上海旅游，那边天气如何？", "上海今天天气也不错，适合旅游。"),
        ("给我讲一个篮球的故事。", "从前有个小男孩叫小明，他有一个篮球梦..."),
        ("你觉得我能成为职业球员吗？", "只要有热情和坚持，一切皆有可能！"),
        ("上海有什么好玩的景点？", "上海有很多著名景点，比如外滩、东方明珠..."),
    ]

    for i, (user_msg, ai_msg) in enumerate(conversations, 1):
        messages.append(HumanMessage(content=user_msg))
        messages.append(AIMessage(content=ai_msg))

        # 每轮检查是否需要压缩
        messages = manage_context_window(
            messages,
            consolidator,
            max_tokens=4000,
        )

    # 最终统计
    print("\n" + "=" * 60)
    print("最终统计")
    print("=" * 60)

    final_tokens = count_tokens_approximately(messages)
    print(f"总消息数: {len(messages)}")
    print(f"总 Token 数: {final_tokens}")

    # 检查是否有摘要
    summary_count = sum(1 for m in messages if "Memory Summary" in str(m.content))
    if summary_count > 0:
        print(f"✓ 生成了 {summary_count} 个摘要消息")

    print("\n消息结构:")
    for i, msg in enumerate(messages, 1):
        role = type(msg).__name__
        preview = str(msg.content)[:50] + "..." if len(str(msg.content)) > 50 else str(msg.content)
        print(f"  {i}. [{role}]: {preview}")

    print("\n" + "=" * 60)
    print("运行完成！")
    print("=" * 60)
