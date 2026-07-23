# 中断与恢复(Interrupt / Resume)

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/interrupt.go`、`resume.go`、`checkpoint.go`、`internal/core/interrupt.go`
> 本文阐述 Eino 的人机交互(HITL)机制:运行中暂停等待外部输入,从检查点恢复。

## 一、概述

中断/恢复让流程在执行中**暂停**(如等待人工确认、外部审批),保存检查点,后续从断点**恢复**继续。这是 HITL(human-in-the-loop)的基础。

三要素:

| 要素 | 职责 |
|---|---|
| **Interrupt** | 节点主动暂停,抛出中断信号(含原因、可选状态) |
| **CheckPointStore** | 持久化检查点(图的运行状态),供恢复时加载 |
| **Resume** | 用中断 ID + 可选数据,从检查点恢复执行 |

典型场景:工具执行前要人工确认、长流程分段审批、需要外部补充信息。

## 二、中断(Interrupt)

### 2.1 主动中断

节点内调用,返回一个错误从 `InvokableRun`/Lambda 抛出:

```go
// interrupt.go:110
func Interrupt(ctx context.Context, info any) error
// interrupt.go:130
func StatefulInterrupt(ctx context.Context, info any, state any) error
// interrupt.go:174
func CompositeInterrupt(ctx context.Context, info any, state any, errs ...error) error
```

- **`Interrupt(ctx, info)`** -- 暂停,`info` 是面向用户的原因(不持久化,仅暴露给调用方)。
- **`StatefulInterrupt(ctx, info, state)`** -- 暂停并保存组件内部 `state`(须可序列化),恢复时经 `GetInterruptState` 取回。组件有需还原的内部状态时用。
- **`CompositeInterrupt`** -- 聚合子组件(图、其他工具)的中断,用于嵌套结构。

### 2.2 节点级中断(编译期声明)

不必在节点代码里调 `Interrupt`,可在编译时声明在特定节点前后中断:

```go
// interrupt.go:31 / :38
compose.WithInterruptBeforeNodes([]string{"node_key"})  // 节点执行前暂停
compose.WithInterruptAfterNodes([]string{"node_key"})   // 节点执行后暂停
```

作为 `Compile` 选项,便于在不改节点代码的前提下插入人工卡点。

### 2.3 检测中断与取回信息

首次运行中断后,调用方从返回的 error 取回中断信息:

```go
// interrupt.go:241
func IsInterruptRerunError(err error) (info any, ok bool)      // 是否中断 + info
// interrupt.go:299
func ExtractInterruptInfo(err error) (*InterruptInfo, bool)     // 取回完整 InterruptInfo
```

`InterruptInfo`(`interrupt.go:258`)含 `InterruptContexts []*InterruptCtx`。每个 `InterruptCtx`(`core/interrupt.go:124`):

```go
type InterruptCtx struct {
    ID          string   // 中断点全限定地址,如 "agent:A;node:graph_a;tool:tool_call_123"
    Address     Address
    Info        any      // 中断时传的 info(给用户看的原因)
    IsRootCause bool
    Parent      *InterruptCtx
}
```

**`InterruptCtx.ID`** 是恢复时的定位标识(`core/interrupt.go:126` 注释明确:"This ID should be used when providing resume data via ResumeWithData")。

## 三、检查点(Checkpoint)

中断时图的运行状态需持久化,才能在恢复时还原。

### 3.1 `CheckPointStore` 接口

```go
// core/interrupt.go:27
type CheckPointStore interface {
    Get(ctx context.Context, checkPointID string) ([]byte, bool, error)
    Set(ctx context.Context, checkPointID string, checkPoint []byte) error
}
// 可选:core/interrupt.go:39
type CheckPointDeleter interface { Delete(ctx context.Context, checkPointID string) error }
```

实现 `Get`/`Set` 即可(内存 map、Redis、DB 均可)。未实现 `CheckPointDeleter` 时,过期检查点由 store 自行清理(如 TTL)。

### 3.2 编译期挂存储

```go
// checkpoint.go:60
runnable, _ := graph.Compile(ctx, compose.WithCheckPointStore(store))
```

### 3.3 运行期指定检查点 ID

```go
// checkpoint.go:74
compose.WithCheckPointID(cpID)            // 加载并默认写入该检查点
// checkpoint.go:84
compose.WithWriteToCheckPointID(cpID)     // 写入到另一个检查点(从旧检查点加载、写新检查点)
// checkpoint.go:91
compose.WithForceNewRun()                 // 忽略检查点,从头跑
```

`WithCheckPointID` 既是运行选项(`Option`),用于 `Invoke`/`Stream`:首次运行传一个 ID(中断时写入),恢复时传同一 ID(加载)。

### 3.4 自定义状态类型注册

检查点序列化需识别 State 中的自定义类型:

```go
// checkpoint.go:48
compose.RegisterSerializableType[MyState]("my_state")
```

## 四、恢复(Resume)

### 4.1 构造恢复上下文

```go
// resume.go:94
func Resume(ctx, interruptIDs ...string) context.Context              // 仅恢复(不带数据)
// resume.go:106
func ResumeWithData(ctx, interruptID string, data any) context.Context // 恢复单点并带数据
// resume.go:119
func BatchResumeWithData(ctx, resumeData map[string]any) context.Context // 批量恢复(核心)
```

`interruptID` 即 `InterruptCtx.ID`。`data` 是恢复时回传给节点的数据(如人工确认结果)。

### 4.2 节点内读取恢复数据

```go
// resume.go:77
func GetResumeContext[T](ctx) (isResumeFlow bool, hasData bool, data T)
// resume.go:32
func GetInterruptState[T](ctx) (wasInterrupted bool, hasState bool, state T)
```

- **`GetResumeContext[T]`** -- 取恢复时携带的数据(`ResumeWithData` 的 `data`);`isResumeFlow` 区分首次还是恢复。
- **`GetInterruptState[T]`** -- 取 `StatefulInterrupt` 保存的内部状态。

### 4.3 恢复调用方式

恢复即再次调用 `Invoke`/`Stream`,传入**恢复上下文** + **检查点 ID**:

```go
resumeCtx := compose.ResumeWithData(ctx, interruptID, humanInput)
result, err := runnable.Invoke(resumeCtx, input, compose.WithCheckPointID(cpID))
```

框架加载检查点、从断点恢复执行,节点内 `GetResumeContext` 拿到 `humanInput`。

## 五、完整 HITL 流程

```go
// 1. 内存 CheckPointStore(生产用 Redis/DB)
type memStore struct {
    m map[string][]byte
    mu sync.Mutex
}
func (s *memStore) Get(_ context.Context, id string) ([]byte, bool, error) { /* 读 s.m[id] */ }
func (s *memStore) Set(_ context.Context, id string, b []byte) error { /* 写 s.m[id] */ }

