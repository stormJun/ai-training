# LangGraph（工程化笔记）

LangGraph 是一个低级编排框架和运行时，用于构建、管理和部署长期运行的有状态智能体。它用"图（Graph）+ 状态（State）"把多轮对话、工具调用、条件分支、循环、持久化与人机协作（HITL）统一到一套抽象里。

官方文档：https://langchain-ai.github.io/langgraph/

**核心优势：**

| 优势 | 说明 |
|------|------|
| **持久执行** | 构建能够在故障中保持存在并可长时间运行的智能体，从上次中断的地方恢复运行 |
| **人机协作** | 通过在任何时候检查和修改智能体状态，纳入人类监督 |
| **全面的记忆能力** | 既具备用于持续推理的短期工作记忆，又拥有跨会话的长期记忆 |
| **调试与观测** | 借助 LangSmith 可视化工具追踪执行路径、捕获状态转换并提供详细的运行时指标 |
| **生产级部署** | 借助可扩展的基础设施，部署复杂的智能体系统 |

> **注意**：LangGraph 层级非常低，且完全专注于智能体的编排。如果您刚刚开始接触智能体，或希望使用更高级别的抽象，可以先使用 LangChain 的预构建智能体架构。

## 目录

- 0. 本仓库学习路线（建议顺序）
- 1. 版本与安装（week04 可复现）
- 2. 为什么需要 LangGraph（从 Chain/DAG 到 循环图/状态机）
- 3. Quickstart 快速入门
  - 3.1 选择 API 风格
  - 3.2 核心三要素
  - 3.3 图 API：最简示例
  - 3.4 图 API：带条件分支的图
  - 3.5 图 API：结合 LLM 的聊天机器人
  - 3.6 流式输出
  - 3.7 可视化图结构
  - 3.8 函数式 API：工具调用智能体
- 4. Thinking in LangGraph（LangGraph 思维模式）
- 5. 工作流与智能体模式
  - 5.1 工作流 vs 智能体
  - 5.2 提示词链（Prompt Chaining）
  - 5.3 并行化（Parallelization）
  - 5.4 路由（Routing）
  - 5.5 协调器-工作器（Orchestrator-Worker）
  - 5.6 评估器-优化器（Evaluator-Optimizer）
  - 5.7 智能体（Agent）
- 6. Graph API 概述与核心概念
  - 6.1 执行模型
  - 6.2 StateGraph
  - 6.3 编译图
  - 6.4 State（状态）
  - 6.5 多个模式
  - 6.6 Reducers（归约器）
  - 6.7 消息处理
  - 6.8 Nodes（节点）
  - 6.9 节点缓存
  - 6.10 Edges（边）
  - 6.11 Send
  - 6.12 Command
  - 6.13 运行时上下文
  - 6.14 递归限制
  - 6.15 图迁移
  - 6.16 面试必背要点
- 7. Graph API 实战指南
  - 7.1 定义和更新状态
  - 7.2 Reducers 使用
  - 7.3 Overwrite 类型
  - 7.4 输入/输出模式
  - 7.5 私有状态
  - 7.6 Pydantic 模型
  - 7.7 运行时配置
  - 7.8 重试策略
  - 7.9 节点缓存
  - 7.10 创建序列
  - 7.11 创建分支
  - 7.12 Map-Reduce 模式
  - 7.13 创建循环
  - 7.14 异步模式
  - 7.15 Command 使用
  - 7.16 可视化
  - 7.17 面试必背要点
- 8. 运行方式与事件（invoke/stream/astream）
  - 8.1 基本运行方式
  - 8.2 支持的流模式
  - 8.3 基本使用示例
  - 8.4 流图状态（updates vs values）
  - 8.5 流子图输出
  - 8.6 流 LLM 令牌（messages 模式）
  - 8.7 流自定义数据（custom 模式）
  - 8.8 调试模式（debug 模式）
  - 8.9 Python < 3.11 异步注意事项
  - 8.10 面试必背要点
- 9. 子图（Subgraph）
  - 9.1 定义子图通信
  - 9.2 在节点内部调用子图
  - 9.3 将子图添加为节点
  - 9.4 子图持久性
  - 9.5 无状态子图
  - 9.6 有状态子图
  - 9.7 检查点参考
  - 9.8 查看子图状态
  - 9.9 流式输出子图结果
  - 9.10 生产环境下的核心工程实践
  - 9.11 面试必背要点
- 10. 持久化与快照（Checkpoint / StateSnapshot）
  - 10.1 Threads 线程
  - 10.2 Checkpoints 检查点
  - 10.3 获取状态
  - 10.4 获取状态历史
  - 10.5 Replay 回放
  - 10.6 更新状态
  - 10.7 Memory Store 内存存储
  - 10.8 语义搜索
  - 10.9 在 LangGraph 中使用 Store
  - 10.10 Checkpointer Libraries 检查点库
  - 10.11 Checkpointer Interface 检查点接口
  - 10.12 Serializer 序列化器
  - 10.13 持久化能力
  - 10.14 生产环境避坑指南
  - 10.15 持久执行（Durable Execution）
  - 10.16 确定性与一致重放
  - 10.17 持久性模式
  - 10.18 恢复工作流
  - 10.19 面试必背要点
- 11. 中断与人机协作（Interrupts / Human-in-the-Loop）
  - 11.1 基本概念
  - 11.2 使用 interrupt 暂停
  - 11.3 恢复中断
  - 11.4 常见模式
  - 11.5 处理多个中断
  - 11.6 审批工作流
  - 11.7 审阅与编辑状态
  - 11.8 工具中的中断
  - 11.9 验证人工输入
  - 11.10 中断规则
  - 11.11 调试中断
  - 11.12 面试必背要点
- 12. 时间旅行（Time-Travel）
  - 12.1 使用时间旅行的步骤
  - 12.2 工作流示例
  - 12.3 步骤 1：运行图
  - 12.4 步骤 2：识别检查点
  - 12.5 步骤 3：更新状态（可选）
  - 12.6 步骤 4：从检查点恢复执行
  - 12.7 面试必背要点
- 13. 记忆（Memory）
  - 13.1 添加短期记忆
  - 13.2 添加长期记忆
  - 13.3 使用语义搜索
  - 13.4 管理短期记忆
  - 13.5 修剪消息
  - 13.6 删除消息
  - 13.7 总结消息
  - 13.8 管理检查点
  - 13.9 数据库管理
  - 13.10 面试必背要点
- 14. 调试与观测（Studio / tracing / 自定义事件）
- 15. 工程模板与部署（可复制，用于作业/项目）
  - 15.1 应用结构
  - 15.2 配置文件（langgraph.json）
  - 15.3 依赖项管理
  - 15.4 图的配置
  - 15.5 环境变量
  - 15.6 本仓库模板
  - 15.7 面试必背要点
- 16. 参考链接

## 0. 本仓库学习路线（建议顺序）

把"目录"直接对齐到仓库内容（保证连贯可跑）：

**第一阶段：基础入门**

1) **Hello World**：先跑通 `StateGraph` + `messages` + `.stream()`
   - Notebook：`week04/p42-langgraph-1.ipynb`
   - 文档章节：第3章 Quickstart、第6章 Graph API 概述

2) **理解核心概念**：状态、节点、边、归约器
   - 文档章节：第4章 Thinking in LangGraph、第6章 Graph API 概述

3) **工作流模式**：提示词链、并行化、路由、协调器-工作器
   - 文档章节：第5章 工作流与智能体模式

**第二阶段：实战技能**

4) **Graph API 实战**：重试策略、缓存、分支、循环、Map-Reduce、Command
   - 文档章节：第7章 Graph API 实战指南
   - Notebook：`week04/p47-tool.ipynb`（工具调用循环）

5) **运行与流式输出**：invoke、stream、astream
   - 文档章节：第8章 运行方式与事件

**第三阶段：进阶特性**

6) **快照/回放**：加 checkpointer，理解 `thread_id` / `checkpoint_id`
   - 文档章节：第10章 持久化与快照
   - Notebook：`week04/p44-snapshot.ipynb`

7) **人机协作（HITL）**：暂停/审批/编辑 state 再继续
   - 文档章节：第11章 中断与人机协作
   - Notebook：`week04/HITL.ipynb`

8) **时间旅行**：回退到历史检查点、分支执行
   - 文档章节：第12章 时间旅行

9) **记忆管理**：短期记忆 + 长期记忆 + 语义搜索
   - 文档章节：第13章 记忆
   - Notebook：`week04/mem0.ipynb`

**第四阶段：工程化落地**

10) **复杂工作流（RAG 可控循环）**：入口路由 + 评分 + 自纠错循环
    - Notebook：`week04/p42-langgraph-0RAG.ipynb`

11) **调试与观测**：LangSmith 追踪、可视化
    - 文档章节：第14章 调试与观测
    - Notebook：`week04/p45-langgraph-studio.ipynb`

12) **工程化部署**：结构/配置/测试/服务化
    - 文档章节：第15章 工程模板与部署
    - 工程模板：`week04/app`、`week04/app2`（含 `pytest` 示例）

## 1. 版本与安装

要安装基础的LangGraph包：

```bash
uv add langgraph
```

## 2. 为什么需要 LangGraph（从 Chain/DAG 到 循环图/状态机）

顺序链（Chain）通常类似 DAG：每一步严格按顺序执行、缺少天然的循环表达。复杂任务经常需要：
- 检索不足 → 继续检索/改写 query → 再检索（循环）
- 结果不确定 → 评分/自检 → 失败回到上游节点（自纠错）
- 关键步骤需要人工确认/编辑 → 再继续（HITL）

LangGraph 用"图 + 状态机"表达这些控制流，让系统更可控、更可调试。

## 3. Quickstart 快速入门

### 3.1 选择 API 风格

LangGraph 提供两种 API 风格，可根据偏好选择：

| API 风格 | 适用场景 | 特点 |
|----------|----------|------|
| **图 API（Graph API）** | 希望将智能体定义为节点和边组成的图 | 显式定义节点和边，结构清晰 |
| **函数式 API（Functional API）** | 倾向于将智能体定义为单个函数 | 在函数内编写控制流（循环、条件），更直观 |

> 本节同时展示两种 API 的用法，帮助你快速上手。

### 3.2 核心三要素

LangGraph 应用由三个核心要素构成：

| 要素 | 说明 |
|------|------|
| **State（状态）** | 在节点间流转的共享数据结构 |
| **Nodes（节点）** | 处理状态的 Python 函数 |
| **Edges（边）** | 定义节点间的流转逻辑 |

### 3.3 图 API：最简示例

下面是一个最简单的 LangGraph 应用，展示基本的图构建与运行：

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. 定义状态
class State(TypedDict):
    message: str

# 2. 定义节点函数
def node_a(state: State) -> dict:
    return {"message": state["message"] + " -> A"}

def node_b(state: State) -> dict:
    return {"message": state["message"] + " -> B"}

# 3. 构建图
graph = StateGraph(State)
graph.add_node("node_a", node_a)
graph.add_node("node_b", node_b)

# 4. 添加边（定义流转）
graph.add_edge(START, "node_a")
graph.add_edge("node_a", "node_b")
graph.add_edge("node_b", END)

# 5. 编译并运行
app = graph.compile()
result = app.invoke({"message": "Hello"})
print(result["message"])  # 输出: Hello -> A -> B
```

### 3.4 图 API：带条件分支的图

使用 `add_conditional_edges` 实现动态路由：

```python
from typing import Literal

def route(state: State) -> Literal["node_a", "node_b"]:
    """根据状态决定下一步走哪个节点"""
    if "error" in state["message"]:
        return "node_a"
    return "node_b"

graph.add_conditional_edges("start", route, {"node_a": "node_a", "node_b": "node_b"})
```

### 3.5 图 API：结合 LLM 的聊天机器人

最常见的用例——构建一个能调用工具的聊天机器人：

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode

# 定义工具
@tool
def get_weather(city: str) -> str:
    """查询天气"""
    return f"{city} 今天晴天，25°C"

tools = [get_weather]
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

# 定义节点
def agent(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: MessagesState):
    return "tools" if state["messages"][-1].tool_calls else END

# 构建图
graph = StateGraph(MessagesState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")

# 运行
app = graph.compile()
```

### 3.6 流式输出

使用 `stream()` 获取中间状态：

```python
for event in app.stream({"messages": ["你好"]}):
    print(event)  # 每个节点的输出
```

### 3.7 可视化图结构

在 Jupyter Notebook 中可视化：

```python
from IPython.display import Image, display
display(Image(app.get_graph().draw_mermaid_png()))
```

### 3.8 函数式 API：工具调用智能体

如果你倾向于将智能体定义为单个函数，可以使用函数式 API。在函数式 API 中，你无需显式定义节点和边，而是在单个函数内编写标准的控制流逻辑（循环、条件语句）。

#### 步骤 1：定义工具和模型

```python
from langchain.tools import tool
from langchain.chat_models import init_chat_model

# 初始化模型
model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    temperature=0
)

# 定义工具
@tool
def multiply(a: int, b: int) -> int:
    """将 a 和 b 相乘"""
    return a * b

@tool
def add(a: int, b: int) -> int:
    """将 a 和 b 相加"""
    return a + b

@tool
def divide(a: int, b: int) -> float:
    """将 a 除以 b"""
    return a / b

# 将工具绑定到模型
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
```

#### 步骤 2：定义模型节点

模型节点用于调用大语言模型，并决定是否调用工具：

```python
from langgraph.func import task
from langchain_core.messages import BaseMessage, SystemMessage

@task
def call_llm(messages: list[BaseMessage]):
    """LLM 决定是否调用工具"""
    return model_with_tools.invoke(
        [SystemMessage(content="你是一个帮助执行算术运算的助手。")]
        + messages
    )
```

#### 步骤 3：定义工具节点

```python
from langchain.messages import ToolCall

@task
def call_tool(tool_call: ToolCall):
    """执行工具调用"""
    tool = tools_by_name[tool_call["name"]]
    return tool.invoke(tool_call)
```

#### 步骤 4：定义智能体

使用 `@entrypoint` 装饰器定义智能体入口：

```python
from langgraph.func import entrypoint
from langgraph.graph import add_messages
from langchain.messages import HumanMessage

@entrypoint()
def agent(messages: list[BaseMessage]):
    # 首次调用 LLM
    model_response = call_llm(messages).result()

    # 循环处理工具调用
    while True:
        # 如果没有工具调用，退出循环
        if not model_response.tool_calls:
            break
        # 并发执行所有工具调用
        tool_result_futures = [
            call_tool(tool_call) for tool_call in model_response.tool_calls
        ]
        tool_results = [fut.result() for fut in tool_result_futures]
        # 更新消息历史
        messages = add_messages(messages, [model_response, *tool_results])
        # 再次调用 LLM 处理工具结果
        model_response = call_llm(messages).result()
    # 添加最终响应到消息历史
    messages = add_messages(messages, model_response)
    return messages
```

#### 步骤 5：运行智能体

```python
# 调用智能体
messages = [HumanMessage(content="计算 3 加 4")]

# 流式输出
for chunk in agent.stream(messages, stream_mode="updates"):
    print(chunk)
    print("\n")
```

## 4. Thinking in LangGraph（LangGraph 思维模式）

使用 LangGraph 构建智能体时，你首先要将其拆分为称为**节点（nodes）**的独立步骤。

然后，你要描述来自每个节点的不同决策和转换。最后，你通过一个**共享的状态（state）**将节点连接起来，每个节点都可以对该状态进行读写操作。

本节以构建**客户支持邮件智能体**为例，展示使用 LangGraph 构建智能体的完整思考过程。

### 4.1 从你想要自动化的流程开始

假设你需要构建一个处理客户支持邮件的人工智能智能体，产品团队给出了以下需求：

**智能体应该能够：**
- 读取收到的客户邮件
- 按紧急程度和主题进行分类
- 搜索相关文档以回答问题
- 起草适当的回复
- 将复杂问题升级给人工客服
- 在需要时安排后续跟进

**需要处理的典型场景：**

| 场景 | 示例 |
|------|------|
| 简单产品问题 | "如何重置密码？" |
| Bug 报告 | "选择 PDF 格式时导出功能崩溃" |
| 紧急账单问题 | "我的订阅被扣了两次款！" |
| 功能请求 | "能在移动应用中添加深色模式吗？" |
| 复杂技术问题 | "我们的 API 集成间歇性地出现 504 错误" |

### 4.2 实现智能体的五个步骤

在 LangGraph 中实现智能体，通常遵循以下五个步骤：

#### 步骤 1：确定流程中的各个步骤

首先确定流程中的各个不同步骤。每个步骤都将成为一个**节点**（执行特定操作的函数）。然后，勾勒出这些步骤之间的连接方式。

**客户邮件智能体的节点设计：**

| 节点 | 功能说明 |
|------|----------|
| Read Email | 提取并解析邮件内容 |
| Classify Intent | 使用 LLM 对紧急程度和主题进行分类，然后路由至适当的操作 |
| Doc Search | 查询知识库以获取相关信息 |
| Bug Track | 在跟踪系统中创建或更新问题 |
| Draft Reply | 生成恰当的回复 |
| Human Review | 提交给人工进行审批或处理 |
| Send Reply | 发送电子邮件回复 |

**流程图：**

```mermaid
flowchart TB
    START([开始]) --> ReadEmail[Read Email<br/>读取邮件]

    ReadEmail --> ClassifyIntent[Classify Intent<br/>分类意图]

    ClassifyIntent -->|question| DocSearch[Doc Search<br/>文档搜索]
    ClassifyIntent -->|bug| BugTrack[Bug Track<br/>漏洞追踪]
    ClassifyIntent -->|billing/feature/complex| DraftReply[Draft Reply<br/>起草回复]

    DocSearch --> DraftReply
    BugTrack --> DraftReply

    DraftReply -->|high/critical urgency| HumanReview[Human Review<br/>人工审核]
    DraftReply -->|low/medium urgency| SendReply[Send Reply<br/>发送回复]

    HumanReview -->|approved| SendReply
    HumanReview -->|rejected| DraftReply

    SendReply --> END([结束])

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style ClassifyIntent fill:#f59e0b,color:#fff
    style HumanReview fill:#f59e0b,color:#fff
    style DraftReply fill:#3b82f6,color:#fff
```

**流程说明：**
- **条件分支节点**（黄色）：Classify Intent 根据意图类型路由，Human Review 根据审核结果路由
- **汇聚节点**（蓝色）：Draft Reply 接收来自多个上游节点的输入
- **固定流转**：Read Email 始终前往 Classify Intent，Doc Search 和 Bug Track 始终前往 Draft Reply

**注意：** 有些节点会决定下一步的去向（Classify Intent、Draft Reply、Human Review），而其他节点则总是前往相同的下一步（Read Email 总是前往 Classify Intent，Doc Search 总是前往 Draft Reply）。

#### 步骤 2：确定每个步骤需要做什么

对于图中的每个节点，确定它代表的操作类型以及它正常工作所需的上下文。

**LLM 步骤（需要理解、分析、生成文本或做出推理决策）：**
- Classify intent（分类意图）
- Draft reply（起草回复）

**数据步骤（需要从外部来源获取信息）：**
- Doc Search（文档搜索）
- Customer History Lookup（客户历史查询）

**执行步骤（需要执行外部操作）：**
- Send Reply（发送回复）
  - 何时执行：审批后（人工或自动）
  - 重试策略：是，针对网络问题采用指数退避算法
  - 不应缓存：每次发送都是一个独特的操作
- Bug Track（漏洞追踪）
  - 何时执行：当意图为 "bug" 时始终执行
  - 重试策略：是，关键在于不丢失错误报告
  - 返回值：要包含在响应中的工单 ID

**用户输入步骤（需要人工干预）：**
- Human Review（人工审核）
  - 决策背景：原始邮件、回复草稿、紧急程度、分类
  - 预期输入格式：批准布尔值以及可选的编辑后回复
  - 触发条件：高紧急性、复杂问题或质量担忧

#### 步骤 3：设计你的状态

**状态（State）是智能体中所有节点都可访问的共享内存。** 可以将其视为智能体在处理过程中用来记录所学知识和所做决定的笔记本。

**针对每一条数据，问问自己：**
- 它需要在各个步骤中保持不变吗？如果需要，就将其放入状态中。
- 你能从其他数据中推导出它吗？如果可以，在需要的时候计算它，而不是将它存储在状态中。

**对于邮件智能体，我们需要跟踪：**
- 原始电子邮件和发件人信息（日后无法重建）
- 分类结果（多个后续/下游节点需要）
- 搜索结果和客户数据（重新获取成本高昂）
- 回复草稿（需要在审核过程中保留）
- 执行元数据（用于调试和恢复）

**状态设计原则：保持原始数据，按需格式化提示**

这种分离意味着：
- 不同的节点可以根据自身需求，对相同的数据进行不同的格式化处理
- 你可以更改提示模板，而无需修改你的状态模式
- 调试更加清晰——你能确切地看到每个节点接收到了哪些数据
- 你的智能体可以在不破坏现有状态的情况下进化

**定义状态：**

```python
from typing import TypedDict, Literal

# 定义邮件分类结构
class EmailClassification(TypedDict):
    intent: Literal["question", "bug", "billing", "feature", "complex"]
    urgency: Literal["low", "medium", "high", "critical"]
    topic: str
    summary: str

class EmailAgentState(TypedDict):
    # 原始邮件数据
    email_content: str
    sender_email: str
    email_id: str

    # 分类结果
    classification: EmailClassification | None

    # 原始搜索/API 结果
    search_results: list[str] | None  # 原始文档块列表
    customer_history: dict | None     # 从 CRM 获取的原始客户数据

    # 生成的内容
    draft_response: str | None
    messages: list[str] | None
```

