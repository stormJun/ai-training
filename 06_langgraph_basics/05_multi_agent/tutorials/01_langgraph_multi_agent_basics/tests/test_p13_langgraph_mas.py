import importlib.util
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "p13-Langgraph-MAS.py"


def load_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_dashscope_api_key_reads_candidate_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=sk-test-from-file\n", encoding="utf-8")

    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    module = load_module("p13_langgraph_mas_env")

    assert module.resolve_dashscope_api_key(env_files=[env_file]) == "sk-test-from-file"


def test_resolve_dashscope_api_key_rejects_placeholder_value(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=your_api_key_here\n", encoding="utf-8")

    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    module = load_module("p13_langgraph_mas_placeholder")

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        module.resolve_dashscope_api_key(env_files=[env_file])


def test_build_llm_uses_chattongyi(monkeypatch):
    module = load_module("p13_langgraph_mas_llm")

    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-direct")

    captured = {}

    class FakeChatTongyi:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(module, "ChatTongyi", FakeChatTongyi)

    module.build_llm()

    assert captured["dashscope_api_key"] == "sk-test-direct"
    assert captured["model"] == "qwen-plus"
    assert captured["temperature"] == 0.5


def test_build_handoff_messages_keeps_only_last_ai_message():
    module = load_module("p13_langgraph_mas_handoff")

    booking_tool_message = ToolMessage(
        content="已成功预订从 BOS 到 JFK 的航班。",
        tool_call_id="call_flight_1",
        name="book_flight",
    )
    last_ai_message = AIMessage(
        content="需要转给酒店助理",
        tool_calls=[
            {
                "name": "transfer_to_hotel_assistant",
                "args": {},
                "id": "call_transfer_1",
                "type": "tool_call",
            }
        ],
    )
    messages = [
        HumanMessage(content="帮我订机票和酒店"),
        booking_tool_message,
        last_ai_message,
    ]

    handoff_messages = module.build_handoff_messages(
        messages=messages,
        tool_call_id="call_transfer_1",
        agent_name="hotel_assistant",
    )

    assert handoff_messages[0] is last_ai_message
    assert len(handoff_messages) == 2
    assert isinstance(handoff_messages[1], ToolMessage)
    assert handoff_messages[1].tool_call_id == "call_transfer_1"
    assert "已完成事项" in handoff_messages[1].content
    assert "已成功预订从 BOS 到 JFK 的航班。" in handoff_messages[1].content
    assert "不要重复处理已完成事项" in handoff_messages[1].content


def test_bind_model_with_tools_disables_parallel_tool_calls():
    module = load_module("p13_langgraph_mas_bind")

    captured = {}

    class FakeModel:
        def bind_tools(self, tools, **kwargs):
            captured["tools"] = tools
            captured.update(kwargs)
            return "bound-model"

    bound = module.bind_model_with_tools(FakeModel(), tools=["tool-a", "tool-b"])

    assert bound == "bound-model"
    assert captured["tools"] == ["tool-a", "tool-b"]
    assert captured["parallel_tool_calls"] is False
