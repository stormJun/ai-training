# Pregel ToolsNode Demo: ToolsNode 增量（7）

> 源码：
> - [`demo.go`](./demo.go)：**ToolsNode + FlakyToolsNode + ModelVertex + 4 场景**
> - [`main.go`](./main.go)：Graph/Compile + Run/StreamRun + **Vertex.ComponentType() + AddToolsNode**（引擎感知增量）
> - [`channel.go`](./channel.go)：channel 抽象核心（不变，从 06）
> - [`checkpoint.go`](./checkpoint.go)：Checkpoint + channel.load 恢复（不变，从 06）
> - [`stream.go`](./stream.go)：流基础设施（不变，从 05）
> - [`llm.go`](./llm.go)：真 LLM 流式（不变，从 05）
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表
>
> 上游：[06_pregel_channel_demo](../06_pregel_channel_demo/pregel_channel_demo.md)（channel 抽象），[05_pregel_stream_demo](../05_pregel_stream_demo/pregel_stream_demo.md)（流式基础）
>
> 本 demo 引入 **ToolsNode**，把多个工具包成一个图顶点，内部分发，将 ReAct 拓扑从 fan-out 变成线性。引擎通过 `ComponentType()` 感知顶点类型。

## 一、概述

06 用 per-tool 顶点实现 ReAct：每个工具是一个独立 Pregel 顶点，model fan-out 到 N 个工具顶点，结果 fan-in 回 model。这需要 edge handler 过滤 ToolCall、merge 扇入结果。

07 引入 **ToolsNode**，把多个工具包成**一个** Pregel 顶点。model 只连一条边到 ToolsNode，ToolsNode 内部按名字分发 ToolCall、并行执行、汇总返回。引擎层不知道 ToolsNode 内部有几个工具。

核心变化：

