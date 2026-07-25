# Pregel MVP 增量 1~3: Checkpoint + Interrupt/Resume + State

> 源码：
> - [`main.go`](./main.go)：Pregel 引擎核心代码（消息、顶点、图、编译、运行、State）
> - [`checkpoint.go`](./checkpoint.go)：Checkpoint 机制（快照结构、存储接口、中断类型、State 深拷贝）
> - [`demo.go`](./demo.go)：演示场景（顶点实现、Resume 函数、main 函数）
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表（概念定义与辨析）
>
> 上游:[`../01_pregel_demo`](../01_pregel_demo/README.md)(Pregel 四机制 + Compile,本 demo 在其上**只增不改**)
> 配套概念文档:[`../pregel.md`](../pregel.md)
>
> 本文仅介绍新增的机制 ⑥ Checkpoint + ⑦ State;Pregel 前五机制的完整拆解见上游 README,此处不再重复。

## 一、概述

本 demo 在 01_pregel_demo 基础上逐步引入三个增量:

| 增量 | 机制 | 新增代码 | 核心能力 |
|------|------|---------|---------|
| 1 | Checkpoint | ~120 行 | 每超步屏障后快照全图状态,崩溃后从断点续跑 |
| 2 | Interrupt/Resume | ~40 行 | 顶点主动暂停(如等待人工审批),Resume 后继续 |
| 3 | State | ~58 行 | 图级共享可变状态,所有顶点可读写,checkpoint 保存/恢复 |

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/02_pregel_checkpoint_demo
go run .
```

### 场景一：正常 ReAct + State

```
── superstep 0 ── 活跃顶点: [model]
  [model] TokenCount += 150 -> 150

── superstep 1 ── 活跃顶点: [calc search]
  [calc] TokenCount += 30 -> 180
  [search] TokenCount += 30 -> 210

── superstep 2 ── 活跃顶点: [model]
  [model] TokenCount += 150 -> 360
[state] TokenCount = 360
```

model 和两个 tool 顶点各自累加 TokenCount,并行顶点(search ∥ calc)在 mutex 下串行化写入。

### 场景五：State checkpoint 恢复

```
Run 1:
  superstep 0: model → TokenCount = 150, 存入 checkpoint
  superstep 1: flaky_search 崩溃

Run 2:
  从 checkpoint 恢复 → State.TokenCount = 150 被保留
  superstep 1: calc + flaky_search → TokenCount = 180 (从 150 继续累加)
  superstep 2: model → TokenCount = 330
  [state] TokenCount = 330
```

**如果没有 State checkpoint 恢复,Run 2 的 TokenCount 会从 0 开始算,得到 180。有了 State 恢复,从 150 继续累加,得到 330。** 这就是 State 进 checkpoint 的意义。

`go vet` 通过,`go run -race` 无数据竞争。

## 三、Pregel 模型与一致性快照

这是增量 1 的核心论点。

分布式系统为计算过程获取一致性快照的经典困难在于:各节点并行执行、消息仍在传递途中,**不存在"全局静止"的时刻**——Chandy-Lamport 算法正是为此设计,需要在执行过程中录制消息,以拼接出一致割(consistent cut)。

BSP 模型中,该问题由执行模型结构性地解决:

```
 超步 S-1                超步 S
┌───────────┐  屏障   ┌───────────┐
│ 顶点全停齐 │ ══════ │ 顶点全停齐 │
│ 消息全在池 │ ══════ │ 消息全在池 │
└───────────┘ ══════ └───────────┘
                  ▲
        一致性切点由模型结构保证,无需额外算法
