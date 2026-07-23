# State 与 Pregel:有环循环为何能跑

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/state.go`、`graph_run.go`、`generic_graph.go`、`flow/agent/react/react.go`
> 本文解答:ReAct 的"模型↔工具"往复是有环循环,纯 DAG 跑不了,Eino 如何让它跑起来?答案就是 **State + Pregel 式 superstep 迭代**。

## 一、概述

DAG(有向无环图)的执行是自然的:节点按拓扑序跑一遍就结束。但 ReAct 是**有环**的(模型 -> 工具 -> 回模型 -> …),纯 DAG 无法表达。Eino 的解法是两件事配合:

- **State** -- 跨"步"累积的数据(如对话历史),让每一轮迭代都能看到之前所有结果。
- **Pregel 式 superstep 迭代** -- 图运行器按"步"循环执行,每步跑就绪节点、更新状态、计算下一步,直到无更多任务或达到步数上限。

二者结合,有环图就能像 ReAct 那样迭代到收敛。

## 二、State:跨节点共享的运行期状态

### 2.1 注册 State

`WithGenLocalState` 给 Graph 挂一份**每次运行独立**的状态(`generic_graph.go:37`):

```go
// generic_graph.go:37
func WithGenLocalState[S any](gls GenLocalState[S]) NewGraphOption

// state.go:30
type GenLocalState[S any] func(ctx context.Context) (state S)
```

`S` 是用户自定义类型(如含 `Messages`、`KVs` 的结构体)。每次 `Invoke`/`Stream` 调用都新生成一份 state,在整个图执行期间共享,运行结束即丢弃。

```go
type state struct {
    Messages []*schema.Message
}

graph := compose.NewGraph[I, O](compose.WithGenLocalState(func(ctx context.Context) *state {
    return &state{Messages: make([]*schema.Message, 0)}
}))
```

### 2.2 访问 State

State 经 context 携带,受 mutex 保护(`state.go:34` 的 `internalState`),有三种访问方式:

| 方式 | 签名 | 时机 |
|---|---|---|
| `WithStatePreHandler` | `StatePreHandler[I,S] func(ctx, in I, state S) (I, error)`(`state.go:42`) | 节点执行**前**,可改写输入、读写 state |
| `WithStatePostHandler` | `StatePostHandler[O,S] func(ctx, out O, state S) (O, error)`(`state.go:46`) | 节点执行**后**,可读写 state、改写输出 |
| `ProcessState[S]` | `func(ctx, handler func(ctx, S) error) error`(`state.go:165`) | 节点**内部**任意位置读写 state |

`StatePreHandler` 最常用:在节点执行前把输入累积进 state,并返回(可能改写后的)输入给节点。

> 流式注意(`state.go:41` 注释):`StatePreHandler`/`StatePostHandler` 在流式模式下会**把流读尽合并成单值**再处理。需保持流式时用 `StreamStatePreHandler`/`StreamStatePostHandler`(`state.go:48`、`:52`)。

## 三、Pregel 式执行:superstep 主循环

图运行器(`graph_run.go` 的 `runner`)按"步"迭代。主循环:

```go
// graph_run.go:241
for step := 0; ; step++ {
    // 1. submit next tasks   -- 提交本轮就绪节点
    // 2. get completed tasks  -- 等待完成
    // 3. calculate next tasks -- 依据完成结果 + 状态,算下一轮就绪节点
}
```

每一步(superstep):

1. 提交所有就绪节点(入边已满足)。
2. 等待它们完成,收集输出,更新 State。
3. 根据边与分支条件,计算下一批就绪节点。
4. 若无下一批 -> 结束;若达到步数上限 -> 报错。

### 3.1 DAG 标志与步数上限

```go
// graph_run.go:249
if !r.dag && step >= maxSteps {
    return nil, newGraphRunError(ErrExceedMaxSteps)
}
```

- **`r.dag`** -- 图是否无环。DAG 不需要步数限制(拓扑序跑完自然终止);**非 DAG(有环)才用 `maxSteps` 兜底**,防止死循环。
- **`maxSteps`** -- 经 `resolveMaxSteps`(`graph_run.go:362`)解析,可由调用选项 `maxRunSteps` 覆盖。

所以"有环图能跑"的本质:运行器把环展开成 superstep 序列,每步推进一轮,靠"无新任务"自然终止、靠 `maxSteps` 兜底。

## 四、ReAct 如何映射到 State + Pregel

`react.NewAgent` 内部正是用这套机制构建 ReAct 循环(`react.go:329` 起)。逐段对照:

### 4.1 图与状态

```go
// react.go:329
graph := compose.NewGraph[[]*schema.Message, *schema.Message](
    compose.WithGenLocalState(func(ctx context.Context) *state {
        return &state{Messages: make([]*schema.Message, 0, config.MaxStep+1)}
    }),
)
```

- 输入 `[]*schema.Message`(用户消息),输出 `*schema.Message`(最终回复)。
- State 是 `*state{Messages}`,容量预留 `MaxStep+1`,准备累积整段对话。

### 4.2 模型节点:每轮看到完整历史

```go
// react.go:333
modelPreHandle := func(ctx, input []*schema.Message, state *state) ([]*schema.Message, error) {
    state.Messages = append(state.Messages, input...)  // 累积输入
    return state.Messages, nil                          // 模型看到完整历史
}
graph.AddChatModelNode(nodeKeyModel, chatModel, compose.WithStatePreHandler(modelPreHandle), ...)
graph.AddEdge(compose.START, nodeKeyModel)   // react.go:353
```

模型节点的 `StatePreHandler` 把本轮输入 append 进 `state.Messages`,再返回**完整历史**给模型。这是 ReAct 的关键:每轮推理都基于全部上下文。

### 4.3 工具节点:累积 tool call 消息

```go
// react.go:357
toolsNodePreHandle := func(ctx, input *schema.Message, state *state) (*schema.Message, error) {
    state.Messages = append(state.Messages, input)  // 累积 assistant 的 ToolCall 消息
    return input, nil
}
graph.AddToolsNode(nodeKeyTools, toolsNode, compose.WithStatePreHandler(toolsNodePreHandle), ...)
```

工具节点的 `StatePreHandler` 把模型产出的含 `ToolCalls` 的 assistant 消息累积进 state。工具执行后,结果(tool 消息)流回模型,再被 model 的 pre-handler 累积。

### 4.4 分支:有 tool call 则回工具,否则结束

```go
// react.go:369
modelPostBranchCondition := func(ctx, sr *schema.StreamReader[*schema.Message]) (string, error) {
    if isToolCall, _ := toolCallChecker(ctx, sr); isToolCall {
        return nodeKeyTools, nil   // 有 tool call -> 去工具节点
    }
    return compose.END, nil        // 无 tool call -> 结束,返回最终回复
}
```

模型之后接流式分支(`NewStreamGraphBranch`):检查输出是否含 tool call。有 -> 路由到 tools;无 -> END。配合 tools -> model 的回边,形成环。

### 4.5 完整循环

```
START ─▶ model ──(StatePreHandler 累积历史)──▶ branch
                                                  │
                              ┌──有 ToolCall──▶ tools ──(StatePreHandler 累积 ToolCall)──▶ model ──…
                              │
                              └──无 ToolCall──▶ END（最终回复）