**注意：** 状态仅包含原始数据——没有提示模板，没有格式化字符串，也没有指令。分类输出直接来自 LLM，以单个字典的形式存储。

#### 步骤 4：构建你的节点

现在我们将每个步骤实现为一个函数。LangGraph 中的节点只是一个 Python 函数，它接收当前状态并返回对其的更新。

**适当处理错误**

不同的错误需要不同的处理策略：

**1. 添加重试策略以自动重试网络问题和速率限制：**

```python
from langgraph.types import RetryPolicy

workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
)
```

**2. 将错误存储在状态中并循环返回，让 LLM 看到出了什么问题并重试：**

```python
from langgraph.types import Command

def execute_tool(state: State) -> Command[Literal["agent", "execute_tool"]]:
    try:
        result = run_tool(state['tool_call'])
        return Command(update={"tool_result": result}, goto="agent")
    except ToolError as e:
        # 让 LLM 看到出了什么问题并重试
        return Command(
            update={"tool_result": f"Tool error: {str(e)}"},
            goto="agent"
        )
```

**3. 在需要时暂停并从用户那里收集信息（如账户 ID、订单号或澄清）：**

```python
from langgraph.types import Command

def lookup_customer_history(state: State) -> Command[Literal["draft_response"]]:
    if not state.get('customer_id'):
        user_input = interrupt({
            "message": "需要客户 ID",
            "request": "请提供客户的账户 ID 以查询其订阅历史"
        })
        return Command(
            update={"customer_id": user_input['customer_id']},
            goto="lookup_customer_history"
        )
    # 现在继续查询
    customer_data = fetch_customer_history(state['customer_id'])
    return Command(update={"customer_history": customer_data}, goto="draft_response")
```

**节点实现示例：**

```python
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage

# 读取邮件节点
def read_email(state: EmailAgentState) -> dict:
    """提取并解析邮件内容"""
    email_content = state["email_content"]
    # 解析逻辑...
    return {"email_content": email_content}

# 分类意图节点
def classify_intent(state: EmailAgentState) -> Command[Literal["search_documentation", "bug_tracking", "draft_response"]]:
    """使用 LLM 对紧急程度和主题进行分类"""
    # 调用 LLM 进行分类
    classification = llm_classify(state["email_content"])

    # 根据分类结果路由
    if classification["intent"] == "bug":
        return Command(
            update={"classification": classification},
            goto="bug_tracking"
        )
    elif classification["intent"] == "question":
        return Command(
            update={"classification": classification},
            goto="search_documentation"
        )
    else:
        return Command(
            update={"classification": classification},
            goto="draft_response"
        )

# 搜索文档节点
def search_documentation(state: EmailAgentState) -> dict:
    """查询知识库以获取相关信息"""
    search_results = search_knowledge_base(state["classification"]["topic"])
    return {"search_results": search_results}

# 起草回复节点
def draft_response(state: EmailAgentState) -> Command[Literal["human_review", "send_reply"]]:
    """生成恰当的回复"""
    draft = generate_response(
        state["email_content"],
        state.get("search_results"),
        state.get("classification")
    )

    # 根据紧急程度决定是否需要人工审核
    if state["classification"]["urgency"] in ["high", "critical"]:
        return Command(update={"draft_response": draft}, goto="human_review")
    return Command(update={"draft_response": draft}, goto="send_reply")

# 人工审核节点
def human_review(state: EmailAgentState) -> Command[Literal["send_reply", "draft_response"]]:
    """提交给人工进行审批"""
    user_input = interrupt({
        "message": "需要人工审核",
        "draft_response": state["draft_response"],
        "urgency": state["classification"]["urgency"]
    })

    if user_input.get("approved"):
        # 如果有编辑后的回复，使用编辑后的版本
        edited = user_input.get("edited_response", state["draft_response"])
        return Command(update={"draft_response": edited}, goto="send_reply")
    else:
        # 需要重新起草
        return Command(
            update={"messages": ["人工要求重新起草"]},
            goto="draft_response"
        )

# 发送回复节点
def send_reply(state: EmailAgentState) -> dict:
    """发送电子邮件回复"""
    send_email(state["sender_email"], state["draft_response"])
    return {"messages": ["邮件已发送"]}
```

#### 步骤 5：将其连接起来

现在我们将节点连接成一个可运行的图。由于我们的节点会自行处理路由决策，因此我们只需要几条必要的边。

**要启用带 `interrupt()` 的人机协作功能，我们需要使用 checkpointer 编译以在运行之间保存状态：**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import RetryPolicy

# 创建图
workflow = StateGraph(EmailAgentState)

# 添加节点，配置适当的错误处理
workflow.add_node("read_email", read_email)
workflow.add_node("classify_intent", classify_intent)

# 为可能有瞬时故障的节点添加重试策略
workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3)
)
workflow.add_node("bug_tracking", bug_tracking)
workflow.add_node("draft_response", draft_response)
workflow.add_node("human_review", human_review)
workflow.add_node("send_reply", send_reply)

# 仅添加必要的边
workflow.add_edge(START, "read_email")
workflow.add_edge("read_email", "classify_intent")
workflow.add_edge("send_reply", END)

# 使用 checkpointer 编译以实现持久化
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

**图结构说明：** 该图结构十分简洁，因为路由是通过 `Command` 对象在节点内部进行的。每个节点都使用诸如 `Command[Literal["node1", "node2"]]` 之类的类型提示来声明其可到达的位置，这使得流程清晰明确且可追踪。

### 4.3 运行智能体

让我们用一个需要人工审核的紧急账单问题来运行我们的智能体。当图遇到 `interrupt()` 时会暂停，将所有内容保存到检查点，并等待。它可以在数天后恢复，精确地从上次中断的地方继续。`thread_id` 确保此对话的所有状态被一起保存。

```python
# 测试紧急账单问题
initial_state = {
    "email_content": "我的订阅被扣了两次款！这很紧急！",
    "sender_email": "customer@example.com",
    "email_id": "email_123",
    "messages": []
}

# 使用 thread_id 进行持久化运行
config = {"configurable": {"thread_id": "customer_123"}}
result = app.invoke(initial_state, config)

# 图将在 human_review 处暂停
print(f"人工审核中断: {result['__interrupt__']}")

# 当准备好时，提供人工输入以恢复
from langgraph.types import Command

human_response = Command(
    resume={
        "approved": True,
        "edited_response": "我们真诚地为双重扣款道歉。我已经立即发起了退款..."
    }
)

# 恢复执行
final_result = app.invoke(human_response, config)
print("邮件发送成功！")
```

### 4.4 小结

**Thinking in LangGraph 的核心要点：**

1. **拆解流程**：将复杂任务拆分为独立的节点步骤
2. **设计状态**：状态是节点间的共享内存，只存储需要持久化的原始数据
3. **节点职责**：每个节点只做一件事，返回状态更新
4. **路由决策**：使用 `Command` 对象在节点内部处理路由逻辑
5. **错误处理**：根据错误类型选择重试、循环返回或人工干预
6. **人机协作**：使用 `interrupt()` 暂停并等待人工输入

### 4.5 面试必背要点

**核心概念：**

| 问题 | 答案要点 |
|------|----------|
| **什么是节点？** | 执行特定操作的函数，接收状态并返回状态更新 |
| **什么是状态？** | 节点间的共享内存，所有节点都可读写 |
| **状态设计原则？** | 只存储原始数据，按需格式化提示，不存储派生数据 |
| **节点类型有哪些？** | LLM步骤（理解/生成）、数据步骤（外部获取）、执行步骤（外部操作）、用户输入步骤（人工干预） |

**错误处理：**

| 错误类型 | 处理方式 |
|----------|----------|
| **网络问题/速率限制** | 添加 `RetryPolicy` 自动重试 |
| **工具执行失败** | 将错误存储在状态中，循环返回让 LLM 重试 |
| **缺少必要信息** | 使用 `interrupt()` 暂停，从用户收集信息 |

**路由与控制流：**

| 问题 | 答案要点 |
|------|----------|
| **Command vs 条件边？** | Command 在节点内部处理路由+状态更新；条件边只处理路由 |
| **interrupt() 的作用？** | 暂停图执行，保存状态到检查点，等待人工输入后恢复 |
| **checkpointer 的作用？** | 持久化状态，支持中断恢复、时间旅行、人机协作 |
| **thread_id 的作用？** | 标识对话线程，确保同一对话的状态被一起保存 |

**代码实操：**

```python
# 1. 状态设计 - 只存原始数据
class State(TypedDict):
    email_content: str           # 原始邮件
    classification: dict | None  # LLM 分类结果
    search_results: list | None  # 原始搜索结果

# 2. 节点使用 Command 路由
def classify(state: State) -> Command[Literal["a", "b"]]:
    if state["classification"]["urgency"] == "high":
        return Command(update={}, goto="human_review")
    return Command(update={}, goto="send_reply")

# 3. 错误处理 - 重试策略
workflow.add_node("search", search_node, retry=RetryPolicy(max_attempts=3))

# 4. 人机协作 - interrupt 暂停
def human_review(state: State) -> Command:
    user_input = interrupt({"message": "需要审核"})
    if user_input["approved"]:
        return Command(update={}, goto="send")
    return Command(update={}, goto="draft")

# 5. 编译时添加 checkpointer
app = workflow.compile(checkpointer=MemorySaver())
```

**设计原则对比：**

| 对比项 | 好的设计 | 不好的设计 |
|--------|----------|------------|
| 状态存储 | 存储原始数据 | 存储格式化字符串 |
| 节点职责 | 单一职责 | 一个节点做多件事 |
| 路由方式 | Command 内部路由 | 复杂的条件边 |
| 错误处理 | 分类处理（重试/返回/人工） | 统一抛出异常 |

## 5. 工作流与智能体模式

本节回顾 LangGraph 中常见的工作流和智能体模式。

![Agent Workflow](/Users/songxijun/workspace/otherProject/ai-training/week04/docs/assets/agent_workflow.png)

### 5.1 工作流 vs 智能体

| 类型 | 特点 | 适用场景 |
|------|------|----------|
| **工作流（Workflows）** | 具有预先确定的代码路径，按特定顺序运行 | 任务流程明确、可预测 |
| **智能体（Agents）** | 动态自主定义流程和工具使用方式 | 问题复杂、解决方案难以预测 |

**工作流和智能体系统基于大语言模型（LLM）以及为其添加的各种增强功能：**
- **工具调用（Tool Calling）**：让 LLM 能够执行外部操作
- **结构化输出（Structured Outputs）**：让 LLM 返回格式化的数据
- **短期记忆（Short-term Memory）**：在对话中保持上下文

### 5.2 提示词链（Prompt Chaining）

**定义**：每个 LLM 调用都会处理上一次调用的输出。通常用于执行那些可以分解为更小、可验证步骤的明确定义的任务。

**典型场景**：
- 将文档翻译成不同的语言
- 验证生成内容的一致性

**流程图**：

```mermaid
flowchart LR
    A[输入] --> B[生成笑话]
    B --> C{检查笑点}
    C -->|Pass| D[结束]
    C -->|Fail| E[改进笑话]
    E --> F[润色笑话]
    F --> D
```

**代码示例**：

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# 定义状态
class State(TypedDict):
    topic: str
    joke: str
    improved_joke: str
    final_joke: str

# 节点：生成初始笑话
def generate_joke(state: State):
    """第一次 LLM 调用：生成初始笑话"""
    msg = llm.invoke(f"写一个关于 {state['topic']} 的短笑话")
    return {"joke": msg.content}

# 条件函数：检查笑话是否有笑点
def check_punchline(state: State):
    """门控函数：检查笑话是否包含笑点"""
    if "?" in state["joke"] or "!" in state["joke"]:
        return "Pass"
    return "Fail"

# 节点：改进笑话
def improve_joke(state: State):
    """第二次 LLM 调用：改进笑话"""
    msg = llm.invoke(f"通过添加双关语让这个笑话更有趣：{state['joke']}")
    return {"improved_joke": msg.content}

# 节点：润色笑话
def polish_joke(state: State):
    """第三次 LLM 调用：最终润色"""
    msg = llm.invoke(f"给这个笑话添加一个意想不到的反转：{state['improved_joke']}")
    return {"final_joke": msg.content}

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("generate_joke", generate_joke)
workflow.add_node("improve_joke", improve_joke)
workflow.add_node("polish_joke", polish_joke)

# 添加边
workflow.add_edge(START, "generate_joke")
workflow.add_conditional_edges(
    "generate_joke", check_punchline, {"Fail": "improve_joke", "Pass": END}
)
workflow.add_edge("improve_joke", "polish_joke")
workflow.add_edge("polish_joke", END)

# 编译
chain = workflow.compile()

# 调用
state = chain.invoke({"topic": "猫"})
print(state.get("final_joke", state["joke"]))
```

### 5.3 并行化（Parallelization）

**定义**：通过并行处理，LLM 可以同时处理多项任务。可以通过同时运行多个独立的子任务，或多次运行同一任务以检查不同输出来实现。

**典型场景**：
- 将子任务拆分并并行运行，提高速度
- 多次运行任务以检查不同的输出，增强可信度
- 一个子任务处理文档提取关键词，另一个检查格式错误
- 基于不同标准（引用数量、来源质量）对文档进行多次评分

**流程图**：

```mermaid
flowchart TB
    START([开始]) --> A[调用 LLM 1: 写笑话]
    START --> B[调用 LLM 2: 写故事]
    START --> C[调用 LLM 3: 写诗]
    A --> D[聚合器]
    B --> D
    C --> D
    D --> END([结束])
```

**代码示例**：

```python
# 定义状态
class State(TypedDict):
    topic: str
    joke: str
    story: str
    poem: str
    combined_output: str

# 节点：生成笑话
def call_llm_1(state: State):
    """第一次 LLM 调用：生成笑话"""
    msg = llm.invoke(f"写一个关于 {state['topic']} 的笑话")
    return {"joke": msg.content}

# 节点：生成故事
def call_llm_2(state: State):
    """第二次 LLM 调用：生成故事"""
    msg = llm.invoke(f"写一个关于 {state['topic']} 的故事")
    return {"story": msg.content}

# 节点：生成诗
def call_llm_3(state: State):
    """第三次 LLM 调用：生成诗"""
    msg = llm.invoke(f"写一首关于 {state['topic']} 的诗")
    return {"poem": msg.content}

# 节点：聚合结果
def aggregator(state: State):
    """将笑话、故事和诗合并为单个输出"""
    combined = f"这是关于 {state['topic']} 的故事、笑话和诗！\n\n"
    combined += f"故事：\n{state['story']}\n\n"
    combined += f"笑话：\n{state['joke']}\n\n"
    combined += f"诗：\n{state['poem']}"
    return {"combined_output": combined}

# 构建工作流
parallel_builder = StateGraph(State)
parallel_builder.add_node("call_llm_1", call_llm_1)
parallel_builder.add_node("call_llm_2", call_llm_2)
parallel_builder.add_node("call_llm_3", call_llm_3)
parallel_builder.add_node("aggregator", aggregator)

# 添加边（并行执行）
parallel_builder.add_edge(START, "call_llm_1")
parallel_builder.add_edge(START, "call_llm_2")
parallel_builder.add_edge(START, "call_llm_3")
parallel_builder.add_edge("call_llm_1", "aggregator")
parallel_builder.add_edge("call_llm_2", "aggregator")
parallel_builder.add_edge("call_llm_3", "aggregator")
parallel_builder.add_edge("aggregator", END)

parallel_workflow = parallel_builder.compile()
```

### 5.4 路由（Routing）

**定义**：路由工作流对输入进行处理，然后将其导向特定于上下文的任务。这使你能够为复杂任务定义专门的流程。

**典型场景**：
- 回答产品相关问题：先处理问题类型，然后路由到定价、退款、退货等特定流程

**流程图**：

```mermaid
flowchart TB
    START([开始]) --> A[路由器]
    A -->|story| B[写故事]
    A -->|joke| C[写笑话]
    A -->|poem| D[写诗]
    B --> END([结束])
    C --> END
    D --> END
```

**代码示例**：

```python
from typing_extensions import Literal
from langchain.messages import HumanMessage, SystemMessage

# 结构化输出模式，用于路由逻辑
class Route(BaseModel):
    step: Literal["poem", "story", "joke"] = Field(
        None, description="路由过程中的下一步"
    )

# 为 LLM 添加结构化输出能力
router = llm.with_structured_output(Route)

# 定义状态
class State(TypedDict):
    input: str
    decision: str
    output: str

# 节点：写故事
def llm_call_1(state: State):
    result = llm.invoke(state["input"])
    return {"output": result.content}

# 节点：写笑话
def llm_call_2(state: State):
    result = llm.invoke(state["input"])
    return {"output": result.content}

# 节点：写诗
def llm_call_3(state: State):
    result = llm.invoke(state["input"])
    return {"output": result.content}

# 节点：路由决策
def llm_call_router(state: State):
    """将输入路由到适当的节点"""
    decision = router.invoke([
        SystemMessage(content="根据用户的请求，将输入路由到 story、joke 或 poem"),
        HumanMessage(content=state["input"])
    ])
    return {"decision": decision.step}

# 条件边函数
def route_decision(state: State):
    if state["decision"] == "story":
        return "llm_call_1"
    elif state["decision"] == "joke":
        return "llm_call_2"
    elif state["decision"] == "poem":
        return "llm_call_3"

# 构建工作流
router_builder = StateGraph(State)
router_builder.add_node("llm_call_1", llm_call_1)
router_builder.add_node("llm_call_2", llm_call_2)
router_builder.add_node("llm_call_3", llm_call_3)
router_builder.add_node("llm_call_router", llm_call_router)

# 添加边
router_builder.add_edge(START, "llm_call_router")
router_builder.add_conditional_edges(
    "llm_call_router", # 【起点节点】：从哪个节点出发做路由判断
    route_decision,    # 【路由函数】：决定下一步去哪的逻辑函数
    {"llm_call_1": "llm_call_1", "llm_call_2": "llm_call_2", "llm_call_3": "llm_call_3"} # 【映射字典】：路由结果 → 目标节点
)
router_builder.add_edge("llm_call_1", END)
router_builder.add_edge("llm_call_2", END)
router_builder.add_edge("llm_call_3", END)

router_workflow = router_builder.compile()
```

### 5.5 协调器-工作器（Orchestrator-Worker）

**定义**：协调器负责任务分解、分配子任务给工作节点、并将工作节点的输出合成为最终结果。这种模式提供了更大的灵活性，通常在子任务无法预先定义时使用。

**典型场景**：
- 编写代码或需要跨多个文件更新内容的工作流
- 需要在数量未知的文档中更新多个 Python 库的安装说明

**流程图**：

```mermaid
flowchart TB
    START([开始]) --> A[协调器: 规划任务]
    A --> B[工作器 1]
    A --> C[工作器 2]
    A --> D[工作器 3]
    B --> E[合成器: 合并结果]
    C --> E
    D --> E
    E --> END([结束])
```

**代码示例**：

```python
from typing import Annotated, List
import operator
from langgraph.types import Send

# 结构化输出：章节规划
class Section(BaseModel):
    name: str = Field(description="报告章节名称")
    description: str = Field(description="章节主题概述")

class Sections(BaseModel):
    sections: List[Section] = Field(description="报告的章节列表")

planner = llm.with_structured_output(Sections)

# 图状态
class State(TypedDict):
    topic: str  # 报告主题
    sections: list[Section]  # 章节列表
    completed_sections: Annotated[list, operator.add]  # 所有工作器并行写入
    final_report: str  # 最终报告

# 工作器状态
class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]

# 节点：协调器
def orchestrator(state: State):
    """协调器：生成报告计划"""
    report_sections = planner.invoke([
        SystemMessage(content="生成报告计划"),
        HumanMessage(content=f"报告主题：{state['topic']}")
    ])
    return {"sections": report_sections.sections}

# 节点：工作器
def llm_call(state: WorkerState):
    """工作器：编写报告章节"""
    section = llm.invoke([
        SystemMessage(content="根据提供的名称和描述编写报告章节"),
        HumanMessage(content=f"章节名称：{state['section'].name}，描述：{state['section'].description}")
    ])
    return {"completed_sections": [section.content]}

# 节点：合成器
def synthesizer(state: State):
    """合成器：将章节合并为完整报告"""
    completed_report_sections = "\n\n---\n\n".join(state["completed_sections"])
    return {"final_report": completed_report_sections}

# 条件边：分配工作器
def assign_workers(state: State):
    """为每个章节分配一个工作器"""
    return [Send("llm_call", {"section": s}) for s in state["sections"]]

# 构建工作流
orchestrator_worker_builder = StateGraph(State)
orchestrator_worker_builder.add_node("orchestrator", orchestrator)
orchestrator_worker_builder.add_node("llm_call", llm_call)
orchestrator_worker_builder.add_node("synthesizer", synthesizer)

# 添加边
orchestrator_worker_builder.add_edge(START, "orchestrator")
orchestrator_worker_builder.add_conditional_edges("orchestrator", assign_workers, ["llm_call"])
orchestrator_worker_builder.add_edge("llm_call", "synthesizer")
orchestrator_worker_builder.add_edge("synthesizer", END)

