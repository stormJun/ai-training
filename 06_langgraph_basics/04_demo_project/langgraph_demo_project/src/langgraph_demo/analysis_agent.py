"""使用 LangGraph 实现的分析子代理。"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import llm
from .models import AgentResponse, StockRecord
from .store import list_stock_mentions


class AnalysisState(TypedDict, total=False):
    """分析工作流在节点之间传递的状态。"""

    query: str
    plan: str
    stocks: list[StockRecord]
    ranking: list[tuple[StockRecord, float]]
    response: AgentResponse


def plan_analysis(state: AnalysisState) -> AnalysisState:
    """为分析子代理生成一个轻量的执行计划。"""

    return {
        "plan": "收集候选股票数据 -> 比较价格表现、增长、估值、波动 -> 输出排序和理由"
    }


def collect_stocks(state: AnalysisState) -> AnalysisState:
    """从用户问题中收集被提到的股票。"""

    return {"stocks": list_stock_mentions(state["query"])}


def score_stocks(state: AnalysisState) -> AnalysisState:
    """用一个简单的打分公式对股票进行排序。"""

    ranking: list[tuple[StockRecord, float]] = []
    for stock in state.get("stocks", []):
        # 价格表现和增长为正向指标，估值和波动率为负向指标。
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
    """组装最终的分析结果。"""

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

    winner, _winner_score = ranking[0]
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
    summary = f"已完成 {len(stocks)} 只股票的对比分析，当前优先关注 {winner.name}"
    detail = "\n".join(lines)
    if llm.is_dashscope_enabled():
        try:
            summary, detail = llm.generate_analysis_response(
                query=state["query"],
                plan=state["plan"],
                ranking=ranking,
            )
        except llm.LLMError:
            pass

    response = AgentResponse(
        agent="analysis_subagent",
        summary=summary,
        detail=detail,
    )
    return {"response": response}


def build_analysis_agent():
    """编译分析子代理对应的 LangGraph 工作流。"""

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
    """执行分析子代理。"""

    result = ANALYSIS_AGENT.invoke({"query": query})
    return result["response"]
