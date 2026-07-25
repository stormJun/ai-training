# Graph:DAG 编排

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/graph.go`、`generic_graph.go`、`branch.go`、`graph_add_node_options.go`
> Graph 是表达力最强的编排原语:任意 DAG 拓扑,支持节点、边、分支、并行、字段映射。

## 一、概述

Chain 是线性特例;Graph 是**任意有向无环图(DAG)**。当流程需要条件分支、并行扇出、多输入多输出、或非线性的复杂拓扑时,用 Graph。

与 Chain 的核心差异:

| | Chain | Graph |
|---|---|---|
| 拓扑 | 线性(+ Branch/Parallel 扩展) | 任意 DAG |
| 加节点 | fluent `AppendXxx`(返回自身,顺序隐式) | `AddXxxNode(key, node)`(显式 key,返回 error) |
| 连接 | 隐式(按 Append 顺序) | 显式 `AddEdge(start, end)` |
| 适用 | 固定步骤 | 复杂拓扑、分支、并行 |

## 二、API

### 2.1 创建与编译

```go
// generic_graph.go:72
func NewGraph[I, O any](opts ...NewGraphOption) *Graph[I, O]

// generic_graph.go:123
func (g *Graph[I, O]) Compile(ctx context.Context, opts ...GraphCompileOption) (Runnable[I, O], error)
```

`Compile` 产出 `Runnable[I, O]`,提供四种执行入口(`generic_graph.go:117` 注释):

- `Invoke(ctx, input)` -- 阻塞
- `Stream(ctx, input)` -- 流式出
- `Collect(ctx, inputReader)` -- 流式入、阻塞出
- `Transform(ctx, inputReader)` -- 流式入、流式出

### 2.2 加节点

每个节点需指定** key**(字符串名),作为连边标识:

```go
// graph.go:350
g.AddChatModelNode(key string, node model.BaseChatModel, opts ...GraphAddNodeOpt) error
// graph.go:433
g.AddLambdaNode(key string, node *Lambda, opts ...GraphAddNodeOpt) error
```

完整列表(`graph.go`):`AddChatModelNode`(`:350`)、`AddToolsNode`(`:399`)、`AddRetrieverNode`(`:315`)、`AddEmbeddingNode`(`:304`)、`AddDocumentTransformerNode`(`:421`)、`AddLambdaNode`(`:433`)等。均返回 `error`(编译期可捕获配置错误)。

### 2.3 连边与起止

```go
// generic_graph.go:106
func (g *Graph[I, O]) AddEdge(startNode, endNode string) error

// graph.go:37 / :40
const START = "start"
const END   = "end"
```

`START` / `END` 是特殊节点 key,分别代表图的入口与出口。每个节点须经 `AddEdge` 显式连入拓扑。

## 三、分支(Branch)

分支实现条件路由:按上游节点输出选择下一条边。

```go
// branch.go:29
type GraphBranchCondition[T any] func(ctx context.Context, in T) (endNode string, err error)

// branch.go:145
func NewGraphBranch[T any](condition GraphBranchCondition[T], endNodes map[string]bool) *GraphBranch

// graph.go:466
func (g *graph) AddBranch(startNode string, branch *GraphBranch) error
```

- **`condition`** -- 接收 `startNode` 的输出 `in`,返回下一个节点的 key。
- **`endNodes`** -- 声明所有可能的目标节点 `map[string]bool`。
- **`AddBranch(startNode, branch)`** -- 在 `startNode` 之后接分支。

语义:`condition` 收到上游节点输出,据此返回目标 key;**被选中的目标节点收到同一份上游输出**(分支只路由,不变换数据)。

流式变体 `NewStreamGraphBranch`(`branch.go:168`)的 condition 接收 `*schema.StreamReader[T]`,可基于首块决定路由(如根据模型流式输出的首个 chunk 判断是否含 tool call)。

## 四、并行(Parallel)

并行有三种表达方式:

### 4.1 `Parallel` 类型(结构化扇出)

`Parallel`(`chain_parallel.go:49`)把多个分支的结果合并为一个 map,keyed by `outputKey`:

```go
// chain_parallel.go:32
p := compose.NewParallel()
p.AddChatModel("output_key01", chatModel01)   // chain_parallel.go:68
p.AddChatModel("output_key02", chatModel02)
// 结果: map[string]any{"output_key01": ..., "output_key02": ...}
```

每个分支用 `AddXxx(outputKey, node)`,结果按 `outputKey` 聚合。`Parallel` 主要经 `Chain.AppendParallel` 接入(`chain.go:459`)。

### 4.2 多路分支(Multi-Branch)

`NewGraphMultiBranch`(`branch.go:89`)的 condition 返回 `map[string]bool`(多个目标),实现**条件并行**--同时路由到多个节点:

```go
// branch.go:35
type GraphMultiBranchCondition[T any] func(ctx, in T) (endNode map[string]bool, err error)
```

### 4.3 Graph 中的扇出 + 字段映射

裸 Graph 无 `AddParallel` 方法,并行通过**一个节点连多条出边 + 字段映射**实现:多个下游节点各用 `WithOutputKey` 把结果写入共享 map 的不同 key,汇总节点用 `WithInputKey` 读取。

## 五、字段映射(Field Mapping)

`WithInputKey` / `WithOutputKey`(`graph_add_node_options.go:67`、`:76`)解决节点间数据形状不匹配,是多输入/多输出、扇出/扇入的关键:

```go
// graph_add_node_options.go:67
func WithInputKey(k string) GraphAddNodeOpt   // 节点从共享 map 的 k 字段读输入
// graph_add_node_options.go:76
func WithOutputKey(k string) GraphAddNodeOpt   // 节点把输出写入共享 map 的 k 字段
```

典型场景:上游扇出产生 `map[string]any{"a": ..., "b": ...}`,下游节点用 `WithInputKey("a")` 只取 `a` 部分。这比用 Lambda 手动拆装更声明式。

## 六、完整示例

### 6.1 线性 Graph(对照 Chain)

用 Graph API 表达与 [`chain_basics.md`](./chain_basics.md) §5.1 相同的线性流程,体会显式 key + AddEdge:

```go
graph := compose.NewGraph[string, string]()