| | 06（per-tool 顶点） | 07（ToolsNode） |
|---|---|---|
| 图结构 | `model → {search, calc} → model` | `model → tools → model` |
| 活跃顶点 | 每步 N 个 | 每步 1 个 |
| 工具分发 | Pregel fan-out + edge handler | 节点内部分发 |
| merge | 需要（N 路扇入） | 不需要（节点内汇总） |
| 加工具 | 改图（加顶点+边+handler） | 改 ToolsNode（注册函数） |

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/07_pregel_toolnode_demo
source /Users/songxijun/workspace/otherProject/eino-examples/.env  # ARK_API_KEY
go run .
```

4 个场景：ToolsNode Run(Invoke) / StreamRun(真 LLM) / 对比 per-tool vs ToolsNode / checkpoint 崩溃恢复。`go vet` 通过，`go build` 通过。

## 三、数据设计：Message 与 ToolCall

### 3.1 Message struct

```go
type Message struct {
    ToolCalls []ToolCall   // 模型要调的工具（Assistant 消息携带）
    Results   []string     // 工具返回的结果（Tool 消息携带）
    Answer    string       // 最终回答（最终回复携带）
}
type ToolCall struct {
    Name string   // 工具名——ToolsNode 按此查 map 分发
    Arg  string   // 工具参数——透传给工具函数
}
```

**设计决策：一条消息承载三种角色。**

06 和 07 共用同一个 Message。没有用 `Role` 字段区分 Assistant/Tool/User，而是用字段是否为空来区分：

- 模型产出时：`ToolCalls` 非空（"我要调这些工具"）
- 工具返回时：`Results` 非空（"这些是工具结果"）
- 最终回复时：`Answer` 非空（"这是回答"）

为什么不用 eino 的 Role 区分？因为 demo 的顶点之间只传一条 Message，没有对话历史累积。eino 用 State 累积 `[]*schema.Message`，需要 Role 区分；demo 不做 State，所以用字段判角色就够了。

### 3.2 ToolCall 设计

demo 的 `ToolCall{Name, Arg}` 是 eino `ToolCall{ID, Type, Function{Name, Arguments}, Index, Extra}` 的极简版。

省掉的字段和原因：

| 省掉 | 为什么能省 |
|---|---|
| `ID` | demo 没有 State 累积对话历史，不需要 ID 匹配"哪个结果对应哪个调用" |
| `Type` | demo 只有一种工具类型（function），eino 预留了 `"computer"` 等 |
| `Index` | demo 的流式合并不用 Index 对齐，eino 的 `concatToolCalls` 需要 |
| `Extra` | demo 不传额外元信息 |

**`Name` 是唯一必须保留的字段**——它是 ToolsNode 内部分发的依据。`Arg` 也可以省（如果工具不需要参数），但 search/calc 都有参数，所以保留。

## 四、ToolsNode 设计

### 4.1 为什么是 `map[string]func` 而不是 `[]tool.BaseTool`

```go
type ToolsNode struct {
    id    string
    tools map[string]func(ctx context.Context, arg string) (string, error)
}
```

eino 用 `[]tool.BaseTool`（接口切片），运行时建 `indexes map[string]int` 做名字→下标映射。

demo 直接用 `map[string]func`，**map 的 key 就是名字，value 就是函数**，省掉了 indexes 间接层。

设计考量：
- eino 需要 `BaseTool` 接口因为工具可以是 `InvokableTool`、`StreamableTool`、`EnhancedInvokableTool` 等多种类型，统一入口是接口
- demo 只有一种工具类型（`func(ctx, arg) (string, error)`），不需要接口分层，直接用函数值

### 4.2 为什么用 `AddTool` 逐步注册而不是构造时一次传入

```go
tools := NewToolsNode("tools")
tools.AddTool("search", func(...) { ... })
tools.AddTool("calc", func(...) { ... })
```

eino 用 `ToolsNodeConfig{Tools: []tool.BaseTool{...}}` 构造时一次传入。

demo 选逐步注册，原因：
- 场景代码更清晰——每行注册一个工具，读起来像配置清单
- FlakyToolsNode 嵌入 ToolsNode 后也需要注册工具，逐步注册比构造时传入更自然

两者功能等价，只是 API 风格差异。

### 4.3 Compute：并行执行的设计

完整代码：

```go
func (tn *ToolsNode) Compute(ctx context.Context, in Message) (Message, error) {
    if len(in.ToolCalls) == 0 {
        return Message{}, fmt.Errorf("ToolsNode: no tool calls in input")
    }

    // 并行执行(对应 eino parallelRunToolCall)
    type toolResult struct {
        name   string
        result string
        err    error
    }
    ch := make(chan toolResult, len(in.ToolCalls))
    for _, tc := range in.ToolCalls {
        fn, ok := tn.tools[tc.Name]    // ① 按名字查 map
        if !ok {                        // ② 找不到 → 直接报错
            ch <- toolResult{name: tc.Name, err: fmt.Errorf("tool %q not found", tc.Name)}
            continue
        }
        go func(tc ToolCall) {          // ③ 找到 → goroutine 并行执行
            r, err := fn(ctx, tc.Arg)
            ch <- toolResult{name: tc.Name, result: r, err: err}
        }(tc)
    }

    var results []string
    for i := 0; i < len(in.ToolCalls); i++ {  // ④ 收齐所有结果
        r := <-ch
        if r.err != nil {
            return Message{}, r.err              // ⑤ 任何一个失败 → 整体失败
        }
        fmt.Printf("  [tools] %s -> %s\n", r.name, r.result)
        results = append(results, r.result)
    }
    return Message{Results: results}, nil
}
```

设计决策，逐条说：

**① 按名字查 map — 这一行替代了 06 的 Branch + edge handler + merge**

06 里"把消息送到正确的工具"需要三步：Branch.Cond 返回目标顶点列表 → edge handler 过滤 ToolCall → channel merge 扇入结果。07 里一行 `tn.tools[tc.Name]` 完成等价工作。

**② 找不到直接报错 — 对应 eino 的 unknownToolHandler 但简化**

eino 有 `unknownToolHandler`：模型幻觉调了一个不存在的工具时，用 handler 兜底返回一个字符串，不中断流程。demo 简化为直接报错，因为 demo 不做幻觉兜底。

**③ goroutine 并行 — 对应 eino 的 parallelRunToolCall**

eino 的 `parallelRunToolCall`（`:985`）用 `sync.WaitGroup` + goroutine。demo 用 buffered channel，功能等价：
- buffered channel 容量 = len(ToolCalls)，每个 goroutine 写一次不阻塞
- 主循环读 N 次收齐，效果同 Wait

**⑤ 任何一个失败 → 整体失败**

eino 的行为更精细：interrupt 的工具走 rerun 逻辑，其他工具结果保留。demo 简化为整体失败，因为 demo 不做 interrupt/rerun。

### 4.4 StreamCompute：为什么是逐个执行而不是并行

完整代码：

```go
func (tn *ToolsNode) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
    out, w := Pipe[Message]()
    go func() {
        defer w.Close()
        msg, err := concatMsg(input)
        if err != nil {
            w.Send(Message{}, err)
            return
        }
        for _, tc := range msg.ToolCalls {
            fn, ok := tn.tools[tc.Name]
            if !ok {
                w.Send(Message{}, fmt.Errorf("tool %q not found", tc.Name))
                return
            }
            r, err := fn(ctx, tc.Arg)
            if err != nil {
                w.Send(Message{}, err)
                return
            }
            fmt.Printf("  [tools] 流式产出: %s -> %s\n", tc.Name, r)
            w.Send(Message{Results: []string{r}}, nil)  // 逐个发送
        }
    }()
    return out, nil
}
```

Compute 用 goroutine 并行，StreamCompute 用 for 循环逐个。为什么不同？

- **Compute 返回单条 Message**——必须收齐所有结果再返回，所以并行 + channel 收齐
- **StreamCompute 返回流**——每个工具结果可以立即 `w.Send` 出去，下游（model）能立刻看到。并行的话需要额外 MergeStreamReaders，demo 工具本身不产出流（`func` 返回 string），并行收益不大

eino 的 `ToolsNode.Stream`（`:1148`）确实是并行执行 + `MergeStreamReaders`，因为 eino 的工具可以是 `StreamableTool`（自己产出流）。demo 的工具全是同步函数，逐个更简单。

### 4.5 引擎感知：ComponentType + AddToolsNode

**Vertex 接口加 ComponentType()：**

```go
type Vertex interface {
    ID() string
    ComponentType() component                              // 增量 7: 引擎感知顶点类型
    Compute(ctx context.Context, in Message) (Message, error)
    StreamCompute(ctx context.Context, in *StreamReader[Message]) (*StreamReader[Message], error)
}
```

对应 eino `graphNode.componentType`（`component_to_graph_node.go:31`）。每个顶点返回自己的组件类型：

| 顶点 | ComponentType() | 对应 eino |
|---|---|---|
| ModelVertex | `ComponentOfChatModel` | `ComponentOfChatModel` |
| ToolsNode | `ComponentOfToolsNode` | `ComponentOfToolsNode` |
| ToolVertex | `ComponentOfTool` | `ComponentOfTool` |
| FlakyToolsNode | `ComponentOfToolsNode`（嵌入提升） | 同 ToolsNode |

**component 常量：**

```go
const (
    ComponentOfChatModel component = "ChatModel"
    ComponentOfToolsNode  component = "ToolsNode"
    ComponentOfTool       component = "Tool"
)
```

对应 eino `compose/types.go` 的 `ComponentOf*` 常量。

**AddToolsNode 语法糖：**

```go
func (g *Graph) AddToolsNode(v Vertex) error {
    if v.ComponentType() != ComponentOfToolsNode {
        return fmt.Errorf("AddToolsNode: vertex %q has ComponentType %q, want %q",
            v.ID(), v.ComponentType(), ComponentOfToolsNode)
    }
    g.AddVertex(v)
    return nil
}
```

对应 eino `graph.AddToolsNode(key, toolsNode)`（`graph.go:399`）。校验 ComponentType 后调 AddVertex，防止误把非 ToolsNode 顶点注册为工具节点。

**运行时效果——superstep 日志带类型：**

06 方式：`── superstep 1 ── 活跃: [calc search]`
07 方式：`── superstep 1 ── 活跃: [tools/ToolsNode]`

场景 3 对比更清晰：
- 3a：`活跃: [calc/Tool search/Tool]` — per-tool 顶点，类型是 Tool
- 3b：`活跃: [tools/ToolsNode]` — ToolsNode 顶点，类型是 ToolsNode

**设计决策：感知但不特殊调度。** 引擎知道顶点类型，但 Run/StreamRun 的调度逻辑不因 ComponentType 而变。eino 里 ComponentType 主要影响 callback 分发（`callbacks.ReuseHandlers(ctx, &callbacks.RunInfo{Component: ...})`），demo 不做 callback，所以目前只用于日志。

### 4.6 与 Vertex 接口的关系（调度层面）

```go
type Vertex interface {
    ID() string
    ComponentType() component
    Compute(ctx context.Context, in Message) (Message, error)
    StreamCompute(ctx context.Context, in *StreamReader[Message]) (*StreamReader[Message], error)
}
```

ToolsNode 实现了 Vertex 接口的三个方法：
- `ID()` → 返回 `"tools"`
- `Compute()` → 内部分发 + 并行 + 汇总
- `StreamCompute()` → 流式逐个执行

**引擎只知道 ToolsNode 是一个 Vertex。** 调 `Compute` 时传 `Message{ToolCalls: [...]}`，拿回 `Message{Results: [...]}`，和调 ModelVertex 没有区别。分发逻辑完全封在 Compute 内部，引擎不参与。

这就是"编排层对引擎层的封装"——ToolsNode 在编排层做分发，引擎层只做调度。

## 五、FlakyToolsNode 设计

```go
type FlakyToolsNode struct {
    ToolsNode       // 嵌入，复用所有逻辑
    calls int       // 调用计数
}