```

屏障刚通过的时刻满足三个条件:所有 `Compute` 均已返回(无 in-flight 计算)、本步产出已全部完成路由并写入 `next`(不存在已发出但尚未到达的消息)、下一步尚未开始。此时 **`current` 单个 map 即构成全图状态的全部内容**,对其快照即完成对全图状态的快照。

demo 的 checkpoint 实现因此得以保持精简——这并非功能上的简化,而是执行模型将"确定一致性切点"这一最困难的部分转化为结构必然。

## 四、与 eino checkpoint 的结构对比

eino 的 `checkpoint` 结构(`compose/checkpoint.go:107`)包含 7 个字段,逐一对照:

| eino 字段 | 作用 | demo 对应 |
|---|---|---|
| `Channels` | 各通道中的在途消息 | `Current` 单个 map 覆盖(demo 为单通道) |
| `Inputs` | 各节点待处理的输入 | 同上——demo 中"顶点 -> 消息列表"本身即输入表 |
| `State` | 跨顶点共享 State | `State *GraphState`(增量 3 已实现) ✅ |
| `SkipPreHandler` / `RerunNodes` | 恢复时需重跑 / 跳过 preHandler 的节点 | `RerunNodes`(增量 2 已实现);`SkipPreHandler` 未实现 |
| `SubGraphs` | 子图的嵌套断点 | 未实现(demo 无子图) |
| `InterruptID2Addr` / `InterruptID2State` | 动态中断信号的寻址与状态 | 未实现(简化版 InterruptInfo) |

**demo 的三个核心字段(Step + Current + State)已覆盖 eino checkpoint 的主体骨架**;其余 4 个字段各自对应一项尚未实现的机制,将随后续增量逐步补齐。

### 两种写入时机:逐超步 vs 仅中断时

| | demo | eino | LangGraph |
|---|---|---|---|
| 何时写 checkpoint | 每个屏障通过后 | **仅在 interrupt 时**(`graph_run.go:561` 与 `:701`) | 每个 superstep |
| 主要用途 | 崩溃恢复(断点续跑) | HITL 人机中断恢复 | 两者兼有,另支持 time travel |
| 正常结束 | 主动删除断点(故 store 增加 `Delete`) | 不涉及(断点随 resume 消耗) | 保留历史 |

## 五、增量 3: State 机制详解

### 5.1 核心机制 vs 应用层选择

State 的**核心机制**只有一个:

> 所有顶点通过 `ProcessState` 读写同一个 struct 实例,mutex 保护并发安全,checkpoint 保存/恢复。

至于 struct 里放什么字段——`TokenCounter` 还是 `Messages`——是**应用层的选择**,不是机制本身:

| 层面 | 例子 | 说明 |
|------|------|------|
| **机制** | `ProcessState` + mutex + checkpoint 深拷贝 | 引擎层面,与字段无关 |
| **应用** | `TokenCounter` | demo 选择:展示机制,最少代码 |
| **应用** | `State.Messages` + `RemainingIterations` | eino ADK 选择:ReAct Agent 的运行时上下文 |

demo 用 `TokenCounter` 展示机制即可,无需引入 eino ADK 层面 `State.Messages` 累积的复杂度。

### 5.2 eino 的 State 真实用法

eino ADK 的 ReAct Agent 用 State 做消息累积(`State.Messages`),所有节点往同一个 `[]Message` 追加——这是"沿边传消息"之外的**第二条数据通道**:

| 通道 | 作用域 | 生命周期 | 可变性 |
|------|--------|---------|--------|
| **沿边传**(Channel) | 沿边传递,前驱→后继 | 一个 superstep | 不可变(发出后不再改) |
| **写进 State** | 全图共享,所有节点可读写 | 整个 Run 生命周期 | 可变(mutex 保护) |

此外 eino 还用 State 做循环次数控制(`RemainingIterations`)、工具直接返回标记(`ReturnDirectlyToolCallID`)等。这些属于 ADK 层面的设计选择,不是 compose 引擎层面的机制。

### 5.3 图级共享 State vs 顶点私有字段

| | 顶点私有字段 | 图级共享 State |
|---|---|---|
| **demo 例子** | `ModelVertex.step` | `GraphState.TokenCount` |
| **谁定义** | 顶点 struct 的字段 | `WithGenLocalState` 在编译时声明 |
| **谁能访问** | 只有该顶点的 `Compute` | 所有顶点通过 `ProcessState` |
| **存在哪** | 顶点 struct 实例 | context(`ctx.Value(stateKey{})`) |
| **并发安全** | 不需要(同一时刻只有一个 Compute 在写) | 需要 mutex(并行顶点同时读写) |
| **checkpoint** | eino 不保存 | eino 深拷贝进 `checkpoint.State` |
| **本质** | 顶点的内部实现细节 | 图的运行时全局状态 |

### 5.4 GenLocalState（工厂函数）

编译时传入的是"造 State 的函数",不是 State 实例本身:

```go
c, _ := g.Compile(WithGenLocalState(func() *GraphState {
    return &GraphState{TokenCount: 0}    // 每次调用都 new 一个新的
}))
```

用工厂函数而非直接传实例的原因:**同一个 Compiled 可能被 Run 多次,每次 Run 需要一个全新的 State 实例**(不能让两次 Run 共享同一个 `TokenCount`)。

`Gen` = Generate,不是传入。

### 5.5 State 生命周期

```
编译时: Compiled { genState: func() *GraphState { ... } }
        ↑ 存的是函数(工厂),不是实例