```

Pregel superstep 序列:

| step | 节点 | 作用 | state.Messages 变化 |
|---|---|---|---|
| 0 | model | 推理 | + 用户消息 |
| 1 | tools | 执行工具 | + assistant(ToolCall) |
| 2 | model | 基于工具结果再推理 | + tool 结果 |
| 3 | tools | ... | + assistant(ToolCall) |
| ... | ... | ... | ... |
| n | model | 无 ToolCall | 分支路由到 END,结束 |

`MaxStep`(默认 12,`react.go:159`)即 `maxSteps`,限制最多迭代步数。每轮 state 累积消息,模型始终看完整历史--这正是"有环循环能跑且能收敛"的机制。

## 五、访问 State:何时用哪种

| 场景 | 选择 |
|---|---|
| 节点执行前累积输入 / 改写输入 | `WithStatePreHandler` |
| 节点执行后写状态 / 改写输出 | `WithStatePostHandler` |
| 节点内部按条件读写 state | `ProcessState[S]` |
| 流式且需保持流 | `StreamStatePreHandler` / `StreamStatePostHandler` |

ReAct 用 `WithStatePreHandler` 在 model/tools 节点入口累积消息,是最典型用法。

## 六、常见坑与排错

- **流式 `StatePreHandler` 退化** -- `StatePreHandler`/`StatePostHandler` 在流式下会**读尽流合并成单值**再处理(`state.go:41`);需保持流式用 `StreamStatePreHandler`/`StreamStatePostHandler`。
- **State 并发访问需加锁** -- State 经 context 携带、受 mutex 保护;节点内 `ProcessState` 已自动加锁,但跨节点并发读写同一 state 字段仍需注意顺序。
- **自定义 State 类型未注册 -> 检查点反序列化失败** -- State 含自定义类型时,中断恢复需 `RegisterSerializableType[T]`,否则反序列化报错。
- **`maxSteps` 兜底误判为 bug** -- 有环图达到 `MaxStep`(ReAct 默认 12)会返回 `ErrExceedMaxSteps`;这是防死循环保护,应调大 `MaxStep` 或检查为何不收敛(如模型反复调工具)。
- **DAG 不走步数循环** -- `r.dag` 为 true(无环)时不限步;有环才用 `maxSteps`。误给 DAG 设大 `MaxStep` 无副作用,但无意义。
- **`WithGenLocalState` 每运行一份** -- State 每次 `Invoke`/`Stream` 新生成,运行间不共享;要跨运行持久化用 CheckPointStore(见 `interrupt_resume.md`)。

## 七、小结

| 关注点 | 机制 |
|---|---|
| 跨步累积数据 | `WithGenLocalState` 挂每运行 state,经 context + mutex 共享 |
| 节点读写 state | `WithStatePreHandler`/`WithStatePostHandler`/`ProcessState` |
| 有环图执行 | Pregel 式 superstep 主循环(`graph_run.go:241`) |
| 步数兜底 | 非 DAG 用 `maxSteps`(DAG 不需要) |
| 自然终止 | 无新任务时结束(如模型不再产出 ToolCall) |
| ReAct 映射 | model/tools 节点用 StatePreHandler 累积消息,model 后分支决定回 tools 还是 END |

State + Pregel 是 Eino 编排层处理"有环、有状态、需迭代"场景的底层机制。它把 ReAct 这类循环从"手写 for 循环"提升为"图拓扑 + 状态驱动的迭代",使 [`react_agent.md`](./react_agent.md) 中的 `NewAgent` 能用 ~两行配置自动跑通完整工具调用循环。

## 八、参考

- [编排设计原则](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/)
- [Checkpoint & interrupt/resume](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/checkpoint_interrupt/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose/state.go`、`graph_run.go`、`flow/agent/react/react.go`