func (f *FlakyToolsNode) Compute(ctx context.Context, in Message) (Message, error) {
    f.calls++
    if f.calls == 1 {
        panic("模拟瞬时故障:首次必崩")
    }
    return f.ToolsNode.Compute(ctx, in)   // 第 2 次起正常执行
}

func (f *FlakyToolsNode) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
    return f.ToolsNode.StreamCompute(ctx, input)  // 流式不 flaky
}
```

**设计决策：嵌入而非组合。**

为什么嵌入 `ToolsNode` 而不是包一个 `*ToolsNode` 指针？因为 FlakyToolsNode 需要自动满足 Vertex 接口。嵌入后 `ID()` 和 `StreamCompute()` 自动提升，只需覆写 `Compute` 加 panic 逻辑。

与 06 的 FlakyToolVertex 对比：
- 06：FlakyToolVertex 是**单个工具**不稳定，其他工具顶点不受影响
- 07：FlakyToolsNode 是**整个 ToolsNode** 不稳定，内部所有工具都不执行

对应 eino 的 interrupt 语义：ToolsNode 整体中断（`ToolsInterruptAndRerunExtra`），不是某个工具中断。

## 六、ReAct 拓扑设计：从 fan-out 到线性

### 6.1 06 方式：fan-out 拓扑

```
START → model ── has ToolCall ──→ search ──┐
              │                    calc  ──┤→ model（回到模型，带工具结果）
              └── no ToolCall ──→ END