Run 时: state = genState()  →  &GraphState{TokenCount: 0}  ← 造实例
        ctx = context.WithValue(ctx, stateKey{}, state)
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
     model      search       calc      ← 并行 Compute
     都从 ctx.Value(stateKey{}) 拿到同一个 state 指针
                    │
         └──────────┼──────────┘
                    ▼
              Run 返回,state 被 GC
```

**共享的根源:Run 只造一次,所有顶点拿到同一个 `*GraphState` 指针。**

### 5.6 实现代码

```go
// GraphState 图级共享状态
type GraphState struct {
    mu         sync.Mutex
    TokenCount int
}

// ProcessState 并发安全地访问 GraphState
func ProcessState(ctx context.Context, fn func(*GraphState)) {
    s, ok := ctx.Value(stateKey{}).(*GraphState)
    if !ok || s { return }  // 图未声明 State,静默跳过
    s.mu.Lock()
    defer s.mu.Unlock()
    fn(s)
}

// WithGenLocalState 编译期选项:注册工厂函数
func WithGenLocalState(gen GenLocalState) CompileOption {
    return func(c *Compiled) { c.genState = gen }
}

// Run 中:初始化 State
if c.genState != nil {
    state = c.genState()
    ctx = context.WithValue(ctx, stateKey{}, state)
}

// Checkpoint 中:深拷贝 State
func cloneState(s *GraphState) *GraphState {
    if s == nil { return nil }
    s.mu.Lock()
    defer s.mu.Unlock()
    cp := *s
    cp.mu = sync.Mutex{}
    return &cp
}
```

## 六、实现要点:文件结构与串联

```
checkpoint.go           Checkpoint + State 机制
├── Checkpoint          快照结构(含 State 字段)
├── CheckPointStore     存储接口
├── InterruptInfo       中断信息（增量 2）
├── InterruptError      中断错误（增量 2）
├── Interrupt()         中断函数（增量 2）
├── memoryStore         内存实现(深拷贝含 State)
├── cloneCheckpoint()   深拷贝 Checkpoint(含 State)
└── cloneCurrent()      深拷贝消息池

main.go                 Pregel 引擎核心
├── Message              消息结构
├── Vertex               顶点接口
├── Graph                图构建
├── Compiled             编译结果(含 genState)
├── Compile()            编译函数
├── Run()                运行函数(State 初始化/恢复/保存)
├── GraphState           图级共享状态(增量 3)
├── ProcessState()       并发安全访问(增量 3)
├── WithGenLocalState()  编译选项(增量 3)
├── cloneState()         State 深拷贝(增量 3)
├── taskManager          屏障管理
└── 辅助函数             环检测、路由等

demo.go                  演示场景
├── ModelVertex          模型顶点(含 ProcessState 调用)
├── ToolVertex           工具顶点(含 ProcessState 调用)
├── FlakyToolVertex      不稳定工具顶点
├── SlowVertex           慢顶点
├── ApprovalToolVertex   审批工具顶点（增量 2）
├── Resume()             恢复函数（增量 2）
└── main()              五个演示场景
```

**串联关系：**

```
checkpoint.go                 main.go                  demo.go
────────────────────────────────────────────────────────────────
Checkpoint          ──────►  Run 中使用
  .State            ──────►  cloneState() 深拷贝
CheckPointStore     ──────►  Compiled.store
InterruptError      ──────►  Run 中检测        ◄─────  Interrupt()
InterruptInfo       ──────►  Run 中保存        ◄─────  顶点返回
GraphState          ──────►  ProcessState()    ◄─────  顶点调用
genState            ──────►  Run 中初始化

                                              demo.go 中的顶点
                                              实现 Vertex 接口
                                                    │
                                                    ▼
                                              main.go 中的
                                              Vertex 接口定义
