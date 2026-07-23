# -*- coding: utf-8 -*-
"""
Supervisor（监督者）模式的个人助理多智能体系统。

系统包含一个中央 supervisor（主管）智能体和两个包装成工具的子智能体：
- 日历智能体 calendar_agent：解析自然语言日程请求、查询空闲时段、创建日程；
- 邮件智能体 email_agent：根据自然语言撰写并发送邮件。

与 p13（handoff 对等转接）不同，本示例中所有路由决策都集中在 supervisor：
子智能体完成任务后把结果返回给 supervisor，由 supervisor 汇总后回复用户。

对应官方教程：Build a personal assistant with subagents
https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant

说明：官方教程基于 LangChain 1.0（langchain.agents.create_agent）。
本仓库当前环境为 langchain 0.3 + langgraph 0.6，因此用
langgraph.prebuilt.create_react_agent 实现同一模式，概念一一对应。
"""

import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # 仓库根目录 ai-training/
DEFAULT_ENV_FILES = [
    SCRIPT_DIR / ".env",
    PROJECT_ROOT / "01_langchain_basics/.env",
    PROJECT_ROOT / ".env",
]
PLACEHOLDER_API_KEYS = {
    "",
    "your_api_key_here",
    "your_dashscope_api_key_here",
    "your-dashscope-api-key",
    "your_api_key",
    "your-api-key",
    "your-api-key-here",
    "your_openai_api_key_here",
    "your_key_here",
    "your_real_api_key_here",
    "your_dashscope_api_key",
    "your key here",
    "replace_me",
    "replace-with-your-key",
    "your_api_here",
}


def ensure_dependencies() -> None:
    """在当前 Python 环境中检查并安装示例所需依赖。"""
    try:
        import dotenv  # noqa: F401
        import langchain_community  # noqa: F401
        import langgraph  # noqa: F401

        print("依赖已安装，跳过安装步骤。")
    except ImportError:
        print(f"正在为当前解释器 ({sys.executable}) 安装依赖，这可能需要几分钟。")
        packages = [
            "langchain",
            "langchain-community",
            "langgraph",
            "python-dotenv",
            "langchain-core",
        ]
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
        print("依赖安装完成。")


ensure_dependencies()

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import convert_to_messages
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt


def is_placeholder_api_key(value: str | None) -> bool:
    """判断 API Key 是否为空或明显占位值。"""
    if value is None:
        return True

    normalized = value.strip()
    if not normalized:
        return True

    return normalized.lower() in PLACEHOLDER_API_KEYS


def load_candidate_env_files(env_files: list[Path] | None = None) -> None:
    """按顺序加载候选 .env 文件，但不覆盖已有环境变量。"""
    for env_file in env_files or DEFAULT_ENV_FILES:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)


def resolve_dashscope_api_key(env_files: list[Path] | None = None) -> str:
    """解析当前脚本运行所需的 DashScope API Key。"""
    load_candidate_env_files(env_files)

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if is_placeholder_api_key(api_key):
        searched = "\n".join(f"- {path}" for path in (env_files or DEFAULT_ENV_FILES))
        raise RuntimeError(
            "未找到可用的 DASHSCOPE_API_KEY。请先设置环境变量，或在以下 .env 文件之一中配置真实密钥：\n"
            f"{searched}"
        )

    return api_key.strip()


def build_llm() -> ChatTongyi:
    """构建与当前环境兼容的 Qwen 聊天模型。"""
    return ChatTongyi(
        model="qwen-plus",
        dashscope_api_key=resolve_dashscope_api_key(),
        temperature=0.5,
    )


def message_text(message) -> str:
    """从消息对象中提取纯文本内容（兼容字符串与 content block 列表）。"""
    content = message.content
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


# ============================================================================
# 第 1 步：定义底层 API 工具（本示例使用桩实现，真实场景下对接 Google 日历、
# SendGrid 等真实 API）
# ============================================================================