```

```go
func addReActEdges(g *Graph) {
    g.AddEdge(START, "model")
    g.AddEdge("search", "model")        // search 回边
    g.AddEdge("calc", "model")          // calc 回边
    g.AddBranch("model", &Branch{
        Cond: func(msg Message) []string {
            if len(msg.ToolCalls) > 0 {
                return []string{"search", "calc"}  // fan-out 到 N 个顶点
            }
            return []string{END}
        },
        EndNodes: map[string]bool{"search": true, "calc": true, END: true},
    })
}
```

引擎在这个拓扑下做的事：
1. Branch.Cond 返回 `["search", "calc"]` → 引擎 fan-out
2. channel.reportValues 把消息投到 search 和 calc 两个 channel → 引擎分发
3. edge handler 过滤每个 channel 的 ToolCall → 引擎过滤
4. search 和 calc 两个顶点并行 Compute → 引擎并行
5. channel.get 合并两个结果 → 引擎 merge 扇入

**5 步，全在引擎层。加一个工具要改 Branch.Cond、EndNodes、AddEdge 三处。**

### 6.2 07 方式：线性拓扑

```
START → model ── has ToolCall ──→ tools ──→ model（回到模型，带工具结果）
              └── no ToolCall ──→ END
```

```go
func addReActEdgesWithToolsNode(g *Graph) {
    g.AddEdge(START, "model")
    g.AddEdge("tools", "model")         // 单条回边
    g.AddBranch("model", &Branch{
        Cond: func(msg Message) []string {
            if len(msg.ToolCalls) > 0 {
                return []string{"tools"}  // 单一目标
            }
            return []string{END}
        },
        EndNodes: map[string]bool{"tools": true, END: true},
    })
}
```

引擎在这个拓扑下做的事：
1. Branch.Cond 返回 `["tools"]` → 引擎路由到 1 个顶点
2. channel.reportValues 把消息投到 tools 的 channel → 引擎分发（1 路）
3. ToolsNode.Compute 内部按名字查 map + goroutine 并行 + channel 收齐 → **节点做分发**
4. 返回 `Message{Results: [...]}` → 引擎投给 model

**1 步路由 + 节点内部分发。加一个工具只改 `AddTool`，图不变。**

### 6.3 运行时差异

06（场景 3a）：
```
[compile] 检测到环: [model->search->model][calc->model->calc]
── superstep 1 ── 活跃: [calc search]   ← 2 个顶点
```

07（场景 3b）：
```
[compile] 检测到环: [model->tools->model]
── superstep 1 ── 活跃: [tools]          ← 1 个顶点
```

### 6.4 对应 eino

eino 的 `react.NewAgent`（`react.go:128`）内部就是 07 方式：

```go
const (
    nodeKeyTools = "tools"  // ToolsNode
    nodeKeyModel = "chat"   // ChatModel
)
```

两个顶点，一条环边 `tools → chat`。`react.NewAgent` 把 ChatModel + ToolsNode + 分支 + MaxStep 封装好，调用方无需手写。

### 6.5 eino 的 model → tools → model 完整流程

**图结构：**

```
START → chat ──has ToolCall──→ tools ──not direct──→ chat（循环）
              └──no ToolCall──→ END
                                  └──direct──→ direct_return → END
