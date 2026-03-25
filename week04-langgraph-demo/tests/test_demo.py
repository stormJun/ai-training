"""Basic tests for the LangGraph demo."""

from week04_langgraph_demo.analysis_agent import run_analysis_agent
from week04_langgraph_demo.host_agent import run_host_agent
from week04_langgraph_demo.stock_agent import run_stock_agent


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
