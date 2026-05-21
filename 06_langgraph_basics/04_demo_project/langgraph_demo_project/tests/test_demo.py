"""Basic tests for the LangGraph demo."""

import importlib

import pytest

from langgraph_demo.analysis_agent import run_analysis_agent
from langgraph_demo.host_agent import run_host_agent
from langgraph_demo.stock_agent import run_stock_agent


def test_stock_agent_returns_company_info() -> None:
    response = run_stock_agent("300750 是什么公司？")
    assert response.status == "completed"
    assert "宁德时代" in response.detail


def test_analysis_agent_compares_multiple_stocks() -> None:
    response = run_analysis_agent("对比一下 300750 和 600519，哪家更值得关注？")
    assert response.status == "completed"
    assert "排序结果" in response.detail


def test_host_agent_routes_directly() -> None:
    result = run_host_agent("分析 300750、600519、000651 的基本面和价格表现", mode="direct")
    assert "Host Agent 路由结果：analysis" in result
    assert "Analysis Subagent" in result


def test_stock_agent_uses_dashscope_when_api_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    llm = importlib.import_module("langgraph_demo.llm")
    stock_agent = importlib.import_module("langgraph_demo.stock_agent")

    def fake_generate_stock_response(*, query: str, stock) -> tuple[str, str]:
        assert query == "300750 是什么公司？"
        assert stock.code == "300750"
        return ("模型版股票摘要", "模型版股票详情")

    monkeypatch.setattr(llm, "generate_stock_response", fake_generate_stock_response)

    response = stock_agent.run_stock_agent("300750 是什么公司？")

    assert response.summary == "模型版股票摘要"
    assert response.detail == "模型版股票详情"


def test_analysis_agent_falls_back_when_dashscope_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    llm = importlib.import_module("langgraph_demo.llm")
    analysis_agent = importlib.import_module("langgraph_demo.analysis_agent")

    def fake_generate_analysis_response(*, query: str, plan: str, ranking) -> tuple[str, str]:
        raise llm.LLMConfigurationError("mock llm failure")

    monkeypatch.setattr(llm, "generate_analysis_response", fake_generate_analysis_response)

    response = analysis_agent.run_analysis_agent("对比一下 300750 和 600519，哪家更值得关注？")

    assert response.status == "completed"
    assert "排序结果" in response.detail