```

**每轮 superstep 做的事：**

1. **chat 节点** — `modelPreHandle` 把完整 `state.Messages` 喂给 ChatModel，模型产出 Assistant 消息（含 ToolCalls 或最终回复）
2. **Branch** — 有 ToolCalls → `tools`，无 → `END`
3. **tools 节点** — `toolsNodePreHandle` 把 Assistant 消息追加进 State；`ToolsNode.Invoke` 按 `ToolCall.Name` 查注册表，goroutine 并行执行，每个 ToolCall 产出一个带 `ToolCallID` 的 ToolMessage
4. **Branch** — 有 `ToolReturnDirectly` → `direct_return`，无 → `chat`
5. 回到步骤 1，State 里已累积了 User + Assistant + Tool 消息，模型看到完整上下文

**具体走一遍：**

```
superstep 0:  chat
  modelPreHandle:      state.Messages += [UserMsg("北京天气怎么样？")]
  ChatModel:           → AssistantMsg{ToolCalls: [{get_weather, ...}]}
  Branch:              → "tools"

superstep 1:  tools
  toolsNodePreHandle:  state.Messages += [AssistantMsg{ToolCalls}]
  ToolsNode.Invoke:    genToolCallTasks → parallelRunToolCall → [ToolMsg8Msg{Content:"晴，28℃"}]
  Branch:              → "chat"

superstep 2:  chat
  modelPreHandle:      state.Messages += [ToolMsg]
  ChatModel:           → AssistantMsg{Content:"北京今天晴，28℃"}
  Branch:              → END
