"""Analysis subagent implemented with LangGraph."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .models import AgentResponse, StockRecord
from .store import list_stock_mentions


class AnalysisState(TypedDict, total=False):
    """State carried by the analysis graph."""

    query: str
    plan: str
    stocks: list[StockRecord]
    ranking: list[tuple[StockRecord, float]]
    response: AgentResponse


def plan_analysis(state: AnalysisState) -> AnalysisState:
    """Build a lightweight plan for the analysis agent."""

    return {
        "plan": "收集候选股票数据 -> 比较价格表现、增长、估值、波动 -> 输出排序和理由"
    }


def collect_stocks(state: AnalysisState) -> AnalysisState:
    """Collect mentioned stocks from the query."""

    return {"stocks": list_stock_mentions(state["query"])}


def score_stocks(state: AnalysisState) -> AnalysisState:
    """Apply a simple scoring formula to rank stocks."""

    ranking: list[tuple[StockRecord, float]] = []
    for stock in state.get("stocks", []):
        score = (
            stock.price_change_pct * 0.35
            + stock.revenue_growth_pct * 0.35
            - stock.pe_ratio * 0.15
            - stock.volatility_pct * 0.15
        )
        ranking.append((stock, round(score, 2)))
    ranking.sort(key=lambda item: item[1], reverse=True)
    return {"ranking": ranking}


def respond_analysis(state: AnalysisState) -> AnalysisState:
    """Build the final analysis result."""

    stocks = state.get("stocks", [])
    ranking = state.get("ranking", [])
    if len(stocks) < 2:
        response = AgentResponse(
            agent="analysis_subagent",
            status="error",
            summary="分析模式至少需要两只股票",
            detail="请在问题里至少提供两只股票代码或公司名，例如：300750 和 600519。",
        )
        return {"response": response}

    winner, winner_score = ranking[0]
    lines = [
        f"计划：{state['plan']}",
        "排序结果：",
    ]
    for stock, score in ranking:
        lines.append(
            f"- {stock.name}（{stock.code}）得分 {score:.2f}；"
            f"涨跌幅 {stock.price_change_pct:.1f}%，增速 {stock.revenue_growth_pct:.1f}%，"
            f"PE {stock.pe_ratio:.1f}，波动率 {stock.volatility_pct:.1f}%"
        )
    lines.append(
        f"综合来看，当前示例数据下更值得优先关注的是 {winner.name}（{winner.code}），"
        f"因为它在增长和价格表现上更强，同时估值与波动仍在可接受区间。"
    )
    response = AgentResponse(
        agent="analysis_subagent",
        summary=f"已完成 {len(stocks)} 只股票的对比分析，当前优先关注 {winner.name}",
        detail="\n".join(lines),
    )
    return {"response": response}


def build_analysis_agent():
    """Compile the LangGraph analysis agent."""

    graph = StateGraph(AnalysisState)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("collect_stocks", collect_stocks)
    graph.add_node("score_stocks", score_stocks)
    graph.add_node("respond_analysis", respond_analysis)
    graph.add_edge(START, "plan_analysis")
    graph.add_edge("plan_analysis", "collect_stocks")
    graph.add_edge("collect_stocks", "score_stocks")
    graph.add_edge("score_stocks", "respond_analysis")
    graph.add_edge("respond_analysis", END)
    return graph.compile()


ANALYSIS_AGENT = build_analysis_agent()


def run_analysis_agent(query: str) -> AgentResponse:
    """Execute the analysis subagent."""

    result = ANALYSIS_AGENT.invoke({"query": query})
    return result["response"]
