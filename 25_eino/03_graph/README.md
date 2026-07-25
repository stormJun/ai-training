# 编排层(Compose)总览

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/`、`flow/`
> 定位(`compose/doc.go:17`):"graph and workflow primitives to build composable, interruptible execution pipelines with callback support"。

## 一、定位

编排层位于组件层之上,职责是**把组件组装成可执行、可流式、可中断恢复的流水线**。组件(ChatModel、Tool、Retriever 等)提供"能力",编排层提供"流程"。

```
组件层(components/)  ChatModel / Tool / Retriever …  ← 能力单元
        ▲
编排层(compose/)     Chain / Graph / Workflow          ← 本文：把组件连成流程
        ▲
ADK 层(adk/)         Agent / Runner / Middleware
```

## 二、三种编排原语

控制力从强到弱、抽象从低到高:

| 原语 | 文件 | 特点 | 适用 |
|---|---|---|---|
| **Chain** | `compose/chain.go` | 线性序列,一进一出 | 固定步骤的线性流程 |
| **Graph** | `compose/graph.go`、`dag.go` | DAG,支持分支、并行、字段映射、状态 | 有条件分支/并行的复杂流程 |
| **Workflow** | `compose/workflow.go` | Graph 之上的声明式结构化抽象 | 节点与数据流的声明式描述 |

> 还有一个特殊的**Agent** 抽象(`flow/agent/react`),用于有环循环(ReAct),见 [react_agent.md](./react_agent.md)。

## 三、核心概念

### 3.1 节点(Node)

把组件或 Lambda 包成图节点。组件接入通过 `component_to_graph_node.go` 提供 `AddChatModelNode`、`AddToolsNode`、`AddRetrieverNode` 等"语法糖";`AddLambdaNode`(`types_lambda.go`)把任意 Go 函数接入。

### 3.2 边(Edge)与分支(Branch)

- **边**:`AddEdge(startNode, endNode)`(`generic_graph.go:106`),特殊节点 `compose.START` / `compose.END`。
- **分支**:`NewGraphBranch[T](condition, endNodes)`(`branch.go:145`),按条件选下一条边,实现 if/switch 路由。`NewStreamGraphBranch` 为流式变体。`NewGraphMultiBranch` 支持同时走多条边(并行)。

### 3.3 字段映射(Field Mapping)

`field_mapping.go` 把上游节点输出的某字段接到下游节点的某入参,解决节点间数据形状不匹配。

### 3.4 状态(State)与 Pregel

- **State**(`state.go`):图级共享状态,跨节点传递累积数据(如 ReAct 的对话历史)。
- **Pregel**(`pregel.go`):顶点为中心的迭代计算模型。**有环循环**(如 ReAct 的模型↔工具往复)在纯 DAG 中无法表达,需要 Pregel 的迭代语义来驱动。执行模型拆解见 [`pregel.md`](./pregel.md),与 State 配合见 [`state_pregel.md`](./state_pregel.md)。

### 3.5 流式自动处理

编排层自动处理跨节点的流式衔接(`stream_concat.go`、`stream_reader.go`):拼接、装箱、合并、复制。组件只需实现 `Stream` 方法,框架负责把上游的 `StreamReader` 适配成下游入参。底层设计见 [`../source_notes/stream_design.md`](../source_notes/stream_design.md)。

### 3.6 编译与运行

`graph.Compile(ctx, opts...)` 产出 `Runnable[I, O]`(`runnable.go`),提供统一入口:

- `Invoke(ctx, input)` -- 阻塞,返回完整结果
- `Stream(ctx, input)` -- 流式,返回 `StreamReader`
- `Collect(ctx, sr)` -- 把流收集成完整结果

编译期校验图结构(连通性、类型匹配),运行期执行。

## 四、ReAct 循环:为何需要 Agent 抽象

工具调用智能体的核心循环是**有环**的:

```
ChatModel ──有 ToolCall──▶ ToolsNode ──▶ 回到 ChatModel ──…
    └──无 ToolCall──▶ END
```

这是循环,不是 DAG。用裸 Graph 手写这个循环需要自行处理 Pregel 状态与分支条件,繁琐易错。因此 eino 在 `flow/agent/react` 提供了 **ReAct agent** 抽象:`react.NewAgent` 接收 ChatModel + 工具,内部构建 Pregel 驱动的 Graph 自动跑循环,调用方只需 `agent.Generate`。

这正是 [`react_agent.md`](./react_agent.md) 的主题--也是"用手写循环(见 `../02_components/demo/tool_demo/`)换取框架自动 ReAct"的切入点。

## 五、与 ADK 的关系

ADK 层(`adk/`)在编排之上,提供更高层的智能体运行时:

- `flow/agent/react` -- 编排/flow 层的 ReAct agent(本文档范畴),直接基于 compose.Graph + Pregel。
- `adk.ChatModelAgent`(`adk/chatmodel.go`)-- ADK 层的智能体,封装更完整的 agent 语义(中间件、HITL、回调等),内部同样驱动 ReAct 循环。

二者关系:`flow/agent/react` 更贴近编排机制;`adk.ChatModelAgent` 是更高层的产品级封装。生产中通常直接用 ADK。详见 ADK 文档。

## 六、文档索引

| 文档 | 内容 | 状态 |
|---|---|---|
| [`react_agent.md`](./react_agent.md) | ReAct agent:`react.NewAgent` 自动 ReAct、Pregel 机制、与手写循环对比 | ✅ |
| [`react_design.md`](./react_design.md) | ReAct 设计深读:带环图拓扑、state 累积、两分支、StreamToolCallChecker、ADK newReact 增强 | ✅ |
| [`planexecute_design.md`](./planexecute_design.md) | Plan-and-Execute 设计深读:Planner/Executor/Replanner 三角色、Sequential+Loop 拓扑、可插拔 Plan | ✅ |
| [`chain_basics.md`](./chain_basics.md) | Chain 线性编排:fluent builder、类型流转、Lambda 四模式、流式 | ✅ |
| [`graph_basics.md`](./graph_basics.md) | Graph DAG:节点/边/起止、分支、并行、字段映射 | ✅ |
| [`pregel.md`](./pregel.md) | Pregel 执行模型:两种运行模式、通道对比、superstep 主循环、时序图 | ✅ |
| [`state_pregel.md`](./state_pregel.md) | State 与 Pregel:有环循环为何能跑、ReAct 映射 | ✅ |
| [`workflow.md`](./workflow.md) | Workflow 声明式编排:AddInput 替代 AddEdge、字段映射、AllPredecessor | ✅ |
| [`interrupt_resume.md`](./interrupt_resume.md) | 中断/恢复与检查点:HITL、CheckpointStore、Resume | ✅ |

## 七、参考

- [Chain & Graph 介绍](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/chain_graph_introduction/)
- [编排设计原则](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/)
- [Graph or Agent - when to use which](https://www.cloudwego.io/zh/docs/eino/overview/graph_or_agent/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose`