```

**核心机制：**

- **State 累积**：每步的 StatePreHandler 把消息追加进 `state.Messages`，模型每轮看到完整对话历史
- **ToolsNode 内部分发**：`genToolCallTasks` 按 Name 查注册表 → `parallelRunToolCall` 并行执行 → 汇总 `[]*schema.Message`
- **Pregel 驱动循环**：不是手写 for，是 Pregel superstep 迭代，`MaxStep` 防死循环

**和 demo 的关键区别：**

| | demo | eino |
|---|---|---|
| 消息传递 | 顶点之间直接传 Message | State 累积 `[]*schema.Message`，StatePreHandler 追加 |
| 模型输入 | 只收到工具结果 `Message{Results: [...]}` | 收到**完整对话历史**（user + assistant + tool 消息） |
| 工具输出 | `Message{Results: []string}` | `[]*schema.Message`（每 ToolCall 一个 ToolMessage，带 ToolCallID） |
| 分支判断 | `len(msg.ToolCalls) > 0` | `toolCallChecker` 检查流首块 |
| StatePreHandler | 无 | **关键**——负责把每步的消息追加进 State，让模型每轮看到完整上下文 |

## 七、场景设计

### 场景 1：ToolsNode Run(Invoke)

目的：展示 ToolsNode 线性拓扑的基本 ReAct 循环，无 LLM，快速验证。

```
[compile] 检测到环: [model->tools->model]
── superstep 0 ── 活跃: [model]
── superstep 1 ── 活跃: [tools]      ← 单顶点（不是 [search, calc]）
── superstep 2 ── 活跃: [model]
```

### 场景 2：StreamRun 真实 LLM

目的：验证流式路径。ToolsNode.StreamCompute 逐个产出工具结果，model.StreamCompute 调真 LLM 流式回答。

### 场景 3：对比 per-tool 顶点 vs ToolsNode

目的：**同一个问题，两种拓扑，并排展示差异。** 这是理解 ToolsNode 设计的核心场景——看到 3a 的 fan-out 和 3b 的线性跑出相同结果，但图结构完全不同。

3a 保留 06 的 `ToolVertex` + `addReActEdges`，3b 用 07 的 `ToolsNode` + `addReActEdgesWithToolsNode`。

### 场景 4：checkpoint + FlakyToolsNode 崩溃恢复

目的：验证 ToolsNode 在 checkpoint 下的行为。FlakyToolsNode 首次 Compute 必崩，Run1 崩溃保存 checkpoint，Run2 从 checkpoint 续跑。

## 八、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `ToolsNode` struct | `compose.ToolsNode`（`:79`） | 多工具包成单顶点 |
| `NewToolsNode` + `AddTool` | `NewToolNode` + `ToolsNodeConfig.Tools` | 构造+注册 |
| `ToolsNode.Compute` | `ToolsNode.Invoke`（`:1046`） | 内部分发+并行执行 |
| `ToolsNode.StreamCompute` | `ToolsNode.Stream`（`:1148`） | 流式版 |
| 并行 goroutine | `parallelRunToolCall`（`:985`） | 多 ToolCall 并行 |
| `FlakyToolsNode` | interrupt + `ToolsInterruptAndRerunExtra` | 节点级故障/中断 |
| `addReActEdgesWithToolsNode` | `react.NewAgent` 内部构图 | 线性拓扑 model↔tools |
| model 分支到 `"tools"` | `nodeKeyTools = "tools"` | 单一目标，无 fan-out |
| `ComponentType()` | `graphNode.componentType` | 引擎感知顶点类型 |
| `AddToolsNode` | `graph.AddToolsNode`（`:399`） | 语法糖+校验 |
| `ComponentOfToolsNode` 常量 | `ComponentOfToolsNode`（`types.go:33`） | 组件类型常量 |
| `map[string]func` | `toolsTuple.indexes` + `[]tool.BaseTool` | 名字→函数的映射 |
| 找不到工具直接报错 | `unknownToolHandler` 兜底 | 幻觉工具处理 |

## 九、简化说明

| # | 简化点 | eino | demo | 设计理由 |
|---|---|---|---|---|
| 1 | 工具类型 | `tool.BaseTool`/`InvokableTool`/`StreamableTool` | `func(ctx, arg) (string, error)` | demo 只需同步函数，不需要接口分层 |
| 2 | middleware | `InvokableToolMiddleware`/`StreamableToolMiddleware` | 无 | demo 不做拦截链 |
| 3 | alias | `ToolAliasConfig`（name+args 别名） | 无 | demo 不做别名解析 |
| 4 | unknownToolHandler | `UnknownToolsHandler` | 直接报错 | demo 不做幻觉工具兜底 |
| 5 | ExecuteSequentially | 可选串行 | 只并行 | demo 只展示并行，串行是配置选项不是机制 |
| 6 | enhanced tool | `EnhancedInvokableTool`/`EnhancedStreamableTool` | 无 | demo 不做多模态工具输出 |
| 7 | interrupt + rerun | `ToolsInterruptAndRerunExtra` | panic + checkpoint | demo 不做部分重跑 |
| 8 | 输出类型 | `[]*schema.Message`（每 ToolCall 一个 ToolMessage） | `Message{Results: []string}` | demo 不做 per-call 消息，结果压在同一个 Message 里 |
| 9 | ToolCall.ID | 唯一标识，用于结果匹配 | 无 | demo 没有 State 累积，不需要 ID 对应 |
| 10 | Message.Role | Assistant/Tool/User 区分 | 无，用字段是否为空判角色 | demo 不做对话历史累积 |

**核心机制全部保留**：多工具包成单顶点、按名字内部分发、并行执行、线性 ReAct 拓扑。

## 十、后续规划

| 内容 | 状态 |
|------|------|
| ToolsNode（内部分发 + 并行执行 + 线性拓扑） | ✅ |
| middleware（拦截链） | 📋 |
| unknownToolHandler（幻觉工具兜底） | 📋 |
| ExecuteSequentially（串行模式） | 📋 |
| enhanced tool（多模态输出） | 📋 |
| interrupt + rerun（部分重跑） | 📋 |
| 引擎感知 ToolsNode（componentType 标签 + AddToolsNode 语法糖） | ✅ |

## 十一、总结

### 一句话

**ToolsNode 把 N 个工具顶点合并为 1 个，将 ReAct 拓扑从 fan-out 变成线性。**

### 核心机制

| 机制 | 06（per-tool 顶点） | 07（ToolsNode） |
|---|---|---|
| 工具分发 | Pregel fan-out + edge handler 过滤 | 节点内部按名字查 map |
| 工具并行 | Pregel 多顶点同时执行 | goroutine in Compute |
| 结果汇总 | channel merge 扇入（N 路汇 1） | 节点内 channel 收齐 |
| 拓扑 | `model → {search, calc} → model`（3 边，fan-out） | `model → tools → model`（2 边，线性） |

### 分层定位

ToolsNode 是**编排层**（compose）概念，不是引擎层：

- **引擎层**（Pregel）：只看到一个 `Vertex`，调 `Compute` / `StreamCompute`，走 channel，做屏障同步。不知道内部有几个工具。
- **编排层**（ToolsNode）：收到 ToolCalls，按名字查 map，goroutine 并行执行，汇总返回。所有分发逻辑在节点内部。
- **组件层**（单个工具）：被 ToolsNode 内部调用的 `func(ctx, arg) (string, error)`。

三层各司其职：组件做单件事，编排把多组件包成节点，引擎调度节点。

### 与 eino 的对应

- `ToolsNode` struct → `compose.ToolsNode`（`tool_node.go:79`）
- `Compute` 内部分发 → `Invoke`（`:1046`）里的 `genToolCallTasks` + `parallelRunToolCall`
- 线性拓扑 `model ↔ tools` → `react.NewAgent` 的 `nodeKeyModel` + `nodeKeyTools`

### 简化边界

保留：多工具包单顶点、按名字内部分发、并行执行、线性 ReAct 拓扑。

省略：middleware、alias、unknownToolHandler、串行模式、enhanced tool、interrupt rerun、per-call Message 输出、ToolCall.ID、Message.Role。