@tool
def create_calendar_event(
    title: str,
    start_time: str,  # ISO 格式: "2026-07-24T14:00:00"
    end_time: str,  # ISO 格式: "2026-07-24T15:00:00"
    attendees: list[str],  # 邮箱地址
    location: str = "",
) -> str:
    """创建日程事件。要求严格的 ISO 日期时间格式。"""
    # 桩实现：实际项目中这里调用 Google Calendar / Outlook API
    return f"日程已创建：{title}，{start_time} 至 {end_time}，参会人 {len(attendees)} 人"


@tool
def send_email(
    to: list[str],  # 邮箱地址
    subject: str,
    body: str,
    cc: list[str] = [],
) -> str:
    """通过邮件 API 发送邮件。要求格式正确的邮箱地址。"""
    # 桩实现：实际项目中这里调用 SendGrid / Gmail API
    return f"邮件已发送给 {', '.join(to)}，主题：{subject}"


@tool
def get_available_time_slots(
    attendees: list[str],
    date: str,  # ISO 格式: "2026-07-24"
    duration_minutes: int,
) -> list[str]:
    """查询指定日期参会人的共同空闲时段。"""
    # 桩实现：实际项目中这里查询日历 API
    return ["09:00", "14:00", "16:00"]


# ============================================================================
# 第 2 步：创建专业化子智能体
#
# 每个子智能体只关注一个领域：自己的提示词 + 自己的底层工具。
# 注意提示词的最后一句——子智能体必须把执行结果写进最终回复，
# 因为 supervisor 只能看到它的最终回复（常见踩坑点）。
# ============================================================================

CALENDAR_AGENT_PROMPT = (
    "你是一位日程安排助理。"
    "请把自然语言的时间表达（例如“下周二下午2点”）解析为 ISO 日期时间格式。"
    "必要时先调用 get_available_time_slots 查询空闲时段；"
    "如果没有合适的时段，直接在回复中说明无法安排。"
    "使用 create_calendar_event 创建日程。"
    "在你的最终回复中，必须完整确认已安排的内容（主题、时间、参会人）。"
)

EMAIL_AGENT_PROMPT = (
    "你是一位邮件助理。"
    "根据自然语言请求撰写专业的邮件：提取收件人信息，拟定合适的主题和正文。"
    "使用 send_email 发送邮件。"
    "在你的最终回复中，必须完整确认已发送的内容（收件人、主题）。"
)


def build_subagents(llm: ChatTongyi):
    """构建日历子智能体和邮件子智能体。"""
    calendar_agent = create_react_agent(
        model=llm,
        tools=[create_calendar_event, get_available_time_slots],
        prompt=CALENDAR_AGENT_PROMPT,
        name="calendar_agent",
    )

    email_agent = create_react_agent(
        model=llm,
        tools=[send_email],
        prompt=EMAIL_AGENT_PROMPT,
        name="email_agent",
    )

    return calendar_agent, email_agent


# ============================================================================
# 第 3 步：把子智能体包装成工具
#
# 这是 supervisor 模式的关键架构步骤：supervisor 看到的是
# schedule_event / manage_email 这样的“高层能力”，而不是
# create_calendar_event 这样的底层 API。工具的 docstring 就是
# supervisor 的路由依据，务必写清楚“什么时候该用这个工具”。
# ============================================================================


def make_schedule_event_tool(calendar_agent):
    """把日历子智能体包装成 supervisor 可调用的工具。"""

    @tool
    def schedule_event(request: str) -> str:
        """用自然语言安排日程。

        当用户想要创建、修改或查询日程时使用本工具。
        可处理日期时间解析、空闲时段查询和日程创建。

        输入：自然语言日程请求（例如“下周二下午2点和设计团队开会”）。
        """
        print(f"\n[委派] supervisor → calendar_agent：{request}")
        result = calendar_agent.invoke({"messages": [{"role": "user", "content": request}]})
        summary = message_text(result["messages"][-1])
        print(f"[回报] calendar_agent → supervisor：{summary}")
        return summary

    return schedule_event


