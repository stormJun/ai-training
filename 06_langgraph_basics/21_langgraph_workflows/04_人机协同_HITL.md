## 人机协同

Langgraph 通过审批、编辑和输入三种常见的用户交互模式，增强 Agent 的能力。这个模式被称为“人机协同”（human in the loop , HITL）

审批模式，表示可以中断 Agent，将当前的状态交给用户，并允许用户接受或拒绝 Agent 的决策。

编辑模式，表示可以中断 Agent，让用户直接编辑状态，然后让 Agent 继续执行。

输入模式，表示可以中断 Agent，可以专门创建一个图节点来收集人类输入，并将该输入直接传递给 Agent。
```python
# LangGraph 人机协同（HITL）演示 

from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# 状态定义
class RefundState(TypedDict):
    messages: Annotated[Sequence, add_messages]
    refund_amount: float
    needs_approval: bool

# 节点函数
def receive_request(state: RefundState):
    """接收退款请求"""
    last_msg = state["messages"][-1].content.strip()
    try:
        amount = float(last_msg)
    except:
        amount = 0.0
    
    print(f" 收到退款申请：{amount} 元")
    return {
        "refund_amount": amount,
        "needs_approval": False
    }

def ai_evaluate(state: RefundState):
    """AI评估退款请求"""
    amount = state["refund_amount"]
    
    if amount <= 0:
        reply = " 退款金额无效"
        needs_approval = False
    elif amount <= 500:
        reply = f" {amount} 元退款自动批准"
        needs_approval = False
    else:
        reply = f" {amount} 元退款需要人工审核"
        needs_approval = True
    
    print(f" AI评估结果：{reply}")
    
    return {
        "messages": [AIMessage(content=reply)],
        "needs_approval": needs_approval
    }

def human_approval(state: RefundState):
    """人工审批节点 - 这里会暂停等待输入"""
    amount = state["refund_amount"]
    
    print(f" 等待人工审批 {amount} 元退款...")
    
    # 获取人工输入（通过 input() 真正暂停）
    while True:
        try:
            decision = input(f"\n请审批 {amount} 元退款申请 (输入 '是' 批准, '否' 拒绝): ").strip()
            if decision in ['是', '否', 'yes', 'no', 'y', 'n']:
                break
            else:
                print("请输入 '是' 或 '否'")
        except KeyboardInterrupt:
            print("\n 审批被取消")
            decision = '否'
            break
    
    approved = decision in ['是', 'yes', 'y']
    result = "批准" if approved else "拒绝"
    
    print(f" 人工决策：{result}")
    
    return {
        "messages": [HumanMessage(content=f"[人工审批] {result}")]
    }

def finalize_refund(state: RefundState):
    """最终处理退款"""
    amount = state["refund_amount"]
    
    # 检查最后一条消息是否包含审批结果
    last_msg = state["messages"][-1].content if state["messages"] else ""
    
    if "批准" in last_msg:
        reply = f" 退款 {amount} 元已批准并处理"
        print(f" {reply}")
    elif "拒绝" in last_msg:
        reply = f" 退款 {amount} 元申请被拒绝"
        print(f" {reply}")
    elif not state.get("needs_approval", True):
        reply = f" 退款 {amount} 元自动处理完成"
        print(f" {reply}")
    else:
        reply = f" 退款 {amount} 元状态未知"
        print(f" {reply}")
    
    return {
        "messages": [AIMessage(content=reply)]
    }

# 路由函数
def should_get_approval(state: RefundState) -> str:
    """决定是否需要人工审批"""
    if state.get("needs_approval", False):
        return "human_approval"
    else:
        return "finalize_refund"

# 构建图
graph = StateGraph(RefundState)

# 添加节点
graph.add_node("receive_request", receive_request)
graph.add_node("ai_evaluate", ai_evaluate)
graph.add_node("human_approval", human_approval)
graph.add_node("finalize_refund", finalize_refund)

# 添加边
graph.add_edge(START, "receive_request")
graph.add_edge("receive_request", "ai_evaluate")

# 条件边：根据是否需要审批来路由
graph.add_conditional_edges(
    "ai_evaluate",
    should_get_approval,
    {
        "human_approval": "human_approval",
        "finalize_refund": "finalize_refund"
    }
)

graph.add_edge("human_approval", "finalize_refund")
graph.add_edge("finalize_refund", END)

# 编译图
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# 主要函数
def process_refund(amount: str, thread_id: str = "default"):
    """处理退款申请"""
    print(f"\n 开始处理退款申请...")
    print("="*50)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # 运行工作流
    result = app.invoke({
        "messages": [HumanMessage(content=amount)]
    }, config=config)
    
    print("="*50)
    print(" 退款流程完成")
    
    return result

# 演示函数
def demo():
    """演示不同场景"""
    print(" LangGraph 人机协同（HITL）演示")
    print("="*60)
    
    # 场景1：小额退款（自动处理）
    print("\n 场景1：小额退款（300元）- 自动处理")
    process_refund("300", "user1")
    
    print("\n" + "="*60)
    
    # 场景2：大额退款（需要人工审批）
    print("\n 场景2：大额退款（800元）- 需要人工审批")
    print(" 这里会真正暂停等待你的输入！")
    process_refund("800", "user2")

if __name__ == "__main__":
    demo()
```
**Output:**

```text
 LangGraph 人机协同（HITL）演示
============================================================

 场景1：小额退款（300元）- 自动处理

 开始处理退款申请...
==================================================
 收到退款申请：300.0 元
 AI评估结果： 300.0 元退款自动批准
  退款 300.0 元已批准并处理
==================================================
 退款流程完成

============================================================

 场景2：大额退款（800元）- 需要人工审批
 这里会真正暂停等待你的输入！

 开始处理退款申请...
==================================================
 收到退款申请：800.0 元
 AI评估结果： 800.0 元退款需要人工审核
 等待人工审批 800.0 元退款...
 人工决策：批准
  退款 800.0 元已批准并处理
==================================================
 退款流程完成
```
