"""Stock subagent implemented with LangGraph."""

from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .models import AgentResponse, StockRecord
from .store import get_stock_by_identifier, load_records


class StockAgentState(TypedDict, total=False):
    """State carried inside the stock query graph."""

    query: str
    identifier: str | None
    stock: StockRecord | None
    response: AgentResponse


def extract_identifier(query: str) -> str | None:
    """Extract a stock code or company name from user input."""

    match = re.search(r"\b\d{6}\b", query)
    if match:
        return match.group(0)

    for record in load_records():
        if record.name in query:
            return record.name
    return None


def parse_query(state: StockAgentState) -> StockAgentState:
    """Parse the user query."""

    return {"identifier": extract_identifier(state["query"])}


def lookup_stock(state: StockAgentState) -> StockAgentState:
    """Fetch stock data from the local repository."""

    identifier = state.get("identifier")
    return {"stock": get_stock_by_identifier(identifier or "")}


def format_response(state: StockAgentState) -> StockAgentState:
    """Build a normalized stock response."""

    stock = state.get("stock")
    if not stock:
        response = AgentResponse(
            agent="stock_subagent",
            status="error",
            summary="未识别到股票代码或公司名称",
            detail="请直接提供 6 位股票代码，或使用内置公司名：宁德时代、贵州茅台、格力电器、云南白药。",
        )
        return {"response": response}

    detail = (
        f"{stock.name}（{stock.code}，{stock.sector}）当前示例收盘价为 {stock.close_price:.1f} 元，"
        f"近一段时间价格变动 {stock.price_change_pct:.1f}%，"
        f"收入增速 {stock.revenue_growth_pct:.1f}%，"
        f"市盈率 {stock.pe_ratio:.1f}，"
        f"波动率 {stock.volatility_pct:.1f}%。"
    )
    response = AgentResponse(
        agent="stock_subagent",
        summary=f"已找到 {stock.name} 的基础行情信息",
        detail=detail,
    )
    return {"response": response}


def build_stock_agent():
    """Compile the LangGraph stock agent."""

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
    """Execute the stock subagent."""

    result = STOCK_AGENT.invoke({"query": query})
    return result["response"]
