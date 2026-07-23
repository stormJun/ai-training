# Customize Deep Agents 梳理

本文基于 LangChain Deep Agents 的 Customize Deep Agents 文档整理，目标是理解 `create_deep_agent` 到底在组装什么，以及各参数在工程系统中的位置。

## 1. Deep Agents 是什么

Deep Agents 不是 Web 框架，也不是业务系统本身。它是一个 Agent 运行底座，基于 LangChain / LangGraph，把常见 Agent 能力预先组装好：

- 任务规划：todo list。
- 文件系统：读文件、写文件、搜索文件。
- 工具调用：业务函数、MCP 工具、外部 API。
- Skill：按需加载任务说明书。
- Memory：启动时加载 `AGENTS.md`。
- Subagent：把任务委派给子 Agent。
- Context management：长上下文压缩、文件化存储。
- Human-in-the-loop：敏感工具调用前暂停等待审批。
- Backend：决定虚拟文件系统、Skill、Memory、临时文件存在哪里。

典型创建方式：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    system_prompt="You are a helpful assistant.",
    tools=[search, fetch_url],
    memory=["./AGENTS.md"],
    skills=["./skills/"],
)
```

从工程角度看，`create_deep_agent` 做的是：

```text
模型 + 系统提示词 + 工具 + Skill + Memory + Backend + Middleware + Subagent
  ↓
一个可运行的 LangGraph Agent
```

## 2. 核心参数

| 参数 | 作用 | 工程理解 |
| --- | --- | --- |
| `model` | 选择模型 | 可以传 `provider:model` 字符串，也可以传初始化好的 chat model |
| `system_prompt` | 自定义行为说明 | 业务角色、回答风格、任务边界 |
| `tools` | Agent 可调用工具 | 真正执行 API、数据库、搜索、业务动作 |
| `memory` | 启动时加载的 `AGENTS.md` | 长期背景、项目约定、身份设定 |
| `skills` | Skill 目录 | 按需读取的任务流程说明 |
| `backend` | 文件/状态后端 | Skill、Memory、临时文件、执行产物放哪里 |
| `permissions` | 文件访问控制 | 控制文件读写路径，支持 allow / deny / interrupt |
| `subagents` | 子 Agent | 把复杂任务委派给专业 Agent |
| `middleware` | 扩展中间件 | 日志、重试、PII 检测、自定义工具拦截等 |
| `interrupt_on` | 人工审批 | 高风险工具调用前暂停 |
| `response_format` | 结构化输出 | 用 Pydantic schema 约束最终输出 |
| `state_schema` | 自定义图状态 | 给 Agent 图增加线程级状态字段 |
| `checkpointer` | checkpoint | 多轮对话、HITL、恢复执行需要 |
| `store` | LangGraph Store | 给 `StoreBackend` 等持久化后端使用 |

## 3. Model：模型只是底座

`model` 可以写成：

```python
agent = create_deep_agent(model="openai:gpt-5.5")
```

也可以传模型实例：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(model="openai:gpt-5.5")
agent = create_deep_agent(model=model)
```

重要点：

- Deep Agents 要求模型支持 tool calling。
- 模型只是推理核心，可靠性来自外层工程：tools、schema、backend、permissions、eval、trace。
- 不同模型可能有 profile，Deep Agents 会追加模型相关的提示词后缀或调整工具描述。

## 4. Tools：真正干活的函数

Tools 是 Agent 可以调用的执行能力。比如：

```python
def internet_search(query: str, max_results: int = 5):
    """Run a web search."""
    return tavily_client.search(query, max_results=max_results)

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[internet_search],
)
```

工程上要把 tools 理解成：

```text
tool = 真实执行入口
```

比如金融场景：

- `resolve_fund`：基金名称转基金代码。
- `query_fund_news`：查基金相关新闻。
- `query_user_position`：查用户持仓。
- `compliance_check`：合规检查。

Tool 要做的事情：

- 参数校验。
- 权限校验。
- 调 API / 数据库。
- 处理超时、重试、限流。
- 记录 trace 和审计日志。

Tool 不应该把可靠性完全交给模型。

## 5. MCP Tools：把远程工具接进来

Deep Agents 支持 MCP 工具。典型方式：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

async with MultiServerMCPClient(
    {
        "my_server": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
        }
    }
) as client:
    tools = await client.get_tools()
    agent = create_deep_agent(model="openai:gpt-5.5", tools=tools)
