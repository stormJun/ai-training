# Eino 框架总览:定位与核心概念

> 本文基于本机 eino 源码整理,源码路径:`/Users/songxijun/workspace/otherProject/eino`。
> 涉及源码结论处标注 `文件:行号`,可点击跳转。

## 一、Eino 是什么

Eino(读音 ['aino])是字节跳动 CloudWeGo 团队出品的 **Go 语言 LLM 应用开发框架**,借鉴了 LangChain、Google ADK 等项目,但按 Go 的惯例重新设计(强类型、接口组合、泛型、显式错误处理)。

它解决的核心问题是:**把 LLM、工具、检索等异构能力,组装成可运行、可流式、可中断恢复、可观测的生产级应用**。

Eino 提供四块能力(见 `README.zh_CN.md:19`):

| 能力 | 说明 |
|---|---|
| **组件(Components)** | `ChatModel`、`Tool`、`Retriever`、`ChatTemplate` 等可复用模块的抽象接口;官方实现在 eino-ext,覆盖 OpenAI / Claude / Gemini / Ark / Ollama 等 |
| **编排(Compose)** | 把组件组装成 Chain / Graph / Workflow,既能独立运行,也能包装成工具给智能体调用 |
| **智能体开发套件(ADK)** | Agent / Runner / Middleware 抽象,内置 ReAct、DeepAgent、Supervisor、Plan-Execute 等开箱即用的智能体模式 |
| **流式 / 回调 / 中断恢复** | 编排层自动处理流式拼接、装箱、合并、复制;固定切点注入回调;支持从检查点恢复 |

### 1.1 定位对比

Eino 借鉴了 LangChain(组件抽象)、Google ADK(智能体套件)等,但按 Go 惯例重新设计。与主流框架的定位差异:

| 框架 | 语言 | 编排模型 | 类型安全 | 主要对标 Eino 的部分 |
|---|---|---|---|---|
| **Eino** | Go | Chain / Graph / Workflow + Pregel | 强类型(泛型 `Chain[I,O]`、编译期校验) | -- |
| LangChain | Python | Chain / LCEL | 动态类型 | 组件抽象、Chain |
| LangGraph | Python | StateGraph(状态图) | 动态类型 | Graph + State(Pregel 思想同源) |
| Google ADK | Python | Agent + Workflow | 动态类型 | ADK 层(Agent/Middleware) |

Eino 的关键差异(Go 原生):

- **编译期类型检查** -- `NewChain[I,O]` / `NewGraph[I,O]` 用泛型固定输入输出,节点间类型不匹配在 `Compile` 时报错,而非运行时崩溃。
- **接口组合而非继承** -- 组件是 interface,实现可平替;编排层只依赖接口。
- **显式错误处理** -- 无 try/exception,错误以返回值上抛(`Generate`/`Invoke` 均返回 `error`)。
- **流式一等公民** -- `StreamReader[T]` 贯穿全栈,编排层自动衔接,而非各处手写 channel。

> 一句话:**Eino ≈ LangChain 的组件生态 + LangGraph 的图编排 + ADK 的智能体套件,但用 Go 的强类型与显式错误重新实现**。

## 二、仓库组成

Eino 是一个多仓库生态(见 `llms.txt:8`):

```
eino            ← 核心框架(本机源码):类型定义、流处理、组件抽象、编排、ADK、回调
eino-ext        ← 组件实现:OpenAI/Ark/Ollama/Redis/S3 等集成、回调处理器、评估器
eino-examples   ← 可运行示例应用与最佳实践
eino-devops     ← 可视化编排与调试(IDE 插件 / 可视化调试)
```

> 设计原则:**核心仓库只定义抽象与机制,实现下沉到 eino-ext**。这样可以保持核心精简,同时让第三方实现可替换。

## 三、核心目录结构

```
eino/
├── schema/        # 数据类型:Message / Document / Tool / StreamReader|Writer / 序列化
├── components/    # 组件抽象接口:model / tool / retriever / indexer / embedding / prompt / document / loader
├── compose/       # 编排引擎:Chain / Graph / Workflow / Branch / State / Pregel / Checkpoint / Interrupt
├── adk/           # 智能体开发套件:Agent 接口 / Runner / 内置 Agent / Middlewares / HITL
├── flow/          # 流程集成组件(较底层):react agent / multi-agent hosting / retriever / indexer flow
├── callbacks/     # 回调切面:aspect_inject / handler_builder / interface
└── internal/      # 内部工具(如 mock、safe panic 处理)
```

## 四、分层架构

Eino 是一个自底向上的三层结构,越往上越"自动",越往下越"可控":

```
┌─────────────────────────────────────────────────────────┐
│  ADK 层(adk/)        Agent / Runner / Middleware        │  ← 自主决策、自动 ReAct 循环
│                        ChatModelAgent / DeepAgent ...    │
├─────────────────────────────────────────────────────────┤
│  编排层(compose/)    Chain / Graph / Workflow            │  ← 确定性流程、精确控制
│                        Branch / Parallel / State         │
├─────────────────────────────────────────────────────────┤
│  组件层(components/)  ChatModel / Tool / Retriever ...   │  ← 可复用能力单元(接口)
├─────────────────────────────────────────────────────────┤
│  类型层(schema/)      Message / Document / StreamReader  │  ← 贯穿全栈的数据契约
└─────────────────────────────────────────────────────────┘
```

- **类型层**定义所有数据契约。最典型的是 `schema.StreamReader[T]`(见 `schema/stream.go:168`),它是贯穿组件、编排、ADK 的流式统一抽象。
- **组件层**只定义接口,实现交给 eino-ext。组件通过实现接口接入框架。
- **编排层**把组件按拓扑连成可执行图,自动处理流式转换、回调注入、状态流转。
- **ADK 层**在编排之上,封装"智能体"语义:自动工具调用循环、多智能体协同、人机交互。

> 关键设计:**编排出来的图可以包装成 Tool 给 Agent 调用**(见 `README.zh_CN.md:113`)。于是"确定性流程"和"自主决策"可以嵌套组合——这是 Eino 区别于纯 Agent 框架的要点。

### 4.1 请求如何流经各层

分层图是静态结构;下面看一次调用如何动态穿过各层。

**A. 直接用编排(Graph/Chain)**

```
runnable.Invoke(ctx, input)                          [编排层 Runnable 入口]
  └─ runner(graph_run.go) 按拓扑序/superstep 调度节点
       ├─ 节点1 调用组件(如 ChatModel.Generate)     [组件层]
       │    └─ eino-ext 实现发 HTTP 到 LLM           [实现层,非本仓库]
       │    └─ 返回 schema.Message                   [类型层]
       ├─ 节点1 输出经字段映射/流式衔接传给节点2       [编排层 stream_concat/field_mapping]
       └─ ... 直到终节点
  └─ runnable 返回 O
```

**B. 用 ADK 智能体**

```
runner.Query(ctx, input)                             [ADK 层 Runner]
  └─ Agent(内含 compose.Graph)                       [ADK -> 编排层]
       └─ Graph runnable 跑 ReAct 循环(Pregel superstep) [编排层 graph_run.go]
            ├─ chat 节点: ChatModel.Generate(带工具)   [组件层]
            ├─ 分支: 有 ToolCall?
            │    ├─ 是 -> tools 节点执行 Tool -> 回 chat [组件层 Tool]
            │    └─ 否 -> END
            └─ 最终 Message
       └─ 事件经 Runner 返回(iter.Next())            [ADK 层]
```

要点:

- **ADK 层不重复实现循环**,而是构造一个编排层 Graph(Pregel 驱动)来跑 ReAct;Agent 是 Graph 之上的薄封装。
- **组件层只产/消 `schema` 类型**,不关心编排;编排层只调度节点,不关心组件内部;各层单向依赖下层。
- **流式与阻塞共用同一套节点**--`Generate`/`Stream` 是同一组件的两个方法,编排层据调用入口(`Invoke`/`Stream`)选择衔接方式。

## 五、核心概念详解

### 5.1 组件(Components)

组件是 Eino 的能力单元。`components/types.go:66` 用一组常量定义了所有组件类别:

```go
ComponentOfPrompt          // ChatTemplate - 模板渲染
ComponentOfAgenticPrompt   // AgenticChatTemplate - 智能体模板
ComponentOfChatModel       // ChatModel - 对话模型
ComponentOfAgenticModel    // AgenticModel - 智能体模型
ComponentOfEmbedding       // Embedding - 向量化
ComponentOfIndexer         // Indexer - 入库索引
ComponentOfRetriever       // Retriever - 检索
ComponentOfLoader          // Loader - 文档加载
ComponentOfTransformer     // DocumentTransformer - 文档变换(切分等)
ComponentOfTool            // Tool - 工具
```

每个组件接口都遵循一个统一范式:**同步 + 流式**双模式。以 ChatModel 为例(`components/model/interface.go:36`):

```go
type BaseModel[M messageType] interface {
    Generate(ctx context.Context, input []M, opts ...Option) (M, error)           // 阻塞,返回完整结果
    Stream(ctx context.Context, input []M, opts ...Option) (*schema.StreamReader[M], error) // 流式,逐块返回
}
```

- 用泛型 `BaseModel[M]` 参数化消息类型,`M` 只能是 `*schema.Message` 或 `*schema.AgenticMessage`(`interface.go:27` 的 sealed constraint)。
- `BaseChatModel = BaseModel[*schema.Message]`(`interface.go:71`)是向后兼容的别名。
- 每个组件还带 `Option` 机制(`option.go`),用 functional options 传参(温度、max_tokens 等)。

组件还有两个横切接口(`components/types.go`):
- `Typer.GetType()` —— 返回组件实现名,用于 DevOps 可视化展示(如 "OpenAIChatModel")。
- `Checker.IsCallbacksEnabled()` —— 控制是否由框架自动注入回调,流式场景下组件可自行决定回调触发时机。

> **Lambda** 是一个特殊的"函数即节点"概念(见 `compose/types_lambda.go`),不算组件常量,但能把任意 Go 函数接入编排,常用于数据格式转换。

### 5.2 编排(Compose)

`compose/doc.go:17` 一句话定位:"graph and workflow primitives to build composable, interruptible execution pipelines with callback support"。三种编排原语,控制力从强到弱:

| 原语 | 文件 | 特点 |
|---|---|---|
| **Chain** | `compose/chain.go` | 线性序列,一进一出,最简单 |
| **Graph** | `compose/graph.go` / `dag.go` | DAG,支持条件分支(Branch)、并行(Parallel)、字段映射(Field Mapping) |
| **Workflow** | `compose/workflow.go` | 在 Graph 之上的结构化抽象,声明式描述节点与数据流 |

编排的几个关键机制:

- **节点(Node)**:把组件或 Lambda 包成图节点(`component_to_graph_node.go`、`graph_node.go`)。`AddChatModelNode`、`AddLambdaNode` 等是糖。
- **边(Edge)**:`AddEdge(from, to)`,特殊节点 `compose.START` / `compose.END`。
- **分支(Branch)**:`branch.go` / `chain_branch.go`,按条件选下一条边,实现 if/switch 路由。
- **字段映射(Field Mapping)**:`field_mapping.go`,把上游节点的某字段接到下游节点的某入参——解决节点间数据形状不匹配。
- **状态(State)**:`state.go`,图级共享状态,配合 Pregel 模型(`pregel.go`)做顶点为中心的迭代计算。
- **流式拼接**:`stream_concat.go` / `stream_reader.go`,编排层自动把上游的 `StreamReader` 适配成下游需要的入参形式(拼接、装箱、合并、复制)。
- **编译与运行**:`graph.Compile(ctx)` 产出 `Runnable`(`runnable.go`),提供 `Invoke` / `Stream` / `Collect` 等入口。

最小编排示例(来自 `README.zh_CN.md:98`):

```go
graph := compose.NewGraph[*Input, *Output]()
graph.AddLambdaNode("validate", validateFn)
graph.AddChatModelNode("generate", chatModel)
graph.AddLambdaNode("format", formatFn)

graph.AddEdge(compose.START, "validate")
graph.AddEdge("validate", "generate")
graph.AddEdge("generate", "format")
graph.AddEdge("format", compose.END)

runnable, _ := graph.Compile(ctx)
result, _ := runnable.Invoke(ctx, input)
```

### 5.3 流式(Streaming)

Eino 的流式是一等公民,核心是 `schema/stream.go` 里的 `StreamReader[T]` / `StreamWriter[T]`:

- `Pipe[T](cap)` 创建一对读写端(`stream.go:99`),底层是带缓冲的 channel + 取消信号通道。
- 编排层自动处理**流式范式**:拼接(concat)、装箱(boxing,多元素合并)、合并(merge,多路 fan-in)、复制(copy,一进多出 fan-out)。
- 组件只需实现业务相关的流式(`Stream` 方法),框架负责跨节点的流式衔接。

> 流式的底层设计详见 [`source_notes/stream_design.md`](../source_notes/stream_design.md),核心是"判别式联合 + 类型擦除接口 + sync.Once 惰性链表"。

### 5.4 回调(Callbacks)

`callbacks/` 提供固定切点的 AOP 能力,适用于组件、图、智能体三层。切点包括:`OnStart`、`OnEnd`、`OnError`、`OnStartWithStreamInput`、`OnEndWithStreamOutput`(见 `README.zh_CN.md:148`)。

- `aspect_inject.go` —— 切面注入机制。
- `handler_builder.go` —— 构建回调处理器链。
- 典型用途:日志、链路追踪、指标采集。

### 5.5 中断与恢复(Interrupt / Resume)

`compose/interrupt.go` + `compose/resume.go` + `compose/checkpoint.go`:任何智能体或工具都能**暂停等待人工输入**,并从检查点恢复,框架负责状态持久化与路由。这是人机交互(HITL)的基础,ADK 层有对应封装(`adk/interrupt.go`)。

### 5.6 智能体开发套件(ADK)

ADK 是最上层,把"智能体"作为一等概念。核心抽象(`adk/interface.go`):

- **Agent 接口**:统一的智能体契约。
- **Runner**(`adk/runner.go`):运行时,`runner.Query(ctx, input)` 返回事件迭代器。
- **Middleware**(`adk/middlewares/`):切面式扩展,内置文件系统、技能、摘要、计划任务、工具搜索、工具归并等中间件。
- **内置 Agent**:
  - `ChatModelAgent`(`adk/chatmodel.go`):基础对话智能体,内部自动跑 ReAct 循环。
  - `react.go`:ReAct 模式。
  - `workflow.go`:Workflow 智能体。
  - `prebuilt/`:DeepAgent 等预置复杂智能体。
  - `failover_chatmodel.go` / `retry_chatmodel.go`:容错与重试。

最简 ADK 用法(`README.zh_CN.md:33`):

```go
agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{Model: chatModel})
runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: agent})
iter := runner.Query(ctx, "Hello, who are you?")
for {
    event, ok := iter.Next()
    if !ok { break }
    fmt.Println(event.Message.Content)
}
```

## 六、Graph 还是 Agent?怎么选

Eino 官方专门讨论了这个选择(`llms.txt:19` 的 "Graph or Agent - when to use which")。原则:

| 场景 | 选择 | 典型实例 |
|---|---|---|
| 流程确定、步骤已知、要精确控制 | **Graph / Chain** | RAG 固定流水线(检索->重排->生成);表单校验->生成->格式化 |
| 由模型自主决定下一步、需要工具调用循环 | **Agent(ADK / ReAct)** | 开放问答(查天气/查库/算数);数据分析助手自主调工具 |
| 确定流程 + 少量自主决策 | **Graph 包装成 Tool 给 Agent** | Agent 把"数据处理流水线"当工具调;确定性 RAG 作为 Agent 子能力 |
| 有环循环 + 跨步状态 | **Agent**(`react.NewAgent`) | 多轮工具调用直到收敛给出最终答案 |

> 判据速记:**步骤谁决定?** 人定 -> Graph;模型定 -> Agent;混合 -> Graph 当 Tool 给 Agent。

> Agent 侧的自动工具调用循环(ReAct)详见 [ReAct agent 手册](https://www.cloudwego.io/zh/docs/eino/core_modules/flow_integration_components/react_agent_manual/),本机文档见 [`../03_graph/react_agent.md`](../03_graph/react_agent.md)。

## 七、常见误解

- **"Eino 是 LangChain 的 Go 移植"** -- 否。借鉴其组件思想,但用 Go 强类型/泛型/显式错误重写;编排模型更接近 LangGraph(图 + State)。
- **"用 Agent 就得用 ADK"** -- 否。`flow/agent/react.NewAgent` 是编排层轻量 ReAct agent,无需 ADK;ADK 的 `ChatModelAgent` 是更上层封装(中间件/HITL/回调)。
- **"Graph 等于有环"** -- 否。Graph 默认 DAG;有环需 State + Pregel 驱动(如 ReAct),裸环会触发 `maxSteps` 兜底。
- **"流式要自己拼 chunk"** -- 否。编排层自动衔接(拼接/装箱/合并/复制);组件只需实现 `Stream`,调用方只需 `Recv` 循环 + `Close`。
- **"组件实现都在 eino 仓库"** -- 否。eino 只定义接口,实现在 eino-ext(OpenAI/Ark/Ollama 等)。
- **"换模型要改业务代码"** -- 否。业务代码依赖 `model.BaseChatModel` 接口,换 ark/openai/ollama 只改构造处。

## 八、学习路径建议

推荐顺序(对应本目录已有文档):

1. **本文(总览)** -- 建立全局视图
2. [`02_components/`](../02_components/) -- 组件接口范式(ChatModel + Tool),配 [demo](../02_components/demo/)
3. [`source_notes/stream_design.md`](../source_notes/stream_design.md) -- `StreamReader/Writer` 底层设计(贯穿全栈)
4. [`03_graph/`](../03_graph/) -- 编排:Chain(线性)-> Graph(DAG)-> Workflow(声明式)-> ReAct Agent(有环)-> State/Pregel -> Interrupt/Resume
5. (后续)ADK 层 -- `ChatModelAgent`、中间件、HITL
6. (后续)回调 / 记忆 / 完整示例

> 端到端可运行示例见 [`02_components/demo/`](../02_components/demo/):ChatModel 基本、Tool 调用(手写 vs Agent 自动)、Workflow 声明式。

## 九、参考

- 官方用户手册:https://www.cloudwego.io/zh/docs/eino/
- [ReAct agent 手册](https://www.cloudwego.io/zh/docs/eino/core_modules/flow_integration_components/react_agent_manual/) -- 工具调用智能体的自动 ReAct 循环
- 核心仓库:https://github.com/cloudwego/eino
- 组件实现:https://github.com/cloudwego/eino-ext
- 示例:https://github.com/cloudwego/eino-examples
- 本机源码:`/Users/songxijun/workspace/otherProject/eino`
