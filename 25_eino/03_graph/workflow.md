# Workflow:声明式编排

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/workflow.go`、`field_mapping.go`
> 可运行 demo:[`../02_components/demo/workflow_demo/`](../02_components/demo/workflow_demo/)(已验证)
> Workflow 是 Graph 的声明式包装,用"声明依赖 + 字段映射"替代 `AddEdge`。

## 一、概述

类型定义(`workflow.go:45`):

> Workflow is wrapper of graph, replacing AddEdge with declaring dependencies and field mappings between nodes. Under the hood it uses NodeTriggerMode(AllPredecessor), so does not support cycles.

核心区别于 Graph:

| | Graph | Workflow |
|---|---|---|
| 连接方式 | 命令式 `AddEdge(start, end)` | 声明式 `node.AddInput(fromKey, ...)` -- 节点声明自己的输入来源 |
| 拓扑 | 显式连边 | 由各节点的输入声明推导 |
| 数据流 | 边只连节点,字段映射另配 | 字段映射内置于 `AddInput` |
| 环 | 支持(配合 State/Pregel) | **不支持**(AllPredecessor 触发) |

Graph 是"连边"思维(关注节点间拓扑);Workflow 是"数据流"思维(关注每个节点的输入从哪来),后者对多输入汇聚场景更自然。

## 二、API

### 2.1 创建与编译

```go
// workflow.go:61
func NewWorkflow[I, O any](opts ...NewGraphOption) *Workflow[I, O]
// workflow.go:82
func (wf *Workflow[I, O]) Compile(ctx, opts ...GraphCompileOption) (Runnable[I, O], error)
```

### 2.2 加节点

`AddXxxNode(key, node, opts...)` 返回 `*WorkflowNode`(`workflow.go:87` 起),用于链式声明输入:

```go
n := wf.AddChatModelNode("chat", chatModel)   // 返回 *WorkflowNode
n.AddInput("build_msgs")                       // 在返回的节点上声明输入
```

支持 `AddChatModelNode`(`:87`)、`AddLambdaNode`(`:159`)、`AddToolsNode`(`:111`)、`AddRetrieverNode`(`:123`)、`AddEmbeddingNode`(`:129`)、`AddIndexerNode`(`:135`)、`AddLoaderNode`(`:141`)、`AddDocumentTransformerNode`(`:147`)、`AddPassthroughNode`(`:173`)、`AddGraphNode`(`:153`,嵌套图)等。

### 2.3 声明数据流(`WorkflowNode` 方法)

| 方法 | 作用 |
|---|---|
| `AddInput(fromKey, mappings...)`(`:197`) | 声明输入来自 `fromKey`;无 mapping 则取整个输出;有则按字段映射 |
| `AddDependency(fromKey)`(`:300`) | 仅声明依赖(保证 `fromKey` 先完成),不传数据 |
| `SetStaticValue(path, value)`(`:311`) | 注入静态输入值(非来自其他节点) |
| `AddInputWithOptions`(`:278`) | `AddInput` 带选项(如 `noDirectDependency`) |

首节点接收工作流初始输入:`node.AddInput(compose.START)`(已验证)。

### 2.4 分支与结束

```go
// workflow.go:420
wf.AddBranch(fromNodeKey, branch *GraphBranch) *WorkflowBranch
// workflow.go:432
wf.AddEnd(fromNodeKey, inputs ...*FieldMapping) *Workflow[I, O]
```

`AddEnd` 声明结束节点取哪个节点的输出(可带字段映射)作为工作流输出。分支复用 Graph 的 `GraphBranch`(见 [`graph_basics.md`](./graph_basics.md) §3)。

## 三、字段映射(Field Mapping)

`AddInput` 的 `mappings` 用三种构造器(`field_mapping.go`),表达不同的数据流向:

| 构造器 | 语义 | 用途 |
|---|---|---|
| `MapFields(from, to)`(`:85`) | 前驱的 `from` 字段 -> 后继的 `to` 字段 | 字段到字段映射 |
| `ToField(to)`(`:73`) | 前驱**整个输出** -> 后继的 `to` 字段 | **多输入汇聚(fan-in)的关键** |
| `FromField(from)`(`:65`) | 前驱的 `from` 字段 -> 后继**整个输入**(独占,不可再加映射) | 取前驱某字段作为全部输入 |

```go
// 例:整个前驱输出映射到后继某字段
combine.AddInput("retrieve", compose.ToField("Docs"))   // retrieve 整个输出 -> combine.Docs
combine.AddInput("chat", compose.ToField("Answer"))     // chat 整个输出 -> combine.Answer
```

`ToField` 使一个节点能从多个前驱各取整个输出、填入自身输入结构体的不同字段--这是 Workflow 表达 fan-in 最自然的方式。

## 四、触发模式:AllPredecessor

Workflow 用 `NodeTriggerMode(AllPredecessor)`(`workflow.go:45`):节点在**所有前驱完成后**才触发。这与 Graph(按边就绪触发)不同,带来两个特点:

- **多输入汇聚天然支持** -- 节点等待所有 `AddInput` 声明的前驱到齐再执行。
- **不支持环** -- AllPredecessor 模式下环会死锁(节点永远等不到所有前驱完成)。需要循环用 Graph + Pregel 或 Agent(见 [`state_pregel.md`](./state_pregel.md)、[`react_agent.md`](./react_agent.md))。

## 五、完整示例(已验证)

[`../02_components/demo/workflow_demo/`](../02_components/demo/workflow_demo/) 用真实 Ark 模型跑通的线性声明式工作流:

```go
wf := compose.NewWorkflow[string, string]()

