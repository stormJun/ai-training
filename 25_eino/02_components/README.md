# 组件层(Components)总览

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/`
> 本文阐述 Eino 组件抽象的设计原则、分类体系与横切机制,为后续逐组件文档建立统一语境。

## 一、定位

组件层位于 Eino 分层架构的第二层,承上(类型层 `schema/`)启下(编排层 `compose/`、ADK 层 `adk/`)。其职责是**定义可复用能力单元的抽象接口**,而非提供实现:

```
类型层(schema/)     Message / Document / StreamReader / ToolInfo
        ▲
组件层(components/)  ChatModel / Tool / Retriever / Embedding …  ← 本文
        ▲
编排层(compose/)     Chain / Graph / Workflow(消费组件接口)
        ▲
ADK 层(adk/)         Agent / Runner / Middleware
```

核心设计决策:**核心仓库仅声明接口,具体实现下沉至 [eino-ext](https://github.com/cloudwego/eino-ext)**。由此实现关注点分离:核心保持精简与稳定,第三方实现可平替。

## 二、设计原则

### 2.1 接口与实现分离

每个组件在 `components/<name>/interface.go` 中以 Go interface 定义契约,实现(OpenAI、Ark、Ollama 等)分布于 `eino-ext/components/<name>/`。框架所有上层逻辑(编排、回调注入、流式衔接)仅依赖接口,对具体实现透明。

### 2.2 同步 / 流式双模式范式

凡涉及生成或检索的组件,均遵循**双模式接口**范式:同时暴露阻塞式与流式两套方法。以 ChatModel 为例(`components/model/interface.go:36`):

```go
type BaseModel[M messageType] interface {
    Generate(ctx context.Context, input []M, opts ...Option) (M, error)                  // 阻塞,返回完整结果
    Stream(ctx context.Context, input []M, opts ...Option) (*schema.StreamReader[M], error) // 流式,逐块产出
}
```

该范式使编排层能在统一抽象上自动处理流式拼接、装箱与合并,组件仅需实现具备业务语义的流式逻辑。详见 [`../source_notes/stream_design.md`](../source_notes/stream_design.md)。

### 2.3 函数式选项(Functional Options)机制

组件参数通过 `...Option` 传递,而非构造期固化。Option 机制支持两类参数的统一传递:

- **通用选项**(common options):框架定义的标准参数,如 `Temperature`、`MaxTokens`、`Tools`;
- **实现特定选项**(impl-specific options):各实现自定义的参数,通过 `WrapImplSpecificOptFn` 包装为统一的 `Option` 类型。

二者在同一个 `...Option` 切片中混合传递,实现方分别以 `GetCommonOptions` 与 `GetImplSpecificOptions` 提取。该设计既保证调用方 API 统一,又允许实现方无限扩展参数,详见 [`chat_model.md`](./chat_model.md)。

### 2.4 横切接口

组件层定义了两个非业务性的横切接口(`components/types.go`),作用于 DevOps 可视化与回调注入:

| 接口 | 方法 | 作用 |
|---|---|---|
| `Typer` | `GetType() string` | 返回组件实现名(如 `"OpenAIChatModel"`),用于 DevOps 工具的展示名 `{GetType()}{ComponentKind}`;亦被 `utils.InferTool` 用于工具实例命名(`types.go:29`) |
| `Checker` | `IsCallbacksEnabled() bool` | 控制框架是否对组件自动注入回调。返回 `true` 时框架跳过默认 `OnStart/OnEnd` 包装,信任组件自行在正确时机(如流式中间)触发回调(`types.go:50`) |

## 三、组件分类

`components/types.go:66` 以一组 `Component` 常量定义全部组件类别。按职能归并为四类:

### 3.1 模型类

| 组件 | 接口包 | 职责 |
|---|---|---|
| `ChatModel` / `ComponentOfChatModel` | `components/model` | 对话模型,接收 `[]*schema.Message`,返回完整或流式响应 |
| `AgenticModel` / `ComponentOfAgenticModel` | `components/model` | 智能体模型,以 `*schema.AgenticMessage` 为消息载体 |

二者共享泛型 `BaseModel[M]`,仅消息类型参数不同,详见 [`chat_model.md`](./chat_model.md)。

### 3.2 提示词类

| 组件 | 接口包 | 职责 |
|---|---|---|
| `ChatTemplate` / `ComponentOfPrompt` | `components/prompt` | 模板渲染,将变量注入模板生成 `[]*schema.Message` |
| `AgenticChatTemplate` / `ComponentOfAgenticPrompt` | `components/prompt` | 面向智能体的模板,生成 `*schema.AgenticMessage` |

### 3.3 检索与索引类

| 组件 | 接口包 | 职责 |
|---|---|---|
| `Embedding` / `ComponentOfEmbedding` | `components/embedding` | 文本向量化 |
| `Retriever` / `ComponentOfRetriever` | `components/retriever` | 根据查询检索相关文档 |
| `Indexer` / `ComponentOfIndexer` | `components/indexer` | 将文档写入向量库建立索引 |

三者构成 RAG 的索引侧(Embedding + Indexer 写入)与检索侧(Retriever 读取)。

### 3.4 文档处理类

| 组件 | 接口包 | 职责 |
|---|---|---|
| `Loader` / `ComponentOfLoader` | `components/document` | 文档加载(本地文件、对象存储等) |
| `DocumentTransformer` / `ComponentOfTransformer` | `components/document` | 文档变换(切分、清洗等) |
| `DocumentParser` | `components/document` | 文档解析(原始字节 → 结构化文档) |

### 3.5 工具类

| 组件 | 接口包 | 职责 |
|---|---|---|
| `Tool` / `ComponentOfTool` | `components/tool` | 供 ChatModel 调用的外部能力,含 `BaseTool` / `InvokableTool` / `StreamableTool` / `Enhanced*Tool` 接口层次 |

> **说明**:`Lambda`(见 `compose/types_lambda.go`)与 `ToolsNode`(见 `compose/tool_node.go`)属于编排层概念,非组件常量。Lambda 将任意 Go 函数接入编排;ToolsNode 是图中的工具执行节点。二者将在 `03_graph/` 中阐述。

## 四、组件接口速查与协作

### 4.1 接口速查

每个组件的核心方法签名(统一范式:`context` + 入参 + `...Option` + 返回 `error`):

| 组件 | 接口包 | 核心方法 | 输入 -> 输出 |
|---|---|---|---|
| ChatModel | `components/model` | `Generate` / `Stream` | `[]*Message` -> `*Message` / `StreamReader[*Message]` |
| ChatTemplate | `components/prompt` | `Format` | `map[string]any` -> `[]*Message` |
| Tool | `components/tool` | `Info` + `InvokableRun` | `() -> *ToolInfo` ; `string` -> `string` |
| Retriever | `components/retriever` | `Retrieve` | `string` -> `[]*Document` |
| Embedder | `components/embedding` | `EmbedStrings` | `[]string` -> `[][]float64` |
| Indexer | `components/indexer` | `Store` | `[]*Document` -> `[]string` |
| Loader | `components/document` | `Load` | `Source` -> `[]*Document` |
| Transformer | `components/document` | `Transform` | `[]*Document` -> `[]*Document` |

> 生成/检索类组件另含 `Stream` 流式变体;所有组件返回 `error`(Go 显式错误)。源码:`components/<name>/interface.go`。

### 4.2 组件协作关系

组件单独只是能力单元,组合起来才成应用。典型 RAG + Agent 的分工:

```
【索引侧(离线写入)】
Loader ─Load─▶ []*Document ─▶ Transformer ─Transform─▶ []*Document(切分)
                                                       │
                                              Embedder ─EmbedStrings─▶ [][]float64
                                                       │
                                              Indexer ─Store─▶ 向量库