```

工程含义：

```text
Deep Agents 不要求所有工具都在本进程里
MCP Server 可以提供数据库、API、文件系统、内部系统能力
```

生产上要注意：

- MCP Server 鉴权。
- 工具白名单。
- 租户隔离。
- 工具调用审计。
- 网络超时和重试。

## 6. System Prompt：业务指令叠加在内置提示词前面

Deep Agents 自带内置 system prompt，告诉模型如何使用：

- todo 工具。
- 文件工具。
- 子 Agent。
- 上下文管理。

你传入的 `system_prompt` 不会完全替换这套底座，而是和 SDK 内置提示词组装起来。

组装顺序是：

```text
USER -> BASE 或 CUSTOM -> SUFFIX
```

含义：

- `USER`：你传入的 `system_prompt`。
- `BASE`：Deep Agents 默认提示词。
- `CUSTOM`：profile 里的自定义 base prompt，可替换 BASE。
- `SUFFIX`：profile 追加的模型适配提示。

所以一般调用：

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    system_prompt="You are a customer-support agent for ACME Corp.",
)
```

实际效果是：

```text
你的业务 prompt
  +
Deep Agents 默认 Agent 行为说明
  +
Claude 相关 profile 后缀
```

## 7. Middleware：Deep Agents 的默认运行栈

Deep Agents 不是只包了一层模型调用，而是安装了一串 middleware。

主 Agent 默认顺序大致是：

```text
1. TodoListMiddleware
2. SkillsMiddleware        只有传 skills 时启用
3. FilesystemMiddleware
4. SubAgentMiddleware
5. SummarizationMiddleware
6. PatchToolCallsMiddleware
7. AsyncSubAgentMiddleware 只有配置异步子 Agent 时启用
8. 用户自定义 middleware
9. profile extras
10. excluded-tool filtering
11. AnthropicPromptCachingMiddleware
12. MemoryMiddleware       只有传 memory 时启用
13. HumanInTheLoopMiddleware 只有传 interrupt_on 时启用
```

这个顺序很重要。

`SkillsMiddleware` 在主 Agent 中排在文件系统 middleware 前面，因为它要先把 Skill metadata 注入 system prompt，然后模型才能通过 `read_file` 去读完整 `SKILL.md`。

`MemoryMiddleware` 比较靠后，是为了减少对 Anthropic prompt cache 前缀的破坏。

`HumanInTheLoopMiddleware` 在尾部，用来拦截需要审批的工具调用。

## 8. Custom Middleware：不要在 middleware 对象上保存可变状态

文档特别强调：不要这样写：

```python
class CustomMiddlewareBad(AgentMiddleware):
    def __init__(self):
        self.x = 1

    def before_agent(self, state, runtime):
        self.x += 1
```

因为多个线程、多个 subagent、多个工具调用可能并发运行，修改 `self.x` 会产生竞态。

应该用 graph state：

```python
class CustomMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        return {"x": state.get("x", 0) + 1}
```

工程规则：

```text
middleware 实例应尽量无状态
请求级/线程级状态放 graph state
跨线程持久状态放 store/backend/database
```

## 9. Interpreters：轻量代码解释器

Deep Agents 可以通过 middleware 加一个 `eval` 工具，例如 QuickJS：

```python
from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware

agent = create_deep_agent(
    model="openai:gpt-5.5",
    middleware=[CodeInterpreterMiddleware()],
)
```

适合：

- 批量处理结构化数据。
- 编排多个工具调用。
- 用代码处理错误恢复。
- 不想给完整 shell 权限，但需要一点可编程能力。

注意：这和 shell sandbox 不是一回事。QuickJS 是 JS 解释器；sandbox backend 是隔离环境里的文件系统和 shell。

## 10. Subagents：把复杂任务拆给专家 Agent

同步子 Agent 示例：

```python
research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "openai:gpt-5.5",
}

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    subagents=[research_subagent],
)
```

工程意义：

```text
主 Agent：负责理解任务、调度、汇总
子 Agent：负责某一类专业任务
```

适合：

- 深度研究。
- 代码审查。
- 数据分析。
- 合规检查。
- 跨领域任务拆分。

子 Agent 和主 Agent 的上下文可以隔离，避免所有细节都塞进主 Agent 上下文。

## 11. Backends：Deep Agents 的虚拟文件系统

Deep Agents 的文件工具、Skill、Memory、临时产物都要通过 backend 读写。

### 11.1 StateBackend

默认 backend。

```python
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=StateBackend(),
)
```

特点：

- 文件存在 LangGraph state 中。
- 线程内持久。
- 不跨 thread 共享。
- 适合会话级临时文件。
- 可以通过 `invoke({"files": ...})` 预置 Skill 或 Memory 文件。

