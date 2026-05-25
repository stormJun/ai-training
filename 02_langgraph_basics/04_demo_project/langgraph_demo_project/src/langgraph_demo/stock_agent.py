"""使用 LangGraph 实现的股票查询子代理。"""

from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import llm
from .models import AgentResponse, StockRecord
from .store import get_stock_by_identifier, load_records


class StockAgentState(TypedDict, total=False):
    """股票查询工作流在节点间传递的状态。"""

    query: str
    identifier: str | None
    stock: StockRecord | None
    response: AgentResponse


def extract_identifier(query: str) -> str | None:
    """从用户输入中提取股票代码或公司名称。"""

    # 先优先匹配 6 位股票代码，再回退到内置公司名匹配。
    match = re.search(r"\b\d{6}\b", query)
    if match:
        return match.group(0)

    for record in load_records():
        if record.name in query:
            return record.name
    return None


def parse_query(state: StockAgentState) -> StockAgentState:
    """解析用户问题。"""

    return {"identifier": extract_identifier(state["query"])}


def lookup_stock(state: StockAgentState) -> StockAgentState:
    """从本地数据仓库中查找股票数据。"""

    identifier = state.get("identifier")
    return {"stock": get_stock_by_identifier(identifier or "")}


def format_response(state: StockAgentState) -> StockAgentState:
    """组装标准化的股票查询响应。"""

    stock = state.get("stock")
    if not stock:
        response = AgentResponse(
            agent="stock_subagent",
            status="error",
            summary="未识别到股票代码或公司名称",
            detail="请直接提供 6 位股票代码，或使用内置公司名：宁德时代、贵州茅台、格力电器、云南白药。",
        )
        return {"response": response}

    summary = f"已找到 {stock.name} 的基础行情信息"
    detail = (
        f"{stock.name}（{stock.code}，{stock.sector}）当前示例收盘价为 {stock.close_price:.1f} 元，"
        f"近一段时间价格变动 {stock.price_change_pct:.1f}%，"
        f"收入增速 {stock.revenue_growth_pct:.1f}%，"
        f"市盈率 {stock.pe_ratio:.1f}，"
        f"波动率 {stock.volatility_pct:.1f}%。"
    )
    if llm.is_dashscope_enabled():
        try:
            summary, detail = llm.generate_stock_response(query=state["query"], stock=stock)
        except llm.LLMError:
            pass

    response = AgentResponse(
        agent="stock_subagent",
        summary=summary,
        detail=detail,
    )
    return {"response": response}


def build_stock_agent():
    """编译股票查询子代理的 LangGraph 工作流。"""

    graph = StateGraph(StockAgentState)
    graph.add_node("parse_query", parse_query)
    graph.add_node("lookup_stock", lookup_stock)
    graph.add_node("format_response", format_response)
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", "lookup_stock")
    graph.add_edge("lookup_stock", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()


STOCK_AGENT = build_stock_agent()


def run_stock_agent(query: str) -> AgentResponse:
    """执行股票查询子代理。"""

    result = STOCK_AGENT.invoke({"query": query})
    return result["response"]