【检索侧(在线问答)】
query ──Retriever.Retrieve──▶ []*Document ──┐
                                              ├─▶ ChatTemplate.Format ─▶ []*Message
query(拼入)─────────────────────────────────┘            │
                                                ChatModel.Generate ─▶ 回答

【工具调用(Agent)】
ChatModel(带 Tools) ─ToolCall─▶ ToolsNode ─执行─▶ Tool.InvokableRun ─结果回传─▶ ChatModel
```

要点:

- **索引侧**:Loader/Transformer/Embedder/Indexer 把原始数据写入向量库。
- **检索侧**:Retriever 取相关片段,经 ChatTemplate 拼 prompt 喂 ChatModel。
- **Agent**:ChatModel + Tool(经 ToolsNode)构成"推理 + 行动";Retriever 也可作为 Agent 的工具。

## 五、组件接口层次范式

多数组件采用**基础接口 + 扩展接口**的层次结构,以 Tool 为典型(`components/tool/interface.go`):

```
BaseTool                        Info() *schema.ToolInfo            仅元数据,供 ChatModel 决策调用
├── InvokableTool               InvokableRun(args string) string   标准可调用,参数为 JSON 字符串
├── StreamableTool              StreamableRun(...) StreamReader    流式可调用
├── EnhancedInvokableTool       InvokableRun(ToolArgument) ToolResult   多模态(图像/音频/文件)
└── EnhancedStreamableTool      StreamableRun(...) StreamReader<ToolResult>
```

`BaseTool` 仅提供元数据,足以支撑"将工具定义传给 ChatModel"的场景;实际执行则由 `InvokableTool` 等扩展接口承担。此分层使"声明工具"与"执行工具"解耦。

## 六、实现归属

| 层 | 仓库 | 内容 |
|---|---|---|
| 接口 | `eino/components/` | 组件契约、Option 定义、横切接口 |
| 实现 | `eino-ext/components/` | OpenAI / Claude / Gemini / Ark / Ollama / Elasticsearch / Redis / S3 等集成 |

实现一套组件仅需满足对应 interface,即可被编排层与 ADK 层无差别消费。

## 七、文档索引

| 文档 | 内容 | 状态 |
|---|---|---|
| [`chat_model.md`](./chat_model.md) | ChatModel 接口层次、双模式、工具绑定并发模型、Option 机制 | ✅ |
| [`tool.md`](./tool.md) | Tool 接口层次、`utils.InferTool` 函数式构造、两阶段 Option、中断/恢复 | ✅ |
| [`retriever_indexer.md`](./retriever_indexer.md) | Embedding / Indexer / Retriever 与 RAG 流水线 | ✅ |
| [`prompt.md`](./prompt.md) | ChatTemplate 提示词模板渲染 | ✅ |
| [`document.md`](./document.md) | Loader / Parser / Transformer 文档处理 | ✅ |

## 八、参考

- 组件总览:https://www.cloudwego.io/zh/docs/eino/core_modules/components/
- 组件实现:https://github.com/cloudwego/eino-ext
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/components`