```

## 七、语义边界与注意事项

1. **断点以屏障为粒度,语义为 at-least-once**。失败超步内已执行成功的顶点会被重复执行。顶点须具备幂等性;具有副作用的顶点(写库、发送消息)应自行实现去重。该语义与 LangGraph 逐超步 checkpoint 一致。
2. **仅在正常结束时清除断点**。崩溃、ctx 取消、maxSteps 强制停止时,断点均保留——这三类"非正常退出"因此都支持恢复执行。
3. **顶点私有状态不纳入快照**。`ModelVertex.step` 记录于结构体字段,不在快照范围内。**图级共享 State(`GraphState`)会纳入快照**,这是增量 3 解决的问题。顶点私有状态的跨进程恢复属于另一个机制(RerunNodes + Inputs 重跑),不在本增量范围内。
4. **store 为内存实现,未涉及序列化**。生产环境需要持久化(Redis/DB),则必须处理类型注册与流转换——即 eino `Serializer` / `schema.RegisterName` 所解决的问题。**序列化涉及持久化存储,超出 demo 教学范围,不在后续增量规划中**。
5. **一个 ID 对应一条执行线**。同 ID 并发执行会相互覆盖断点。
6. **ProcessState 在图未声明 State 时静默跳过**。顶点无需关心 State 是否存在,同一顶点代码在有无 State 的图中均可运行。

## 八、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `Checkpoint{Step, Current, State}` | `checkpoint`(`checkpoint.go:107`) | demo 覆盖 Channels+Inputs+State 骨架 |
| `CheckPointStore` / `memoryStore` | `core.CheckPointStore`(`checkpoint.go:52`) | demo 增加 `Delete`(逐超步写入,故需清除) |
| `WithCheckPointStore` | 同名(`checkpoint.go:60`) | 编译期装配存储 |
| `GraphState` + `ProcessState` | `ProcessState[S]`(`state.go:165`) | demo 用具体类型,eino 用泛型 |
| `WithGenLocalState(func() *GraphState)` | `WithGenLocalState[S]`(`state.go:30`) | 工厂函数模式一致 |
| `stateKey{}` + `context.WithValue` | `stateKey{}` + `context.WithValue`(`state.go:32`) | context 传递方式一致 |
| `cloneState()` 深拷贝 | `deepCopyState()`(`graph_run.go:572`) | eino 用序列化深拷贝,demo 用值拷贝 |
| `InterruptError` / `Interrupt()` | `Interrupt()`(`interrupt.go`) | 简化版:无 StatefulInterrupt/CompositeInterrupt |
| `Resume()` | `Resume()` / `ResumeWithData()`(`resume.go`) | 简化版:无层级寻址 |
| 循环前的恢复 | `restoreCheckPointState`(`graph_run.go:173-184`) | 存在断点则跳过初始化 |
| 屏障后 `store.Set` | `handleInterrupt` 内的 `checkPointer.set`(`graph_run.go:561/701`) | 时机不同:demo 逐超步写入,eino 仅在 interrupt 时写入 |
| 未实现:序列化 / 流转换 | `Serializer`、`convertCheckPoint` | demo 无流式、消息为纯值,无需处理 |

## 九、后续规划

| 增量 | 内容 | 状态 |
|------|------|------|
| 增量 1 | Checkpoint（每超步快照 + 断点续跑）| ✅ 已完成 |
| 增量 2 | Interrupt/Resume（主动暂停 + 人工审批）| ✅ 已完成 |
| 增量 3 | State（图级共享状态 + ProcessState + checkpoint 集成）| ✅ 已完成 |
| 增量 4 | Streaming（四范式:Invoke/Stream/Collect/Transform）| 📋 规划中 |
| 增量 5 | DAG Channel（skip 传播 + AllPredecessor 触发）| 📋 规划中 |

**说明**：序列化（持久化到 Redis/DB）涉及生产环境存储,超出 demo 教学范围,不在增量规划中。

## 十、总结

**屏障提供了一致性切点,`current` 单个 map 即构成全图状态——checkpoint 的全部实现可概括为:屏障后写入、循环前读取、结束后清除。State 的核心机制同样精简:Run 开头造实例放进 ctx,顶点通过 ProcessState 加锁读写,checkpoint 深拷贝保存/恢复。** 其余复杂度(序列化、中断寻址、子图嵌套)均属于后续增量需要补齐的机制,而非 Pregel 模型本身的成本。
