import importlib.util
from pathlib import Path

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT1 = PROJECT_DIR / "p28-A2A-LangGraph.py"
SCRIPT2 = PROJECT_DIR / "p28-A2A-LangGraph2.py"


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_search_tool_reports_missing_tavily_key(monkeypatch):
    module = load_module("p28_a2a_langgraph_search", SCRIPT1)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    result = module.search_tavily.invoke({"query": "测试搜索"})

    assert result["success"] is False
    assert "TAVILY_API_KEY" in result["error"]


def test_build_model_prefers_dashscope_compatible_settings(monkeypatch):
    module = load_module("p28_a2a_langgraph_model", SCRIPT1)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("TOOL_LLM_URL", raising=False)
    monkeypatch.delenv("TOOL_LLM_NAME", raising=False)

    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(module, "ChatOpenAI", FakeChatOpenAI)

    module.build_model()

    assert captured["model"] == "qwen-plus"
    assert captured["openai_api_key"] == "sk-dashscope-test"
    assert captured["openai_api_base"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_validate_runtime_configuration_allows_missing_tavily(monkeypatch):
    module = load_module("p28_a2a_langgraph_server", SCRIPT2)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("TOOL_LLM_URL", raising=False)
    monkeypatch.delenv("TOOL_LLM_NAME", raising=False)
    monkeypatch.delenv("model_source", raising=False)

    config = module.validate_runtime_configuration()

    assert config["search_enabled"] is False
    assert config["model_source"] == "openai"


def test_validate_runtime_configuration_requires_some_model_key(monkeypatch):
    module = load_module("p28_a2a_langgraph_server_missing", SCRIPT2)
    for key in [
        "TAVILY_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "API_KEY",
        "TOOL_LLM_URL",
        "TOOL_LLM_NAME",
        "model_source",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(module.MissingAPIKeyError):
        module.validate_runtime_configuration()