graph.AddLambdaNode("to_msgs", compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
    return []*schema.Message{schema.UserMessage(q)}, nil
}))
graph.AddChatModelNode("chat", chatModel)
graph.AddLambdaNode("to_text", compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
    return msg.Content, nil
}))

graph.AddEdge(compose.START, "to_msgs")
graph.AddEdge("to_msgs", "chat")
graph.AddEdge("chat", "to_text")
graph.AddEdge("to_text", compose.END)

runnable, err := graph.Compile(ctx)
if err != nil {
    return err
}
out, err := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
```

线性场景下 Graph 比 Chain 啰嗦(要写 key 和 AddEdge),故线性流程优先用 Chain。

### 6.2 带 Branch 的 Graph

按输入内容路由到不同处理路径:

```go
graph := compose.NewGraph[string, string]()

// router: 把输入原样返回(分支条件据此决定路由,被选中路径也收到同一份输入)
graph.AddLambdaNode("router", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
    return in, nil
}))
graph.AddLambdaNode("code_path", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
    return "[代码路径] " + in, nil
}))
graph.AddLambdaNode("chat_path", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
    return "[对话路径] " + in, nil
}))

graph.AddEdge(compose.START, "router")
// 在 router 之后接分支:按输入内容选 code_path 或 chat_path
graph.AddBranch("router", compose.NewGraphBranch(
    func(ctx context.Context, in string) (string, error) {
        if strings.Contains(in, "代码") {
            return "code_path", nil
        }
        return "chat_path", nil
    },
    map[string]bool{"code_path": true, "chat_path": true},
))
graph.AddEdge("code_path", compose.END)
graph.AddEdge("chat_path", compose.END)

runnable, err := graph.Compile(ctx)
// runnable.Invoke(ctx, "帮我写代码")   -> "[代码路径] 帮我写代码"
// runnable.Invoke(ctx, "你好")         -> "[对话路径] 你好"
```

要点:
- `AddBranch("router", branch)` -- 分支挂在 `router` 之后。
- condition 收到 `router` 的输出(此处即原输入),返回目标 key。
- 两条路径都连到 `END`(扇入)。

## 八、常见坑与排错

- **节点 key 重复或缺失** -- `AddXxxNode(key, ...)` 的 key 全图唯一;重复会覆盖,未连入拓扑的节点不执行。`START`/`END` 是保留 key。
- **未连 `START` / `END`** -- 每条路径须从 `START` 可达、到 `END` 可达;悬空节点或断路会在 `Compile` 报错。
- **分支 `condition` 返回未声明节点** -- `NewGraphBranch` 的 `endNodes` 必须包含所有可能返回值;condition 返回 `endNodes` 外的 key 会运行时报错。
- **分支后下个节点收到的是上游输出** -- `AddBranch(startNode, ...)` 的 condition 接收 `startNode` 输出,**被选中节点也收到同一份输出**(分支只路由不变换)。要按原输入路由,前置节点需原样返回(见 `../02_components/demo/graph_demo/` 的 router)。
- **扇出结果合并需字段映射** -- 一个节点连多条出边时,下游各用 `WithOutputKey` 写入共享 map 不同 key,汇总节点用 `WithInputKey` 读;否则类型/数据错乱。
- **Graph 有环需 State+Pregel** -- 裸 Graph 有环会触发 `maxSteps` 兜底(`ErrExceedMaxSteps`);ReAct 类循环用 `react.NewAgent`(见 `react_agent.md`)。

## 八、小结

| 关注点 | Graph 的解法 |
|---|---|
| 任意 DAG | `AddXxxNode(key, node)` + `AddEdge` 显式连边 |
| 起止 | `compose.START` / `compose.END` 特殊节点 |
| 条件路由 | `NewGraphBranch` + `AddBranch`(condition 返回目标 key) |
| 条件并行 | `NewGraphMultiBranch`(condition 返回多目标 map) |
| 结构化扇出 | `Parallel` 类型(经 Chain.AppendParallel) |
| 扇出/扇入数据 | `WithOutputKey` / `WithInputKey` 字段映射 |
| 流式分支 | `NewStreamGraphBranch`(基于首块决定路由) |
| 执行 | `Compile` -> `Runnable` 的 `Invoke`/`Stream`/`Collect`/`Transform` |

Graph 适合需要分支、并行、复杂拓扑的场景。线性流程用 Chain 更简洁;有环循环(ReAct)用 Agent(见 [`react_agent.md`](./react_agent.md))。

## 九、参考

- [Chain & Graph 介绍](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/chain_graph_introduction/)
- [编排设计原则](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose/graph.go`
