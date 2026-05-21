"""LangGraph 人机协同（HITL）示例。

这个示例用退款审批流程演示：
1. 系统先根据规则自动判断
2. 大额退款切换到人工审批
3. 人工决策完成后，图继续执行
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


AUTO_APPROVAL_LIMIT = 500.0
APPROVE_INPUTS = {"是", "yes", "y"}
REJECT_INPUTS = {"否", "no", "n"}


class RefundState(TypedDict):
    """退款工作流状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    refund_amount: float
    needs_approval: bool


def parse_refund_amount(raw_text: str) -> float:
    """把用户输入解析成退款金额。"""
    try:
        return float(raw_text.strip())
    except (TypeError, ValueError):
        return 0.0


def receive_request(state: RefundState):
    """接收并解析退款请求。"""
    last_message = state["messages"][-1].content
    amount = parse_refund_amount(last_message)

    print(f"收到退款申请：{amount} 元")
    return {
        "refund_amount": amount,
        "needs_approval": False,
    }


def ai_evaluate(state: RefundState):
    """根据退款金额决定是否需要人工审批。"""
    amount = state["refund_amount"]

    if amount <= 0:
        reply = "退款金额无效"
        needs_approval = False
    elif amount <= AUTO_APPROVAL_LIMIT:
        reply = f"{amount} 元退款自动批准"
        needs_approval = False
    else:
        reply = f"{amount} 元退款需要人工审核"
        needs_approval = True

    print(f"AI 评估结果：{reply}")
    return {
        "messages": [AIMessage(content=reply)],
        "needs_approval": needs_approval,
    }


def ask_for_human_decision(amount: float) -> str:
    """阻塞等待人工输入审批结果。"""
    prompt = f"\n请审批 {amount} 元退款申请（输入 '是' 批准，'否' 拒绝）: "

    while True:
        try:
            decision = input(prompt).strip().lower()
        except KeyboardInterrupt:
            print("\n审批被取消，默认拒绝。")
            return "拒绝"

        if decision in APPROVE_INPUTS:
            return "批准"
        if decision in REJECT_INPUTS:
            return "拒绝"

        print("请输入 '是' / '否'，或 yes / no。")


def human_approval(state: RefundState):
    """人工审批节点。"""
    amount = state["refund_amount"]
    print(f"等待人工审批 {amount} 元退款...")

    result = ask_for_human_decision(amount)
    print(f"人工决策：{result}")

    return {
        "messages": [HumanMessage(content=f"[人工审批] {result}")],
    }


def finalize_refund(state: RefundState):
    """根据审批结果输出最终处理结论。"""
    amount = state["refund_amount"]
    last_message = state["messages"][-1].content if state["messages"] else ""

    if "批准" in last_message:
        reply = f"退款 {amount} 元已批准并处理"
    elif "拒绝" in last_message:
        reply = f"退款 {amount} 元申请被拒绝"
    elif not state.get("needs_approval", True):
        reply = f"退款 {amount} 元自动处理完成"
    else:
        reply = f"退款 {amount} 元状态未知"

    print(reply)
    return {
        "messages": [AIMessage(content=reply)],
    }


def should_get_approval(state: RefundState) -> str:
    """在自动处理与人工审批之间路由。"""
    if state.get("needs_approval", False):
        return "human_approval"
    return "finalize_refund"


graph = StateGraph(RefundState)
graph.add_node("receive_request", receive_request)
graph.add_node("ai_evaluate", ai_evaluate)
graph.add_node("human_approval", human_approval)
graph.add_node("finalize_refund", finalize_refund)

graph.add_edge(START, "receive_request")
graph.add_edge("receive_request", "ai_evaluate")
graph.add_conditional_edges(
    "ai_evaluate",
    should_get_approval,
    {
        "human_approval": "human_approval",
        "finalize_refund": "finalize_refund",
    },
)
graph.add_edge("human_approval", "finalize_refund")
graph.add_edge("finalize_refund", END)

app = graph.compile(checkpointer=MemorySaver())


def process_refund(amount: str, thread_id: str = "default"):
    """执行一次退款流程。"""
    print("\n开始处理退款申请...")
    print("=" * 50)

    result = app.invoke(
        {"messages": [HumanMessage(content=amount)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    print("=" * 50)
    print("退款流程完成")
    return result


def demo():
    """运行两个演示场景。"""
    print("LangGraph 人机协同（HITL）演示")
    print("=" * 60)

    print("\n场景 1：300 元退款，自动处理")
    process_refund("300", "user1")

    print("\n" + "=" * 60)
    print("\n场景 2：800 元退款，需要人工审批")
    process_refund("800", "user2")


if __name__ == "__main__":
    demo()
