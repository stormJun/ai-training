# Pregel ToolsNode Demo: ToolsNode 增量（7）

> 源码：
> - [`demo.go`](./demo.go)：**ToolsNode + FlakyToolsNode + ModelVertex + 4 场景**（增量 7 核心）
> - [`main.go`](./main.go)：Graph/Compile + Run/StreamRun + **Vertex.ComponentType() + AddToolsNode**（引擎感知增量）
> - [`channel.go`](./channel.go)：channel 抽象核心（不变，从 06）
> - [`checkpoint.go`](./checkpoint.go)：Checkpoint + channel.load 恢复（不变，从 06）
> - [`stream.go`](./stream.go)：流基础设施（不变，从 05）
> - [`llm.go`](./llm.go)：真 LLM 流式（不变，从 05）
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表
>
> 上游：[06_pregel_channel_demo](../06_pregel_channel_demo/pregel_channel_demo.md)（channel 抽象），[05_pregel_stream_demo](../05_pregel_stream_demo/pregel_stream_demo.md)（流式）
>
> 本 demo 引入 **ToolsNode**，把多个工具包成一个图顶点，内部分发，将 ReAct 拓扑从 fan-out 变成线性。引擎通过 `ComponentType()` 感知顶点类型。

## 术语表

本文件只定义增量 7 的新术语。06 的术语（channel、edge handler、merge、superstep、StreamCompute 等）见 [06 CONTEXT.md](../06_pregel_channel_demo/CONTEXT.md)。

### ToolsNode

**ToolsNode**:
把多个工具包成一个图顶点的编排层概念。收到含 ToolCalls 的消息后，按名字内部分发到对应工具函数，并行执行，汇总结果返回。对应 eino `compose.ToolsNode`（`tool_node.go:79`）。引擎层通过 `ComponentType()` 知道它是 ToolsNode，但调度逻辑和普通顶点无区别。
_Avoid_: 工具节点（太宽泛）、工具管理器（暗示外部管理）

**内部分发（internal dispatch）**:
ToolsNode 收到消息后，按 `ToolCall.Name` 查找对应工具函数并执行的过程。对应 eino `ToolsNode.Invoke`（`:1046`）里的 `genToolCallTasks` + `parallelRunToolCall`（`:985`）。
_Avoid_: 路由（路由是 Pregel 层的 Branch 概念）、分发（太宽泛）

**并行执行（parallel dispatch）**:
ToolsNode 对多个 ToolCall 并行执行（goroutine），汇总后返回。对应 eino `parallelRunToolCall`（`:985`）。可选串行（`ExecuteSequentially`），demo 只实现并行。
_Avoid_: 并发执行（并行是同时跑，并发是调度模型）

**线性拓扑（linear topology）**:
ToolsNode 版 ReAct 的图结构：`model → tools → model`（2 条边）。Pregel 每步只有 1 个活跃顶点，无 fan-out/fan-in。对应 eino react agent 的 `nodeKeyModel` + `nodeKeyTools`。
_Avoid_: 简单拓扑（线性是拓扑形态描述）

**fan-out 拓扑（fan-out topology）**:
06 方式 per-tool 顶点的图结构：`model → {search, calc} → model`（3 条边 + fan-out/fan-in）。Pregel 每步有 N 个工具顶点并行，需要 edge handler 过滤或工具内部过滤。
_Avoid_: 多节点拓扑（fan-out 是拓扑形态描述）

**FlakyToolsNode**:
首次 Compute 必崩的 ToolsNode，用于 checkpoint 演示。对应 06 的 FlakyToolVertex，但崩的是整个 ToolsNode（内部所有工具都不执行），不是单个工具。
_Avoid_: 不稳定工具（是节点级别不稳定，不是工具级别）

### 引擎感知

**ComponentType()**:
Vertex 接口的方法，返回顶点的组件类型。引擎运行时通过此方法感知顶点是什么类型（ChatModel、ToolsNode、Tool 等）。对应 eino `graphNode.componentType`（`component_to_graph_node.go:31`）。目前用于日志打印，不做调度区分。
_Avoid_: 类型标签（ComponentType 是方法，不是字段）

**component 常量**:
`ComponentOfChatModel`、`ComponentOfToolsNode`、`ComponentOfTool`。对应 eino `compose/types.go` 的 `ComponentOf*` 常量。引擎日志打印如 `[tools/ToolsNode]`。
_Avoid_: 类型字符串（component 是具名类型，不是裸 string）

**AddToolsNode**:
Graph 的语法糖方法：校验 ComponentType 为 ToolsNode 后调 AddVertex。对应 eino `graph.AddToolsNode(key, toolsNode)`（`graph.go:399`）。
_Avoid_: 注册工具（AddToolsNode 是注册顶点，不是注册工具函数）

### 对比

**per-tool 顶点 vs ToolsNode**:
| | per-tool 顶点（06） | ToolsNode（07） |
|---|---|---|
| 图结构 | model → {search, calc} → model | model → tools → model |
| 活跃顶点 | 每步 N 个（每个工具一个） | 每步 1 个 |
| 工具分发 | Pregel fan-out + edge handler | 节点内部分发 |
| merge | 需要（N 个工具结果扇入） | 不需要（节点内汇总） |
| 加工具 | 改图（加顶点+边+handler） | 改 ToolsNode（注册函数） |
| 引擎感知 | N 个 Tool 顶点 | 1 个 ToolsNode 顶点 |
| 对应 eino | 06 阶段的简化 | `compose.ToolsNode` + `react.NewAgent` |

**ToolsNode 在 eino 中的位置**:
ToolsNode 是编排层（compose）概念，不是引擎层。它在 Graph 中是一个普通顶点，引擎通过 ComponentType 感知其类型但不做特殊调度。内部工具分发、并行执行、middleware 都是编排层逻辑。
_Avoid_: 引擎层概念（ToolsNode 不涉及 superstep/channel/屏障的调度逻辑）