def make_manage_email_tool(email_agent):
    """把邮件子智能体包装成 supervisor 可调用的工具。"""

    @tool
    def manage_email(request: str) -> str:
        """用自然语言发送邮件。

        当用户想要发送通知、提醒或任何邮件沟通时使用本工具。
        可处理收件人提取、主题生成和邮件撰写。

        输入：自然语言邮件请求（例如“给他们发一封会议提醒邮件”）。
        """
        print(f"\n[委派] supervisor → email_agent：{request}")
        result = email_agent.invoke({"messages": [{"role": "user", "content": request}]})
        summary = message_text(result["messages"][-1])
        print(f"[回报] email_agent → supervisor：{summary}")
        return summary

    return manage_email


# ============================================================================
# 第 4 步：创建 supervisor 智能体
#
# supervisor 只做“领域级”的路由决策（该找日程专家还是邮件专家），
# 不关心底层 API 的细节。多个子任务可以并行委派。
# ============================================================================

SUPERVISOR_PROMPT = (
    "你是一位得力的个人助理主管，负责协调两位专家："
    "日程专家（schedule_event）和邮件专家（manage_email）。"
    "请把用户请求拆解为合适的工具调用并协调结果；"
    "当请求涉及多个领域时，按需依次或并行调用多个工具；"
    "最后汇总各专家的结果，用中文给出连贯的回复。"
)


def build_supervisor(llm: ChatTongyi, calendar_agent, email_agent):
    """构建不带审批的基础版 supervisor。"""
    return create_react_agent(
        model=llm,
        tools=[
            make_schedule_event_tool(calendar_agent),
            make_manage_email_tool(email_agent),
        ],
        prompt=SUPERVISOR_PROMPT,
        name="personal_assistant_supervisor",
    )


def build_hitl_supervisor(llm: ChatTongyi, calendar_agent, email_agent):
    """构建带人工审批（human-in-the-loop）的 supervisor。

    与官方教程的对比：官方在 LangChain 1.0 中用 HumanInTheLoopMiddleware
    拦截子智能体内部的底层工具（send_email 等）。当前环境为 langgraph 0.6，
    这里用等价的 interrupt() 在“委派边界”上实现审批：
    supervisor 决定委派后、子智能体真正执行前，先暂停等待人工决策。

    审批决策格式（Command(resume=...) 的取值）：
    - {"action": "approve"}                        批准，按原请求执行
    - {"action": "edit", "edited_request": "..."}  修改委派请求后执行
    - {"action": "reject"}                         拒绝，子智能体不会执行
    """

    def approve_or_adjust(kind: str, request: str) -> str | None:
        """发起审批中断；返回最终要执行的请求文本，拒绝时返回 None。"""
        decision = interrupt(
            {
                "type": f"{kind}_approval",
                "request": request,
                "说明": "批准后将委派子智能体执行；可批准(approve)、修改(edit)或拒绝(reject)。",
            }
        )
        action = decision.get("action") if isinstance(decision, dict) else "approve"
        if action == "reject":
            return None
        if action == "edit" and decision.get("edited_request"):
            return decision["edited_request"]
        return request

    @tool
    def schedule_event(request: str) -> str:
        """用自然语言安排日程（执行前需要人工审批）。

        当用户想要创建、修改或查询日程时使用本工具。
        输入：自然语言日程请求。
        """
        final_request = approve_or_adjust("calendar", request)
        if final_request is None:
            return "用户拒绝了该日程请求，未创建任何日程。"
        print(f"\n[委派] supervisor → calendar_agent：{final_request}")
        result = calendar_agent.invoke({"messages": [{"role": "user", "content": final_request}]})
        summary = message_text(result["messages"][-1])
        print(f"[回报] calendar_agent → supervisor：{summary}")
        return summary

    @tool
    def manage_email(request: str) -> str:
        """用自然语言发送邮件（执行前需要人工审批）。

        当用户想要发送通知、提醒或任何邮件沟通时使用本工具。
        输入：自然语言邮件请求。
        """
        final_request = approve_or_adjust("email", request)
        if final_request is None:
            return "用户拒绝了该邮件请求，未发送任何邮件。"
        print(f"\n[委派] supervisor → email_agent：{final_request}")
        result = email_agent.invoke({"messages": [{"role": "user", "content": final_request}]})
        summary = message_text(result["messages"][-1])
        print(f"[回报] email_agent → supervisor：{summary}")
        return summary

    # 注意：checkpointer 只加在顶层 supervisor 上。
    # 子智能体在工具函数内部被调用，复用顶层图的检查点即可。
    return create_react_agent(
        model=llm,
        tools=[schedule_event, manage_email],
        prompt=SUPERVISOR_PROMPT,
        name="personal_assistant_supervisor_hitl",
        checkpointer=InMemorySaver(),
    )


