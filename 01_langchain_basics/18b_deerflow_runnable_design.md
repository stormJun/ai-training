# DeerFlow 中的 Runnable 设计落地

这篇文档是对 DeerFlow 中 `Runnable` 使用方式的工程化补充。

如果说：

- [18_chain_and_runnable_guide.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/18_chain_and_runnable_guide.md)
  - 重点解释 `Runnable` 是什么、为什么 `prompt | model | parser` 能成立
- [18a_runnable_config_guide.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/18a_runnable_config_guide.md)
  - 重点解释 `RunnableConfig` 怎么用、怎么传播

那么这篇文档回答的是第三个问题：

> 在一个真实 agent 系统里，DeerFlow 到底是怎么使用 LangChain / LangGraph 的 Runnable 体系的？

可以先用一句话概括：

> 在 DeerFlow 里，Runnable 更像“运行时协议 + 配置总线 + graph 执行入口”，而不是“主要拿来写 LCEL 表达式”的语法工具。

## 讨论范围

这篇文档聚焦 DeerFlow 里和 `Runnable` 直接相关的几类代码：

- `backend/app/gateway/services.py`
- `backend/packages/harness/deerflow/client.py`
- `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `backend/packages/harness/deerflow/runtime/runs/worker.py`
- `backend/packages/harness/deerflow/agents/middlewares/title_middleware.py`
- `backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py`
- `backend/packages/harness/deerflow/tools/builtins/present_file_tool.py`
- `backend/packages/harness/deerflow/tools/builtins/invoke_acp_agent_tool.py`
- `backend/packages/harness/deerflow/models/openai_codex_provider.py`

这里不重点讨论：

- LCEL 的完整语法
- PromptTemplate / OutputParser 细节
- 模型 provider 的底层 HTTP 实现

## 先说结论

DeerFlow 确实使用了 LangChain / LangGraph 的 `Runnable` 体系，但重点不是：

```python
prompt | model | parser
```

而是这三件事：

1. 用 `RunnableConfig` 传递 thread 和运行模式
2. 用 `agent.astream(..., config=...)` 驱动 agent graph
3. 让 middleware、tool、额外模型调用共享同一条运行时上下文

所以理解 DeerFlow 时，最重要的不是去找“LCEL 链条在哪”，而是去看：

- config 从哪里来
- graph 从哪里执行
- 中间层从哪里读当前运行时信息

## 先建立基础概念

### 1. Runnable 在 DeerFlow 里是什么意思

在 LangChain 里，`Runnable` 是统一执行抽象：

- 可以 `invoke(...)`
- 可以 `ainvoke(...)`
- 可以 `stream(...)`
- 可以 `astream(...)`
- 可以接收 `config`

在 DeerFlow 里，这个抽象被用在：

- agent graph
- 模型调用
- 中间件派生调用
- tool 运行时上下文传播

所以它更像一套统一执行协议，而不是单纯的链式语法。

### 2. RunnableConfig 在 DeerFlow 里是什么意思

`RunnableConfig` 在 DeerFlow 里承载的是“本次运行的 thread / mode / tracing 参数包”。

最常见的内容包括：

- `thread_id`
- `model_name`
- `thinking_enabled`
- `is_plan_mode`
- `subagent_enabled`
- `agent_name`
- `metadata`
- `callbacks`

也可以把它理解成：

```text
RunnableConfig = 这次运行附带的上下文与控制参数
```

### 3. `get_config()` 在 DeerFlow 里为什么重要

`get_config()` 的价值不在于“能拿到某个配置字段”，而在于：

- middleware 不需要每层手传 `thread_id`
- tool 可以在当前运行链里反查 thread 语境
- 额外模型调用可以继承父级运行的 tags / metadata / callbacks

所以 `get_config()` 是 DeerFlow 里读取运行时上下文的关键入口之一。

### 4. `with_config()` 在 DeerFlow 里主要干什么

它最典型的用途不是改业务逻辑，而是派生一个“带额外运行时标签的新 runnable”。

比如 summarization 的模型调用会额外打上：

- `middleware:summarize`

这样 tracing 才能知道这次模型调用属于 summarization middleware，而不是 lead agent 的主回答。

### 5. `RunnableBinding` 在 DeerFlow 里主要干什么

它最典型的用途是：

- 保留原模型 runnable
- 预绑定工具 schema
- 返回一个“已经绑好 tools 的新 runnable”

这在自定义 provider 的 `bind_tools()` 逻辑里尤其明显。

## DeerFlow 为什么会用 Runnable

DeerFlow 不是一个“单轮 prompt -> model -> parser”脚本，而是一套 agent runtime。

它需要同时处理：

- 多轮 thread
- 运行模式切换
- middleware 链
- tools
- subagent
- tracing
- stream 输出

如果没有统一执行协议，很多信息都会变成：

- 到处手动传参
- 中间层上下文不统一
- tracing 难以贯通
- 工具和 middleware 拿不到 thread 级信息

`Runnable` 在 DeerFlow 里解决的就是这个问题。

## DeerFlow 的高层心智模型

可以先用下面这张图理解：

```text
HTTP request / local client call
        |
        v