orchestrator_worker = orchestrator_worker_builder.compile()
```

### 5.6 评估器-优化器（Evaluator-Optimizer）

**定义**：一个 LLM 调用生成响应，另一个评估该响应。如果评估器或人工判定响应需要改进，就会提供反馈并重新生成响应，直到生成可接受的响应为止。

**典型场景**：
- 任务有特定的成功标准，但需要通过迭代来满足
- 翻译文本：可能需要几次迭代才能生成在两种语言中含义相同的翻译

**流程图**：

```mermaid
flowchart TB
    START([开始]) --> A[生成器]
    A --> B[评估器]
    B --> C{评估结果}
    C -->|Accepted| END([结束])
    C -->|Rejected + Feedback| A
```

**代码示例**：

```python
# 定义状态
class State(TypedDict):
    joke: str
    topic: str
    feedback: str
    funny_or_not: str

# 结构化输出：评估反馈
class Feedback(BaseModel):
    grade: Literal["funny", "not funny"] = Field(description="判断笑话是否好笑")
    feedback: str = Field(description="如果不好笑，提供改进建议")

evaluator = llm.with_structured_output(Feedback)

# 节点：生成笑话
def llm_call_generator(state: State):
    """LLM 生成笑话"""
    if state.get("feedback"):
        msg = llm.invoke(f"写一个关于 {state['topic']} 的笑话，参考反馈：{state['feedback']}")
    else:
        msg = llm.invoke(f"写一个关于 {state['topic']} 的笑话")
    return {"joke": msg.content}

# 节点：评估笑话
def llm_call_evaluator(state: State):
    """LLM 评估笑话"""
    grade = evaluator.invoke(f"评估这个笑话：{state['joke']}")
    return {"funny_or_not": grade.grade, "feedback": grade.feedback}

# 条件边：路由
def route_joke(state: State):
    """根据评估结果决定是否重新生成"""
    if state["funny_or_not"] == "funny":
        return "Accepted"
    elif state["funny_or_not"] == "not funny":
        return "Rejected + Feedback"

# 构建工作流
optimizer_builder = StateGraph(State)
optimizer_builder.add_node("llm_call_generator", llm_call_generator)
optimizer_builder.add_node("llm_call_evaluator", llm_call_evaluator)

# 添加边
optimizer_builder.add_edge(START, "llm_call_generator")
optimizer_builder.add_edge("llm_call_generator", "llm_call_evaluator")
optimizer_builder.add_conditional_edges(
    "llm_call_evaluator",
    route_joke,
    {"Accepted": END, "Rejected + Feedback": "llm_call_generator"}
)

optimizer_workflow = optimizer_builder.compile()
```

### 5.7 智能体（Agent）

**定义**：智能体通过 LLM 使用工具来执行操作，在持续的反馈循环中运行。与工作流相比，智能体具有更高的自主性，能够自主决定使用哪些工具以及如何解决问题。

**特点**：
- 适用于问题和解决方案都难以预测的场景
- 可以定义智能体可用的工具集以及其行为准则
- LLM 自主决定是否调用工具

**流程图**：

```mermaid
flowchart TB
    START([开始]) --> A[LLM 调用]
    A --> B{需要工具?}
    B -->|是| C[执行工具]
    C --> A
    B -->|否| END([结束])
```

**代码示例**：

```python
from langchain.tools import tool
from langgraph.graph import MessagesState
from langchain.messages import SystemMessage, HumanMessage, ToolMessage

# 定义工具
@tool
def multiply(a: int, b: int) -> int:
    """将 a 和 b 相乘"""
    return a * b

@tool
def add(a: int, b: int) -> int:
    """将 a 和 b 相加"""
    return a + b

@tool
def divide(a: int, b: int) -> float:
    """将 a 除以 b"""
    return a / b

# 绑定工具到 LLM
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)

# 节点：LLM 调用
def llm_call(state: MessagesState):
    """LLM 决定是否调用工具"""
    return {
        "messages": [
            llm_with_tools.invoke([
                SystemMessage(content="你是一个帮助执行算术运算的助手")
            ] + state["messages"])
        ]
    }

# 节点：执行工具
def tool_node(state: dict):
    """执行工具调用"""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