// 2. 会中断的节点:首次中断等确认,恢复时拿到人工输入
confirm := compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
    if isResume, _, data := compose.GetResumeContext[string](ctx); isResume {
        return "已确认:" + data, nil
    }
    return "", compose.Interrupt(ctx, "需要人工确认: "+in)
})

// 3. 编译并挂检查点存储
g := compose.NewGraph[string, string]()
g.AddLambdaNode("confirm", confirm)
g.AddEdge(compose.START, "confirm")
g.AddEdge("confirm", compose.END)
runnable, _ := g.Compile(ctx, compose.WithCheckPointStore(&memStore{m: map[string][]byte{}}))

cpID := "run-001"

// 4. 首次运行 -> 中断,返回 error
_, err := runnable.Invoke(ctx, "删除文件", compose.WithCheckPointID(cpID))
info, _ := compose.ExtractInterruptInfo(err)
ic := info.InterruptContexts[0]
// ic.Info == "需要人工确认: 删除文件"(展示给人工)

// 5. 人工确认 -> 带数据恢复
resumeCtx := compose.ResumeWithData(ctx, ic.ID, "同意")
result, _ := runnable.Invoke(resumeCtx, "删除文件", compose.WithCheckPointID(cpID))
// result == "已确认:同意"
```

流程要点:

1. **首次** `Invoke` -> 节点 `Interrupt` -> 检查点写入 store -> 返回中断 error。
2. 调用方 `ExtractInterruptInfo` 取回 `InterruptContexts[].ID` 与 `Info`,把 `Info` 展示给人工。
3. 人工决策后,`ResumeWithData(ctx, id, data)` 构造恢复上下文。
4. **再次** `Invoke(resumeCtx, input, WithCheckPointID)` -> 加载检查点 -> 从断点恢复 -> 节点 `GetResumeContext` 拿到 `data` -> 继续执行。

> 注:中断/恢复是两次独立的 `Invoke` 调用,跨进程亦可(检查点持久化在 store 中)。这使长流程审批、跨会话续跑成为可能。

## 六、工具内的中断

[`../02_components/tool.md`](../02_components/tool.md) §6 的 `tool.Interrupt` / `tool.StatefulInterrupt` 是 `compose.Interrupt` 的封装,供工具节点使用:

```go
// components/tool/interrupt.go:44
func Interrupt(ctx, info any) error  // 内部调 core.Interrupt
```

工具内调 `tool.Interrupt(ctx, "需确认")` 即可暂停整个图;恢复时 `tool.GetResumeContext` / `tool.GetInterruptState` 取数据。机制与本文一致,只是入口在工具层。

## 七、常见坑与排错

- **自定义 State 未 `RegisterSerializableType`** -- 检查点序列化需识别 State 中的自定义类型;漏注册会导致 `Set`/`Get` 时序列化或反序列化失败。
- **interrupt ID 取错** -- 恢复时 `ResumeWithData(ctx, id, data)` 的 `id` 必须是 `InterruptCtx.ID`(全限定地址),不是 `InterruptInfo` 本身;取错会导致恢复不到目标节点。
- **CheckPointStore 未实现 `Delete`** -- 仅实现 `Get`/`Set` 时过期检查点不会自动清理;生产环境用 TTL 或实现 `CheckPointDeleter`,否则存储无限增长。
- **恢复时漏传 `WithCheckPointID`** -- 恢复是再次 `Invoke`,必须带 `WithCheckPointID(cpID)` 加载检查点;漏传会从头跑(`WithForceNewRun` 语义)而非续跑。
- **首次与恢复的 input 要一致** -- 恢复时传入的 input 应与首次一致(框架主要靠检查点恢复状态,input 用于校验/补全);乱传可能破坏状态一致性。
- **`log.Fatalf` 跳过 checkpoint 写入** -- 中断是正常返回 error(非 panic);用 `log.Fatalf` 处理中断 error 会 `os.Exit`,可能跳过检查点持久化。应 `return err` 让上层处理。

## 八、小结

| 关注点 | 机制 |
|---|---|
| 主动暂停 | `Interrupt` / `StatefulInterrupt` / `CompositeInterrupt` |
| 节点级卡点 | `WithInterruptBeforeNodes` / `WithInterruptAfterNodes` |
| 检测中断 | `IsInterruptRerunError` / `ExtractInterruptInfo` |
| 中断点定位 | `InterruptCtx.ID`(恢复时用) |
| 状态持久化 | `CheckPointStore`(`Get`/`Set`)+ `WithCheckPointStore` |
| 检查点 ID | `WithCheckPointID` / `WithWriteToCheckPointID` / `WithForceNewRun` |
| 恢复上下文 | `Resume` / `ResumeWithData` / `BatchResumeWithData` |
| 节点内取数据 | `GetResumeContext` / `GetInterruptState` |
| 自定义类型 | `RegisterSerializableType` |

中断/恢复让 Eino 的编排从"一跑到底"扩展为"可暂停、可跨进程续跑",支撑 HITL、长流程审批、人工兜底等场景。它与 State/Pregel 配合:检查点保存的正是 State 等运行期状态,恢复后 Pregel 从断点继续迭代。

## 九、参考

- [Checkpoint & interrupt/resume](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/checkpoint_interrupt/)
- [Agent HITL](https://www.cloudwego.io/zh/docs/eino/core_modules/eino_adk/agent_hitl/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose/interrupt.go`、`resume.go`、`checkpoint.go`