build RunnableConfig
  - thread_id
  - model_name
  - thinking_enabled
  - plan mode
  - subagent mode
  - metadata / callbacks
        |
        v
make_lead_agent(config)
  -> 根据 config 装配 model / tools / middleware / prompt
        |
        v
create_agent(...)
        |
        v
agent.astream(input, config=RunnableConfig)
        |
        v
middleware / tools / model
  -> 通过 runtime / get_config() 读取当前运行时信息
        |
        v
stream result back to client / gateway
```

这个模型说明：

- DeerFlow 不是先写一条 LCEL 链，再执行
- 而是先构造一份运行时配置，再用它装配并驱动整个 agent graph

## 一条真实请求是怎么流动的

在 DeerFlow 里，一次典型请求大致这样流动：

1. 入口先构造 `RunnableConfig`
2. `make_lead_agent(config)` 根据这份 config 决定模型、模式、工具、中间件和 prompt section
3. `create_agent(...)` 产出真正可运行的 agent graph
4. 后续通过 `agent.astream(..., config=runnable_config)` 执行
5. middleware、tool、额外模型调用都可以在运行时读到这份 config

可以进一步记成：

```text
入口组装 config
-> agent 工厂消费 config
-> graph 执行带着 config 跑
-> 中间层共享 config
```

## DeerFlow 里 Runnable 的 7 种真实用法

### 1. 用 RunnableConfig 传 thread 和运行模式

这是最常见的用法。

无论是 Gateway 路径，还是本地 `DeerFlowClient` 路径，都会先构造 `RunnableConfig`，把这些值放进去：

- `thread_id`
- `model_name`
- `thinking_enabled`
- `is_plan_mode`
- `subagent_enabled`
- `agent_name`

这意味着 DeerFlow 不是靠“不同工厂函数”服务不同模式，而是靠“一套 agent 装配逻辑 + 一份运行时 config”去驱动不同行为。

### 2. 用 RunnableConfig 作为 lead agent 工厂输入

`make_lead_agent(config)` 不是只拿 config 做 tracing，它会真正读取里面的运行参数，决定：

- 当前模型名
- 是否开启 thinking
- 是否 plan mode
- 是否 subagent mode
- 当前 agent_name
- 当前 skills
- 需要挂哪些 middlewares
- prompt 要拼哪些说明块

所以在 DeerFlow 里，`RunnableConfig` 不是“执行附加参数”，而是“agent 装配阶段的输入”。

### 3. 用 `agent.astream(..., config=...)` 作为主执行入口

DeerFlow 的主执行路径不是手写 while 循环调模型，而是直接跑 graph 的：

- `astream(...)`

也就是说，真正跑起来的是 Runnable / LangGraph graph 本身。

这个点很重要，因为它决定了：

- stream 是主路径，不是附加能力
- config 的传播天然发生在 graph 执行链上

### 4. middleware 里通过 `get_config()` 读取运行时配置

这是 DeerFlow 最值得注意的一点。

像 `TitleMiddleware`、`ThreadDataMiddleware` 这类中间件，并不是通过函数参数显式拿到所有上下文，而是会：

- 先看 `runtime.context`
- 或使用 `get_config()`

去反查当前 runnable 执行链中的配置。

这让中间件不需要和上游强耦合，但仍然能知道：

- 当前 thread 是谁
- 当前运行模式是什么
- 当前 tracing 标签是什么

### 5. tool 里通过 runtime / config 拿 thread 信息

工具层也沿用同一思路。

例如文件呈现工具、ACP 工具这类场景里，tool 会优先从：

- `runtime.context`
- `runtime.config`
- `get_config()`

中恢复当前 thread 语境，而不是要求用户把 `thread_id` 显式作为业务参数传进来。

这让工具天然处在“当前运行上下文”里工作。

### 6. 用 `with_config()` 给子调用打 tracing 标签

DeerFlow 中像标题生成、summarization 这种“不是主回答，但仍要调用模型”的场景，会通过 `with_config()` 派生一个带额外 tag 的 runnable。

这个动作的价值主要是：

- tracing 能区分主回答和 middleware 子调用
- run journal 不会把它们混在一起

所以在 DeerFlow 里，`with_config()` 更偏 observability 和上下文派生，而不是业务功能切换。

### 7. 用 `RunnableBinding` 绑定工具后的模型 runnable

自定义 provider 在 `bind_tools()` 里会把：

- 原始 model runnable
- 工具 schema 参数

组合成一个新的 `RunnableBinding`。

这一步不是重写模型，而是给模型预绑定额外 kwargs，让后续调用都自动带着这份工具配置。

## DeerFlow 没把 Runnable 主要用在哪

为了避免带着错误预期读代码，这里也要反过来说一下：DeerFlow **没有** 把 Runnable 主要用在这些地方：

- 没把整个系统主要写成 `prompt | model | parser`
- 没大量依赖 `RunnableSequence`
- 没把 `RunnableParallel` 作为主组织方式
- 没用大规模 LCEL 表达式来搭系统

也就是说，如果你学 LangChain 时对 Runnable 的第一印象是“链式表达式语法”，那读 DeerFlow 时会觉得不对劲。

在 DeerFlow 中，更准确的理解应该是：

```text
Runnable = 统一运行协议
RunnableConfig = 运行时上下文总线
astream = graph 执行入口
get_config = 中间层取上下文的方式
with_config / RunnableBinding = 子调用派生机制
```

## 一个最小例子：`thread_id` 怎么流进系统

这是理解 DeerFlow Runnable 用法最直观的例子：

```text
request / client call
-> build RunnableConfig(configurable.thread_id=...)
-> make_lead_agent(config)
-> agent.astream(..., config=config)
-> middleware / tool / model side calls get_config()
-> 读到当前 thread_id
```

它直接带来的效果是：

- middleware 能找到当前 thread 的目录或状态
- tool 能知道当前文件属于哪个 thread
- 子 agent / ACP 工具能沿着同一线程语境工作
- 额外模型调用仍然挂在同一运行链上

## 如果你要改代码，先看哪里

### 1. 改“运行参数从哪里来”

优先看：

- Gateway 的 config 构造入口
- `DeerFlowClient` 的 config 构造入口

典型场景：

- 新增 thread / request 级开关
- 把某个运行参数从上游透传进 agent

### 2. 改“agent 怎么读这些参数”

优先看：

- `make_lead_agent(config)`
- `_get_runtime_config(config)` 这类合并逻辑

典型场景：

- 新增 runtime config 字段
- 让某个 middleware / prompt section 根据 config 变化

### 3. 改“middleware / tool 怎么拿上下文”

优先看：

- `get_config()`
- `runtime.context`
- `runtime.config`

典型场景：

- 工具需要 thread_id / agent_name / run metadata
- 中间件需要恢复当前线程语境

### 4. 改“模型绑定和子调用配置”

优先看：

- `with_config()` 的派生调用
- provider 里的 `RunnableBinding`

典型场景：

- 给某类子调用打 tracing 标签
- 调整 provider 的工具绑定方式

## 常见坑

### 1. 只改 config 入口，忘了下游读取逻辑

把字段写进 `RunnableConfig` 不等于所有下游都会自动看到。你还要确认：

- 工厂层有没有读取
- middleware / tool 有没有按正确路径取值

### 2. 把 thread 级信息改成普通函数参数

短期能跑，长期会让：

- Gateway 路径
- 本地 client 路径
- tool 路径

三条执行链开始分叉，最后越来越难维护。

### 3. 忘了额外模型调用也要继承 config

标题生成、summarization 这类子调用也需要：

- tags
- metadata
- callbacks

否则 tracing 和 usage 统计很容易错位。

### 4. 把 Runnable 等同于 LCEL

这是最常见的理解偏差。

在 DeerFlow 里，Runnable 的价值主要是：

- 统一执行协议
- 传播运行时上下文
- 驱动 graph

而不是主要用来写 LCEL 表达式。

## 最小验证建议

如果你改了和 Runnable 相关的逻辑，至少验证下面几件事：

1. 入口配置能不能真正进到 agent
2. middleware / tool 能不能在运行时读到它
3. `astream(...)` 主路径有没有被破坏
4. tracing / tags / metadata 是否仍然正确

尤其在 DeerFlow 里，stream 路径才是主路径，不能只看同步调用。

## 一句话总结

DeerFlow 里确实用了 LangChain 的 Runnable，但它的重点不是“链式表达式”，而是“统一运行时接口”。

更准确地说，DeerFlow 把 Runnable 用在了：

- `RunnableConfig` 作为运行参数包
- `agent.astream()` 作为 graph 执行入口
- `get_config()` 作为运行时上下文读取方式
- `with_config()` 作为子调用配置派生方式
- `RunnableBinding` 作为模型绑定工具 schema 的方式

理解了这条主线，再去看 DeerFlow 的 middleware、tool、runtime、provider 代码，就会清楚得多。
