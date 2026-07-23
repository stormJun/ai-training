# -*- coding: utf-8 -*-
"""p14 supervisor 教程的机制测试：不调用真实 LLM，用 FakeChatModel 验证流程。"""
import importlib.util
from pathlib import Path

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.types import Command


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "p14-Langgraph-Supervisor.py"


def load_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeToolChatModel(GenericFakeChatModel):
    """GenericFakeChatModel 未实现 bind_tools；fake 返回固定消息，直接跳过绑定。"""

    def bind_tools(self, tools, **kwargs):
        return self


def ai_tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def make_calendar_agent(module):
    fake = FakeToolChatModel(
        messages=iter([
            ai_tool_call(
                "create_calendar_event",
                {
                    "title": "设计评审会",
                    "start_time": "2026-07-28T14:00:00",
                    "end_time": "2026-07-28T15:00:00",
                    "attendees": ["designteam@example.com"],
                },
                "call_cal_1",
            ),
            AIMessage(content="已创建日程：设计评审会，2026-07-28 14:00-15:00。"),
        ])
    )
    return module.create_react_agent(
        model=fake,
        tools=[module.create_calendar_event, module.get_available_time_slots],
        prompt=module.CALENDAR_AGENT_PROMPT,
        name="calendar_agent",
    )


def make_email_agent(module):
    fake = FakeToolChatModel(
        messages=iter([
            ai_tool_call(
                "send_email",
                {"to": ["designteam@example.com"], "subject": "评审提醒", "body": "请提前评审。"},
                "call_mail_1",
            ),
            AIMessage(content="已发送提醒邮件给设计团队。"),
        ])
    )
    return module.create_react_agent(
        model=fake,
        tools=[module.send_email],
        prompt=module.EMAIL_AGENT_PROMPT,
        name="email_agent",
    )


# ---------------------------------------------------------------------------
# 环境与工具函数
# ---------------------------------------------------------------------------


def test_resolve_dashscope_api_key_reads_candidate_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=sk-test-from-file\n", encoding="utf-8")

    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    module = load_module("p14_env_file")
    assert module.resolve_dashscope_api_key(env_files=[env_file]) == "sk-test-from-file"


def test_resolve_dashscope_api_key_rejects_placeholder_value(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=your_api_key_here\n", encoding="utf-8")

    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    module = load_module("p14_env_placeholder")
    try:
        module.resolve_dashscope_api_key(env_files=[env_file])
    except RuntimeError as exc:
        assert "DASHSCOPE_API_KEY" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("应拒绝占位 API Key")


def test_message_text_handles_string_and_blocks():
    module = load_module("p14_message_text")
    assert module.message_text(AIMessage(content="你好")) == "你好"
    blocks = [{"type": "text", "text": "前半"}, {"type": "text", "text": "后半"}]
    assert module.message_text(AIMessage(content=blocks)) == "前半后半"


def test_stub_tools_return_expected_strings():
    module = load_module("p14_stub_tools")
    result = module.create_calendar_event.invoke(
        {
            "title": "站会",
            "start_time": "2026-07-24T09:00:00",
            "end_time": "2026-07-24T09:30:00",
            "attendees": ["a@example.com", "b@example.com"],
        }
    )
    assert "站会" in result and "2 人" in result

    slots = module.get_available_time_slots.invoke(
        {"attendees": [], "date": "2026-07-24", "duration_minutes": 30}
    )
    assert slots == ["09:00", "14:00", "16:00"]


# ---------------------------------------------------------------------------
# supervisor 机制（fake model，无真实 LLM 调用）
# ---------------------------------------------------------------------------


def test_supervisor_delegates_to_both_subagents():
    module = load_module("p14_delegation")
    supervisor_fake = FakeToolChatModel(
        messages=iter([
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "schedule_event",
                        "args": {"request": "下周二下午2点设计评审会"},
                        "id": "call_sup_1",
                        "type": "tool_call",
                    },
                    {
                        "name": "manage_email",
                        "args": {"request": "给设计团队发评审提醒"},
                        "id": "call_sup_2",
                        "type": "tool_call",
                    },
                ],
            ),
            AIMessage(content="已安排评审会并发送提醒邮件。"),
        ])
    )
    supervisor = module.build_supervisor(
        supervisor_fake, make_calendar_agent(module), make_email_agent(module)
    )

    result = supervisor.invoke({"messages": [{"role": "user", "content": "安排评审会并发邮件"}]})

    tool_names = [m.name for m in result["messages"] if m.type == "tool"]
    assert "schedule_event" in tool_names
    assert "manage_email" in tool_names
    assert "评审会" in module.message_text(result["messages"][-1])


def test_hitl_interrupt_then_edit_resume():
    module = load_module("p14_hitl_edit")
    supervisor_fake = FakeToolChatModel(
        messages=iter([
            ai_tool_call("manage_email", {"request": "给设计团队发评审提醒"}, "call_hitl_1"),
            AIMessage(content="好的，已按修改后的要求发送邮件。"),
        ])
    )
    supervisor = module.build_hitl_supervisor(
        supervisor_fake, make_calendar_agent(module), make_email_agent(module)
    )
    config = {"configurable": {"thread_id": "test-hitl-edit"}}

    supervisor.invoke({"messages": [{"role": "user", "content": "发邮件提醒设计团队"}]}, config)

    snapshot = supervisor.get_state(config)
    pending = [item for task in snapshot.tasks for item in task.interrupts]
    assert len(pending) == 1
    assert pending[0].value["type"] == "email_approval"

    final_state = supervisor.invoke(
        Command(resume={"action": "edit", "edited_request": "发正式邮件，周五前完成评审"}),
        config,
    )
    assert "修改后" in module.message_text(final_state["messages"][-1])


def test_hitl_reject_skips_subagent():
    module = load_module("p14_hitl_reject")
    supervisor_fake = FakeToolChatModel(
        messages=iter([
            ai_tool_call("manage_email", {"request": "给设计团队发评审提醒"}, "call_hitl_2"),
            AIMessage(content="好的，已取消发送。"),
        ])
    )
    supervisor = module.build_hitl_supervisor(
        supervisor_fake, make_calendar_agent(module), make_email_agent(module)
    )
    config = {"configurable": {"thread_id": "test-hitl-reject"}}

    supervisor.invoke({"messages": [{"role": "user", "content": "发邮件提醒设计团队"}]}, config)
    final_state = supervisor.invoke(Command(resume={"action": "reject"}), config)

    tool_messages = [m for m in final_state["messages"] if m.type == "tool"]
    assert "拒绝" in tool_messages[-1].content
