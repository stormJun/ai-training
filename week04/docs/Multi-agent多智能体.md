# 1. Multi-agent 多智能体

> **文档索引**：获取完整文档索引：https://docs.langchain.com/llms.txt
> 在进一步探索之前，使用此文件发现所有可用页面。

## 目录

- [1. Multi-agent 多智能体](#1-multi-agent-多智能体)
  - [1.1 为什么需要多智能体？](#11-为什么需要多智能体)
  - [1.2 模式概览](#12-模式概览)
    - [1.2.1 选择模式](#121-选择模式)
    - [1.2.2 可视化概览](#122-可视化概览)
- [2. 子智能体详细指南](#2-子智能体详细指南)
- [3. 交接详细指南](#3-交接详细指南)
- [4. 路由器详细指南](#4-路由器详细指南)
- [5. 自定义工作流详细指南](#5-自定义工作流详细指南)
- [6. 性能比较](#6-性能比较)
- [7. 最佳实践](#7-最佳实践)
- [8. 相关资源](#8-相关资源)

---

多智能体系统协调专门的组件来处理复杂的工作流程。然而，并非每个复杂任务都需要这种方法——拥有正确（有时是动态的）工具和提示的单个智能体通常可以达到类似的效果。

## 1.1 为什么需要多智能体？

当开发者说他们需要"多智能体"时，他们通常在寻找以下一个或多个能力：

* **上下文管理**：提供专门的知识而不让模型的上下文窗口不堪重负。如果上下文是无限的且延迟为零，你可以将所有知识转储到单个提示中——但由于事实并非如此，你需要模式来选择性地呈现相关信息。
* **分布式开发**：允许不同的团队独立开发和维护功能，将它们组合成一个具有清晰边界的更大系统。
* **并行化**：为子任务生成专门的工作器并并发执行它们以获得更快的结果。

当单个智能体有太多的[工具](/oss/python/langchain/tools)并且在使用哪个工具方面做出错误决策时，当任务需要具有大量上下文的专门知识（长提示和领域特定工具）时，或者当你需要强制执行仅在满足某些条件后才解锁功能的顺序约束时，多智能体模式特别有价值。

> 在多智能体设计的核心是**[上下文工程](/oss/python/langchain/context-engineering)**——决定每个智能体看到什么信息。系统的质量取决于确保每个智能体都能访问其任务所需的正确数据。

## 1.2 模式概览

以下是构建多智能体系统的主要模式，每种模式适用于不同的用例：

| 模式                                                                  | 工作原理                                                                                                                                                                                        |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [**子智能体**](#子智能体详细指南)             | 主智能体将子智能体作为工具进行协调。所有路由都通过主智能体，主智能体决定何时以及如何调用每个子智能体。                                                         |
| [**交接**](#交接详细指南)               | 行为根据状态动态变化。工具调用更新状态变量，触发路由或配置更改，切换智能体或调整当前智能体的工具和提示。 |
| [**技能**](#技能详细指南)                   | 按需加载专门的提示和知识。单个智能体保持控制，同时根据需要从技能加载上下文。                                                                    |
| [**路由器**](#路由器)                   | 路由步骤对输入进行分类并将其定向到一个或多个专门的智能体。结果被合成为组合响应。                                                                 |
| [**自定义工作流**](#自定义工作流) | 使用 [LangGraph](/oss/python/langgraph/overview) 构建定制执行流程，混合确定性逻辑和智能体行为。将其他模式作为节点嵌入到你的工作流中。                    |

### 1.2.1 选择模式

使用此表将你的需求与正确的模式匹配：

| 模式 | 分布式开发 | 并行化 | 多跳 | 直接用户交互 |
|------|:----------:|:------:|:----:|:------------:|
| [**子智能体**](#子智能体详细指南) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| [**交接**](#交接详细指南) | — | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| [**技能**](#技能详细指南) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| [**路由器**](#路由器) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ |

* **分布式开发**：不同的团队可以独立维护组件吗？
* **并行化**：多个智能体可以并发执行吗？
* **多跳**：该模式是否支持串联调用多个子智能体？
* **直接用户交互**：子智能体可以直接与用户对话吗？

> 你可以混合使用模式！例如，**子智能体**架构可以调用工具，这些工具又调用自定义工作流或路由器智能体。子智能体甚至可以使用**技能**模式按需加载上下文。可能性是无限的！

### 1.2.2 可视化概览

#### 子智能体（Subagents）
主智能体将子智能体作为工具进行协调。所有路由都通过主智能体。

```
┌──────────┐
│   用户    │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│    主智能体       │
│  (Main Agent)    │
└──┬────┬────┬─────┘
   │    │    │
   ▼    ▼    ▼
┌────┐┌────┐┌────┐
│子A ││子B ││子C │
└─┬──┘└─┬──┘└─┬──┘
  │     │     │
  └─────┴─────┘
        │
        ▼
┌──────────────────┐
│   用户响应        │
└──────────────────┘
```

#### 交接（Handoffs）
智能体通过工具调用相互转移控制权。每个智能体可以交接给其他智能体或直接响应用户。

```
┌──────────┐     交接      ┌──────────┐     交接      ┌──────────┐
│  智能体A  │ ──────────► │  智能体B  │ ──────────► │  智能体C  │
│ (Agent A)│             │ (Agent B)│             │ (Agent C)│
└──────────┘             └──────────┘             └──────────┘
     │                        │                        │
     │                        │                        │
     ▼                        ▼                        ▼
  直接响应                  直接响应                  直接响应
   用户                     用户                     用户
```

#### 技能（Skills）
单个智能体按需加载专门的提示和知识，同时保持控制。

```
┌──────────┐
│   用户    │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│    智能体         │
└──┬────┬────┬─────┘
   │    │    │
   ▼    ▼    ▼
┌────┐┌────┐┌────┐
│技能A││技能B││技能C│
└────┘└────┘└────┘
```

#### 路由器（Router）
路由步骤对输入进行分类并将其定向到专门的智能体。结果被合成。

```
                        ┌──────────────┐
                        │    输入      │
                        │   (Input)    │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   路由步骤    │
                        │  (Routing)   │
                        └──────┬───────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐
   │ 专门智能体 A  │    │ 专门智能体 B  │    │ 专门智能体 C  │
   │(Specialized  │    │(Specialized  │    │(Specialized  │
   │   Agent A)   │    │   Agent B)   │    │   Agent C)   │
   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                        ┌──────▼───────┐
                        │  结果合成    │
                        │ (Synthesis)  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │    输出      │
                        │  (Output)    │
                        └──────────────┘
```

---

# 2. 子智能体详细指南

在**子智能体**架构中，一个中央主智能体（通常称为**监督者 supervisor**）通过将子智能体作为工具调用来协调它们。主智能体决定调用哪个子智能体、提供什么输入以及如何组合结果。

子智能体是无状态的——它们不记得过去的交互，所有对话记忆都由主智能体维护。这提供了上下文隔离：每次子智能体调用都在干净的上下文窗口中工作，防止主对话中的上下文膨胀。

## 2.1 关键特性

* **集中控制**：所有路由都通过主智能体
* **无直接用户交互**：子智能体将结果返回给主智能体，而不是用户（尽管你可以在子智能体内使用中断来允许用户交互）
* **通过工具调用子智能体**：子智能体通过工具调用
* **并行执行**：主智能体可以在单轮中调用多个子智能体

> **Supervisor vs. Router** (监督者 vs. 路由器)：监督者智能体（此模式）与路由器不同。监督者是一个完整的智能体，它维护对话上下文并在多轮中动态决定调用哪些子智能体。路由器通常是单个分类步骤，将请求分发给智能体而不维护持续的对话状态。

## 2.2 何时使用

当你有多个不同的领域（例如，日历、电子邮件、CRM、数据库），子智能体不需要直接与用户对话，或者你想要集中式工作流控制时，使用子智能体模式。对于只有少量工具的简单情况，使用单个智能体。

> **需要在子智能体内进行用户交互？** 虽然子智能体通常将结果返回给主智能体而不是直接与用户对话，但你可以在子智能体内使用中断来暂停执行并收集用户输入。当子智能体在继续之前需要澄清或批准时，这很有用。主智能体仍然是协调者，但子智能体可以在任务中途从用户收集信息。

## 2.3 基本实现

核心机制是将子智能体包装为主智能体可以调用的工具：

```python
from langchain.tools import tool
from langchain.agents import create_agent

# 创建一个子智能体
subagent = create_agent(model="anthropic:claude-sonnet-4-20250514", tools=[...])

# 将其包装为工具
@tool("research", description="研究一个主题并返回发现")
def call_research_agent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# 带有子智能体作为工具的主智能体
main_agent = create_agent(model="anthropic:claude-sonnet-4-20250514", tools=[call_research_agent])
```

## 2.4 设计决策

在实现子智能体模式时，你将做出几个关键的设计选择：

| 决策 | 选项 |
|------|------|
| [**同步 vs. 异步**](#同步-vs-异步) | 同步（阻塞）vs. 异步（后台） |
| [**工具模式**](#工具模式) | 每个智能体一个工具 vs. 单一分发工具 |
| [**子智能体规范**](#子智能体规范) | 系统提示 vs. 枚举约束 vs. 基于工具的发现（仅限单一分发工具） |
| [**子智能体输入**](#子智能体输入) | 仅查询 vs. 完整上下文 |
| [**子智能体输出**](#子智能体输出) | 子智能体结果 vs 完整对话历史 |

### 2.4.1 同步 vs. 异步

子智能体执行可以是**同步**（阻塞）或**异步**（后台）。你的选择取决于主智能体是否需要结果才能继续。

| 模式      | 主智能体行为                         | 最适合                               | 权衡                            |
| --------- | ------------------------------------------- | -------------------------------------- | ----------------------------------- |
| **同步**  | 等待子智能体完成              | 主智能体需要结果才能继续    | 简单，但会阻塞对话 |
| **异步** | 在子智能体在后台运行时继续 | 独立任务，用户不应等待 | 响应式，但更复杂        |

> 不要与 Python 的 `async`/`await` 混淆。这里的"async"意味着主智能体启动一个后台作业（通常在单独的进程或服务中）并在不阻塞的情况下继续。

#### 同步（默认）

默认情况下，子智能体调用是**同步**的——主智能体在继续之前等待每个子智能体完成。当主智能体的下一个操作依赖于子智能体的结果时使用同步。

![image-20260302132815987](/Users/songxijun/workspace/otherProject/ai-training/week04/docs/assets/image-20260302132815987.png)

**何时使用同步：**

* 主智能体需要子智能体的结果来制定其响应
* 任务有顺序依赖性（例如，获取数据 → 分析 → 响应）
* 子智能体失败应该阻塞主智能体的响应

**权衡：**

* 简单的实现——只需调用并等待
* 用户在所有子智能体完成之前看不到响应
* 长时间运行的任务会冻结对话

#### 异步

当子智能体的工作是独立的时使用**异步执行**——主智能体不需要结果就能继续与用户对话。主智能体启动一个后台作业并保持响应。

**何时使用异步：**

* 子智能体工作独立于主对话流程
* 用户应该能够在工作发生时继续聊天
* 你想要并行运行多个独立任务

**三工具模式：**

1. **启动作业**：启动后台任务，返回作业 ID
2. **检查状态**：返回当前状态（待处理、运行中、已完成、失败）
3. **获取结果**：检索已完成的结果

**处理作业完成：** 当作业完成时，你的应用程序需要通知用户。一种方法：显示一个通知，当点击时，发送一个 `HumanMessage`，如"检查 job_123 并总结结果。"

### 2.4.2 工具模式

有两种主要方式将子智能体公开为工具：

| 模式                                           | 最适合                                                      | 权衡                                         |
| ------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------- |
| [**每个智能体一个工具**](#每个智能体一个工具)             | 对每个子智能体的输入/输出进行细粒度控制        | 更多设置，但更多自定义                |
| [**单一分发工具**](#单一分发工具) | 许多智能体、分布式团队、约定优于配置 | 更简单的组合，更少的每个智能体自定义 |

#### 每个智能体一个工具

关键思想是将子智能体包装为主智能体可以调用的工具：

```python
from langchain.tools import tool
from langchain.agents import create_agent

# 创建一个子智能体
subagent = create_agent(model="...", tools=[...])

# 将其包装为工具
@tool("subagent_name", description="subagent_description")
def call_subagent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# 带有子智能体作为工具的主智能体
main_agent = create_agent(model="...", tools=[call_subagent])
```

主智能体在决定任务与子智能体的描述匹配时调用子智能体工具，接收结果，并继续编排。

#### 单一分发工具

另一种方法是使用单个参数化工具为独立任务调用临时子智能体。与每个智能体一个工具方法（其中每个子智能体被包装为单独的工具）不同，这使用基于约定的方法，使用单个 `task` 工具：任务描述作为人类消息传递给子智能体，子智能体的最终消息作为工具结果返回。

当你想要跨多个团队分发智能体开发、需要将复杂任务隔离到单独的上下文窗口中、需要一种可扩展的方式来添加新智能体而不修改协调器，或者更喜欢约定而不是自定义时，使用此方法。

**关键特性：**

* **单一任务工具**：一个参数化工具，可以按名称调用任何注册的子智能体
* **基于约定的调用**：按名称选择智能体，任务作为人类消息传递，最终消息作为工具结果返回
* **团队分发**：不同的团队可以独立开发和部署智能体
* **智能体发现**：子智能体可以通过系统提示（列出可用智能体）或通过渐进式披露（通过工具按需加载智能体信息）来发现

> 这种方法的一个有趣方面是，子智能体可能与主智能体具有完全相同的功能。在这种情况下，调用子智能体**实际上是关于上下文隔离**作为主要原因——允许复杂的多步骤任务在隔离的上下文窗口中运行，而不会使主智能体的对话历史膨胀。子智能体自主完成其工作并仅返回简洁的摘要，使主线程保持专注和高效。

<details>
<summary>智能体注册表与任务分发器示例</summary>

```python
from langchain.tools import tool
from langchain.agents import create_agent

# 由不同团队开发的子智能体
research_agent = create_agent(
    model="gpt-4.1",
    prompt="你是一个研究专家..."
)

writer_agent = create_agent(
    model="gpt-4.1",
    prompt="你是一个写作专家..."
)

# 可用子智能体的注册表
SUBAGENTS = {
    "research": research_agent,
    "writer": writer_agent,
}

@tool
def task(
    agent_name: str,
    description: str
) -> str:
    """为任务启动临时子智能体。

    可用智能体：
    - research：研究和事实查找
    - writer：内容创建和编辑
    """
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": description}
        ]
    })
    return result["messages"][-1].content

# 主协调器智能体
main_agent = create_agent(
    model="gpt-4.1",
    tools=[task],
    system_prompt=(
        "你协调专门的子智能体。"
        "可用：research（事实查找）、"
        "writer（内容创建）。"
        "使用 task 工具委派工作。"
    ),
)
```
## 2.5 子智能体上下文工程

控制上下文如何在主智能体和其子智能体之间流动：

| 类别 | 目的 | 影响 |
|------|------|------|
| [**子智能体规范**](#子智能体规范) | 确保子智能体在应该被调用时被调用 | 主智能体路由决策 |
| [**子智能体输入**](#子智能体输入) | 确保子智能体能够以优化的上下文良好执行 | 子智能体性能 |
| [**子智能体输出**](#子智能体输出) | 确保监督者能够根据子智能体结果采取行动 | 主智能体性能 |

### 2.5.1 子智能体规范

与子智能体关联的**名称**和**描述**是主智能体知道要调用哪些子智能体的主要方式。这些是提示杠杆——仔细选择它们。

* **名称**：主智能体如何引用子智能体。保持清晰且以行动为导向（例如，`research_agent`、`code_reviewer`）。
* **描述**：主智能体对子智能体能力的了解。具体说明它处理什么任务以及何时使用它。

对于单一分发工具设计，你还必须向主智能体提供有关它可以调用的子智能体的信息。你可以根据智能体数量以及注册表是静态还是动态，以不同方式提供此信息：

| 方法                        | 最适合                                 | 权衡                                                             |
| ----------------------------- | ---------------------------------------- | -------------------------------------------------------------------- |
| **系统提示枚举** | 小型、静态的智能体列表（< 10 个智能体） | 简单，但需要在智能体更改时更新提示               |
| **枚举约束**           | 小型、静态的智能体列表（< 10 个智能体） | 类型安全且明确，但需要在智能体更改时更改代码 |
| **基于工具的发现**      | 大型或动态的智能体注册表        | 灵活且可扩展，但增加了复杂性                           |

##### 系统提示枚举

在主智能体的系统提示中直接列出可用智能体。

**示例：**

```python
main_agent = create_agent(
    model="...",
    tools=[task],
    system_prompt=(
        "你协调专门的子智能体。"
        "可用智能体：\n"
        "- research：研究和事实查找\n"
        "- writer：内容创建和编辑\n"
        "- reviewer：代码和文档审查\n"
        "使用 task 工具委派工作。"
    ),
)
```

##### 枚举约束

在分发工具的 `agent_name` 参数中添加枚举约束。

**示例：**

```python
from enum import Enum

class AgentName(str, Enum):
    RESEARCH = "research"
    WRITER = "writer"
    REVIEWER = "reviewer"

@tool
def task(
    agent_name: AgentName,  # 枚举约束
    description: str
) -> str:
    """为任务启动临时子智能体。"""
    # ...
```

##### 基于工具的发现

提供一个单独的工具（例如，`list_agents` 或 `search_agents`），主智能体可以调用它来按需发现可用智能体。

**示例：**

```python
@tool
def list_agents(query: str = "") -> str:
    """列出可用的子智能体，可选择按查询过滤。"""
    agents = search_agent_registry(query)
    return format_agent_list(agents)

@tool
def task(agent_name: str, description: str) -> str:
    """为任务启动临时子智能体。"""
    # ...

main_agent = create_agent(
    model="...",
    tools=[task, list_agents],
    system_prompt="使用 list_agents 发现可用的子智能体，然后使用 task 调用它们。"
)
```

### 2.5.2 子智能体输入

自定义子智能体接收什么上下文来执行其任务。通过从智能体的状态中提取，添加在静态提示中不切实际捕获的输入——完整的消息历史、先前的结果或任务元数据。

```python
from langchain.agents import AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    example_state_key: str

@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(query: str, runtime: ToolRuntime[None, CustomState]):
    # 应用任何需要的逻辑将消息转换为合适的输入
    subagent_input = some_logic(query, runtime.state["messages"])
    result = subagent1.invoke({
        "messages": subagent_input,
        "example_state_key": runtime.state["example_state_key"]
    })
    return result["messages"][-1].content
```

### 2.5.3 子智能体输出

自定义主智能体接收回的内容，以便它可以做出良好的决策。两种策略：

1. **提示子智能体**：明确指定应该返回什么。一个常见的失败模式是子智能体执行工具调用或推理，但不在其最终消息中包含结果——提醒它监督者只看到最终输出。
2. **在代码中格式化**：在返回响应之前调整或丰富响应。例如，除了最终文本之外，还使用 `Command` 传回特定的状态键。

```python
from typing import Annotated
from langchain.agents import AgentState
from langchain.tools import InjectedToolCallId
from langgraph.types import Command

@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    result = subagent1.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return Command(update={
        "example_state_key": result["example_state_key"],
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id
            )
        ]
    })
```

## 2.6 检查点和状态检查

默认情况下，子智能体使用**继承的检查点**模式——每次调用都以新鲜状态开始、支持中断并安全地并行运行。如果你需要子智能体在调用之间维护自己的持久对话历史，请使用 `checkpointer=True`（延续模式）编译它。

因为子智能体在工具函数内调用，LangGraph 无法静态发现它们。这意味着 `get_state` 与 `subgraphs` 不会返回子智能体状态。如果你需要读取嵌套图状态（例如，在中断期间），请从节点函数在自定义图中调用子智能体  langgraph Subgraphs。

---

# 3. 交接详细指南

在**交接**架构中，行为根据状态动态变化。

核心机制：工具更新一个跨轮次持久化的状态变量（例如 `current_step` 或 `active_agent`），系统读取此变量来调整行为——要么应用不同的配置（系统提示、工具），要么路由到不同的智能体。此模式既支持不同智能体之间的交接，也支持单个智能体内的动态配置更改。

> **handoffs**一词由 [OpenAI](https://openai.github.io/openai-agents-python/handoffs/) 创造，用于使用工具调用（例如 `transfer_to_sales_agent`）在智能体或状态之间转移控制权。

## 3.1 关键特性

* **状态驱动行为**：行为基于状态变量（例如 `current_step` 或 `active_agent`）变化
* **基于工具的转换**：工具更新状态变量以在状态之间移动
* **直接用户交互**：每个状态的配置直接处理用户消息
* **持久状态**：状态在对话轮次之间保持

## 3.2 何时使用

当你需要强制执行顺序约束（仅在满足前提条件后解锁功能）、智能体需要在不同状态下直接与用户对话，或者你正在构建多阶段对话流程时，使用交接模式。此模式对于客户支持场景特别有价值，在这些场景中你需要按特定顺序收集信息——例如，在处理退款之前收集保修 ID。

## 3.3 基本实现

核心机制是一个工具，它返回一个 `Command` 来更新状态，触发到新步骤或智能体的转换：

```python
from langchain.tools import tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def transfer_to_specialist(runtime) -> Command:
    """转移到专家智能体。"""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="已转移到专家",
                    tool_call_id=runtime.tool_call_id
                )
            ],
            "current_step": "specialist"  # 触发行为更改
        }
    )
```

> **为什么要包含 `ToolMessage`？** 当 LLM 调用工具时，它期望得到响应。带有匹配 `tool_call_id` 的 `ToolMessage` 完成此请求-响应周期——没有它，对话历史会变得畸形。每当你的交接工具更新消息时都需要这样做。

## 3.4 实现方法

有两种实现交接的方式：**[带中间件的单个智能体](#带中间件的单个智能体)**（具有动态配置的一个智能体）或**[多个智能体子图](#多个智能体子图)**（作为图节点的不同智能体）。

### 3.4.1 带中间件的单个智能体

单个智能体根据状态更改其行为。中间件拦截每个模型调用并动态调整系统提示和可用工具。工具更新状态变量以触发转换：

```python
from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """记录保修状态并转换到下一步。"""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"保修状态已记录：{status}",
                    tool_call_id=runtime.tool_call_id
                )
            ],
            "warranty_status": status,
            "current_step": "specialist"  # 更新状态以触发转换
        }
    )
```

<details>
<summary>完整示例：带中间件的客户支持</summary>

```python
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable

# 1. 定义带有 current_step 跟踪器的状态
class SupportState(AgentState):
    """跟踪当前活动的步骤。"""
    current_step: str = "triage"
    warranty_status: str | None = None

# 2. 工具通过 Command 更新 current_step
@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """记录保修状态并转换到下一步。"""
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"保修状态已记录：{status}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "warranty_status": status,
        # 转换到下一步
        "current_step": "specialist"
    })

# 3. 中间件根据 current_step 应用动态配置
@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """根据 current_step 配置智能体行为。"""
    step = request.state.get("current_step", "triage")

    # 将步骤映射到其配置
    configs = {
        "triage": {
            "prompt": "收集保修信息...",
            "tools": [record_warranty_status]
        },
        "specialist": {
            "prompt": "根据保修提供解决方案：{warranty_status}",
            "tools": [provide_solution, escalate]
        }
    }

    config = configs[step]
    request = request.override(
        system_prompt=config["prompt"].format(**request.state),
        tools=config["tools"]
    )
    return handler(request)

# 4. 使用中间件创建智能体
agent = create_agent(
    model,
    tools=[record_warranty_status, provide_solution, escalate],
    state_schema=SupportState,
    middleware=[apply_step_config],
    checkpointer=InMemorySaver()  # 跨轮次持久化状态
)
```


### 3.4.2 多个智能体子图

多个不同的智能体作为图中单独的节点存在。交接工具使用 `Command.PARENT` 在智能体节点之间导航，以指定接下来执行哪个节点。

> Subgraph handoffs 需要仔细的**上下文工程**。与单个智能体中间件（消息历史自然流动）不同，你必须明确决定哪些消息在智能体之间传递。弄错这一点，智能体会收到畸形的对话历史或膨胀的上下文。

```python
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command

@tool
def transfer_to_sales(
    runtime: ToolRuntime,
) -> Command:
    """转移到销售智能体。"""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="已转移到销售智能体",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT
    )
```

<details>
<summary>完整示例：带交接的销售和支持</summary>

此示例显示了一个具有独立销售和支持智能体的多智能体系统。每个智能体是一个单独的图节点，交接工具允许智能体相互转移对话。

```python
from typing import Literal
from langchain.agents import AgentState, create_agent
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import NotRequired

# 1. 定义带有 active_agent 跟踪器的状态
class MultiAgentState(AgentState):
    active_agent: NotRequired[str]

# 2. 创建交接工具
@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    """转移到销售智能体。"""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="已从支持智能体转移到销售智能体",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )

@tool
def transfer_to_support(runtime: ToolRuntime) -> Command:
    """转移到支持智能体。"""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="已从销售智能体转移到支持智能体",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="support_agent",
        update={
            "active_agent": "support_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )

# 3. 使用交接工具创建智能体
sales_agent = create_agent(
    model="anthropic:claude-sonnet-4-20250514",
    tools=[transfer_to_support],
    system_prompt="你是销售智能体。帮助销售咨询。如果被问及技术问题或支持，转移到支持智能体。",
)

support_agent = create_agent(
    model="anthropic:claude-sonnet-4-20250514",
    tools=[transfer_to_sales],
    system_prompt="你是支持智能体。帮助技术问题。如果被问及定价或购买，转移到销售智能体。",
)

# 4. 创建调用智能体的智能体节点
def call_sales_agent(state: MultiAgentState) -> Command:
    """调用销售智能体的节点。"""
    response = sales_agent.invoke(state)
    return response

def call_support_agent(state: MultiAgentState) -> Command:
    """调用支持智能体的节点。"""
    response = support_agent.invoke(state)
    return response

# 5. 创建路由器，检查是否应该结束或继续
def route_after_agent(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent", "__end__"]:
    """基于 active_agent 路由，如果智能体完成而没有交接则 END。"""
    messages = state.get("messages", [])

    # 检查最后一条消息 - 如果是没有工具调用的 AIMessage，我们就完成了
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
            return "__end__"

    # 否则路由到活动智能体
    active = state.get("active_agent", "sales_agent")
    return active if active else "sales_agent"

def route_initial(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent"]:
    """根据状态路由到活动智能体，默认为销售智能体。"""
    return state.get("active_agent") or "sales_agent"

# 6. 构建图
builder = StateGraph(MultiAgentState)
builder.add_node("sales_agent", call_sales_agent)
builder.add_node("support_agent", call_support_agent)

# 从基于初始 active_agent 的条件路由开始
builder.add_conditional_edges(START, route_initial, ["sales_agent", "support_agent"])

# 在每个智能体之后，检查是否应该结束或路由到另一个智能体
builder.add_conditional_edges(
    "sales_agent", route_after_agent, ["sales_agent", "support_agent", END]
)
builder.add_conditional_edges(
    "support_agent", route_after_agent, ["sales_agent", "support_agent", END]
)

graph = builder.compile()
```
> 对于大多数handoffs用例，使用**带中间件的单个智能体**——它更简单。
>
> 仅当你需要定制智能体实现（例如，一个本身就是具有反思或检索步骤的复杂图的节点）时，才使用**多个智能体子图**。

## 3.5 上下文工程

使用子图交接，你可以精确控制哪些消息在智能体之间流动。这种精度对于维护有效的对话历史和避免可能混淆下游智能体的上下文膨胀至关重要。

**在交接期间处理上下文**

在智能体之间交接时，你需要确保对话历史保持有效。LLM 期望工具调用与其响应配对，因此当使用 `Command.PARENT` 交接给另一个智能体时，你必须包含：

1. **包含工具调用的 `AIMessage`**（触发交接的消息）
2. **确认交接的 `ToolMessage`**（对该工具调用的人工响应）

没有这种配对，接收智能体将看到不完整的对话，并可能产生错误或意外行为。

```python
@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    # 获取触发此交接的 AI 消息
    last_ai_message = runtime.state["messages"][-1]

    # 创建人工工具响应以完成配对
    transfer_message = ToolMessage(
        content="已转移到销售智能体",
        tool_call_id=runtime.tool_call_id,
    )

    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            # 只传递这两条消息，而不是完整的子智能体历史
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )
```

> **为什么不传递所有子智能体消息？** 虽然你可以在交接中包含完整的子智能体对话，但这通常会产生问题。接收智能体可能会被无关的内部推理混淆，并且 token 成本会不必要地增加。通过只传递交接对，你可以使父图的上下文专注于高级协调。如果接收智能体需要额外的上下文，考虑在 ToolMessage 内容中总结子智能体的工作，而不是传递原始消息历史。

**将控制权返回给用户**

当将控制权返回给用户（结束智能体的轮次）时，确保最终消息是 `AIMessage`。这维护了有效的对话历史，并向用户界面发出智能体已完成其工作的信号。

## 3.6 实现考虑因素

在设计多智能体系统时，请考虑：

* **上下文过滤策略**：每个智能体是接收完整的对话历史、过滤的部分还是摘要？不同的智能体可能需要不同的上下文，具体取决于其角色。
* **工具语义**：阐明交接工具是仅更新路由状态还是也执行副作用。例如，`transfer_to_sales()` 是否也应该创建支持工单，还是应该是一个单独的操作？
* **Token 效率**：平衡上下文完整性与 token 成本。随着对话变长，摘要和选择性上下文传递变得更加重要。

---

# 4. 路由器详细指南

在**路由器**架构中，路由步骤对输入进行分类并将其定向到专门的智能体。当你有明确的**垂直领域**——每个都需要自己智能体的独立知识领域时，这很有用。

```
┌──────────┐
│   查询    │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│    路由器         │
└──┬────┬────┬─────┘
   │    │    │
   ▼    ▼    ▼
┌────┐┌────┐┌────┐
│智能A││智能B││智能C│
└──┬─┘└──┬─┘└──┬─┘
   │      │      │
   └──────┼──────┘
          │
          ▼
┌──────────────────┐
│   结果合成        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   组合答案        │
└──────────────────┘
```

## 4.1 关键特性

* 路由器分解查询
* 零个或多个专门智能体并行调用
* 结果被合成为连贯的响应

## 4.2 何时使用

当你有明确的垂直领域（每个都需要自己智能体的独立知识领域）、需要并行查询多个来源，并希望将结果合成为组合响应时，使用路由器模式。

## 4.3 基本实现

路由器对查询进行分类并将其定向到适当的智能体。使用 `Command` 进行单个智能体路由，或使用 `Send` 进行并行扇出到多个智能体。

#### 单个智能体

使用 `Command` 路由到单个专门智能体：

```python
from langgraph.types import Command

def classify_query(query: str) -> str:
    """使用 LLM 对查询进行分类并确定适当的智能体。"""
    # 分类逻辑在这里
    ...

def route_query(state: State) -> Command:
    """根据查询分类路由到适当的智能体。"""
    active_agent = classify_query(state["query"])

    # 路由到选定的智能体
    return Command(goto=active_agent)
```

#### 多个智能体（并行）

使用 `Send` 扇出到多个专门智能体并行执行：

```python
from typing import TypedDict
from langgraph.types import Send

class ClassificationResult(TypedDict):
    query: str
    agent: str

def classify_query(query: str) -> list[ClassificationResult]:
    """使用 LLM 对查询进行分类并确定要调用哪些智能体。"""
    # 分类逻辑在这里
    ...

def route_query(state: State):
    """根据查询分类路由到相关智能体。"""
    classifications = classify_query(state["query"])

    # 扇出到选定的智能体并行执行
    return [
        Send(c["agent"], {"query": c["query"]})
        for c in classifications
    ]
```

## 4.4 无状态 vs. 有状态

两种方法：

* [**无状态路由器**](#无状态路由器) 独立处理每个请求
* [**有状态路由器**](#有状态路由器) 在请求之间维护对话历史

### 4.4.1 无状态路由器

每个请求独立路由——调用之间没有记忆。对于多轮对话，请参阅[有状态路由器](#有状态路由器)。

> **路由器 vs. 子智能体**：两种模式都可以将工作分发给多个智能体，但它们在路由决策方式上有所不同：
>
> * **路由器**：一个专用的路由步骤（通常是单个 LLM 调用或基于规则的逻辑）对输入进行分类并分发给智能体。路由器本身通常不维护对话历史或执行多轮编排——它是一个预处理步骤。
> * **子智能体**：一个主监督者智能体作为持续对话的一部分动态决定调用哪些子智能体。主智能体维护上下文，可以跨轮次调用多个子智能体，并编排复杂的多步骤工作流。
>
> 当你有明确的输入类别并想要确定性或轻量级分类时，使用**路由器**。当你需要灵活的、对话感知的编排，其中 LLM 根据不断演变的上下文决定下一步做什么时，使用**监督者**。

### 4.4.2 有状态路由器

对于多轮对话，你需要跨调用维护上下文。

#### 工具包装器

最简单的方法：将无状态路由器包装为对话智能体可以调用的工具。对话智能体处理记忆和上下文；路由器保持无状态。这避免了跨多个并行智能体管理对话历史的复杂性。

```python
@tool
def search_docs(query: str) -> str:
    """跨多个文档来源搜索。"""
    result = workflow.invoke({"query": query})
    return result["final_answer"]

# 对话智能体使用路由器作为工具
conversational_agent = create_agent(
    model,
    tools=[search_docs],
    prompt="你是一个有用的助手。使用 search_docs 回答问题。"
)
```

#### 完整持久化

如果你需要路由器本身维护状态，使用[持久化](/oss/python/langchain/short-term-memory)来存储消息历史。当路由到智能体时，从状态中获取以前的消息并有选择地将它们包含在智能体的上下文中——这是[上下文工程](/oss/python/langchain/context-engineering)的一个杠杆。

> **有状态路由器需要自定义历史管理。** 如果路由器在轮次之间切换智能体，当智能体有不同的语气或提示时，对话对最终用户可能感觉不流畅。对于并行调用，你需要在路由器级别维护历史（输入和合成输出），并在路由逻辑中利用此历史。考虑使用[交接模式](#交接详细指南)或[子智能体模式](#子智能体详细指南)代替——两者都为多轮对话提供了更清晰的语义。

---

# 5. 自定义工作流详细指南

在**自定义工作流**架构中，你使用 [LangGraph](/oss/python/langgraph/overview) 定义自己的定制执行流程。你可以完全控制图结构——包括顺序步骤、条件分支、循环和并行执行。

```
┌──────────┐
│   输入    │
└─────┬────┘
      │
      ▼
┌──────────────┐
│  条件判断     │
└──┬────────┬──┘
   │        │
   │ path_a │ path_b
   ▼        ▼
┌──────┐  ┌──────────┐
│确定性 │  │ 智能体   │
│步骤  │  │  步骤    │
└──┬───┘  └────┬─────┘
   │           │
   └─────┬─────┘
         │
         ▼
   ┌──────────┐
   │   输出    │
   └──────────┘
```

## 5.1 关键特性

* 完全控制图结构
* 混合确定性逻辑和智能体行为
* 支持顺序步骤、条件分支、循环和并行执行
* 可以将其他模式作为节点嵌入到工作流中

## 5.2 何时使用

当标准模式（子智能体、技能等）不符合你的需求、你需要混合确定性逻辑和智能体行为，或者你的用例需要复杂的路由或多阶段处理时，使用自定义工作流。

工作流中的每个节点可以是一个简单的函数、一个 LLM 调用，或者一个带有[工具](/oss/python/langchain/tools)的完整[智能体](/oss/python/langchain/agents)。你还可以在自定义工作流中组合其他架构——例如，将多智能体系统作为单个节点嵌入。

## 5.3 基本实现

核心见解是你可以在任何 LangGraph 节点内直接调用 LangChain 智能体，将自定义工作流的灵活性与预构建智能体的便利性结合起来：

```python
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END

agent = create_agent(model="openai:gpt-4.1", tools=[...])

def agent_node(state: State) -> dict:
    """调用 LangChain 智能体的 LangGraph 节点。"""
    result = agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"answer": result["messages"][-1].content}

# 构建简单的工作流
workflow = (
    StateGraph(State)
    .add_node("agent", agent_node)
    .add_edge(START, "agent")
    .add_edge("agent", END)
    .compile()
)
```

## 5.4 示例：RAG 管道

一个常见的用例是将[检索](/oss/python/langchain/retrieval)与智能体结合。此示例构建了一个 WNBA 统计助手，它从知识库检索并可以获取实时新闻。

<details>
<summary>自定义 RAG 工作流示例</summary>

该工作流演示了三种类型的节点：

* **模型节点**（Rewrite）：使用[结构化输出](/oss/python/langchain/structured-output)重写用户查询以获得更好的检索效果。
* **确定性节点**（Retrieve）：执行向量相似度搜索——不涉及 LLM。
* **智能体节点**（Agent）：基于检索到的上下文进行推理，并可以通过工具获取额外信息。

```
┌──────────┐
│   查询    │
└─────┬────┘
      │
      ▼
┌──────────────┐
│   重写查询    │
└─────┬────────┘
      │
      ▼
┌──────────────┐
│    检索      │
└─────┬────────┘
      │
      ▼
┌──────────────┐
│   智能体      │
└─────┬────────┘
      │
      ▼
┌──────────────┐
│    响应      │
└──────────────┘
```

> **提示：** 你可以使用 LangGraph 状态在工作流步骤之间传递信息。这允许工作流的每个部分读取和更新结构化字段，使得在节点之间共享数据和上下文变得容易。

```python
from typing import TypedDict
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

class State(TypedDict):
    question: str
    rewritten_query: str
    documents: list[str]
    answer: str

# WNBA 知识库，包含阵容、比赛结果和球员统计数据
embeddings = OpenAIEmbeddings()
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_texts([
    # 阵容
    "New York Liberty 2024 阵容：Breanna Stewart, Sabrina Ionescu, Jonquel Jones, Courtney Vandersloot.",
    "Las Vegas Aces 2024 阵容：A'ja Wilson, Kelsey Plum, Jackie Young, Chelsea Gray.",
    "Indiana Fever 2024 阵容：Caitlin Clark, Aliyah Boston, Kelsey Mitchell, NaLyssa Smith.",
    # 比赛结果
    "2024 WNBA 总决赛：New York Liberty 以 3-2 击败 Minnesota Lynx 赢得冠军。",
    "2024 年 6 月 15 日：Indiana Fever 85, Chicago Sky 79。Caitlin Clark 得到 23 分和 8 次助攻。",
    "2024 年 8 月 20 日：Las Vegas Aces 92, Phoenix Mercury 84。A'ja Wilson 得到 35 分。",
    # 球员统计
    "A'ja Wilson 2024 赛季数据：26.9 PPG, 11.9 RPG, 2.6 BPG。获得 MVP 奖项。",
    "Caitlin Clark 2024 新秀数据：19.2 PPG, 8.4 APG, 5.7 RPG。获得年度最佳新秀。",
    "Breanna Stewart 2024 数据：20.4 PPG, 8.5 RPG, 3.5 APG。",
])
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

@tool
def get_latest_news(query: str) -> str:
    """获取最新的 WNBA 新闻和更新。"""
    # 在这里添加你的新闻 API
    return "最新消息：WNBA 宣布 2025 年将扩大季后赛格式..."

agent = create_agent(
    model="openai:gpt-4.1",
    tools=[get_latest_news],
)

model = ChatOpenAI(model="gpt-4.1")

class RewrittenQuery(BaseModel):
    query: str

def rewrite_query(state: State) -> dict:
    """重写用户查询以获得更好的检索效果。"""
    system_prompt = """重写此查询以检索相关的 WNBA 信息。
知识库包含：球队阵容、带比分的比赛结果和球员统计数据（PPG, RPG, APG）。
专注于提到的具体球员姓名、球队名称或统计类别。"""
    response = model.with_structured_output(RewrittenQuery).invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["question"]}
    ])
    return {"rewritten_query": response.query}

def retrieve(state: State) -> dict:
    """根据重写的查询检索文档。"""
    docs = retriever.invoke(state["rewritten_query"])
    return {"documents": [doc.page_content for doc in docs]}

def call_agent(state: State) -> dict:
    """使用检索到的上下文生成答案。"""
    context = "\n\n".join(state["documents"])
    prompt = f"上下文：\n{context}\n\n问题：{state['question']}"
    response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return {"answer": response["messages"][-1].content_blocks}

workflow = (
    StateGraph(State)
    .add_node("rewrite", rewrite_query)
    .add_node("retrieve", retrieve)
    .add_node("agent", call_agent)
    .add_edge(START, "rewrite")
    .add_edge("rewrite", "retrieve")
    .add_edge("retrieve", "agent")
    .add_edge("agent", END)
    .compile()
)

result = workflow.invoke({"question": "谁赢得了 2024 年 WNBA 总冠军？"})
print(result["answer"])
```
</details>

---

# 6. 性能比较

不同的模式具有不同的性能特征。理解这些权衡有助于你根据延迟和成本要求选择正确的模式。

**关键指标：**

* **模型调用**：LLM 调用次数。更多调用 = 更高延迟（特别是如果是顺序的）和更高的每次请求 API 成本。
* **处理的 Token 数**：所有调用中的总上下文窗口使用量。更多 token = 更高的处理成本和潜在的上下文限制。

## 6.1 单次请求

> **用户：**"买咖啡"

专门的咖啡智能体/技能可以调用 `buy_coffee` 工具。

| 模式 | 模型调用 | 最佳适配 |
|------|:--------:|:--------:|
| [**子智能体**](#子智能体详细指南) | 4 | |
| [**交接**](#交接详细指南) | 3 | ✅ |
| [**技能**](#技能详细指南) | 3 | ✅ |
| [**路由器**](#路由器) | 3 | ✅ |

### 6.1.1 子智能体（Subagents）
**4 次模型调用：**

```
用户请求 ──► 主智能体 ──► 子智能体(咖啡) ──► 返回结果 ──► 主智能体 ──► 用户响应
   │            │              │              │            │
   │          (1)            (2)            (3)          (4)
   │
   └── 结果必须通过主智能体返回，增加一次额外调用
```

### 6.1.2 交接（Handoffs）
**3 次模型调用：**

```
用户请求 ──► 主智能体 ──► 交接到咖啡智能体 ──► 直接响应
   │            │                │
   │          (1)              (2)
   │
   └── 智能体直接响应用户，无需返回主智能体
```

### 6.1.3 技能（Skills）
**3 次模型调用：**

```
用户请求 ──► 智能体 ──► 加载咖啡技能 ──► 调用工具 ──► 响应
   │            │           │            │
   │          (1)         (2)          (3)
   │
   └── 单一智能体按需加载上下文
```

### 6.1.4 路由器（Router）
**3 次模型调用：**

```
用户请求 ──► 路由器 ──► 咖啡智能体 ──► 响应
   │            │           │
   │          (1)         (2)
   │
   └── 路由器分类后直接调用专门智能体
```

**关键洞察：** 对于单个任务，交接、技能和路由器最有效（各 3 次调用）。子智能体增加一次额外调用，因为结果必须通过主智能体返回——这种开销提供了集中控制。

## 6.2 重复请求

> **第 1 轮：**"买咖啡"
> **第 2 轮：**"再买一杯咖啡"

用户在同一对话中重复相同的请求。

| 模式 | 第 2 轮调用 | 总计（两轮） | 最佳适配 |
|------|:-----------:|:------------:|:--------:|
| [**子智能体**](#子智能体详细指南) | 4 | 8 | |
| [**交接**](#交接详细指南) | 2 | 5 | ✅ |
| [**技能**](#技能详细指南) | 2 | 5 | ✅ |
| [**路由器**](#路由器) | 3 | 6 | |

### 6.2.1 子智能体（Subagents）
**再次 4 次调用 → 总共 8 次**

* 子智能体**设计上是无状态的**——每次调用都遵循相同的流程
* 主智能体维护对话上下文，但子智能体每次都从新开始
* 这提供了强大的上下文隔离，但会重复完整流程

### 6.2.2 交接（Handoffs）
**2 次调用 → 总共 5 次**

* 咖啡智能体从第 1 轮开始**仍然处于活动状态**（状态持续）
* 不需要交接——智能体直接调用 `buy_coffee` 工具（调用 1）
* 智能体响应用户（调用 2）
* **通过跳过交接节省 1 次调用**

### 6.2.3 技能（Skills）
**2 次调用 → 总共 5 次**

* 技能上下文**已经加载**到对话历史中
* 无需重新加载——智能体直接调用 `buy_coffee` 工具（调用 1）
* 智能体响应用户（调用 2）
* **通过重用已加载的技能节省 1 次调用**

### 6.2.4 路由器（Router）
**再次 3 次调用 → 总共 6 次**

* 路由器是**无状态的**——每个请求都需要 LLM 路由调用
* 第 2 轮：路由器 LLM 调用 (1) → 牛奶智能体调用 buy_coffee (2) → 牛奶智能体响应 (3)
* 可以通过在有状态智能体中包装为工具来优化

**关键洞察：** 有状态模式（交接、技能）在重复请求上节省 40-50% 的调用。子智能体保持每次请求的一致成本——这种无状态设计提供了强大的上下文隔离，但代价是重复的模型调用。

## 6.3 多领域

> **用户：**"比较 Python、JavaScript 和 Rust 在 Web 开发中的优劣"

每个语言智能体/技能包含约 2000 个 token 的文档。所有模式都可以进行并行工具调用。

| 模式 | 模型调用 | 总 Token 数 | 最佳适配 |
|------|:--------:|:-----------:|:--------:|
| [**子智能体**](#子智能体详细指南) | 5 | ~9K | ✅ |
| [**交接**](#交接详细指南) | 7+ | ~14K+ | |
| [**技能**](#技能详细指南) | 3 | ~15K | |
| [**路由器**](#路由器) | 5 | ~9K | ✅ |

### 6.3.1 子智能体（Subagents）
**5 次调用，约 9K token**

```
用户请求 ──► 主智能体 ──┬──► Python 子智能体 ──┐
                      │                      │
                      ├──► JS 子智能体 ──────┼──► 返回主智能体 ──► 响应
                      │      (并行)          │
                      └──► Rust 子智能体 ────┘
                            (并行)
```

每个子智能体在**隔离**中工作，只有其相关的上下文。总计：**9K token**。

### 6.3.2 交接（Handoffs）
**7+ 次调用，约 14K+ token**

```
用户请求 ──► 智能体A ──► 智能体B ──► 智能体C ──► ...
             (顺序)      (顺序)      (顺序)
```

交接**顺序执行**——无法并行研究所有三种语言。不断增长的对话历史增加了开销。总计：**约 14K+ token**。

### 6.3.3 技能（Skills）
**3 次调用，约 15K token**

```
用户请求 ──► 智能体 ──► 加载所有技能 ──► 响应
                         (6K token)
```

加载后，**每次后续调用都处理所有 6K token 的技能文档**。由于上下文隔离，子智能体总体处理的 token 少 67%。总计：**15K token**。

### 6.3.4 路由器（Router）
**5 次调用，约 9K token**

```
用户请求 ──► 路由器 ──┬──► Python 智能体 ──┐
                      │                     │
                      ├──► JS 智能体 ──────┼──► 合成响应
                      │      (并行)         │
                      └──► Rust 智能体 ────┘
                            (并行)
```

路由器使用 **LLM 进行路由**，然后并行调用智能体。类似于子智能体，但有显式的路由步骤。总计：**9K token**。

**关键洞察：** 对于多领域任务，具有并行执行的模式（子智能体、路由器）最有效。技能调用较少，但由于上下文累积，token 使用量高。交接在这里效率低下——它必须顺序执行，无法利用并行工具调用来同时咨询多个领域。

## 6.4 总结

以下是所有三种场景中模式的比较：

| 模式 | 单次请求 | 重复请求 | 多领域 |
|------|:--------:|:--------:|:------:|
| [**子智能体**](#子智能体详细指南) | 4 次调用 | 8 次调用 (4+4) | 5 次调用, 9K token |
| [**交接**](#交接详细指南) | 3 次调用 | 5 次调用 (3+2) | 7+ 次调用, 14K+ token |
| [**技能**](#技能详细指南) | 3 次调用 | 5 次调用 (3+2) | 3 次调用, 15K token |
| [**路由器**](#路由器) | 3 次调用 | 6 次调用 (3+3) | 5 次调用, 9K token |

**选择模式：**

| 优化目标 | [子智能体](#子智能体详细指南) | [交接](#交接详细指南) | [技能](#技能详细指南) | [路由器](#路由器) |
|----------|:-----------------------------:|:---------------------:|:---------------------:|:-----------------:|
| 单次请求 | | ✅ | ✅ | ✅ |
| 重复请求 | | ✅ | ✅ | |
| 并行执行 | ✅ | | | ✅ |
| 大上下文领域 | ✅ | | | ✅ |
| 简单、专注的任务 | | | ✅ | |

# 7. 最佳实践

## 7.1 不要过度设计

在决定使用多智能体之前，考虑：
- 单个智能体配合动态工具是否足够？
- 是否真的需要上下文隔离？
- 复杂性是否值得收益？

## 7.2 选择正确的模式

根据你的具体需求选择：
- **需要并行处理？** → 子智能体或路由器
- **需要状态持久化？** → 交接或技能
- **需要分布式开发？** → 子智能体或技能
- **需要直接用户交互？** → 交接或技能

## 7.3 优化上下文

- 确保每个智能体只看到必要的信息
- 使用上下文工程最小化 token 使用
- 考虑上下文窗口限制

## 7.4 监控和调试

- 跟踪每个智能体的调用次数
- 监控 token 使用量
- 记录智能体之间的交接

# 8. 相关资源

- [LangGraph 文档](/oss/python/langgraph/overview)
- [上下文工程指南](/oss/python/langchain/context-engineering)
- [工具使用文档](/oss/python/langchain/tools)

---

> [在 GitHub 上编辑此页面](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/multi-agent/index.mdx) 或 [提交问题](https://github.com/langchain-ai/docs/issues/new/choose)。