### 11.2 FilesystemBackend

读写本机文件系统。

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
)
```

风险：

- Agent 可以读写本机文件。
- 可能读到密钥、配置、源码。
- 如果再配合网络工具，有数据外泄风险。

适合：

- 本地 CLI。
- 受控开发环境。
- CI 中经过限制的工作区。

不建议：

- 普通 Web API 服务直接使用未隔离的本地文件系统。

### 11.3 LocalShellBackend

比 `FilesystemBackend` 更危险，因为它还支持 shell `execute`。

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=LocalShellBackend(root_dir=".", virtual_mode=True),
)
```

它适合本地开发或严格受控环境，不适合裸放到生产服务。

### 11.4 StoreBackend

持久化、跨 thread 的存储。

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=StoreBackend(
        namespace=lambda rt: (rt.server_info.user.identity,),
    ),
    store=InMemoryStore(),
)
```

工程价值：

- 跨会话保存文件。
- 适合存 Skill、Memory、长期资料。
- 可以通过 namespace 做用户/租户隔离。

生产中重点是 namespace：

```text
namespace = tenant_id / user_id / assistant_id
```

否则多个用户可能看到同一份文件或记忆。

### 11.5 CompositeBackend

按路径把不同文件交给不同 backend。

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(namespace=lambda _rt: ("memories",)),
    },
)
```

工程上很有用：

```text
/tmp/**        -> StateBackend，会话临时文件
/skills/**     -> StoreBackend，共享 Skill
/memories/**   -> StoreBackend，长期记忆
/workspace/**  -> SandboxBackend，隔离执行环境
```

## 12. Sandboxes：隔离执行环境

Sandbox 是特殊 backend，提供：

- 自己的文件系统。
- shell `execute` 工具。
- 隔离运行环境。

适合：

- 写代码。
- 安装依赖。
- 跑测试。
- 数据处理。
- 不想改动本机环境的任务。

文档列了多种 provider：

- LangSmith Sandbox。
- Daytona。
- E2B。
- Modal。
- Runloop。
- Vercel Sandbox。

工程建议：

```text
Agent 服务本身不要裸跑代码
把代码执行交给 sandbox backend
限制 CPU / 内存 / 时间 / 网络 / 文件路径
记录执行日志和产物
```

## 13. Human-in-the-loop：敏感动作前暂停

示例：

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[remove_file, fetch_file, notify_email],
    interrupt_on={
        "remove_file": True,
        "fetch_file": False,
        "notify_email": {"allowed_decisions": ["approve", "reject"]},
    },
    checkpointer=checkpointer,
)
```

注意：

- HITL 需要 `checkpointer`。
- 因为执行会暂停，后续要能恢复。

金融场景中，以下动作应该考虑 HITL：

- 交易提交。
- 发送外部消息。
- 修改客户资料。
- 调用高风险工具。
- 输出投资建议。
- 删除或覆盖重要文件。

## 14. Skills：按需加载的任务说明书

文档对 Skill 的定义很关键：

```text
tools 偏底层执行能力
skills 偏任务流程、专业知识、模板、参考材料
```

Skill 文件不是启动时全部塞进上下文，而是：

```text
启动时只加载 name/description/path
模型判断相关后再 read_file 读取完整 SKILL.md
```

这叫 progressive disclosure，作用是减少 token 和上下文负担。

### 14.1 StateBackend 中使用 Skill

StateBackend 下，需要把 Skill 文件通过 `files` 预置进去：

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
backend = StateBackend()

skills_files = {
    "/skills/langgraph-docs/SKILL.md": create_file_data(skill_content),
}

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=backend,
    skills=["/skills/"],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "What is langgraph?"}],
        "files": skills_files,
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

适合：

- 临时演示。
- 单次任务。
- 测试。

不适合：

- 多实例共享 Skill。
- 生产级 Skill 版本管理。

### 14.2 StoreBackend 中使用 Skill

StoreBackend 下，先把 Skill 放进 store：

```python
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
backend = StoreBackend(namespace=lambda _rt: ("filesystem",))

store.put(
    namespace=("filesystem",),
    key="/skills/langgraph-docs/SKILL.md",
    value=create_file_data(skill_content),
)

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=backend,
    store=store,
    skills=["/skills/"],
)
```

适合：

- 多轮会话。
- 多实例服务。
- 共享 Skill。
- 用户/租户隔离。

### 14.3 FilesystemBackend 中使用 Skill

本地磁盘方式：

```python
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