# 条件边：决定是否继续
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """根据 LLM 是否调用工具决定继续循环还是停止"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    return END

# 构建智能体
agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

# 添加边
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")

agent = agent_builder.compile()

# 调用
messages = [HumanMessage(content="计算 3 加 4")]
result = agent.invoke({"messages": messages})
```

### 5.8 模式选择指南

| 模式 | 适用场景 | 复杂度 | 灵活性 |
|------|----------|--------|--------|
| **提示词链** | 任务可分解为顺序步骤 | 低 | 低 |
| **并行化** | 多个独立子任务 | 中 | 中 |
| **路由** | 需要根据输入选择不同处理路径 | 中 | 中 |
| **协调器-工作器** | 子任务数量不固定 | 高 | 高 |
| **评估器-优化器** | 需要迭代优化直到满足标准 | 中 | 中 |
| **智能体** | 问题复杂、解决方案难以预测 | 高 | 最高 |

## 6. Graph API 概述与核心概念

LangGraph 的核心是将智能体工作流建模为图。你可以使用三个关键组件来定义智能体的行为：

- **State（状态）**：一种共享数据结构，用于表示应用程序的当前快照。它可以是任何数据类型，但通常使用共享状态模式来定义
- **Nodes（节点）**：对智能体逻辑进行编码的函数。它们接收当前状态作为输入，执行某些计算或副作用，并返回更新后的状态
- **Edges（边）**：根据当前状态确定下一个要执行的 Node 的函数。它们可以是条件分支或固定转换

**简而言之：节点执行工作，边决定接下来做什么。**

通过组合 Nodes 和 Edges，你可以创建复杂的、循环的工作流，这些工作流会随着时间推移不断更新状态。Nodes 和 Edges 只不过是函数——它们可以包含一个大语言模型，或者仅仅是一些传统代码。

### 6.1 执行模型

LangGraph 的底层运行时由 Pregel 实现，管理 LangGraph 应用程序的执行。编译 `StateGraph` 或创建 `@entrypoint` 会生成一个 Pregel 实例。Pregel 运行时得名于谷歌的 Pregel 算法，该算法描述了一种使用图进行大规模并行计算的高效方法。

在 LangGraph 中，Pregel 将参与者（actors）和通道（channels）组合成一个应用程序。参与者从通道读取数据并向通道写入数据。Pregel 遵循 Pregel 算法/批量同步并行模型，将应用程序的执行组织为多个步骤。

**每个步骤包含三个阶段：**

1. **计划（Plan）**：确定此步骤中要执行哪些参与者。例如，在第一步中选择订阅特殊输入通道的参与者；在后续步骤中选择订阅上一步骤中更新的通道的参与者。
2. **执行（Execution）**：并行执行所有选定的参与者，直到全部完成、其中一个失败或达到超时时间。在此阶段，通道更新对参与者而言是不可见的，直至下一步。
3. **更新（Update）**：使用本步骤中参与者写入的值更新通道。

重复执行，直到没有参与者被选中执行，或者达到最大步骤数。

**超级步骤（Super-step）：**
- 可以被视为对图节点的一次迭代
- 并行运行的节点属于同一个超级步骤
- 顺序运行的节点属于不同的超级步骤

**通道类型：**

| 通道类型 | 说明 |
|----------|------|
| **LastValue** | 存储发送到该通道的最后一个值，适用于输入和输出值 |
| **Topic** | 可配置的发布订阅主题，适用于在角色之间发送多个值或累积输出。可配置为去除重复项或在多个步骤中累积值 |
| **BinaryOperatorAggregate** | 存储持久值，通过二进制操作符更新，适用于计算多步骤聚合（如求和、累积） |

**高级 API：**

LangGraph 提供了两个用于创建 Pregel 应用程序的高级 API：
- **StateGraph（图 API）**：更高级的抽象，简化 Pregel 应用程序的创建，允许定义节点和边的图
- **Functional API**：函数式风格的 API

### 6.2 StateGraph

`StateGraph` 类是要使用的主图类。它由用户定义的 State 对象进行参数化。

```python
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    messages: list[str]

builder = StateGraph(State)
# 添加节点和边...
graph = builder.compile()
```

### 6.3 编译图

要构建你的图，首先需要定义状态，然后添加节点和边，接着进行编译。

编译是一个相当简单的步骤：
- 对图结构进行基本检查（例如没有孤立节点等）
- 可以指定运行时参数，如检查点工具和断点

```python
graph = graph_builder.compile(...)
```

> **注意**：在使用图之前，你必须对其进行编译。

### 6.4 State（状态）

定义图时，首先要做的是定义图的 State。State 由图的模式以及 reducer 函数组成，其中 reducer 函数指定了如何对状态应用更新。

**模式类型：**
- `TypedDict`：主要推荐的方式
- `dataclass`：如果想在状态中提供默认值
- `Pydantic BaseModel`：如果需要递归数据验证（性能较低）

**默认行为（覆盖更新）：**

```python
from typing_extensions import TypedDict

class State(TypedDict):
    foo: int
    bar: list[str]
```

如果没有为任何键指定归约函数，每次更新都会覆盖该键的值。

**自定义行为（追加/累加）：**

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: int
    bar: Annotated[list[str], add]  # 列表追加而不是覆盖
```

### 6.5 多个模式

通常情况下，所有图形节点都通过单一模式进行通信。但在某些情况下，我们希望对此拥有更多控制权：

**场景：**
- 内部节点可以传递图的输入/输出中不需要的信息
- 为图使用不同的输入/输出模式

**示例：**

```python
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    foo: str
    user_input: str
    graph_output: str

class PrivateState(TypedDict):
    bar: str

def node_1(state: InputState) -> OverallState:
    return {"foo": state["user_input"] + " name"}

def node_2(state: OverallState) -> PrivateState:
    return {"bar": state["foo"] + " is"}

def node_3(state: PrivateState) -> OutputState:
    return {"graph_output": state["bar"] + " Lance"}

builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

graph = builder.compile()
graph.invoke({"user_input": "My"})
# {'graph_output': 'My name is Lance'}
```

### 6.6 Reducers（归约器）

Reducers 是理解节点更新如何应用于 State 的关键。State 中的每个键都有其独立的归约器函数。

**默认归约器：** 如果未明确指定归约器函数，则默认对该键的所有更新都应覆盖它。

**带 Annotated 的归约器：** 使用 `Annotated` 类型指定归约函数。

```python
from typing import Annotated
from operator import add

class State(TypedDict):
    # 默认：覆盖
    foo: int
    # 使用 add 归约器：追加
    bar: Annotated[list[str], add]
```

### 6.7 消息处理

大多数现代大模型提供商都有一个聊天模型接口，该接口接受消息列表作为输入。

**使用 add_messages：**

```python
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

`add_messages` 函数的功能：
- **智能追加**：将新消息添加到现有列表中
- **按 ID 去重**：如果消息 ID 已存在，则覆盖更新
- **序列化**：自动将消息反序列化为 LangChain Message 对象

**MessagesState：**

由于在状态中包含消息列表非常常见，LangGraph 提供了预构建的 `MessagesState`：

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    documents: list[str]  # 添加更多字段
```

### 6.8 Nodes（节点）

在 LangGraph 中，节点是 Python 函数（同步或异步），接受以下参数：
- `state`：图的状态
- `config`：包含配置信息（如 thread_id）和跟踪信息的 RunnableConfig 对象
- `runtime`：包含运行时上下文和其他信息的 Runtime 对象

```python
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

def plain_node(state: State):
    return state

def node_with_runtime(state: State, runtime: Runtime[Context]):
    print("用户ID: ", runtime.context.user_id)
    return {"results": f"Hello, {state['input']}!"}

def node_with_config(state: State, config: RunnableConfig):
    print("线程ID: ", config["configurable"]["thread_id"])
    return {"results": f"Hello, {state['input']}!"}

builder.add_node("plain_node", plain_node)
builder.add_node("node_with_runtime", node_with_runtime)
builder.add_node("node_with_config", node_with_config)
```

**START 节点：** 代表将用户输入发送到图的节点。

```python
from langgraph.graph import START
graph.add_edge(START, "node_a")
```

**END 节点：** 代表终端节点。

```python
from langgraph.graph import END
graph.add_edge("node_a", END)
```

### 6.9 节点缓存

LangGraph 支持基于节点输入对任务/节点进行缓存：

```python
from langgraph.cache.memory import InMemoryCache
from langgraph.types import CachePolicy

def expensive_node(state: State) -> dict:
    # 高成本计算
    time.sleep(2)
    return {"result": state["x"] * 2}

builder.add_node("expensive_node", expensive_node, cache_policy=CachePolicy(ttl=3))
graph = builder.compile(cache=InMemoryCache())
```

### 6.10 Edges（边）

边定义了逻辑的路由方式以及图决定停止的方式。

**普通边：** 直接从一个节点到下一个节点。

```python
graph.add_edge("node_a", "node_b")
```

**条件边：** 调用函数以确定接下来要前往哪个节点。

```python
graph.add_conditional_edges("node_a", routing_function)
# 或带映射
graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
```

**入口点：** 用户输入到达时首先调用哪个节点。

```python
from langgraph.graph import START
graph.add_edge(START, "node_a")
```

**条件入口点：** 根据自定义逻辑从不同节点开始。

```python
graph.add_conditional_edges(START, routing_function)
```

### 6.11 Send

用于 map-reduce 设计模式，当边数量未知时：

```python
def continue_to_jokes(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state['subjects']]

graph.add_conditional_edges("node_a", continue_to_jokes)
```

### 6.12 Command

将控制流（边）和状态更新（节点）结合起来：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        update={"foo": "bar"},  # 状态更新
        goto="my_other_node"     # 控制流
    )
```

**何时使用 Command vs 条件边：**
- 使用 **Command**：当需要同时更新图状态和路由到不同节点
- 使用 **条件边**：当只需要有条件地在节点之间路由而不更新状态

**导航到父图中的节点：**

```python
def my_node(state: State) -> Command[Literal["other_subgraph"]]:
    return Command(
        update={"foo": "bar"},
        goto="other_subgraph",
        graph=Command.PARENT  # 导航到最近的父图
    )
```

### 6.13 运行时上下文

创建图时，可以指定 `context_schema` 用于传递不属于图状态的信息：

```python
@dataclass
class ContextSchema:
    llm_provider: str = "openai"

graph = StateGraph(State, context_schema=ContextSchema)

# 调用时传递上下文
graph.invoke(inputs, context={"llm_provider": "anthropic"})

# 节点中访问
def node_a(state: State, runtime: Runtime[ContextSchema]):
    llm = get_llm(runtime.context.llm_provider)
```

### 6.14 递归限制

递归限制设置了图在单次执行过程中可以执行的超级步骤的最大数量。默认限制为 1000 步。

```python
graph.invoke(inputs, config={"recursion_limit": 5})
```

**访问当前步骤计数器：**

```python
def my_node(state: dict, config: RunnableConfig) -> dict:
    current_step = config["metadata"]["langgraph_step"]
    print(f"当前步骤: {current_step}")
    return state
```

**使用 RemainingSteps 进行主动处理：**

```python
from langgraph.managed import RemainingSteps

class State(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    remaining_steps: RemainingSteps

def reasoning_node(state: State) -> dict:
    remaining = state["remaining_steps"]
    if remaining <= 2:
        return {"messages": ["接近限制，正在收尾..."]}
    return {"messages": ["思考中..."]}
```

### 6.15 图迁移

LangGraph 可以轻松处理图定义的迁移：

- **对于图末端的线程**：可以更改整个拓扑结构（所有节点和边）
- **对于被中断的线程**：支持除重命名/移除节点外的所有拓扑变更
- **状态键**：添加和删除键具有完全的前后兼容性
- **重命名的状态键**：会丢失其在现有线程中保存的状态

### 6.16 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **LangGraph 的三个核心组件？** | State（状态）、Nodes（节点）、Edges（边） |
| **什么是超级步骤？** | 对图节点的一次迭代，并行节点属于同一超级步骤，顺序节点属于不同超级步骤 |
| **为什么需要编译图？** | 1) 基本检查（无孤立节点）；2) 指定运行时参数（checkpointer、断点） |

**State 类：**

| 问题 | 答案要点 |
|------|----------|
| **State 的三种模式类型？** | TypedDict（推荐）、dataclass（默认值）、Pydantic（验证） |
| **默认 reducer 行为？** | 覆盖更新 |
| **如何实现列表追加？** | 使用 `Annotated[list[str], add]` |
| **MessagesState 的作用？** | 预构建的消息列表状态，使用 add_messages 归约器 |

**Nodes 和 Edges 类：**

| 问题 | 答案要点 |
|------|----------|
| **节点的参数？** | state、config、runtime |
| **START 和 END 节点？** | START：用户输入入口；END：终端节点 |
| **普通边 vs 条件边？** | 普通：固定流转；条件：根据状态选择下一节点 |
| **Send 的用途？** | map-reduce 模式，边数量未知时使用 |
| **Command 的用途？** | 同时更新状态和路由，用于多智能体交接 |

**代码实操类：**

```python
# 1. 定义 State
class State(TypedDict):
    messages: Annotated[list[str], add]

# 2. 定义节点
def my_node(state: State) -> dict:
    return {"messages": ["新消息"]}

# 3. 构建图
builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)

# 4. 编译并运行
graph = builder.compile(checkpointer=MemorySaver())
result = graph.invoke({"messages": []}, config={"configurable": {"thread_id": "1"}})

# 5. 条件边
def route(state: State) -> Literal["a", "b"]:
    return "a" if state["messages"] else "b"
builder.add_conditional_edges("my_node", route)

# 6. Command
def node_with_command(state: State) -> Command[Literal["next"]]:
    return Command(update={"foo": "bar"}, goto="next")
```

**对比记忆类：**

| 对比项 | 默认 reducer | 带 Annotated 的 reducer |
|--------|--------------|-------------------------|
| 更新方式 | 覆盖 | 追加/合并 |
| 典型用途 | 单值字段 | 列表、消息历史 |

| 对比项 | 条件边 | Command |
|--------|--------|---------|
| 状态更新 | 不更新 | 可以更新 |
| 路由控制 | 是 | 是 |
| 适用场景 | 纯路由 | 多智能体交接 |

## 7. Graph API 实战指南

本章提供 Graph API 的实际使用示例，涵盖状态定义、reducer、分支、循环、异步等核心操作。

### 7.1 定义和更新状态

**基本状态定义：**

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: int
    bar: str
    baz: Annotated[list[str], add]  # 使用 add reducer 进行列表追加
```

**更新状态：**

节点函数返回一个字典，表示要更新的状态键。如果没有为某个键指定 reducer，则新值将覆盖旧值。

```python
def my_node(state: State) -> dict:
    # 覆盖 foo，追加到 baz
    return {"foo": 5, "baz": ["新项目"]}
```

### 7.2 Reducers 使用

**add reducer：**

使用 `operator.add` 或 `Annotated` 来指定列表追加行为：

```python
from typing import Annotated
from operator import add

def reduce_list(left: list | None, right: list | None) -> list:
    """自定义列表合并 reducer"""
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

class State(TypedDict):
    # 使用 operator.add（效果相同）
    messages: Annotated[list, add]
```

**add_messages reducer：**

用于处理消息列表的专用 reducer，支持追加和删除消息：

```python
from langgraph.graph import MessageGraph
from langchain_core.messages import AnyMessage, RemoveMessage

# MessagesState 预置了 add_messages reducer
from langgraph.graph import MessagesState

class State(MessagesState):
    # 继承 messages: Annotated[list[AnyMessage], add_messages]
    extra_field: str

# 删除消息示例
def delete_messages(state: State) -> dict:
    # 删除最后一条消息之前的所有消息
    messages = state["messages"]
    delete_messages = [RemoveMessage(id=m.id) for m in messages[:-1]]
    return {"messages": delete_messages}
```

### 7.3 Overwrite 类型

当使用 reducer 时，有时需要绕过 reducer 直接覆盖值。使用 `Overwrite` 类型：

```python
from langgraph.graph import StateGraph, START, END
from typing import Annotated
from operator import add
from langgraph.typing import Overwrite

class State(TypedDict):
    items: Annotated[list[str], add]

def node_a(state: State) -> dict:
    # 正常追加
    return {"items": ["a", "b"]}

def node_b(state: State) -> dict:
    # 覆盖而不是追加
    return {"items": Overwrite(["x", "y"])}

builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_node("b", node_b)
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("b", END)

graph = builder.compile()
result = graph.invoke({"items": []})
# result["items"] = ["x", "y"]（被覆盖）
```

### 7.4 输入/输出模式

为图定义不同的输入和输出模式：

```python
from typing_extensions import TypedDict

class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    foo: str
    user_input: str
    graph_output: str

def node(state: OverallState) -> dict:
    # 处理逻辑
    return {"graph_output": state["user_input"] + " processed"}

builder = StateGraph(OverallState, input=InputState, output=OutputState)
builder.add_node("node", node)
builder.add_edge(START, "node")
builder.add_edge("node", END)

graph = builder.compile()
# 输入只需要 user_input
result = graph.invoke({"user_input": "hello"})
# 输出只有 graph_output
print(result)  # {"graph_output": "hello processed"}
```

### 7.5 私有状态

在节点之间传递不需要在图的输入/输出中暴露的私有状态：

```python
class Node1Output(TypedDict):
    private_data: str

def node1(state: OverallState) -> Node1Output:
    return {"private_data": "secret"}

def node2(state: OverallState | Node1Output) -> dict:
    # 可以访问 private_data
    return {"graph_output": state["private_data"] + " used"}

builder = StateGraph(OverallState)
builder.add_node("node1", node1)
builder.add_node("node2", node2)
builder.add_edge(START, "node1")
builder.add_edge("node1", "node2")
builder.add_edge("node2", END)
```

### 7.6 Pydantic 模型

使用 Pydantic 进行数据验证：

```python
from pydantic import BaseModel, field_validator

class State(BaseModel):
    foo: int
    bar: list[str]

    @field_validator("foo")
    @classmethod
    def validate_foo(cls, v):
        if v < 0:
            raise ValueError("foo must be non-negative")
        return v

def node(state: State) -> dict:
    return {"foo": state.foo + 1}

builder = StateGraph(State)
# 注意：Pydantic 模型性能略低于 TypedDict
```

### 7.7 运行时配置

在节点中访问运行时配置：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_config

class State(TypedDict):
    messages: list[str]

def node(state: State) -> dict:
    config = get_config()
    user_id = config["configurable"]["user_id"]
    return {"messages": [f"Hello {user_id}"]}

builder = StateGraph(State)
builder.add_node("node", node)
builder.add_edge(START, "node")
builder.add_edge("node", END)

graph = builder.compile()
result = graph.invoke(
    {"messages": []},
    config={"configurable": {"user_id": "alice"}}
)
```

**context_schema：**

为运行时配置定义模式：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_config
from dataclasses import dataclass

@dataclass
class MyContext:
    user_id: str
    tier: str = "free"

class State(TypedDict):
    messages: list[str]

def node(state: State) -> dict:
    config = get_config()
    context: MyContext = config["context"]
    return {"messages": [f"User: {context.user_id}, Tier: {context.tier}"]}

builder = StateGraph(State, context_schema=MyContext)
builder.add_node("node", node)
builder.add_edge(START, "node")
builder.add_edge("node", END)

graph = builder.compile()
result = graph.invoke(
    {"messages": []},
    config={"context": MyContext(user_id="alice", tier="premium")}
)
```

### 7.8 重试策略

在许多使用场景中，你可能希望节点具有自定义的重试策略，例如在调用 API、查询数据库或调用大语言模型等情况下。LangGraph 允许你为节点添加重试策略。

要配置重试策略，请将 `retry_policy` 参数传递给 `add_node`。`retry_policy` 参数接收一个 `RetryPolicy` 命名元组对象。下面我们使用默认参数实例化一个 `RetryPolicy` 对象，并将其与一个节点相关联：

```python
from langgraph.types import RetryPolicy

builder.add_node(
    "node_name",
    node_function,
    retry_policy=RetryPolicy(),
)
```

**默认重试策略：**

默认情况下，`retry_on` 参数使用 `default_retry_on` 函数，该函数会对任何异常进行重试，除了以下情况：

| 不重试的异常类型 |
|------------------|
| ValueError |
| TypeError |
| ArithmeticError |
| ImportError |
| LookupError |
| NameError |
| SyntaxError |
| RuntimeError |
| ReferenceError |
| StopIteration |
| StopAsyncIteration |
| OSError |

此外，对于来自 `requests` 和 `httpx` 等常用 HTTP 请求库的异常，它仅在出现 5xx 状态码时重试。

**扩展示例：自定义重试策略**

考虑一个从 SQL 数据库读取数据的例子，我们传递两种不同的重试策略给节点：

```python
import sqlite3
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.types import RetryPolicy
from langchain_community.utilities import SQLDatabase
from langchain.messages import AIMessage

db = SQLDatabase.from_uri("sqlite:///:memory:")
model = init_chat_model("claude-haiku-4-5-20251001")

def query_database(state: MessagesState):
    query_result = db.run("SELECT * FROM Artist LIMIT 10;")
    return {"messages": [AIMessage(content=query_result)]}

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# 定义图
builder = StateGraph(MessagesState)
builder.add_node(
    "query_database",
    query_database,
    retry_policy=RetryPolicy(retry_on=sqlite3.OperationalError),
)
builder.add_node("model", call_model, retry_policy=RetryPolicy(max_attempts=5))
builder.add_edge(START, "model")
builder.add_edge("model", "query_database")
builder.add_edge("query_database", END)
graph = builder.compile()
```

### 7.9 节点缓存

要配置缓存策略，请将 `cache_policy` 参数传递给 `add_node` 函数。在下面的示例中，实例化了一个 `CachePolicy` 对象，其生存时间为 120 秒，并使用默认的 `key_func` 生成器。然后将其与节点相关联：

```python
from langgraph.types import CachePolicy

builder.add_node(
    "node_name",
    node_function,
    cache_policy=CachePolicy(ttl=120),
)
```

然后，要为图启用节点级缓存，请在编译图时设置 `cache` 参数。下面的示例使用 `InMemoryCache` 来设置具有内存缓存的图，但也可以使用 `SqliteCache`。

```python
from langgraph.cache.memory import InMemoryCache

graph = builder.compile(cache=InMemoryCache())
```

### 7.10 创建序列

本节演示如何构建一个简单的步骤序列，包括如何构建顺序图以及内置的简写方式。

**为什么要使用 LangGraph 将应用步骤拆分为序列？**

LangGraph 能轻松为你的应用添加底层持久化层。这使得状态可以在节点执行间隙进行检查点保存，因此你的 LangGraph 节点可控制：
- 状态更新是如何被检查点保存
- 在"人机协作"工作流中如何恢复中断
- 如何利用 LangGraph 的时间旅行功能来"回退"和分支执行
- 执行步骤如何被流式传输，以及如何使用 Studio 对应用程序进行可视化和调试

**定义状态：**

```python
from typing_extensions import TypedDict

class State(TypedDict):
    value_1: str
    value_2: int
```

**定义节点：**

节点只是 Python 函数，它们读取图的状态并对其进行更新。第一个参数始终是状态：

```python
def step_1(state: State):
    return {"value_1": "a"}

def step_2(state: State):
    current_value_1 = state["value_1"]
    return {"value_1": f"{current_value_1} b"}

def step_3(state: State):
    return {"value_2": 10}
```

在发布对状态的更新时，每个节点只需指定其希望更新的键的值即可。默认情况下，这将覆盖相应键的值。

**构建图：**

使用 `add_node` 和 `add_edge` 来填充图并定义控制流：

```python
from langgraph.graph import START, StateGraph

builder = StateGraph(State)

# 添加节点
builder.add_node(step_1)
builder.add_node(step_2)
builder.add_node(step_3)

# 添加边
builder.add_edge(START, "step_1")
builder.add_edge("step_1", "step_2")
builder.add_edge("step_2", "step_3")
```

**指定自定义名称：**

可以使用 `add_node` 为节点指定自定义名称：

```python
builder.add_node("my_node", step_1)
```

注意事项：
- `add_edge` 接收节点名称，对于函数而言，其默认值为 `node.__name__`
- 必须指定图的入口点，为此添加一条与 `START` 节点相连的边
- 当没有更多节点可执行时，图会停止运行

**编译和运行：**

```python
graph = builder.compile()

# 可视化
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))

# 调用
result = graph.invoke({"value_1": "c"})
# {'value_1': 'a b', 'value_2': 10}
```

**内置简写：**

`langgraph>=0.2.46` 包含一个用于添加节点序列的内置简写 `add_sequence`：

```python
builder = StateGraph(State).add_sequence([step_1, step_2, step_3])
builder.add_edge(START, "step_1")

graph = builder.compile()
graph.invoke({"value_1": "c"})
```

### 7.11 创建分支

节点的并行执行对于加快整体图操作至关重要。LangGraph 原生支持节点的并行执行，这能显著提升基于图的工作流的性能。这种并行化是通过扇出和扇入机制实现的，同时利用了标准边和条件边。

#### 并行运行图节点

在这个示例中，我们从 Node A 扇出到 B 和 C，然后扇入到 D。在状态中指定 `operator.add` 归约器，这将合并或累加状态中特定键的值，而不是简单地覆盖现有值。对于列表，这意味着将新列表与现有列表连接起来。

```python
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add 归约器使此字段只能追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

def d(state: State):
    print(f'Adding "D" to {state["aggregate"]}')
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_node(d)
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()

# 调用
graph.invoke({"aggregate": []})
# Adding "A" to []
# Adding "B" to ['A']
# Adding "C" to ['A']
# Adding "D" to ['A', 'B', 'C']
# 结果: {'aggregate': ['A', 'B', 'C', 'D']}
```

在上面的示例中，节点 "b" 和 "c" 在同一个超级步骤中并发执行。由于它们处于同一步骤，节点 "d" 会在 "b" 和 "c" 都完成后才执行。

**异常处理：**

LangGraph 在超级步骤内执行节点，这意味着虽然并行分支是并行执行的，但整个超级步骤是事务性的。如果这些分支中的任何一个引发异常，所有更新都不会应用到状态（整个超级步骤出错）。

如果遇到容易出错的情况（或许是想要处理不稳定的 API 调用），LangGraph 提供了两种解决方法：
- 可以在节点内编写常规的 Python 代码来捕获和处理异常
- 可以设置一个 `retry_policy` 来指示图对引发特定类型异常的节点进行重试。只有失败的分支会被重试，因此无需担心执行冗余工作

**设置最大并发数：**

调用图时，可以通过在配置中设置 `max_concurrency` 来控制并发任务的最大数量：

```python
graph.invoke({"aggregate": []}, {"configurable": {"max_concurrency": 10}})
```

#### 延迟节点执行

延迟节点执行在希望将某个节点的执行推迟到所有其他未完成任务都完成时非常有用。这在分支长度不同的情况下尤其适用，这种情况在映射-归约等工作流中很常见。

如果有一个分支包含不止一个步骤，可以在汇聚节点上设置 `defer=True`：

```python
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    aggregate: Annotated[list, operator.add]

def a(state: State):
    return {"aggregate": ["A"]}

def b(state: State):
    return {"aggregate": ["B"]}

def b_2(state: State):
    return {"aggregate": ["B_2"]}

def c(state: State):
    return {"aggregate": ["C"]}

def d(state: State):
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(b_2)
builder.add_node(c)
builder.add_node(d, defer=True)  # 延迟执行
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "b_2")
builder.add_edge("b_2", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()

graph.invoke({"aggregate": []})
# Adding "A" to []
# Adding "B" to ['A']
# Adding "C" to ['A']
# Adding "B_2" to ['A', 'B', 'C']
# Adding "D" to ['A', 'B', 'C', 'B_2']
```

在上面的示例中，节点 "b" 和 "c" 在同一个超级步骤中并发执行。在节点 d 上设置了 `defer=True`，因此它要等到所有未完成的任务都结束后才会执行，即等到整个 "b" 分支完成后才会执行。

#### 条件分支

如果扇出需要在运行时根据状态变化，可以使用 `add_conditional_edges` 通过图状态选择一条或多条路径：

```python
import operator
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    which: str  # 用于决定如何分支

def a(state: State):
    return {"aggregate": ["A"], "which": "c"}

def b(state: State):
    return {"aggregate": ["B"]}

def c(state: State):
    return {"aggregate": ["C"]}

def conditional_edge(state: State) -> Literal["b", "c"]:
    # 根据状态决定下一个节点
    return state["which"]

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_edge(START, "a")
builder.add_edge("b", END)
builder.add_edge("c", END)
builder.add_conditional_edges("a", conditional_edge)

graph = builder.compile()
result = graph.invoke({"aggregate": []})
# {'aggregate': ['A', 'C'], 'which': 'c'}
```

条件边可以路由到多个目标节点：

```python
def route_bc_or_cd(state: State) -> Sequence[str]:
    if state["which"] == "cd":
        return ["c", "d"]
    return ["b", "c"]
```

### 7.12 Map-Reduce 模式

LangGraph 通过 `Send` API 支持 map-reduce 及其他高级分支模式。

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict, Annotated
import operator

class OverallState(TypedDict):
    topic: str
    subjects: list[str]
    jokes: Annotated[list[str], operator.add]
    best_selected_joke: str

def generate_topics(state: OverallState):
    return {"subjects": ["lions", "elephants", "penguins"]}

def generate_joke(state: OverallState):
    joke_map = {
        "lions": "Why don't lions like fast food? Because they can't catch it!",
        "elephants": "Why don't elephants use computers? They're afraid of the mouse!",
        "penguins": "Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice."
    }
    return {"jokes": [joke_map[state["subject"]]]}

def continue_to_jokes(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state["subjects"]]

def best_joke(state: OverallState):
    return {"best_selected_joke": "penguins"}

builder = StateGraph(OverallState)
builder.add_node("generate_topics", generate_topics)
builder.add_node("generate_joke", generate_joke)
builder.add_node("best_joke", best_joke)
builder.add_edge(START, "generate_topics")
builder.add_conditional_edges("generate_topics", continue_to_jokes, ["generate_joke"])
builder.add_edge("generate_joke", "best_joke")
builder.add_edge("best_joke", END)
graph = builder.compile()

# 调用图生成笑话列表
for step in graph.stream({"topic": "animals"}):
    print(step)
# {'generate_topics': {'subjects': ['lions', 'elephants', 'penguins']}}
# {'generate_joke': {'jokes': ["Why don't lions like fast food? Because they can't catch it!"]}}
# {'generate_joke': {'jokes': ["Why don't elephants use computers? They're afraid of the mouse!"]}}
# {'generate_joke': {'jokes': ['Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice.']}}
# {'best_joke': {'best_selected_joke': 'penguins'}}
```

### 7.13 创建循环

在创建带有循环的图时，需要一种终止执行的机制。最常见的做法是添加一条条件边，当达到某个终止条件时路由到 `END` 节点。

还可以在调用或流式传输图时设置图的递归限制。递归限制规定了图在抛出错误之前允许执行的超级步骤数量。

#### 基本循环

创建循环时，可以包含一个指定终止条件的条件边：

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add 归约器使此字段只能追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Node A sees {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Node B sees {state["aggregate"]}')
    return {"aggregate": ["B"]}

def route(state: State) -> Literal["b", END]:
    if len(state["aggregate"]) < 7:
        return "b"
    else:
        return END

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()

graph.invoke({"aggregate": []})
# Node A sees []
# Node B sees ['A']
# Node A sees ['A', 'B']
# ...
```

这种架构类似于 ReAct 智能体，其中节点 "a" 是一个工具调用模型，节点 "b" 代表工具。

#### 设置递归限制

在某些应用中，可能无法保证会达到给定的终止条件。可以设置图的递归限制，这将在经过指定数量的超级步骤后引发 `GraphRecursionError`：

```python
from langgraph.errors import GraphRecursionError

try:
    graph.invoke({"aggregate": []}, {"recursion_limit": 4})
except GraphRecursionError:
    print("Recursion Error")
```

#### 使用 RemainingSteps 优雅降级

可以在状态中引入一个新的键来跟踪距离达到递归限制还剩的步数，而不是抛出 `GraphRecursionError`。LangGraph 实现了一个特殊的 `RemainingSteps` 注解：

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.managed.is_last_step import RemainingSteps

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    remaining_steps: RemainingSteps

def a(state: State):
    print(f'Node A sees {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Node B sees {state["aggregate"]}')
    return {"aggregate": ["B"]}

def route(state: State) -> Literal["b", END]:
    if state["remaining_steps"] <= 2:
        return END
    else:
        return "b"

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()

result = graph.invoke({"aggregate": []}, {"recursion_limit": 4})
# Node A sees []
# Node B sees ['A']
# Node A sees ['A', 'B']
# {'aggregate': ['A', 'B', 'A']}
```

#### 带分支的循环

更复杂的例子：实现一个循环，其中一个步骤会扇出为两个节点：

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    aggregate: Annotated[list, operator.add]

def a(state: State):
    return {"aggregate": ["A"]}

def b(state: State):
    return {"aggregate": ["B"]}

def c(state: State):
    return {"aggregate": ["C"]}

def d(state: State):
    return {"aggregate": ["D"]}

def route(state: State) -> Literal["b", END]:
    if len(state["aggregate"]) < 7:
        return "b"
    else:
        return END

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_node(d)
builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "c")
builder.add_edge("b", "d")
builder.add_edge(["c", "d"], "a")
graph = builder.compile()

# 这个图可以理解为超级步骤的循环：
# 1. Node A
# 2. Node B
# 3. Nodes C 和 D（并发执行）
# 4. Node A
# ...

result = graph.invoke({"aggregate": []})
# Node A sees []
# Node B sees ['A']
# Node D sees ['A', 'B']
# Node C sees ['A', 'B']
# Node A sees ['A', 'B', 'C', 'D']
# ...
```

如果将递归限制设置为 4，只能完成一圈，因为每圈包含 4 个超级步骤。

### 7.14 异步模式

使用异步编程范式在并发运行 IO 密集型代码时（例如，向聊天模型提供商并发发出 API 请求），可以显著提升性能。

**将 sync 实现转换为 async 实现：**

1. 将节点更新为使用 `async def` 而非 `def`
2. 适当使用 `await` 更新内部代码
3. 根据需要，使用 `.ainvoke` 或 `.astream` 调用该图

由于许多 LangChain 对象都实现了 Runnable Protocol，该协议的所有 sync 方法都有对应的 async 变体，因此通常可以快速地将 sync 图升级为 async 图。

**异步节点示例：**

```python
import asyncio

async def async_node(state: State) -> dict:
    await asyncio.sleep(1)
    return {"result": "async done"}

builder = StateGraph(State)
builder.add_node("async_node", async_node)

graph = builder.compile()

# 异步调用
result = await graph.ainvoke({"result": ""})

# 异步流式输出
async for chunk in graph.astream({"result": ""}):
    print(chunk)
```

**Python < 3.11 注意事项：**

```python
# Python < 3.11 需要确保在事件循环中使用异步图
import asyncio

async def main():
    result = await graph.ainvoke({"result": ""})
    print(result)

# 不要直接使用 asyncio.run() 在 Jupyter 中
# Jupyter 已经有运行中的事件循环
```

### 7.15 Command 使用

将控制流（边）和状态更新（节点）结合起来可能会很有用。例如，你可能希望在同一个节点中既执行状态更新，又决定下一步要前往哪个节点。LangGraph 提供了一种实现方式，即从节点函数返回一个 `Command` 对象：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        # 状态更新
        update={"foo": "bar"},
        # 控制流
        goto="my_other_node"
    )
```

**端到端示例：**

创建一个包含 3 个节点（A、B、C）的简单图。首先执行节点 A，然后根据节点 A 的输出决定接下来是前往节点 B 还是节点 C：

```python
import random
from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START
from langgraph.types import Command

# 定义图状态
class State(TypedDict):
    foo: str

# 定义节点
def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    print("Called A")
    value = random.choice(["b", "c"])
    # 这是条件边函数的替代
    if value == "b":
        goto = "node_b"
    else:
        goto = "node_c"

    # Command 允许同时更新图状态并路由到下一个节点
    return Command(
        # 状态更新
        update={"foo": value},
        # 边的替代
        goto=goto,
    )

def node_b(state: State):
    print("Called B")
    return {"foo": state["foo"] + "b"}

def node_c(state: State):
    print("Called C")
    return {"foo": state["foo"] + "c"}

# 创建 StateGraph
# 注意：图中没有用于路由的条件边！控制流在 node_a 内部通过 Command 定义
builder = StateGraph(State)
builder.add_edge(START, "node_a")
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)
# 注意：节点 A、B、C 之间没有边！

graph = builder.compile()

# 调用
graph.invoke({"foo": ""})
# Called A
# Called C (或 Called B，取决于随机选择)
```

**返回类型注解：**

使用 `Command` 作为返回类型注解（例如 `Command[Literal["node_b", "node_c"]]`）对于图形渲染是必要的，它告诉 LangGraph node_a 可以导航到 node_b 和 node_c。

**多目标 Command：**

```python
def router(state: State) -> Command[Literal["a", "b", "c"]]:
    targets = ["a", "b"] if state["value"] > 5 else ["c"]
    return Command(
        update={"messages": ["routing"]},
        goto=targets
    )
```

### 7.16 可视化

**Mermaid 图：**

```python
from IPython.display import Image, display

# 获取 Mermaid 图
mermaid = graph.get_graph().draw_mermaid()
print(mermaid)

# 在 Jupyter 中显示
display(Image(graph.get_graph().draw_mermaid_png()))
```

**PNG 图：**

```python
# 保存为 PNG 文件
png_data = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png_data)
```

**ASCII 艺术：**

```python
# 打印 ASCII 图
print(graph.get_graph().draw_ascii())
```

### 7.17 面试必背要点

**状态定义与更新：**

| 问题 | 答案要点 |
|------|----------|
| **如何定义追加列表？** | 使用 `Annotated[list[str], operator.add]` |
| **如何绕过 reducer 覆盖？** | 使用 `Overwrite(["new"])` 返回值 |
| **add_messages 的作用？** | 追加消息，支持 `RemoveMessage` 删除 |
| **如何定义输入/输出模式？** | `StateGraph(State, input=InputState, output=OutputState)` |
| **私有状态的作用？** | 节点间传递不在图输入/输出中暴露的数据 |

**重试与缓存：**

| 问题 | 答案要点 |
|------|----------|
| **如何配置重试策略？** | `RetryPolicy(max_attempts=3, retry_on=Exception)` |
| **默认不重试的异常？** | ValueError、TypeError、SyntaxError、OSError 等 12 种 |
| **HTTP 请求何时重试？** | 仅 5xx 状态码时重试 |
| **如何配置节点缓存？** | `CachePolicy(ttl=120)` + `compile(cache=InMemoryCache())` |

**流程控制：**

| 问题 | 答案要点 |
|------|----------|
| **如何创建顺序节点链？** | `builder.add_sequence([step1, step2, step3])` |
| **并行执行的原理？** | 扇出到多个节点，同一超级步骤内并发执行 |
| **defer=True 的作用？** | 延迟执行，等待所有未完成任务完成 |
| **条件边 vs Command？** | 条件边只路由；Command 可同时更新状态和路由 |
| **Send 的用途？** | map-reduce 模式，动态创建多个目标节点 |

**循环与递归：**

| 问题 | 答案要点 |
|------|----------|
| **如何创建循环？** | 条件边返回自身节点或 END |
| **recursion_limit 作用？** | 限制超级步骤数量，超出抛出 `GraphRecursionError` |
| **RemainingSteps 用途？** | 优雅降级，在达到限制前安全退出 |
| **超级步骤是什么？** | 并行节点属于同一超级步骤，顺序节点属于不同超级步骤 |

**异步编程：**

| 问题 | 答案要点 |
|------|----------|
| **如何转换为异步？** | `async def` + `await` + `.ainvoke()` / `.astream()` |
| **异步的优势？** | IO 密集型场景并发执行，显著提升性能 |

**代码实操类：**

```python
# 1. 带归约器的状态定义
class State(TypedDict):
    aggregate: Annotated[list, operator.add]

# 2. 重试策略
builder.add_node("node", func, retry=RetryPolicy(max_attempts=3))

# 3. 节点缓存
builder.add_node("node", func, cache_policy=CachePolicy(ttl=120))
graph = builder.compile(cache=InMemoryCache())

# 4. Map-Reduce 模式
def map_jokes(state: State) -> list[Send]:
    return [Send("generate", {"subject": s}) for s in state["subjects"]]

# 5. Command 路由
def router(state: State) -> Command[Literal["a", "b"]]:
    return Command(update={"msg": "hi"}, goto="a" if state["x"] > 5 else "b")

# 6. 循环与递归限制
def route(state: State) -> Literal["b", END]:
    if state["remaining_steps"] <= 2:
        return END
    return "b"

# 7. 异步节点
async def async_node(state: State) -> dict:
    await asyncio.sleep(1)
    return {"done": True}

# 8. 并行分支 + 延迟执行
builder.add_node("d", node_d, defer=True)
```

**对比记忆类：**

| 对比项 | 条件边 | Command |
|--------|--------|---------|
| 路由控制 | ✓ | ✓ |
| 状态更新 | ✗ | ✓ |
| 适用场景 | 纯路由 | 多智能体交接、同时更新状态 |

| 对比项 | 默认 reducer | 带 Annotated 的 reducer |
|--------|--------------|------------------------|
| 更新方式 | 覆盖 | 追加/合并 |
| 典型用途 | 单值字段 | 列表、消息历史 |

| 对比项 | GraphRecursionError | RemainingSteps |
|--------|---------------------|----------------|
| 处理方式 | 异常捕获 | 优雅降级 |
| 适用场景 | 调试、错误处理 | 生产环境、安全退出 |

## 8. 运行方式与事件（invoke/stream/astream）

LangGraph 实现了一个流式系统来呈现实时更新。流式传输对于增强基于 LLM 构建的应用程序的响应性至关重要。通过逐步显示输出，甚至在完整响应准备好之前就开始显示，流式传输极大地改善了用户体验（UX）。

### 8.1 基本运行方式

| 方法 | 说明 |
|------|------|
| `invoke` / `ainvoke` | 同步/异步，返回最终 state |
| `stream` / `astream` | 流式运行，返回迭代器 |

### 8.2 支持的流模式

| 模式 | 说明 |
|------|------|
| `values` | 在图的每一步之后流式传输**完整状态** |
| `updates` | 在图的每一步之后流式传输**状态增量更新** |
| `messages` | 从 LLM 调用的节点流式传输**令牌元组**（token, metadata） |
| `custom` | 从图节点内部流式传输**自定义数据** |
| `debug` | 在图的整个执行过程中流式传输**尽可能多的调试信息** |

### 8.3 基本使用示例

```python
# 单一流模式
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)

# 多种流模式（输出为元组 (mode, chunk)）
for mode, chunk in graph.stream(inputs, stream_mode=["updates", "custom"]):
    print(f"模式: {mode}, 数据: {chunk}")
```

### 8.4 流图状态（updates vs values）

使用流模式 `updates` 和 `values` 来流式传输图在执行时的状态：

| 模式 | 说明 |
|------|------|
| `updates` | 在图的每一步之后流式传输**状态增量更新**。如果同一步有多个更新，会分别流式传输 |
| `values` | 在图的每一步之后流式传输**完整状态值** |

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    topic: str
    joke: str

def refine_topic(state: State):
    return {"topic": state["topic"] + " and cats"}

def generate_joke(state: State):
    return {"joke": f"This is a joke about {state['topic']}"}

graph = (
    StateGraph(State)
    .add_node(refine_topic)
    .add_node(generate_joke)
    .add_edge(START, "refine_topic")
    .add_edge("refine_topic", "generate_joke")
    .add_edge("generate_joke", END)
    .compile()
)

# updates 模式：仅流式传输节点返回的状态更新
for chunk in graph.stream({"topic": "ice cream"}, stream_mode="updates"):
    print(chunk)
# 输出: {'refine_topic': {'topic': 'ice cream and cats'}}
#       {'generate_joke': {'joke': 'This is a joke about ice cream and cats'}}

# values 模式：流式传输完整状态
for chunk in graph.stream({"topic": "ice cream"}, stream_mode="values"):
    print(chunk)
# 输出: {'topic': 'ice cream', 'joke': ''}
#       {'topic': 'ice cream and cats', 'joke': ''}
#       {'topic': 'ice cream and cats', 'joke': 'This is a joke about...'}
```

### 8.5 流式输出子图结果

设置 `subgraphs=True` 可以流式传输来自父图和任何子图的输出：

```python
for chunk in graph.stream(
    {"foo": "foo"},
    subgraphs=True,  # 启用子图输出
    stream_mode="updates",
):
    print(chunk)
# 输出格式: (namespace, data)
# ((), {'node_1': {'foo': 'hi! foo'}})
# (('node_2:xxx',), {'subgraph_node_1': {'bar': 'bar'}})
```

### 8.6 流 LLM 令牌（messages 模式）

使用 `messages` 模式从图中任何 LLM 调用逐令牌流式传输：

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START
from dataclasses import dataclass

@dataclass
class MyState:
    topic: str
    joke: str = ""

model = init_chat_model(model="gpt-4o-mini")

def call_model(state: MyState):
    # 即使使用 .invoke，也会发出消息事件
    response = model.invoke([
        {"role": "user", "content": f"Generate a joke about {state.topic}"}
    ])
    return {"joke": response.content}

graph = (
    StateGraph(MyState)
    .add_node(call_model)
    .add_edge(START, "call_model")
    .compile()
)

# messages 模式返回 (message_chunk, metadata) 元组
for message_chunk, metadata in graph.stream(
    {"topic": "ice cream"},
    stream_mode="messages",
):
    if message_chunk.content:
        print(message_chunk.content, end="|", flush=True)
```

**按标签筛选 LLM 调用：**

```python
# 为 LLM 调用添加标签
model_1 = init_chat_model(model="gpt-4o-mini", tags=['joke'])
model_2 = init_chat_model(model="gpt-4o-mini", tags=['poem'])

# 按标签筛选
async for msg, metadata in graph.astream(
    {"topic": "cats"},
    stream_mode="messages",
):
    if metadata["tags"] == ["joke"]:
        print(msg.content, end="|", flush=True)
```

**按节点筛选：**

```python
for msg, metadata in graph.stream(inputs, stream_mode="messages"):
    if msg.content and metadata["langgraph_node"] == "some_node_name":
        print(msg.content)
```

### 8.7 流自定义数据（custom 模式）

使用 `get_stream_writer` 从节点内部发送自定义数据：

```python
from langgraph.config import get_stream_writer

class State(TypedDict):
    query: str
    answer: str

def node(state: State):
    # 获取流写入器
    writer = get_stream_writer()
    # 发送自定义数据（如进度更新）
    writer({"progress": "正在处理...", "step": 1})
    writer({"progress": "即将完成", "step": 2})
    return {"answer": "处理完成"}

graph = (
    StateGraph(State)
    .add_node(node)
    .add_edge(START, "node")
    .compile()
)

# 设置 stream_mode="custom" 接收自定义数据
for chunk in graph.stream({"query": "example"}, stream_mode="custom"):
    print(chunk)
# 输出: {'progress': '正在处理...', 'step': 1}
#       {'progress': '即将完成', 'step': 2}
```

**与非 LangChain LLM 配合使用：**

```python
from langgraph.config import get_stream_writer

def call_arbitrary_model(state):
    writer = get_stream_writer()
    # 使用自定义流式客户端
    for chunk in your_custom_streaming_client(state["topic"]):
        writer({"custom_llm_chunk": chunk})
    return {"result": "completed"}

# 流式接收
for chunk in graph.stream({"topic": "cats"}, stream_mode="custom"):
    print(chunk)
```

### 8.8 调试模式（debug 模式）

```python
for chunk in graph.stream(
    {"topic": "ice cream"},
    stream_mode="debug",
):
    print(chunk)
```

### 8.9 Python < 3.11 异步注意事项

在 Python < 3.11 中，需要显式传递配置：

```python
# 必须将 config 传递给 ainvoke()
async def call_model(state, config):
    response = await model.ainvoke(
        [{"role": "user", "content": f"Write a joke about {state.topic}"}],
        config,  # 显式传递配置
    )
    return {"joke": response.content}

# 不能使用 get_stream_writer，必须直接传递 writer
async def generate_joke(state: State, writer: StreamWriter):
    writer({"custom_key": "自定义数据"})
    return {"joke": f"笑话: {state['topic']}"}
```

### 8.10 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **LangGraph 流式传输的作用？** | 通过逐步显示输出改善用户体验，特别在处理 LLM 延迟问题时 |
| **五种流模式的区别？** | `values`（完整状态）、`updates`（增量更新）、`messages`（LLM令牌）、`custom`（自定义数据）、`debug`（调试信息） |
| **updates 和 values 的区别？** | `updates` 仅返回节点更新的增量；`values` 返回每步后的完整状态 |
| **如何流式传输 LLM 令牌？** | 使用 `stream_mode="messages"`，返回 `(message_chunk, metadata)` 元组 |

**实践应用类：**

| 问题 | 答案要点 |
|------|----------|
| **如何从子图获取流式输出？** | 在 `.stream()` 中设置 `subgraphs=True`，输出格式为 `(namespace, data)` |
| **如何发送自定义进度更新？** | 使用 `get_stream_writer()` 获取写入器，调用 `writer({"key": "value"})` |
| **如何筛选特定节点的 LLM 令牌？** | 通过 `metadata["langgraph_node"] == "node_name"` 筛选 |
| **如何为特定 LLM 禁用流式传输？** | 初始化时设置 `streaming=False` 或 `disable_streaming=True` |

**代码实操类：**

```python
# 面试常考：流式传输的基本用法

# 1. 单一流模式
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)

# 2. 多种流模式
for mode, chunk in graph.stream(inputs, stream_mode=["updates", "custom"]):
    print(f"{mode}: {chunk}")

# 3. 流 LLM 令牌
for msg, metadata in graph.stream(inputs, stream_mode="messages"):
    if msg.content:
        print(msg.content, end="")

# 4. 流自定义数据
writer = get_stream_writer()
writer({"progress": "50%"})

# 5. 流子图输出
for chunk in graph.stream(inputs, subgraphs=True, stream_mode="updates"):
    print(chunk)
```

**对比记忆类：**

| 对比项 | updates | values |
|--------|---------|--------|
| 输出内容 | 节点返回的增量更新 | 每步后的完整状态 |
| 数据量 | 较小 | 较大 |
| 适用场景 | 只关心变化 | 需要完整状态快照 |

| 对比项 | messages | custom |
|--------|----------|--------|
| 数据来源 | LLM 调用自动捕获 | 手动调用 writer |
| 输出格式 | (token, metadata) | 任意字典 |
| 适用场景 | LLM 流式输出 | 进度信号、自定义日志 |

## 9. 子图（Subgraph）

子图是一个用作另一个图中节点的图。

**子图的用途包括：**
- 构建多智能体系统
- 在多个图中重用一组节点
- 分布式开发：当你希望不同团队独立处理图的不同部分时，可以将每个部分定义为子图，并且只要遵循子图接口（输入和输出模式），父图就可以在不了解子图任何细节的情况下构建完成

### 9.1 定义子图通信

添加子图时，你需要定义父图和子图如何通信：

| 模式 | 何时使用 | 状态模式 |
|------|----------|----------|
| **在节点内部调用子图** | 父图和子图具有不同的状态模式（没有共享键），或者您需要在它们之间转换状态 | 你编写一个包装函数，将父状态映射到子图输入，并将子图输出映射回父状态 |
| **将子图添加为节点** | 父图和子图共享状态键——子图与父图读写相同的通道 | 你可以将编译后的子图直接传递给 `add_node`——无需包装函数 |

### 9.2 在节点内部调用子图

当父图和子图具有不同的状态模式（没有共享键）时，在节点函数内部调用子图。这在你希望为多智能体系统中的每个智能体保留私有消息历史时很常见。

节点函数在调用子图之前会将父状态转换为子图状态，并在返回前将结果转换回父状态。

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class SubgraphState(TypedDict):
    bar: str

# 子图
def subgraph_node_1(state: SubgraphState):
    return {"bar": "你好! " + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# 父图
class State(TypedDict):
    foo: str

def call_subgraph(state: State):
    # 将状态转换为子图状态
    subgraph_output = subgraph.invoke({"bar": state["foo"]})
    # 将响应转换回父状态
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(State)
builder.add_node("node_1", call_subgraph)
builder.add_edge(START, "node_1")
graph = builder.compile()
```

### 9.3 将子图添加为节点

当父图和子图共享状态键时，你可以将编译后的子图直接传递给 `add_node`。不需要包装函数——子图会自动从父图的状态通道读取数据并向其写入数据。

例如，在多智能体系统中，智能体通常通过共享的 `messages` 键进行通信。

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class State(TypedDict):
    foo: str

# 子图
def subgraph_node_1(state: State):
    return {"foo": "你好! " + state["foo"]}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# 父图
builder = StateGraph(State)
builder.add_node("node_1", subgraph)  # 直接传递编译后的子图
builder.add_edge(START, "node_1")
graph = builder.compile()
```

### 9.4 子图持久性

使用子图时，你需要决定在调用之间其内部数据会发生什么。

**默认情况下，子图是无状态的（没有内存）**：每次调用都从空白状态开始。这对于大多数应用程序来说都是正确的选择，包括多智能体系统，其中子智能体处理独立请求。

如果子智能体需要多轮对话记忆（例如，一个能在多次交互中构建上下文的研究助手），你可以使其成为有状态的（持久内存），这样它的对话历史和数据就会在同一线程的多次调用中累积。

> **注意**：要使子图持久化功能（中断、状态检查、有状态内存）正常工作，父图必须与检查点工具一起编译。

### 9.5 无状态子图

当子图的每次调用都是独立的，且子智能体不需要记住之前调用的任何内容时，请使用无状态子图。

**带中断（推荐）：**

这是大多数应用程序的推荐模式。它支持中断、持久执行和并行调用，同时保持每次调用的隔离性。

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

@tool
def fruit_info(fruit_name: str) -> str:
    """查询水果信息"""
    interrupt("继续？")  # 可以在工具中使用中断
    return f"关于 {fruit_name} 的信息"

# 子智能体 - 不设置检查点工具（继承父图）
fruit_agent = create_agent(
    model="gpt-4.1-mini",
    tools=[fruit_info],
    prompt="你是水果专家。",
)

# 外部智能体带检查点工具
agent = create_agent(
    model="gpt-4.1-mini",
    tools=[ask_fruit_expert],
    checkpointer=MemorySaver(),
)
```

**无中断：**

当你希望像调用普通函数一样运行子智能体，且无需检查点开销时使用。编译时需设置 `checkpointer=False`。

```python
subgraph_builder = StateGraph(...)
subgraph = subgraph_builder.compile(checkpointer=False)
```

### 9.6 有状态子图

当子智能体需要记住之前的交互时，请使用有状态子图。使用 `checkpointer=True` 进行编译。

```python
# 带持久状态子智能体
fruit_agent = create_agent(
    model="gpt-4.1-mini",
    tools=[fruit_info],
    prompt="你是水果专家。",
    checkpointer=True,  # 启用有状态持久性
)
```

> **注意**：有状态子图不支持并行工具调用，会导致检查点冲突。

### 9.7 检查点参考

使用 `.compile()` 上的 `checkpointer` 参数控制子图持久性：

```python
subgraph = builder.compile(checkpointer=False)  # 或 True / None
```

| 特性 | 无中断 | 带中断（默认） | 有状态 |
|------|--------|----------------|--------|
| `checkpointer=` | `False` | `None` | `True` |
| 中断（人机交互） | ❌ | ✅ | ✅ |
| 多轮记忆 | ❌ | ❌ | ✅ |
| 多次调用（不同子图） | ✅ | ✅ | ⚠️ |
| 多次调用（相同子图） | ✅ | ✅ | ❌ |
| 状态检查 | ❌ | ⚠️ | ✅ |

### 9.8 查看子图状态

启用持久性后，您可以使用 `subgraphs` 选项检查子图状态。

```python
config = {"configurable": {"thread_id": "1"}}
graph.invoke({"foo": ""}, config)

# 查看当前调用的子图状态
subgraph_state = graph.get_state(config, subgraphs=True).tasks[0].state

# 恢复子图
graph.invoke(Command(resume="bar"), config)
```

### 9.9 流式输出子图结果

要在流式输出中包含子图的输出，可以在父图的 `stream` 方法中设置 `subgraphs` 选项。

```python
for chunk in graph.stream(
    {"foo": "foo"},
    subgraphs=True,  # 启用子图输出
    stream_mode="updates",
):
    print(chunk)
```

### 9.10 生产环境下的核心工程实践

**实践 1：状态一致性处理与防腐层**

主图的全局状态与子图的局部状态职责应严格分离。若二者状态定义不一致，推荐使用适配器模式：

```python
def subgraph_adapter(state: MainState):
    sub_input = {"sub_task_id": state["task_id"], "context": state["raw_data"]}
    sub_result = optimized_subgraph.invoke(sub_input)
    return {"final_output": sub_result["processed_output"]}
```

**实践 2：事件流穿透与可观测性**

通过 `app.stream(..., subgraphs=True)` 启动子图事件暴露。系统会自动为嵌套事件附加语义路径前缀。

**实践 3：全局检查点单点托管**

严禁在编译子图模块时主动挂载独立的 `checkpointer`，避免"双重持久化"引发状态死锁。子图应以无状态模式编译，统一由顶层主引擎负责快照。

**实践 4：边界异常隔离降级**

子图级别的执行异常会向上层冒泡。主系统设计时配置统一的条件分支/回退机制，确保高可用编排。

### 9.11 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **什么是子图？** | 一个用作另一个图中节点的图，用于构建多智能体系统、重用节点、分布式开发 |
| **子图通信有哪两种模式？** | 1) 在节点内部调用（不同状态模式）；2) 直接添加为节点（共享状态键） |
| **无状态和有状态子图的区别？** | 无状态：每次调用从空白开始；有状态：跨调用保留状态 |

**代码实操类：**

```python
# 1. 在节点内部调用子图（不同状态模式）
def call_subgraph(state: ParentState):
    subgraph_output = subgraph.invoke({"bar": state["foo"]})
    return {"foo": subgraph_output["bar"]}

# 2. 直接添加子图为节点（共享状态键）
builder.add_node("node_1", compiled_subgraph)

# 3. 无状态子图
subgraph = builder.compile(checkpointer=False)

# 4. 有状态子图
subgraph = builder.compile(checkpointer=True)

# 5. 流式输出包含子图
for chunk in graph.stream(inputs, subgraphs=True):
    print(chunk)
```

## 10. 持久化与快照（Checkpoint / StateSnapshot）

LangGraph 有一个内置的持久化层，通过检查点工具来实现。当你使用检查点工具编译图时，检查点工具会在每个超级步骤保存图状态的 `checkpoint`。这些检查点会被保存到一个 `thread` 中，在图执行后可以访问该线程。由于 `threads` 允许在执行后访问图的状态，因此多种强大功能成为可能，包括**人机协作、内存、时间回溯和容错能力**。

### 10.1 Threads 线程

线程是检查点保存器保存的每个检查点所分配的唯一 ID 或线程标识符。它包含一系列运行的累积状态。当运行被执行时，助手底层图的状态将被持久化到该线程中。

**使用检查点调用图时，必须在配置的可配置部分指定 `thread_id`：**

```python
config = {"configurable": {"thread_id": "1"}}
graph.invoke({"foo": ""}, config)
```

- 可以获取线程的当前状态和历史状态
- 要持久化状态，必须在执行运行之前创建线程
- 检查点工具将 `thread_id` 用作存储和检索检查点的主键
- 如果没有它，检查点工具就无法保存状态，也无法在中断后恢复执行

### 10.2 Checkpoints 检查点

线程在特定时间点的状态称为检查点。检查点是在每个超级步骤保存的图状态快照，由具有以下关键属性的 `StateSnapshot` 对象表示：

| 属性 | 说明 |
|------|------|
| `config` | 与此检查点相关联的配置 |
| `metadata` | 与此检查点相关联的元数据 |
| `values` | 此时状态通道的值 |
| `next` | 图中接下来要执行的节点名称元组 |
| `tasks` | 包含 `PregelTask` 对象的元组，包含下一步要执行的任务信息 |

**示例：查看检查点保存过程**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: str
    bar: Annotated[list[str], add]

def node_a(state: State):
    return {"foo": "a", "bar": ["a"]}

def node_b(state: State):
    return {"foo": "b", "bar": ["b"]}

workflow = StateGraph(State)
workflow.add_node(node_a)
workflow.add_node(node_b)
workflow.add_edge(START, "node_a")
workflow.add_edge("node_a", "node_b")
workflow.add_edge("node_b", END)

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}
graph.invoke({"foo": "", "bar": []}, config)
```

运行该图后，会看到正好 4 个检查点：

| 检查点 | 状态值 | 下一个节点 |
|--------|--------|-----------|
| 1 | 空 | START |
| 2 | `{'foo': '', 'bar': []}` | node_a |
| 3 | `{'foo': 'a', 'bar': ['a']}` | node_b |
| 4 | `{'foo': 'b', 'bar': ['a', 'b']}` | 无（结束） |

> **注意**：`bar` 通道值包含来自两个节点的输出，因为我们为 `bar` 通道配置了 reducer（`add`）。

### 10.3 获取状态

与保存的图状态交互时，你**必须**指定一个线程标识符。

```python
# 获取最新状态快照
config = {"configurable": {"thread_id": "1"}}
graph.get_state(config)

# 获取特定 checkpoint_id 的状态快照
config = {"configurable": {"thread_id": "1", "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"}}
graph.get_state(config)
```

`get_state` 的输出示例：

```python
StateSnapshot(
    values={'foo': 'b', 'bar': ['a', 'b']},
    next=(),
    config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28fe-6528-8002-5a559208592c'}},
    metadata={'source': 'loop', 'writes': {'node_b': {'foo': 'b', 'bar': ['b']}}, 'step': 2},
    created_at='2024-08-29T19:19:38.821749+00:00',
    parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f9-6ec4-8001-31981c2c39f8'}},
    tasks=()
)
```

### 10.4 获取状态历史

通过调用 `graph.get_state_history(config)`，你可以获取特定线程的完整图执行历史。检查点将按时间顺序排列，最新的检查点位于列表首位。

```python
for snapshot in graph.get_state_history(config):
    print(snapshot.config, snapshot.values)
```

### 10.5 Replay 回放

可以回放之前的图执行。如果使用 `invoke` 和 `thread_id` + `checkpoint_id` 调用图，将回放该检查点之前的执行步骤，并只执行检查点之后的步骤。

```python
config = {"configurable": {"thread_id": "1", "checkpoint_id": "0c62ca34-ac19-445d-bbb0-5b4984975b2a"}}
graph.invoke(None, config=config)
```

**关键特性**：LangGraph 知道某个特定步骤是否已被执行过。如果已执行，LangGraph 会简单地重播该步骤而不会重新执行。`checkpoint_id` 之后的所有步骤都将被执行（即新的分支）。

### 10.6 更新状态 (`update_state`)

除了从特定检查点重新运行图外，还可以编辑图状态。

**`update_state` 方法接受三个参数：**

| 参数 | 说明 |
|------|------|
| `config` | 应包含 `thread_id` 指定要更新的线程。可选包含 `checkpoint_id` 来分叉所选检查点 |
| `values` | 用于更新状态的值。这些值会传递给 reducer 函数（如果定义了） |
| `as_node` | 可选，指定更新来自哪个节点。用于控制下一步执行哪个节点 |

**示例：时间旅行与状态修改**

```python
# 1. 定位需要回滚的历史节点快照
target_checkpoint = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_id": "1ef663ba-28fe-XXXX"
    }
}

# 2. 强行更新该历史节点的状态
# as_node="agent" 的作用：这笔状态更新假装是由 agent 节点执行完做出的
app.update_state(
    target_checkpoint,
    {"messages": [{"role": "assistant", "content": "人工接管修正后的安全回复"}]},
    as_node="agent"
)

# 3. 恢复执行（基于 Fork 出的全新分支）
app.invoke(None, config=target_checkpoint)
```

### 10.7 Memory Store 内存存储

状态模式指定了在图执行时会被填充的一组键。检查点程序可以在每个图步骤将状态写入线程，实现状态持久性。但是，如果想在**多个线程之间**保留一些信息呢？

**Store 接口**允许跨线程存储任意信息。

**基本用法：**

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 命名空间划分（用户级别）
user_id = "1"
namespace_for_memory = (user_id, "memories")

# 保存记忆
import uuid
memory_id = str(uuid.uuid4())
memory = {"food_preference": "我喜欢披萨"}
store.put(namespace_for_memory, memory_id, memory)

# 搜索记忆
memories = store.search(namespace_for_memory)
print(memories[-1].dict())
# {'value': {'food_preference': '我喜欢披萨'}, 'key': '...', 'namespace': ['1', 'memories'], ...}
```

**记忆对象属性：**

| 属性 | 说明 |
|------|------|
| `value` | 记忆的值（本身是一个字典） |
| `key` | 此命名空间中该记忆的唯一键 |
| `namespace` | 字符串元组，此记忆的命名空间 |

### 10.8 语义搜索

存储支持语义搜索，让你能够基于含义而非精确匹配来查找记忆。需要为存储配置一个嵌入模型：

```python
# 查找关于食物偏好的记忆
memories = store.search(
    namespace_for_memory,
    query="用户喜欢吃什么？",
    limit=3  # 返回前 3 个匹配
)
```

### 10.9 在 LangGraph 中使用 Store

Store 与 Checkpointer 协同工作：Checkpointer 将状态保存到线程，Store 允许跨线程存储任意信息。

```python
from dataclasses import dataclass
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_id: str

checkpointer = InMemorySaver()
store = InMemoryStore()

# 编译图
graph = builder.compile(checkpointer=checkpointer, store=store)

# 调用图
config = {"configurable": {"thread_id": "1"}}
for update in graph.stream(
    {"messages": [{"role": "user", "content": "你好"}]},
    config,
    stream_mode="updates",
    context=Context(user_id="1"),
):
    print(update)
```

**在节点中访问 Store：**

```python
async def update_memory(state: MessagesState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")

    # 保存新记忆
    memory_id = str(uuid.uuid4())
    await runtime.store.aput(namespace, memory_id, {"memory": "新记忆"})

async def call_model(state: MessagesState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")

    # 搜索记忆
    memories = await runtime.store.asearch(
        namespace,
        query=state["messages"][-1].content,
        limit=3
    )
    info = "\n".join([d.value["memory"] for d in memories])
    # 在模型调用中使用记忆...
```

### 10.10 Checkpointer Libraries 检查点库

在底层，检查点功能由符合 `BaseCheckpointSaver` 接口的检查点对象提供支持：

| 库 | 说明 | 安装 |
|----|------|------|
| `langgraph-checkpoint` | 基础接口，包含 `InMemorySaver` | 已包含 |
| `langgraph-checkpoint-sqlite` | SQLite 实现，适合实验和本地工作流 | 需单独安装 |
| `langgraph-checkpoint-postgres` | Postgres 实现，用于生产环境 | 需单独安装 |
| `langgraph-checkpoint-cosmosdb` | Azure Cosmos DB 实现 | 需单独安装 |

### 10.11 Checkpointer Interface 检查点接口

每个检查点工具都遵循 `BaseCheckpointSaver` 接口：

| 方法 | 说明 |
|------|------|
| `.put` | 存储包含配置和元数据的检查点 |
| `.put_writes` | 存储与检查点相关联的中间写入 |
| `.get_tuple` | 使用配置获取检查点元组 |
| `.list` | 列出匹配条件的检查点 |

如果检查点工具与异步图执行配合使用，将使用异步版本（`.aput`、`.aput_writes`、`.aget_tuple`、`.alist`）。

### 10.12 Serializer 序列化器

当检查点保存器保存图状态时，需要将状态中的通道值序列化。

**默认序列化器**：`JsonPlusSerializer` 可处理多种类型，包括 LangChain 和 LangGraph 基元、日期时间、枚举等。

**使用 pickle 作为备用**：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

graph.compile(
    checkpointer=InMemorySaver(serde=JsonPlusSerializer(pickle_fallback=True))
)
```

**加密**：检查点工具可以选择性地加密所有持久化状态。

```python
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

serde = EncryptedSerializer.from_pycryptodome_aes()  # 从 LANGGRAPH_AES_KEY 读取
checkpointer = SqliteSaver(sqlite3.connect("checkpoint.db"), serde=serde)
```

### 10.13 持久化能力

| 能力 | 说明 |
|------|------|
| **人机协作** | 允许人类检查、中断和批准图步骤 |
| **记忆** | 允许在交互之间存在"记忆"，如对话历史 |
| **时间回溯** | 允许重放先前的图执行，分叉状态探索替代路径 |
| **容错性** | 如果节点失败，可以从最后一个成功的步骤重新启动图 |
| **待处理写入** | 当节点中途失败时，存储其他成功节点的待处理写入 |

### 10.14 生产环境避坑指南

**1. State IO 瓶颈与体积爆炸**
- **问题**：每次节点跳转都会存下全量快照，大对象会击穿数据库写入限制
- **解决**：遵循**按引用传递**原则（仅存 OSS 定位符）；设计 Summarizer 节点压缩历史

**2. 不可序列化对象陷阱**
- **问题**：State 中的所有字段都必须能被序列化
- **解决**：**绝对不要**把数据库连接池、Socket、文件句柄等放入 State

**3. thread_id 并发隔离**
- **问题**：混用 `thread_id` 会导致数据覆盖和隐私泄漏
- **解决**：每个用户会话分配**全局唯一且不可重用**的 `thread_id`

### 10.15 持久执行（Durable Execution）

持久执行是一种技术，指流程或工作流在关键节点保存其进度，使其能够暂停，之后准确从暂停处恢复。这在以下场景中尤其有用：
- **人机协作**：用户可以在继续之前检查、验证或修改流程
- **长时间运行任务**：可能遇到中断或错误（如 LLM 调用超时）
- **延迟恢复**：即使经过很长时间（如一周后），也能恢复而无需重新处理先前的步骤

**启用持久执行的要求：**

| 要求 | 说明 |
|------|------|
| **指定 Checkpointer** | 保存工作流进度的检查点程序 |
| **指定 thread_id** | 跟踪特定工作流实例的执行历史 |
| **包装非确定性操作** | 将随机数生成、文件写入、API 调用等包装在 task 中 |

### 10.16 确定性与一致重放

当你恢复工作流运行时，代码**不会**从执行停止的同一行代码处恢复；相反，它会确定一个合适的起始点，从该点继续执行。这意味着工作流将重新执行从起始点开始的所有步骤。

**编写持久执行工作流的指南：**

| 原则 | 说明 |
|------|------|
| **避免重复工作** | 如果节点包含多个副作用操作，将每个操作包装在单独的 task 中 |
| **封装非确定性操作** | 将随机数生成等代码包装在 task 或 node 中 |
| **使用幂等操作** | 确保 API 调用、文件写入等是幂等的，使用幂等键避免重复 |

**示例：在节点中使用 task 包装副作用操作**

```python
from typing import NotRequired
from typing_extensions import TypedDict
import uuid
import requests

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.func import task

# 定义状态
class State(TypedDict):
    url: str
    result: NotRequired[str]

# 将副作用操作包装在 task 中
@task
def call_api(url: str) -> str:
    """包装 API 请求的 task"""
    return requests.get(url).text[:100]

def call_api_node(state: State):
    """节点调用 task"""
    result = call_api(state['url']).result()
    return {"result": result}

# 构建图
builder = StateGraph(State)
builder.add_node("call_api", call_api_node)
builder.add_edge(START, "call_api")
builder.add_edge("call_api", END)

# 编译时指定 checkpointer
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# 执行时指定 thread_id
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}
graph.invoke({"url": "https://www.example.com"}, config)
```

### 10.17 持久性模式

LangGraph 支持三种持久性模式，允许根据应用需求平衡性能和数据一致性：

```python
graph.stream(
    {"input": "test"},
    durability="sync"  # 指定持久性模式
)
```

| 模式 | 持久性 | 性能 | 说明 |
|------|--------|------|------|
| `"exit"` | 最低 | 最高 | 仅在图执行退出时保存（成功/出错/中断），无法从执行中的系统故障恢复 |
| `"async"` | 中等 | 良好 | 异步保存更改，性能和持久性平衡，进程崩溃时有小风险丢失检查点 |
| `"sync"` | 最高 | 较低 | 同步保存更改，每个检查点写入后才继续执行，高耐久性但有性能开销 |

### 10.18 恢复工作流

启用持久执行后，可以在以下场景中恢复执行：

**1. 暂停和恢复**

```python
from langgraph.types import interrupt, Command

# 在节点中暂停
def human_review_node(state):
    user_input = interrupt("需要人工审核")
    return Command(update={"approved": user_input["approved"]})

# 恢复执行
graph.invoke(Command(resume={"approved": True}), config)
```

**2. 从故障中恢复**

```python
# 发生异常后，使用相同的 thread_id 恢复
# 传入 None 作为输入值，从最后成功的检查点继续
graph.invoke(None, config)
```

**恢复工作流的起始点：**

| 场景 | 起始点 |
|------|--------|
| StateGraph（图 API） | 执行停止的节点的起始位置 |
| 子图调用 | 父节点（子图内部为执行停止的特定节点） |
| 函数式 API | 入口点（entrypoint）中执行停止的位置 |

### 10.19 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **什么是 LangGraph 的持久化？** | 通过 Checkpointer 在每个超级步骤保存图状态的 checkpoint 到 thread 中，支持人机协作、记忆、时间回溯和容错 |
| **thread_id 和 checkpoint_id 的区别？** | `thread_id` 是线程唯一标识，包含一系列运行的累积状态；`checkpoint_id` 是线程中特定检查点的标识，用于定位历史快照 |
| **StateSnapshot 包含哪些属性？** | `config`（配置）、`metadata`（元数据）、`values`（状态值）、`next`（下一节点）、`tasks`（任务信息） |
| **Checkpointer 和 Store 的区别？** | Checkpointer 将状态保存到**线程**（单会话内）；Store 允许**跨线程**存储信息（如用户级别的长期记忆） |
| **什么是持久执行（Durable Execution）？** | 流程在关键节点保存进度，能够暂停后准确从暂停处恢复，即使经过很长时间也无需重新处理先前步骤 |
| **持久执行的三要素？** | 1) 指定 Checkpointer 保存进度；2) 指定 thread_id 跟踪执行历史；3) 将非确定性操作和副作用包装在 task 中 |

**持久性模式类：**

| 问题 | 答案要点 |
|------|----------|
| **三种持久性模式及区别？** | `exit`（仅退出时保存，性能最高）、`async`（异步保存，平衡模式）、`sync`（同步保存，耐久性最高） |
| **何时使用 sync 模式？** | 需要高耐久性、不能丢失任何检查点的场景，如金融交易、关键业务流程 |
| **何时使用 exit 模式？** | 长时间运行的图、对中间状态不敏感、可接受从开始重试的场景 |

**确定性与恢复类：**

| 问题 | 答案要点 |
|------|----------|
| **为什么恢复时不会从停止的代码行继续？** | LangGraph 会确定合适的起始点重新执行，因此必须将副作用包装在 task 中避免重复执行 |
| **如何保证工作流的确定性？** | 1) 避免重复工作（每个副作用包装在单独 task）；2) 封装非确定性操作；3) 使用幂等操作 |
| **从故障恢复时如何继续执行？** | 使用相同的 `thread_id`，传入 `None` 作为输入值：`graph.invoke(None, config=config)` |
| **不同 API 恢复的起始点？** | 图 API：执行停止的节点起始位置；函数式 API：entrypoint 中执行停止的位置；子图：父节点 |

**实践应用类：**

| 问题 | 答案要点 |
|------|----------|
| **如何实现人机协作（HITL）？** | 1) 使用 Checkpointer 编译图；2) 在节点中调用 `interrupt()` 暂停；3) 人工审核后用 `Command(resume=...)` 恢复执行 |
| **如何实现时间回溯？** | 通过 `get_state_history()` 获取历史快照，指定 `checkpoint_id` 调用 `invoke()` 回放，或用 `update_state()` 分叉状态探索替代路径 |
| **`update_state` 的 `as_node` 参数作用？** | 指定更新来自哪个节点，用于"欺骗"下游逻辑，控制下一步执行哪个节点 |
| **生产环境如何避免状态体积爆炸？** | 1) 按引用传递（存 OSS 定位符而非原始数据）；2) 设计 Summarizer 节点压缩历史；3) 不要把连接池、Socket 等不可序列化对象放入 State |

**代码实操类：**

```python
# 面试常考：如何获取和更新状态？
config = {"configurable": {"thread_id": "user-123"}}

# 获取最新状态
snapshot = graph.get_state(config)

# 获取历史状态
for snapshot in graph.get_state_history(config):
    print(snapshot.values)

# 更新状态（时间旅行）
graph.update_state(
    config,
    {"messages": [{"role": "assistant", "content": "修正后的回复"}]},
    as_node="agent"
)

# 从故障恢复（传入 None）
graph.invoke(None, config=config)

# 指定持久性模式
graph.stream({"input": "test"}, config, durability="sync")

# 暂停恢复（人机协作）
graph.invoke(Command(resume={"approved": True}), config)
```

**对比记忆类：**

| 对比项 | Checkpointer | Store |
|--------|--------------|-------|
| 作用范围 | 单线程内 | 跨线程 |
| 存储内容 | 图状态快照 | 任意信息（如用户记忆） |
| 典型用途 | 会话记忆、断点续传 | 长期记忆、用户画像 |
| 命名空间 | thread_id | 自定义元组（如 user_id） |

| 持久性模式 | 持久性 | 性能 | 适用场景 |
|-----------|--------|------|----------|
| `exit` | 最低 | 最高 | 长时间运行、可接受重试 |
| `async` | 中等 | 良好 | 大多数场景的平衡选择 |
| `sync` | 最高 | 较低 | 关键业务、不能丢失数据 |

## 11. 中断与人机协作

中断允许你在特定点暂停图的执行，并在继续之前等待外部输入。这实现了"人在回路"模式，即需要外部输入才能继续的场景。当触发中断时，LangGraph 会使用其持久化层保存图的状态，并无限期等待，直到你恢复执行。

中断的工作原理是在图节点的任意位置调用 `interrupt()` 函数。该函数接受任何可序列化为 JSON 的值，这些值会呈现给调用者。当你准备好继续时，可以通过重新调用带有 `Command` 的图来恢复执行，该命令随后会成为节点内部 `interrupt()` 调用的返回值。

与静态断点（在特定节点之前或之后暂停）不同，中断是动态的——它们可以放在代码中的任何位置，并且可以根据应用程序逻辑设置为条件中断。

**核心要点：**
- **检查点功能会记录您的位置**：检查点工具会写入精确的图状态，因此您稍后可以恢复，即使处于错误状态也是如此
- **thread_id 是你的指针**：设置 `config={"configurable": {"thread_id": ...}}` 以告知检查点加载哪个状态
- **中断负载显示为 `__interrupt__`**：传递给 `interrupt()` 的值会返回到调用方的 `__interrupt__` 字段中，这样您就知道图正在等待什么
- **thread_id 是持久化游标**：复用它会恢复到同一个检查点；使用新值则会启动一个全新的、状态为空的线程

### 11.1 使用 interrupt 暂停

`interrupt` 函数会暂停图的执行，并向调用者返回一个值。当你在节点内调用 `interrupt` 时，LangGraph 会保存当前的图状态，并等待你通过输入来恢复执行。

**使用 interrupt 的前提条件：**
1. **Checkpointer**：用于持久化图状态（生产环境使用数据库支持的检查点工具）
2. **thread_id**：配置中的线程 ID，以便运行时知道从哪个状态恢复
3. **interrupt()**：在你想要暂停的位置调用（负载必须可序列化为 JSON）

```python
from langgraph.types import interrupt

def approval_node(state: State):
    # 暂停并请求批准
    approved = interrupt("是否批准此操作？")

    # 恢复时，Command(resume=...) 的值会返回到这里
    return {"approved": approved}
```

**调用 interrupt 时发生的事情：**
1. 图执行会在调用 `interrupt` 的确切位置暂停
2. 使用检查点保存器保存状态，以便之后可以恢复执行（生产环境应使用数据库支持的持久化检查点）
3. 值会返回到 `__interrupt__` 下的调用方；它可以是任何可 JSON 序列化的值（字符串、对象、数组等）
4. 图会无限期等待，直到你通过响应恢复执行
5. 当你恢复时，响应会传递回节点，成为 `interrupt()` 调用的返回值

### 11.2 恢复中断

中断暂停执行后，您可以通过再次调用包含恢复值的 `Command` 来恢复图。恢复值会传递回 `interrupt` 调用，使节点能够利用外部输入继续执行。

```python
from langgraph.types import Command

# 初始运行 - 遇到中断并暂停
# thread_id 是持久化指针（生产环境存储稳定的 ID）
config = {"configurable": {"thread_id": "thread-1"}}
result = graph.invoke({"input": "data"}, config=config)

# 检查中断内容
# __interrupt__ 包含传递给 interrupt() 的负载
print(result["__interrupt__"])
# > [Interrupt(value='是否批准此操作？')]

# 恢复执行 - 传入人类的响应
# 恢复负载成为节点内 interrupt() 的返回值
graph.invoke(Command(resume=True), config=config)
```

**恢复要点：**
- 恢复时必须使用中断发生时所使用的**相同的 thread ID**
- 传递给 `Command(resume=...)` 的值会成为 `interrupt` 调用的返回值
- 节点在恢复时会从调用 `interrupt` 的节点**开头重新启动**，因此 `interrupt` 之前的所有代码会再次运行
- 你可以将任何可序列化为 JSON 的值作为恢复值传递

### 11.3 常见模式

中断解锁的关键在于能够暂停执行并等待外部输入。这在多种使用场景中都很有用：

| 模式 | 说明 |
|------|------|
| **审批工作流** | 在执行关键操作（API 调用、数据库更改、财务交易）前暂停 |
| **处理多个中断** | 在单次调用中恢复多个中断时，将中断 ID 与恢复值配对 |
| **审阅和编辑** | 让人类在继续之前审阅和修改大语言模型的输出或工具调用 |
| **中断工具调用** | 在执行工具调用前暂停，以便在执行前检查和编辑工具调用 |
| **验证人工输入** | 在进入下一步之前暂停，以验证人工输入 |

### 11.4 带人机协作中断的流式传输

在构建具有人机协作流程的交互式智能体时，你可以同时流式传输消息片段和节点更新，以便在处理中断时提供实时反馈。

使用多种流模式（`"messages"` 和 `"updates"`）并结合 `subgraphs=True`（如果存在子图）来：
- 在生成 AI 响应时实时流式传输它们
- 检测图何时遇到中断
- 处理用户输入并无缝恢复执行

```python
async for metadata, mode, chunk in graph.astream(
    initial_input,
    stream_mode=["messages", "updates"],
    subgraphs=True,
    config=config
):
    if mode == "messages":
        # 处理流式消息内容
        msg, _ = chunk
        if isinstance(msg, AIMessageChunk) and msg.content:
            # 实时显示内容
            display_streaming_content(msg.content)

    elif mode == "updates":
        # 检查中断
        if "__interrupt__" in chunk:
            # 停止流式显示
            interrupt_info = chunk["__interrupt__"][0].value

            # 处理用户输入
            user_response = get_user_input(interrupt_info)

            # 使用更新的输入恢复图
            initial_input = Command(resume=user_response)
            break

        else:
            # 跟踪节点转换
            current_node = list(chunk.keys())[0]
```

**关键参数说明：**
- `stream_mode=["messages", "updates"]`：启用消息块和图状态更新的双重流传输
- `subgraphs=True`：嵌套图中中断检测所需的参数
- `"__interrupt__"` 检测：在需要人工输入时发出信号
- `Command(resume=...)`：使用用户提供的数据恢复图执行

### 11.5 处理多个中断

当并行分支同时中断时（例如，扇出到多个节点，每个节点都调用 `interrupt()`），您可能需要在一次调用中恢复多个中断。使用一次调用恢复多个中断时，请将每个中断 ID 映射到其恢复值。这可确保在运行时每个响应都与正确的中断配对。

```python
from typing import Annotated, TypedDict
import operator
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    vals: Annotated[list[str], operator.add]


def node_a(state):
    answer = interrupt("question_a")
    return {"vals": [f"a:{answer}"]}


def node_b(state):
    answer = interrupt("question_b")
    return {"vals": [f"b:{answer}"]}


graph = (
    StateGraph(State)
    .add_node("a", node_a)
    .add_node("b", node_b)
    .add_edge(START, "a")
    .add_edge(START, "b")
    .add_edge("a", END)
    .add_edge("b", END)
    .compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

# 步骤 1：两个并行节点都触发中断并暂停
interrupted_result = graph.invoke({"vals": []}, config)
print(interrupted_result)
# {
#     'vals': [],
#     '__interrupt__': [
#         Interrupt(value='question_a', id='bd4f3183600f2c41dddafbf8f0f7be7b'),
#         Interrupt(value='question_b', id='29963e3d3585f0cef025dd0f14323f55')
#     ]
# }

# 步骤 2：一次恢复所有待处理的中断
resume_map = {
    i.id: f"answer for {i.value}"
    for i in interrupted_result["__interrupt__"]
}
result = graph.invoke(Command(resume=resume_map), config)

print("最终状态:", result)
# > 最终状态: {'vals': ['a:answer for question_a', 'b:answer for question_b']}
```

### 11.6 批准或拒绝

中断最常见的用途之一是在执行关键操作前暂停并请求批准。例如，你可能希望让人类批准一项 API 调用、一次数据库更改或其他任何重要决策。

```python
from typing import Literal
from langgraph.types import interrupt, Command

def approval_node(state: State) -> Command[Literal["proceed", "cancel"]]:
    # 暂停执行；负载显示在 result["__interrupt__"] 中
    is_approved = interrupt({
        "question": "是否要执行此操作？",
        "details": state["action_details"]
    })

    # 根据响应路由
    if is_approved:
        return Command(goto="proceed")  # 在提供恢复负载后运行
    else:
        return Command(goto="cancel")


# 恢复图时，传递 true 表示批准，false 表示拒绝
graph.invoke(Command(resume=True), config=config)   # 批准
graph.invoke(Command(resume=False), config=config)  # 拒绝
```

### 11.7 审阅和编辑状态

有时你希望让人类在继续之前审阅并编辑部分图状态。这对于纠正大语言模型、补充缺失信息或进行调整很有用。

```python
from langgraph.types import interrupt

def review_node(state: State):
    # 暂停并显示当前内容供审阅（显示在 result["__interrupt__"] 中）
    edited_content = interrupt({
        "instruction": "审阅并编辑此内容",
        "content": state["generated_text"]
    })

    # 使用编辑后的版本更新状态
    return {"generated_text": edited_content}


# 恢复时，提供编辑后的内容
graph.invoke(
    Command(resume="编辑和改进后的文本"),  # 值成为 interrupt() 的返回值
    config=config
)
```

**完整示例：**

```python
from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt


class ReviewState(TypedDict):
    generated_text: str


def review_node(state: ReviewState):
    # 请求审阅者编辑生成的内容
    updated = interrupt({
        "instruction": "审阅并编辑此内容",
        "content": state["generated_text"],
    })
    return {"generated_text": updated}


builder = StateGraph(ReviewState)
builder.add_node("review", review_node)
builder.add_edge(START, "review")
builder.add_edge("review", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "review-42"}}
initial = graph.invoke({"generated_text": "初始草稿"}, config=config)
print(initial["__interrupt__"])  # -> [Interrupt(value={'instruction': ..., 'content': ...})]

# 恢复并提供审阅者的编辑
final_state = graph.invoke(
    Command(resume="审阅后改进的草稿"),
    config=config,
)
print(final_state["generated_text"])  # -> "审阅后改进的草稿"
```

### 11.8 工具中的中断

你也可以将中断直接放置在工具函数内部。这会使工具在每次被调用时暂停以等待批准，并允许在执行工具调用之前进行人工审阅和编辑。

当你希望审批逻辑与工具本身共存，使其能在图的不同部分重复使用时，这种方法会很有用。大语言模型可以自然地调用该工具，而且每当工具被调用时，中断机制会暂停执行，让你能够批准、编辑或取消该操作。

```python
from langchain.tools import tool
from langgraph.types import interrupt

@tool
def send_email(to: str, subject: str, body: str):
    """发送邮件给收件人"""

    # 发送前暂停；负载显示在 result["__interrupt__"] 中
    response = interrupt({
        "action": "send_email",
        "to": to,
        "subject": subject,
        "body": body,
        "message": "批准发送此邮件？"
    })

    if response.get("action") == "approve":
        # 恢复值可以在执行前覆盖输入
        final_to = response.get("to", to)
        final_subject = response.get("subject", subject)
        final_body = response.get("body", body)
        return f"邮件已发送至 {final_to}，主题为 '{final_subject}'"
    return "邮件已被用户取消"


# 恢复时批准并可选编辑参数
graph.invoke(
    Command(resume={"action": "approve", "subject": "更新后的主题"}),
    config=config,
)
```

### 11.9 验证人工输入

有时你需要验证来自人类的输入，如果输入无效，就再次询问。你可以通过在循环中多次调用 `interrupt` 来实现这一点。

每次你使用无效输入重新运行该图时，它都会用更清晰的信息再次询问。一旦提供了有效的输入，节点就会完成，图也会继续运行。

```python
from langgraph.types import interrupt

def get_age_node(state: State):
    prompt = "请输入您的年龄？"

    while True:
        answer = interrupt(prompt)  # 负载显示在 result["__interrupt__"] 中

        # 验证输入
        if isinstance(answer, int) and answer > 0:
            # 有效输入 - 继续
            return {"age": answer}
        else:
            # 无效输入 - 使用更具体的提示再次询问
            prompt = f"'{answer}' 不是有效的年龄。请输入一个正数。"


# 使用示例
config = {"configurable": {"thread_id": "form-1"}}
first = graph.invoke({"age": None}, config=config)
print(first["__interrupt__"])  # -> [Interrupt(value='请输入您的年龄？', ...)]

# 提供无效数据；节点重新提示
retry = graph.invoke(Command(resume="三十"), config=config)
print(retry["__interrupt__"])  # -> [Interrupt(value="'三十' 不是有效的年龄...", ...)]

# 提供有效数据；循环退出，状态更新
final = graph.invoke(Command(resume=30), config=config)
print(final["age"])  # -> 30
```

### 11.10 中断规则

当你在节点内调用 `interrupt` 时，LangGraph 会通过抛出一个异常来暂停执行，该异常会向运行时发出暂停信号。此异常会沿调用栈向上传播，并被运行时捕获，运行时随后会通知图保存当前状态并等待外部输入。

当执行恢复时（在你提供请求的输入之后），运行时会**从头重新启动整个节点**——它不会从调用 `interrupt` 的确切行继续执行。这意味着在 `interrupt` 之前运行的任何代码都会再次执行。因此，在使用中断时需要遵循一些重要规则，以确保它们能按预期运行。

**规则 1：不要将 interrupt 调用包裹在 try/except 中**

`interrupt` 通过抛出一种特殊异常的方式，在调用点暂停执行。如果将 `interrupt` 调用包裹在 try/except 块中，你会捕获到这个异常，且中断不会传递回图。

```python
# ✅ 正确：捕获特定异常类型，不会捕获中断异常
def node_a(state: State):
    try:
        name = interrupt("你的名字是？")
        fetch_data()  # 这可能会失败
    except NetworkException as e:
        print(e)
    return state

# ❌ 错误：在空的 try/except 块中包裹 interrupt
def node_b(state: State):
    try:
        interrupt("你的名字是？")  # 异常会被捕获，中断不会传递
    except Exception as e:
        print(e)
    return state
```

**规则 2：不要在节点内重新排序 interrupt 调用**

在单个节点中使用多个中断是很常见的，但如果处理不当，可能会导致意外行为。

当一个节点包含多个中断调用时，LangGraph 会保留一份特定于执行该节点的任务的恢复值列表。每当执行恢复时，都会从节点的开头开始。对于遇到的每个中断，LangGraph 会检查任务的恢复列表中是否存在匹配的值。**匹配是严格基于索引的**，因此节点内中断调用的顺序很重要。

```python
# ✅ 正确：interrupt 调用每次都按相同顺序发生
def node_a(state: State):
    name = interrupt("你的名字？")
    age = interrupt("你的年龄？")
    city = interrupt("你的城市？")

    return {
        "name": name,
        "age": age,
        "city": city
    }

# ❌ 错误：有条件地跳过 interrupt 会改变顺序
def node_b(state: State):
    name = interrupt("你的名字？")
    if state.get("needs_age"):  # 条件可能导致索引不匹配
        age = interrupt("你的年龄？")
    city = interrupt("你的城市？")
    return {"name": name, "city": city}

# ❌ 错误：使用在不同执行过程中不具有确定性的逻辑来循环调用 interrupt
def node_c(state: State):
    results = []
    for item in state.get("dynamic_list", []):  # 列表可能在运行之间改变
        result = interrupt(f"批准 {item}？")
        results.append(result)

    return {"results": results}
```

**规则 3：不要在 interrupt 调用中返回复杂值**

根据所使用的检查点工具不同，复杂值可能无法序列化（例如，无法序列化函数）。为了使你的图能适应任何部署环境，最佳做法是只使用那些可以合理序列化的值。

```python
# ✅ 正确：传递简单的、可 JSON 序列化的类型
def node_a(state: State):
    name = interrupt("你的名字？")
    count = interrupt(42)
    approved = interrupt(True)
    return {"name": name, "count": count, "approved": approved}

# ✅ 正确：传递具有简单值的字典
def node_b(state: State):
    response = interrupt({
        "question": "输入用户详情",
        "fields": ["name", "email", "age"],
        "current_values": state.get("user", {})
    })
    return {"user": response}

# ❌ 错误：传递函数、类实例或其他复杂对象
class DataProcessor:
    def __init__(self, config):
        self.config = config

def node_c(state: State):
    processor = DataProcessor({"mode": "strict"})

    # ❌ 错误：传递类实例给 interrupt
    response = interrupt({
        "question": "输入要处理的数据",
        "processor": processor  # 这会失败
    })
    return {"result": response}
```

**规则 4：interrupt 之前的副作用必须是幂等的**

由于中断的工作原理是重新运行调用它们的节点，因此在 `interrupt` 之前调用的副作用（理想情况下）应该是幂等的。幂等性意味着相同的操作可以多次应用，而不会在初始执行之外改变结果。

例如，你可能会有一个 API 调用来更新节点内的记录。如果在该调用之后调用了 `interrupt`，那么当节点恢复时，该调用将被多次重新运行，这可能会覆盖最初的更新或创建重复的记录。

```python
# ✅ 正确：在 interrupt 前使用幂等操作
def node_a(state: State):
    db.upsert_user(user_id=state["user_id"], status="pending_approval")
    approved = interrupt("批准此更改？")
    return {"approved": approved}

# ✅ 正确：将副作用放在 interrupt 调用之后
def node_b(state: State):
    approved = interrupt("批准此更改？")
    if approved:
        db.create_audit_log(user_id=state["user_id"], action="approved")
    return {"approved": approved}

# ✅ 正确：尽可能将副作用分离到单独的节点中
def approval_node(state: State):
    # 只在此节点处理中断
    approved = interrupt("批准此更改？")
    return {"approved": approved}

def notification_node(state: State):
    # 副作用发生在单独的节点中
    # 这在批准后运行，所以只执行一次
    if state.approved:
        send_notification(
            user_id=state["user_id"],
            status="approved"
        )
    return state

# ❌ 错误：在 interrupt 前创建新记录（恢复时会重复创建）
def node_c(state: State):
    audit_id = db.create_audit_log({...})  # 每次恢复都会创建重复记录
    approved = interrupt("批准此更改？")
    return {"approved": approved, "audit_id": audit_id}

# ❌ 错误：在 interrupt 前向列表追加内容
def node_d(state: State):
    db.append_to_history(state["user_id"], "approval_requested")  # 每次恢复都会添加重复条目
    approved = interrupt("批准此更改？")
    return {"approved": approved}
```

**与作为函数调用的子图一起使用：**

在节点内调用子图时，父图将从调用子图并触发 `interrupt` 的节点的起始位置恢复执行。同样，子图也将从调用 `interrupt` 的节点的起始位置恢复执行。

```python
def node_in_parent_graph(state: State):
    some_code()  # <-- 恢复时会重新执行
    # 作为函数调用子图
    # 子图包含一个 `interrupt` 调用
    subgraph_result = subgraph.invoke(some_input)
    # ...

def node_in_subgraph(state: State):
    some_other_code()  # <-- 恢复时也会重新执行
    result = interrupt("你的名字是？")
    # ...
```

### 11.11 使用中断进行调试

要调试和测试图，你可以使用静态中断作为断点，一次逐步执行图中的一个节点。静态中断会在节点执行之前或之后的指定点触发。你可以在编译图时通过指定 `interrupt_before` 和 `interrupt_after` 来设置这些中断。

> **注意**：静态中断不建议用于人机协作工作流。请改用 `interrupt` 函数。

```python
# 运行时设置
config = {
    "configurable": {
        "thread_id": "some_thread"
    }
}

# 运行图直到断点
graph.invoke(
    inputs,
    interrupt_before=["node_a"],  # 在 node_a 执行前暂停
    interrupt_after=["node_b", "node_c"],  # 在这些节点执行后暂停
    config=config,
)

# 恢复图
graph.invoke(None, config=config)
```

**说明：**
- `interrupt_before` 指定在节点执行之前应暂停的节点
- `interrupt_after` 指定在节点执行之后应暂停的节点
- 图会运行直到遇到第一个断点
- 通过传入 `None` 作为输入来恢复图，这将运行图直到遇到下一个断点

要调试您的中断，请使用 LangSmith。你也可以使用 LangSmith Studio 在运行图之前，在用户界面中为图设置静态中断，还可以使用该用户界面检查执行过程中任何时刻的图状态。

### 11.12 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **什么是 LangGraph 的中断机制？** | 允许在特定点暂停图执行，等待外部输入后继续，实现人在回路模式 |
| **interrupt 和静态断点的区别？** | `interrupt()` 是动态的，可在代码任意位置条件触发；静态断点在编译时指定，用于调试 |
| **中断需要什么前提条件？** | 1) Checkpointer 持久化状态；2) thread_id 标识状态；3) 可序列化为 JSON 的中断负载 |
| **恢复时 interrupt 的返回值是什么？** | `Command(resume=...)` 传入的值会成为 `interrupt()` 调用的返回值 |
| **thread_id 的作用是什么？** | `thread_id` 是**持久化游标**：复用它恢复到同一检查点；使用新值则启动全新的空状态线程 |

**实践应用类：**

| 问题 | 答案要点 |
|------|----------|
| **如何恢复中断？** | 使用相同的 `thread_id`，调用 `graph.invoke(Command(resume=value), config)` |
| **如何处理多个并行中断？** | 构建 `{interrupt_id: resume_value}` 映射，传递给 `Command(resume=map)` |
| **节点恢复时从哪里开始？** | 从**节点开头**重新执行，因此 interrupt 前的代码会再次运行 |
| **为什么副作用要放在 interrupt 之后？** | 因为节点会重新执行，interrupt 前的非幂等操作会重复执行导致问题 |
| **如何实现输入验证？** | 在 while True 循环中调用 interrupt，验证失败则修改提示继续循环 |

**中断规则类：**

| 规则 | 说明 |
|------|------|
| **不要包裹 try/except** | 会捕获中断异常，导致中断无法传递；应使用特定异常类型 |
| **不要重新排序 interrupt** | 匹配是严格基于索引的，顺序改变或有条件跳过会导致值错配 |
| **不要传复杂对象** | 函数、类实例等无法序列化；只使用可 JSON 序列化的值 |
| **副作用要幂等** | interrupt 前的操作会重复执行，应使用幂等操作或将副作用放在 interrupt 后 |

**代码实操类：**

```python
# 面试常考：中断的基本用法

from langgraph.types import interrupt, Command

# 1. 在节点中使用中断
def approval_node(state):
    approved = interrupt("是否批准？")
    return {"approved": approved}

# 2. 初始调用 - 遇到中断
config = {"configurable": {"thread_id": "thread-1"}}
result = graph.invoke(inputs, config)
print(result["__interrupt__"])  # [Interrupt(value='是否批准？')]

# 3. 恢复执行
graph.invoke(Command(resume=True), config)

# 4. 处理多个并行中断
resume_map = {i.id: f"answer for {i.value}" for i in result["__interrupt__"]}
graph.invoke(Command(resume=resume_map), config)

# 5. 静态断点（调试用）
graph = builder.compile(
    interrupt_before=["node_a"],
    interrupt_after=["node_b"],
    checkpointer=checkpointer,
)

# 6. 验证输入循环
def get_input_node(state):
    prompt = "请输入年龄？"
    while True:
        answer = interrupt(prompt)
        if isinstance(answer, int) and answer > 0:
            return {"age": answer}
        prompt = f"'{answer}' 无效，请输入正数"
```

**对比记忆类：**

| 对比项 | interrupt() | 静态断点 |
|--------|-------------|----------|
| 设置时机 | 运行时，代码任意位置 | 编译时或运行时参数 |
| 触发方式 | 动态，可条件触发 | 固定，节点前后 |
| 主要用途 | 人机协作工作流 | 调试和测试 |
| 灵活性 | 高 | 低 |
| 推荐场景 | 生产环境 | 开发调试 |

## 12. 时间旅行（Time-Travel）

在处理基于模型做出决策的非确定性系统（例如由大语言模型驱动的智能体）时，详细检查它们的决策过程可能会很有用：

- **理解推理过程**：分析达成成功结果的步骤
- **调试错误**：确定错误发生的位置和原因
- **探索替代方案**：测试不同路径以发现更好的解决方案

LangGraph 提供了时间回溯功能来支持这些使用场景。具体来说，你可以从之前的检查点恢复执行——要么重放相同的状态，要么对其进行修改以探索其他可能性。在所有情况下，恢复过去的执行都会在历史记录中产生一个新的分支。

### 12.1 使用时间旅行的步骤

1. **运行图**：使用 `invoke` 或 `stream` 方法，以初始输入运行该图
2. **识别检查点**：使用 `get_state_history` 方法检索特定 `thread_id` 的执行历史，并找到所需的 `checkpoint_id`。或者，在希望执行暂停的节点之前设置一个 `interrupt`。然后，您可以找到截至该中断记录的最新检查点
3. **更新图状态（可选）**：使用 `update_state` 方法在检查点修改图的状态，并从替代状态恢复执行
4. **从检查点恢复执行**：使用 `invoke` 或 `stream` 方法，输入为 `None`，配置中包含适当的 `thread_id` 和 `checkpoint_id`

### 12.2 工作流示例

这个示例构建了一个简单的 LangGraph 工作流，该工作流使用大语言模型生成一个笑话主题并编写一个笑话。它展示了如何运行该图、检索过去的执行检查点、选择性地修改状态，以及从选定的检查点恢复执行以探索其他可能的结果。

**设置：**

```bash
pip install langchain_core langchain-anthropic langgraph
```

```python
import os
import getpass
from langchain_anthropic import ChatAnthropic

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("ANTHROPIC_API_KEY")

llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")
```

**实现工作流：**

该工作流的实现是一个简单的图，包含两个节点，一个用于生成笑话主题，另一个用于编写笑话本身，还有一个状态用于存储中间值。

```python
import uuid
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver


class State(TypedDict):
    topic: NotRequired[str]
    joke: NotRequired[str]


model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    temperature=0,
)


def generate_topic(state: State):
    """LLM 调用：生成笑话主题"""
    msg = model.invoke("给我一个有趣的笑话主题")
    return {"topic": msg.content}


def write_joke(state: State):
    """LLM 调用：根据主题编写笑话"""
    msg = model.invoke(f"写一个关于 {state['topic']} 的短笑话")
    return {"joke": msg.content}


# 构建工作流
workflow = StateGraph(State)

# 添加节点
workflow.add_node("generate_topic", generate_topic)
workflow.add_node("write_joke", write_joke)

# 添加边连接节点
workflow.add_edge(START, "generate_topic")
workflow.add_edge("generate_topic", "write_joke")
workflow.add_edge("write_joke", END)

# 编译
checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
```

### 12.3 步骤 1：运行图

要启动工作流，需调用 `invoke` 且不带任何输入。请注意 `thread_id`，以便跟踪此次执行并在之后检索其检查点。

```python
config = {
    "configurable": {
        "thread_id": uuid.uuid4(),
    }
}
state = graph.invoke({}, config)

print(state["topic"])
print()
print(state["joke"])
```

输出示例：

```
"袜子的秘密生活"

我终于发现了所有丢失的袜子去哪了。原来它们根本没有丢失——它们只是和洗衣店里的其他袜子私奔了，开始新的生活。

我的蓝色菱形纹袜子现在和一只红色波点袜子住在百慕大，在袜子上发度假照片，还给我寄棉絮当赡养费。
```

### 12.4 步骤 2：识别检查点

要从图运行中的上一个点继续，请使用 `get_state_history` 检索所有状态，并选择要从中恢复执行的状态。

```python
# 状态按时间倒序返回
states = list(graph.get_state_history(config))

for state in states:
    print(state.next)
    print(state.config["configurable"]["checkpoint_id"])
    print()
```

输出示例：

```
()
1f02ac4a-ec9f-6524-8002-8f7b0bbeed0e

('write_joke',)
1f02ac4a-ce2a-6494-8001-cb2e2d651227

('generate_topic',)
1f02ac4a-a4e0-630d-8000-b73c254ba748

('__start__',)
1f02ac4a-a4dd-665e-bfff-e6c8c44315d9
```

```python
# 这是倒数第二个状态（状态按时间顺序列出）
selected_state = states[1]
print(selected_state.next)
print(selected_state.values)
```

输出示例：

```
('write_joke',)
{'topic': '"袜子的秘密生活"——探索袜子成对进入洗衣机却单独出来的神秘现象...'}
```

### 12.5 步骤 3：更新状态（可选）

`update_state` 将创建一个新的检查点。这个新检查点将与同一个线程相关联，但会有一个新的检查点 ID。

```python
new_config = graph.update_state(selected_state.config, values={"topic": "chickens"})
print(new_config)
```

输出示例：

```
{'configurable': {'thread_id': 'c62e2e03-c27b-4cb6-8cea-ea9bfedae006', 'checkpoint_ns': '', 'checkpoint_id': '1f02ac4a-ecee-600b-8002-a1d21df32e4c'}}
```

### 12.6 步骤 4：从检查点恢复执行

要从选定的检查点恢复执行，请使用指向新检查点的配置调用 `invoke`。

```python
graph.invoke(None, new_config)
```

输出示例：

```python
{'topic': 'chickens',
 'joke': '为什么鸡加入了乐队？\n\n因为它有出色的鼓槌！'}
```

### 12.7 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **什么是时间旅行功能？** | 允许从之前的检查点恢复执行，重放状态或修改状态探索替代方案，产生新的历史分支 |
| **时间旅行有什么用途？** | 1) 理解推理过程；2) 调试错误；3) 探索替代方案 |
| **如何识别检查点？** | 使用 `get_state_history` 检索执行历史，找到所需的 `checkpoint_id` |

**实践应用类：**

| 问题 | 答案要点 |
|------|----------|
| **时间旅行的四个步骤？** | 1) 运行图；2) 识别检查点；3) 更新状态（可选）；4) 从检查点恢复执行 |
| **如何从检查点恢复？** | 调用 `invoke(None, config)`，config 包含 `thread_id` 和 `checkpoint_id` |
| **update_state 的作用？** | 在检查点修改图状态，创建新检查点（同一线程，新 checkpoint_id） |

**代码实操类：**

```python
# 面试常考：时间旅行基本用法

# 1. 运行图并记录 thread_id
config = {"configurable": {"thread_id": "my-thread"}}
result = graph.invoke(inputs, config)

# 2. 获取状态历史（倒序）
states = list(graph.get_state_history(config))

# 3. 选择要恢复的检查点
selected_state = states[1]  # 倒数第二个状态

# 4. 可选：更新状态
new_config = graph.update_state(
    selected_state.config,
    values={"topic": "新主题"}
)

# 5. 从检查点恢复执行
result = graph.invoke(None, new_config)
```

**对比记忆类：**

| 对比项 | 回放（Replay） | 时间旅行 |
|--------|----------------|----------|
| 状态修改 | 不修改 | 可修改 |
| 历史分支 | 不产生新分支 | 产生新分支 |
| 主要用途 | 调试、查看历史 | 探索替代方案、A/B 测试 |

## 13. 记忆（Memory）

人工智能应用需要记忆来在多次交互中共享上下文。在 LangGraph 中，你可以添加两种类型的记忆：

- **短期记忆**：作为智能体状态的一部分添加，以实现多轮对话
- **长期记忆**：跨会话存储用户特定数据或应用程序级数据

### 13.1 添加短期记忆

短期记忆（线程级持久性）使智能体能够跟踪多轮对话。

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph

checkpointer = InMemorySaver()

builder = StateGraph(...)
graph = builder.compile(checkpointer=checkpointer)

graph.invoke(
    {"messages": [{"role": "user", "content": "你好！我是小明"}]},
    {"configurable": {"thread_id": "1"}},
)
```

**生产环境中的使用：**

在生产环境中，使用由数据库支持的检查点工具：

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    builder = StateGraph(...)
    graph = builder.compile(checkpointer=checkpointer)
```

**在子图中的使用：**

如果你的图包含子图，只需在编译父图时提供检查点工具即可。LangGraph 会自动将检查点工具传播到子图中。

```python
from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict

class State(TypedDict):
    foo: str

# 子图
def subgraph_node_1(state: State):
    return {"foo": state["foo"] + "bar"}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# 父图
builder = StateGraph(State)
builder.add_node("node_1", subgraph)
builder.add_edge(START, "node_1")

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

你可以配置特定于子图的检查点行为：

```python
subgraph_builder = StateGraph(...)
subgraph = subgraph_builder.compile(checkpointer=True)
```

### 13.2 添加长期记忆

利用长期记忆跨对话存储用户特定或应用特定的数据。

```python
from langgraph.store.memory import InMemoryStore
from langgraph.graph import StateGraph

store = InMemoryStore()

builder = StateGraph(...)
graph = builder.compile(store=store)
```

**访问节点内部的存储：**

一旦你用存储编译图，LangGraph 会自动将该存储注入到你的节点函数中。访问存储的推荐方式是通过 Runtime 对象。

```python
from dataclasses import dataclass
from langgraph.runtime import Runtime
from langgraph.graph import StateGraph, MessagesState, START
import uuid

@dataclass
class Context:
    user_id: str

async def call_model(state: MessagesState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")

    # 搜索相关记忆
    memories = await runtime.store.asearch(
        namespace, query=state["messages"][-1].content, limit=3
    )
    info = "\n".join([d.value["data"] for d in memories])

    # ... 在模型调用中使用记忆

    # 存储新记忆
    await runtime.store.aput(
        namespace, str(uuid.uuid4()), {"data": "用户偏好深色模式"}
    )

builder = StateGraph(MessagesState, context_schema=Context)
builder.add_node(call_model)
builder.add_edge(START, "call_model")
graph = builder.compile(store=store)

# 在调用时传递上下文
graph.invoke(
    {"messages": [{"role": "user", "content": "你好"}]},
    {"configurable": {"thread_id": "1"}},
    context=Context(user_id="1"),
)
```

**生产环境中的使用：**

```python
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresStore.from_conn_string(DB_URI) as store:
    builder = StateGraph(...)
    graph = builder.compile(store=store)
```

### 13.3 使用语义搜索

在你的图的内存存储中启用语义搜索，让图智能体能够通过语义相似度在存储中搜索项目。

```python
from langchain.embeddings import init_embeddings
from langgraph.store.memory import InMemoryStore

# 创建启用语义搜索的存储
embeddings = init_embeddings("openai:text-embedding-3-small")
store = InMemoryStore(
    index={
        "embed": embeddings,
        "dims": 1536,
    }
)

store.put(("user_123", "memories"), "1", {"text": "我喜欢披萨"})
store.put(("user_123", "memories"), "2", {"text": "我是水管工"})

items = store.search(
    ("user_123", "memories"), query="我饿了", limit=1
)
```

### 13.4 管理短期记忆

启用短期记忆后，长对话可能会超出大语言模型的上下文窗口。常见的解决方案包括：

- **修剪消息**：删除开头或结尾的 N 条消息（在调用大语言模型之前）
- **删除消息**：从 LangGraph 状态中永久删除消息
- **总结消息**：总结历史记录中较早的消息，并用摘要替换它们
- **管理检查点**：存储和检索消息历史记录
- **自定义策略**：例如，消息过滤等

这使得智能体能够跟踪对话，同时不会超出大语言模型的上下文窗口。

### 13.5 修剪消息

大多数大语言模型都有一个最大支持的上下文窗口（以令牌为单位）。决定何时截断消息的一种方法是计算消息历史中的令牌数量，并在接近该限制时进行截断。

```python
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)

def call_model(state: MessagesState):
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=128,
        start_on="human",
        end_on=("human", "tool"),
    )
    response = model.invoke(messages)
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node(call_model)
```

### 13.6 删除消息

你可以从图状态中删除消息来管理消息历史。当你想要删除特定消息或清除整个消息历史时，这会很有用。

要让 `RemoveMessage` 正常工作，你需要使用带有 `add_messages` reducer 的状态键，例如 `MessagesState`。

**删除特定消息：**

```python
from langchain.messages import RemoveMessage

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # 删除最早的两条消息
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
```

**删除所有消息：**

```python
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

> **注意**：删除消息时，确保生成的消息历史记录有效。一些提供商要求消息历史以用户消息开始；大多数提供商要求包含工具调用的助手消息后必须跟有相应的工具结果消息。

### 13.7 总结消息

修剪或删除消息的问题在于，你可能会因删减消息队列而丢失信息。一些应用程序会受益于一种更复杂的方法——使用聊天模型来总结消息历史。

你可以扩展 `MessagesState` 以包含一个 `summary` 键：

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    summary: str
```

然后，你可以生成聊天历史的摘要，并将任何现有的摘要作为下一次摘要的上下文：

```python
def summarize_conversation(state: State):
    # 首先，获取任何现有的摘要
    summary = state.get("summary", "")

    # 创建摘要提示
    if summary:
        # 摘要已存在
        summary_message = (
            f"这是迄今为止对话的摘要：{summary}\n\n"
            "通过考虑上面的新消息来扩展摘要："
        )
    else:
        summary_message = "创建上述对话的摘要："

    # 将提示添加到历史记录
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)

    # 删除除最近 2 条消息外的所有消息
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}
```

### 13.8 管理检查点

你可以查看和删除检查点工具存储的信息。

**查看线程状态：**

```python
config = {
    "configurable": {
        "thread_id": "1",
        # 可选：提供特定检查点的 ID
        # 否则显示最新检查点
        # "checkpoint_id": "1f029ca3-1f5b-6704-8004-820c16b69a5a"
    }
}
graph.get_state(config)
```

**查看对话历史：**

```python
config = {
    "configurable": {
        "thread_id": "1"
    }
}
list(graph.get_state_history(config))
```

**删除一个线程的所有检查点：**

```python
thread_id = "1"
checkpointer.delete_thread(thread_id)
```

### 13.9 数据库管理

如果您正在使用任何基于数据库的持久性实现（如 Postgres 或 Redis）来存储短期和/或长期记忆，那么在将其与数据库一起使用之前，您需要运行迁移以设置所需的架构。

按照惯例，大多数特定于数据库的库会在检查点或存储实例上定义一个 `setup()` 方法，用于运行所需的迁移。

```python
# 运行数据库迁移
await checkpointer.setup()
# 或
await store.setup()
```

我们建议将迁移作为专门的部署步骤来运行，或者您也可以确保它们在服务器启动时运行。

### 13.10 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **LangGraph 有哪两种记忆类型？** | 1) 短期记忆（线程级持久化，多轮对话）；2) 长期记忆（跨会话存储用户数据） |
| **短期记忆如何实现？** | 使用 Checkpointer（如 `InMemorySaver`、`PostgresSaver`）编译图时传入 |
| **长期记忆如何实现？** | 使用 Store（如 `InMemoryStore`、`PostgresStore`）编译图时传入 |
| **如何在节点中访问 Store？** | 通过 Runtime 对象：`runtime.store.asearch()` / `runtime.store.aput()` |

**实践应用类：**

| 问题 | 答案要点 |
|------|----------|
| **如何管理超出上下文窗口的对话？** | 1) 修剪消息；2) 删除消息；3) 总结消息；4) 自定义策略 |
| **如何删除特定消息？** | 使用 `RemoveMessage(id=m.id)`，需要 `add_messages` reducer |
| **如何删除所有消息？** | 使用 `RemoveMessage(id=REMOVE_ALL_MESSAGES)` |
| **总结消息的优势？** | 不会丢失信息，用摘要替换早期消息 |

**代码实操类：**

```python
# 面试常考：记忆管理基本用法

# 1. 添加短期记忆
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# 2. 添加长期记忆
from langgraph.store.memory import InMemoryStore
store = InMemoryStore()
graph = builder.compile(store=store)

# 3. 修剪消息
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
messages = trim_messages(
    state["messages"],
    strategy="last",
    token_counter=count_tokens_approximately,
    max_tokens=128,
)

# 4. 删除消息
from langchain.messages import RemoveMessage
return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}

# 5. 查看线程状态
graph.get_state({"configurable": {"thread_id": "1"}})

# 6. 查看历史
list(graph.get_state_history(config))
```

**对比记忆类：**

| 对比项 | 短期记忆 | 长期记忆 |
|--------|----------|----------|
| 存储方式 | Checkpointer | Store |
| 作用范围 | 单线程/会话 | 跨会话 |
| 典型用途 | 多轮对话 | 用户画像、偏好 |
| 生产环境 | PostgresSaver | PostgresStore |

| 对比项 | 修剪消息 | 删除消息 | 总结消息 |
|--------|----------|----------|----------|
| 信息保留 | 部分保留 | 完全删除 | 摘要保留 |
| 实现复杂度 | 低 | 低 | 中 |
| 适用场景 | 固定窗口 | 清理历史 | 长对话 |

## 14. 调试与观测（Studio / tracing / 自定义事件）

- LangGraph Studio：可视化主图/子图结构与执行路径；适合"看懂路由/循环为什么这么走"。
- tracing（LangSmith/Langfuse 等）：把一次请求当作 root trace，在节点/LLM/工具调用里透传 callbacks。
- 自定义日志事件：用 writer 输出结构化事件（前端/日志系统更容易消费）。

### 观测：Langfuse（开源，可选）

Langfuse 是开源自建的 tracing/观测平台。最简单的接入方式是给 LLM 调用传 callbacks：

- 配置环境变量：`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、（可选）`LANGFUSE_HOST`
- 将 `CallbackHandler()` 放进 `config={"callbacks": [...]}`，并在 `llm.invoke(..., config=...)` 以及 `graph.stream(..., config=...)` 里透传

> `week04/p42-langgraph-0RAG.ipynb` 已按上述方式做了"可选启用"：不配 key 时自动禁用，不影响运行。

## 15. 工程模板与部署（可复制，用于作业/项目）

### 15.1 应用结构

一个 LangGraph 应用程序由以下部分组成：
- 一个或多个图
- 一个配置文件（`langgraph.json`）
- 一个指定依赖项的文件
- 一个可选的 `.env` 文件（指定环境变量）

**典型目录结构：**

```
my-app/
├── my_agent              # 所有项目代码
│   ├── utils             # 图的工具
│   │   ├── __init__.py
│   │   ├── tools.py      # 图的工具函数
│   │   ├── nodes.py      # 图的节点函数
│   │   └── state.py      # 图的状态定义
│   ├── __init__.py
│   └── agent.py          # 构建图的代码
├── .env                  # 环境变量
├── requirements.txt      # 包依赖（或 pyproject.toml）
└── langgraph.json        # LangGraph 配置文件
```

### 15.2 配置文件（langgraph.json）

`langgraph.json` 文件是一个 JSON 文件，指定了部署 LangGraph 应用程序所需的依赖项、图、环境变量和其他设置。

**配置示例：**

```json
{
  "dependencies": ["langchain_openai", "./your_package"],
  "graphs": {
    "my_agent": "./your_package/your_file.py:agent"
  },
  "env": "./.env"
}
```

**说明：**
- `dependencies`：指定依赖项，包括自定义本地包和第三方包
- `graphs`：指定可用的图，每个图通过唯一名称和路径标识
- `env`：指定环境变量文件路径

### 15.3 依赖项管理

要正确设置依赖项，需要指定：

1. **依赖文件**：目录中指定依赖项的文件（如 `requirements.txt`、`pyproject.toml`）
2. **dependencies 键**：在 LangGraph 配置文件中指定运行应用所需的依赖
3. **dockerfile_lines 键**：（可选）指定额外的二进制文件或系统库

### 15.4 图的配置

使用 `graphs` 键在配置文件中指定哪些图将在部署的应用中可用。

可以指定一个或多个图。每个图通过名称（唯一）和路径标识：
- 已编译的图
- 或定义生成图的函数

**示例：**

```json
{
  "graphs": {
    "agent": "./src/agent.py:graph",
    "rag_agent": "./src/rag.py:compiled_graph"
  }
}
```

### 15.5 环境变量

- **本地开发**：在 `env` 键中配置 `.env` 文件路径
- **生产部署**：在部署环境中配置环境变量

### 15.6 本仓库模板

本仓库在 `week04/` 下有两套可复制模板：

**模板 A：LangGraph Server + Studio（推荐做演示）**

路径：`week04/app`

```bash
cd week04/app
pip install -e . "langgraph-cli[inmem]"
cp .env.example .env
langgraph dev
```

**模板 B：业务工作流工程化示例（条件路由 + 分层 + 测试）**

路径：`week04/app2`

```bash
cd week04/app2
pip install -e . "langgraph-cli[inmem]" pytest
cp .env.example .env
pytest -q
```

### 15.7 面试必背要点

**核心概念类：**

| 问题 | 答案要点 |
|------|----------|
| **LangGraph 应用由哪些部分组成？** | 1) 一个或多个图；2) langgraph.json 配置文件；3) 依赖文件；4) .env 环境变量 |
| **langgraph.json 的作用？** | 指定依赖项、图、环境变量和其他部署设置 |
| **如何指定多个图？** | 在 `graphs` 键中以键值对形式指定，名称唯一 |

**配置实操类：**

```json
// 典型 langgraph.json 配置
{
  "dependencies": [
    "langchain_openai",
    "./my_agent"  // 本地包
  ],
  "graphs": {
    "my_agent": "./my_agent/agent.py:graph"
  },
  "env": "./.env"
}
```

**目录结构类：**

| 文件/目录 | 作用 |
|-----------|------|
| `langgraph.json` | 配置文件，指定依赖、图、环境变量 |
| `requirements.txt` / `pyproject.toml` | Python 依赖 |
| `.env` | 环境变量（API 密钥等） |
| `my_agent/utils/` | 工具函数、节点、状态定义 |
| `my_agent/agent.py` | 图的构建和编译 |

## 16. 参考链接

- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- Persistence 概念：https://github.langchain.ac.cn/langgraph/concepts/persistence/