# ============================================================================
# 第 5 步：运行 supervisor
# ============================================================================


def pretty_print_update(update) -> None:
    """打印 stream_mode='updates' 产生的更新块（每个节点的最后一条消息）。"""
    for node_name, node_update in update.items():
        messages = (node_update or {}).get("messages")
        if not messages:
            continue
        message = convert_to_messages(messages)[-1]
        print(f"--- 节点 {node_name} ---")
        print(message.pretty_repr(html=False))
        print()


def demo_supervisor_basic(llm: ChatTongyi) -> None:
    """演示 1：基础 supervisor，分别处理单领域和跨领域请求。"""
    calendar_agent, email_agent = build_subagents(llm)
    supervisor = build_supervisor(llm, calendar_agent, email_agent)

    print("\n" + "=" * 70)
    print("演示 1-A：单领域请求（只涉及日程）")
    print("=" * 70)
    query = "帮我安排明天上午9点的团队站会，时长30分钟。"
    print(f"用户：{query}\n")
    for chunk in supervisor.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="updates",
    ):
        pretty_print_update(chunk)

    print("\n" + "=" * 70)
    print("演示 1-B：跨领域请求（日程 + 邮件，supervisor 协调两位专家）")
    print("=" * 70)
    query = (
        "下周二下午2点帮我安排一个和设计团队的评审会，时长1小时；"
        "然后给设计团队发一封邮件，提醒他们提前评审新版设计稿。"
    )
    print(f"用户：{query}\n")
    for chunk in supervisor.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="updates",
    ):
        pretty_print_update(chunk)


def demo_human_in_the_loop(llm: ChatTongyi) -> None:
    """演示 2：带人工审批的 supervisor。

    流程：发起请求 → supervisor 决定委派邮件专家 → 触发中断等待审批 →
    人工选择“修改后批准”（edit）→ 子智能体按修改后的请求执行 →
    supervisor 汇总回复。
    """
    calendar_agent, email_agent = build_subagents(llm)
    supervisor = build_hitl_supervisor(llm, calendar_agent, email_agent)

    config = {"configurable": {"thread_id": "p14-hitl-demo"}}
    query = "给设计团队发一封邮件，提醒他们评审新版设计稿。"

    print("\n" + "=" * 70)
    print("演示 2：人工审批（human-in-the-loop）")
    print("=" * 70)
    print(f"用户：{query}\n")

    # 第一次运行：在委派边界触发 interrupt，图暂停
    supervisor.invoke({"messages": [{"role": "user", "content": query}]}, config)

    snapshot = supervisor.get_state(config)
    pending = [item for task in snapshot.tasks for item in task.interrupts]
    for item in pending:
        print(f"[中断] 等待人工审批：{item.value}\n")

    if not pending:
        print("未触发审批中断，流程已直接完成。")
        return

    # 人工决策：修改委派请求后批准（edit）。
    # 也可以换成 {"action": "approve"} 直接批准，或 {"action": "reject"} 拒绝。
    resume_value = {
        "action": "edit",
        "edited_request": (
            "给设计团队（designteam@example.com）发一封正式邮件，"
            "提醒他们在本周五下班前完成新版设计稿的评审并反馈意见。"
        ),
    }
    print(f"[人工决策] {resume_value}\n")

    final_state = supervisor.invoke(Command(resume=resume_value), config)
    print("--- 最终回复 ---")
    print(message_text(final_state["messages"][-1]))


def main() -> int:
    """依次执行 supervisor 基础演示和人工审批演示。"""
    try:
        llm = build_llm()
    except RuntimeError as exc:
        print(exc)
        return 1

    demo_supervisor_basic(llm)
    demo_human_in_the_loop(llm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