root_dir = "/Users/user/project"
backend = FilesystemBackend(root_dir=root_dir)

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=backend,
    skills=[str(Path(root_dir) / "skills")],
)
```

适合本地开发，不建议直接用于普通 Web 服务生产环境。

## 15. Memory：启动时加载 AGENTS.md

Memory 和 Skill 不一样。

```text
Memory：启动时加载，用于提供长期背景和约定
Skill：按需加载，用于某类任务的操作流程和参考材料
```

示例：

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    memory=["/AGENTS.md"],
)
```

如果使用 `StateBackend`，也需要通过 `files` 注入：

```python
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Please tell me what's in your memory files."}],
        "files": {"/AGENTS.md": create_file_data(agents_md)},
    },
    config={"configurable": {"thread_id": "123456"}},
)
```

区别总结：

| 项 | Memory | Skill |
| --- | --- | --- |
| 文件 | `AGENTS.md` | `SKILL.md` |
| 加载时机 | 启动时加载 | 相关时按需读取 |
| 作用 | 背景、身份、项目约定 | 任务流程、专业步骤、模板 |
| token 成本 | 每次进入上下文 | 用到时才进入上下文 |

## 16. Profiles：按模型复用配置

Profile 是一组模型相关配置。比如当使用某个 OpenAI 模型时，自动追加提示词：

```python
from deepagents import HarnessProfile, register_harness_profile

register_harness_profile(
    "openai:gpt-5.5",
    HarnessProfile(system_prompt_suffix="Respond in under 100 words."),
)
```

适合：

- 针对某个模型调优提示词。
- 改写工具描述。
- 排除某些工具。
- 给某个 provider 加特定 middleware。

不要把业务规则全塞到 profile。业务规则更适合 `system_prompt`、Skill 或工具校验。

## 17. Structured Output：结构化返回

Deep Agents 支持 `response_format`：

```python
from pydantic import BaseModel, Field

class WeatherReport(BaseModel):
    location: str = Field(description="The location")
    temperature: float
    condition: str

agent = create_deep_agent(
    model=model,
    response_format=WeatherReport,
    tools=[internet_search],
)
```

结果会出现在：

```python
result["structured_response"]
```

适合：

- API 返回。
- 报告结构化。
- 金融指标表。
- 任务执行计划。
- 工具调用后汇总结果。

注意：结构化输出约束最终回答，不等于保证事实正确。事实仍然要来自工具和数据库。

## 18. 和“四车间”架构的对应关系

如果把 Deep Agents 放到金融可信智能体的“四车间”里看：

| 四车间 | Deep Agents 对应能力 | 说明 |
| --- | --- | --- |
| 意图车间 | 外部 intent router / 自定义 middleware | Deep Agents 不内置金融意图矩阵，需要自己做 |
| 策划车间 | Skill + system prompt + tool schema | 根据任务选择 Skill，形成工具调用计划 |
| 执行车间 | tools / MCP tools / backend / sandbox | 真正调用 API、数据库、沙箱、内部系统 |
| 表达车间 | 主 Agent 输出 / structured output | 汇总工具结果，生成自然语言或结构化回答 |

所以 Deep Agents 可以作为 Agent runtime，但不是完整金融业务系统。

## 19. 生产落地建议

### 19.1 推荐架构

```text
客户端
  ↓
FastAPI / 网关
  ↓
业务鉴权、租户识别、限流
  ↓
Deep Agents runtime
  ↓
tools / MCP / backend / sandbox
  ↓
数据库、搜索、内部系统、对象存储
```

### 19.2 Skill 存储

本地开发：

```text
FilesystemBackend + ./skills/
```

生产建议：

```text
StoreBackend / 配置中心 / 数据库 / Git 发布产物
```

关键点：

- Skill 版本化。
- 发布前评测。
- 灰度切流。
- 支持回滚。
- 请求开始时固定 Skill 版本。

### 19.3 并发隔离

每个请求应有：

```text
tenant_id
user_id
thread_id
request_id
skill_version
trace_id
permissions
```

不要在 middleware 实例或全局变量上保存请求状态。

### 19.4 高风险操作

高风险操作要靠：

- tool 层权限校验。
- `interrupt_on` 人工审批。
- 后端幂等 key。
- 审计日志。
- 合规规则。

不要只靠 Skill 里的自然语言规则。

## 20. 一句话总结

`create_deep_agent` 是一个已经装好常见 Agent 工程能力的 harness。它把模型、工具、Skill、Memory、Backend、Subagent、Middleware、HITL 组装成可运行的 Agent。生产系统里，Deep Agents 负责 Agent 编排；业务可靠性仍然要靠后端 tools、权限、状态存储、沙箱、评测、观测和发布流程来保证。
