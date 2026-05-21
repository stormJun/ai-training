# 人机协同（HITL）

HITL 是 `Human in the Loop`，意思是把“人”明确放进工作流里，而不是让 Agent 从头到尾自动跑完。

在 LangGraph 里，常见的人机协同方式有三类：

- 审批
  先让图跑到某一步，再由人决定“通过”还是“拒绝”
- 编辑
  先暂停，把当前状态交给人修改，然后继续执行
- 输入
  专门留一个节点收集人工输入，再把输入写回图状态

这份示例只聚焦最容易理解的一类：

> 退款工作流里的“人工审批”

---

## 这个示例讲什么

我们用一个很小的退款流程演示 HITL：

1. 用户提交退款金额
2. 系统先做规则判断
3. 小额退款自动通过
4. 大额退款进入人工审批
5. 最后统一给出处理结果

对应的图结构可以理解成：

```text
START
  -> receive_request
  -> ai_evaluate
  -> human_approval | finalize_refund
  -> END
```

这里最关键的点不是“退款”这个业务，而是：

- LangGraph 可以先自动判断
- 再用条件边把流程切到人工节点
- 人工节点处理完以后，图还能继续往下走

---

## 这个例子里的状态

状态只有 3 类信息：

```python
class RefundState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    refund_amount: float
    needs_approval: bool
```

它们各自的作用是：

- `messages`
  保存流程中的消息记录
- `refund_amount`
  保存本次退款金额
- `needs_approval`
  表示当前是否需要人工审批

这里 `messages` 用了 `add_messages`，表示新消息会追加进去，而不是覆盖旧消息。

---

## 节点职责

### 1. `receive_request`

职责很简单：

- 从用户输入里取出退款金额
- 转成 `float`
- 写入状态

它不做业务判断，只做“接收和解析”。

### 2. `ai_evaluate`

这个节点模拟系统规则判断：

- 金额小于等于 `500`，自动通过
- 金额大于 `500`，进入人工审批
- 非法金额直接标记为无效

它的核心输出是：

- 一条系统判断消息
- `needs_approval`

### 3. `human_approval`

这是人机协同的核心节点。

它会：

- 读取当前退款金额
- 用 `input()` 暂停程序
- 等待人工输入“是 / 否”
- 再把人工决策写回消息列表

从教学角度看，这个节点体现的是：

> 工作流并不一定全自动，节点本身也可以显式等待人工参与。

### 4. `finalize_refund`

这个节点统一做收尾：

- 如果人工批准，则输出“已批准并处理”
- 如果人工拒绝，则输出“申请被拒绝”
- 如果本来就不需要人工审批，则输出“自动处理完成”

这样可以把“最终结果输出”收口到一个节点里，逻辑更集中。

---

## 条件路由是怎么做的

这个例子里最值得注意的是这里：

```python
def should_get_approval(state: RefundState) -> str:
    if state.get("needs_approval", False):
        return "human_approval"
    return "finalize_refund"
```

然后把它挂到条件边上：

```python
graph.add_conditional_edges(
    "ai_evaluate",
    should_get_approval,
    {
        "human_approval": "human_approval",
        "finalize_refund": "finalize_refund",
    },
)
```

这段代码表达的意思很直接：

- 如果需要人工审批，就走 `human_approval`
- 否则直接走 `finalize_refund`

所以 HITL 的关键不只是“有一个人工节点”，而是：

> 图能根据状态，决定什么时候切到人工节点。

---

## 为什么这里还用了 `MemorySaver`

示例里编译图时用了：

```python
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

这表示图的运行状态会按 `thread_id` 保存。

在这个小例子里，它的价值主要是教学：

- 让你看到 LangGraph 的工作流不是一次性函数调用
- 它可以带着上下文和线程配置运行

虽然这个示例没有做复杂恢复，但已经具备了“带线程执行”的基本形态。

---

## 如何运行

直接运行脚本：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/06_langgraph_basics/02_workflows/tutorials/02_human_in_the_loop
python 04_人机协同_HITL.py
```

脚本会演示两个场景：

1. `300` 元退款
   自动处理，不需要人工审批
2. `800` 元退款
   会暂停并等待你输入审批结果

你在第二个场景里可以输入：

- `是` / `yes` / `y`
- `否` / `no` / `n`

---

## 这份示例真正要学的点

- HITL 的本质是把“人”放进图执行链路里
- 条件边决定什么时候从自动流程切到人工流程
- 人工节点不是特殊魔法，本质上也是一个普通节点
- 业务上常见的审批流，非常适合用 LangGraph 这种状态化工作流表达

---

## 建议下一步

如果你已经看懂这个例子，再继续看：

- `05_记忆机制_基础.md`

HITL 解决的是“人怎么进入流程”，记忆机制解决的是“流程怎么记住上下文”。