buildMsgs := wf.AddLambdaNode("build_msgs", compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
    return []*schema.Message{schema.UserMessage(q)}, nil
}))
chat := wf.AddChatModelNode("chat", chatModel)
toText := wf.AddLambdaNode("to_text", compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
    return msg.Content, nil
}))

// 数据流声明（替代 AddEdge）
buildMsgs.AddInput(compose.START) // 首节点接收工作流输入
chat.AddInput("build_msgs")       // chat 的输入来自 build_msgs（整个输出，类型自然匹配）
toText.AddInput("chat")
wf.AddEnd("to_text")              // 结束取 to_text 输出

runnable, err := wf.Compile(ctx)
out, err := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
```

对照 [`graph_basics.md`](./graph_basics.md) §6.1 的线性 Graph:那里用 `AddEdge(START, "to_msgs")` 等连边,这里用 `buildMsgs.AddInput(compose.START)` 等声明输入,等价但更"数据流"导向。

### 多输入汇聚示例

```go
type Combine struct {
    Docs   []*schema.Document
    Answer *schema.Message
}

wf := compose.NewWorkflow[string, string]()
wf.AddLambdaNode("query", compose.InvokableLambda(...))      // string -> string
wf.AddRetrieverNode("retrieve", retriever)                    // string -> []*Document
wf.AddLambdaNode("build_msgs", compose.InvokableLambda(...))  // string -> []*Message
wf.AddChatModelNode("chat", chatModel)                        // []*Message -> *Message

combine := wf.AddLambdaNode("combine", compose.InvokableLambda(func(ctx context.Context, in Combine) (string, error) {
    return fmt.Sprintf("答案:%s\n依据:%d 篇", in.Answer.Content, len(in.Docs)), nil
}))
combine.AddInput("retrieve", compose.ToField("Docs"))   // 两个前驱的整个输出分别填入字段
combine.AddInput("chat", compose.ToField("Answer"))
wf.AddEnd("combine")

// retrieve 与 chat 并行执行,combine 等二者都完成(AllPredecessor)后触发
```

`combine` 用 `ToField` 从 `retrieve`、`chat` 各取整个输出填入 `Combine.Docs`、`Combine.Answer`,无需手写合并逻辑。这是 Workflow 相对 Graph 的核心优势:多输入汇聚用字段映射声明式表达。

## 六、何时用 Workflow / Graph / Chain

| 场景 | 选择 |
|---|---|
| 固定线性流程 | **Chain**(最简洁) |
| 需要分支、并行、任意 DAG、或有环(ReAct) | **Graph** / Agent |
| 多输入汇聚、数据流导向、声明式偏好 | **Workflow**(DAG,无环) |
| 有环循环 + 状态 | **Agent**(`react.NewAgent`)或 Graph+Pregel |

## 七、常见坑与排错

- **Workflow 不支持环** -- `AllPredecessor` 触发模式下,环会死锁(节点永远等不到所有前驱完成)。需要循环用 Graph+Pregel 或 Agent。
- **多输入未用 `ToField` -> 类型不匹配** -- 一个节点 `AddInput` 多个前驱时,若都不带 mapping(整个输出作输入),会冲突;必须用 `ToField(to)` 把各前驱整个输出映射到输入结构体不同字段。
- **`AddInput(compose.START)` 漏写** -- 首节点接收工作流输入需显式 `node.AddInput(compose.START)`;漏写则该节点无输入源,Compile 报错(见 `../02_components/demo/workflow_demo/`)。
- **`MapFields` 字段路径错误** -- `MapFields(from, to)` 的 from/to 是字段路径(点分);路径写错或字段不存在会在运行时映射失败。
- **`AddDependency` 与 `AddInput` 混淆** -- `AddDependency` 只声明顺序依赖、不传数据;需要数据流必须用 `AddInput`。
- **Workflow 与 Graph 的触发差异** -- Graph 按边就绪触发(可更早开始);Workflow 等所有前驱完成才触发(AllPredecessor),并行度可能更低但语义更确定。

## 八、小结

| 关注点 | Workflow 的解法 |
|---|---|
| 连接 | `node.AddInput(fromKey, mappings...)` 声明输入来源,替代 `AddEdge` |
| 首节点输入 | `AddInput(compose.START)` |
| 字段映射 | `MapFields` / `ToField` / `FromField` 内置于 `AddInput` |
| 多输入汇聚 | `ToField` 把多个前驱整个输出填入不同字段 |
| 仅依赖不传数据 | `AddDependency` |
| 静态输入 | `SetStaticValue` |
| 触发 | AllPredecessor(所有前驱完成才触发) |
| 环 | 不支持(用 Graph/Agent) |

Workflow 适合数据流清晰、多输入汇聚、声明式偏好的 DAG 场景。它的底层仍是 Graph,只是把"连边 + 字段映射"提升为"节点自声明输入"的更抽象表达。

## 九、参考

- [Workflow 编排框架](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/workflow_orchestration_framework/)
- [编排设计原则](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose/workflow.go`
