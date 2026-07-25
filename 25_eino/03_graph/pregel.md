# Pregel:有环图为何能跑

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/pregel.go`、`dag.go`、`graph.go`、`graph_run.go`、`graph_compile_options.go`
> 配套:[state_pregel.md](./state_pregel.md)(State + Pregel 如何共同支撑 ReAct)、[react_agent.md](./react_agent.md)(ReAct agent 设计)。
> 本文聚焦:**Pregel 是什么、Eino 如何用两种通道与超步循环实现有环图执行**。

## 0. 一句话定位

Eino 的 Graph 默认运行在 **Pregel 模式**--一种"顶点为中心、按超步(superstep)迭代、节点间靠通道传消息"的执行模型。它允许图中存在环(如 ReAct 的"模型↔工具"往复),由图运行器逐超步驱动,而非在业务代码里写 `for` 循环。无环的 DAG 模式是另一种运行形态,编译期即拒绝环。

## 1. Pregel 是什么

Pregel 是 Google 2010 年提出的大规模图计算系统(论文《Pregel: A System for Large-Scale Graph Processing》),核心是一套 **BSP(Bulk Synchronous Parallel,整体同步并行)** 执行模型。Eino(及 LangGraph 等)借用的是其**执行思想**,并非真的在跑分布式系统。四个核心机制:

1. **顶点为中心(Think like a vertex)**:不写"遍历整张图"的循环,而是给每个顶点写一段 `compute()` 逻辑,由图引擎决定何时调度谁。
2. **超步 + 屏障同步**:执行分成一轮轮 superstep,每轮所有被激活的顶点并行跑 `compute()`,一轮结束处有全局屏障(barrier),全部完成后才进入下一轮。
3. **消息传递**:顶点在 superstep S 给别的顶点发消息,这些消息在 **superstep S+1** 才被对方收到。顶点之间不直接调用,靠消息解耦。
4. **触发与终止**:顶点收到消息即被激活;无消息可处理时"投票停止",全局所有顶点停止且无在途消息时,计算结束。

### 1.1 四机制图示

**图一:顶点为中心 -- 不写循环,只写每个顶点的 compute()**

```
  命令式(你写循环)                  Pregel(你写顶点,引擎写循环)
  ────────────────                  ───────────────────────────
  for !done {                       A.compute = 收到消息->算->发消息
    跑A()                            B.compute = 收到消息->算->发消息
    if ... { 跑B() }                 C.compute = 收到消息->算->发消息
    ...                             // 没有 for。何时调 A/B/C 由引擎决定
  }
```

**图二:超步时间轴(三个顶点 A/B/C,消息在屏障间的"在途消息池"里传递)**

```
                A                 B                 C
                ─                 ─                 ─

 ▶ S0     ┌─────────┐
          │compute()│        idle              idle
          │ 初始消息 │
          │ 发->B,->C │
          └─────────┘
 ══════════════════ 屏障(barrier)═════════════════════════
   在途消息池:    [->B]  [->C]            ← S0 发出, S1 才送达
 ═════════════════════════════════════════════════════════
                          ▼                  ▼
 ▶ S1     idle      ┌─────────┐       ┌─────────┐
                    │compute()│       │compute()│   ◀ B、C 同时激活 = 并行
                    │ 收A消息 │       │ 收A消息 │
                    │ 发->C    │       │ halt ✓  │   ◀ C 处理完,投票停止
                    └─────────┘       └─────────┘
 ══════════════════ 屏障 ═════════════════════════════════
   在途消息池:           [->C]              ← B 发出, S2 送达
 ═════════════════════════════════════════════════════════
                                            ▼
 ▶ S2     idle       halt ✓         ┌─────────┐
                                    │compute()│   ◀ 收到B消息, 重新激活
                                    │ halt ✓  │
                                    └─────────┘
 ══════════════════ 屏障 ═════════════════════════════════
   在途消息池:    (空)
 ═════════════════════════════════════════════════════════

 ▶ S3    halt ✓     halt ✓          halt ✓      ◀ 全部 halt + 在途空
                                                       => END 计算结束
```

四机制对照:

- **① 顶点为中心**:A/B/C 三列各有自己的 `compute()` 框,互不调用(见图一)。A 不知 B 何时跑,B 不知 C 何时跑。
- **② 超步 + 屏障**:`S0`/`S1`/`S2` 是三个 superstep,`═══屏障═══` 保证本步所有激活顶点全跑完、消息全入池才进下一步。S1 里 B、C **同一行同时跑**即"每轮并行"。
- **③ 消息 S -> S+1**:关键看**在途消息池**。S0 里 A 发的 `[->B][->C]` 不立刻到达,停在屏障间的池子里,**S1 开头才送达**(两个 ▼);B 在 S1 发的 `[->C]` 同样停到 S2 才到 C。顶点间从不直接调用,消息在池子里"隔一步"才被收到。
- **④ 触发与终止**:每个 ▼ 表示"收到消息才激活"--没收到消息的列为 `idle`;C 在 S1 处理完 `halt ✓`(投票停止),S2 又收到 B 消息故**重新激活**再 halt;到 S3 池子空 + 三顶点全 `halt ✓` => END。

> 循环不是写出来的,是"顶点互相发消息 + 引擎一轮轮调度"自然转出来的。

这四个机制恰好对应 agent 循环的需求:节点 = 顶点,`compute()` = 节点 endpoint,消息 = 通道里的值,激活 = 触发,终止 = 走到 END。下面看 Eino 如何落地。

## 2. 两种运行模式:Pregel vs DAG

`graph.go:46-48` 定义两种运行类型:

```go
// runTypePregel ... Can have cycles in graph. Compatible with NodeTriggerType.AnyPredecessor.
runTypePregel graphRunType = "Pregel"
// runTypeDAG ... directed acyclic graph ... Compatible with NodeTriggerType.AllPredecessor.
runTypeDAG     graphRunType = "DAG"
```

编译时按触发模式选择运行类型与通道构造器(`graph.go:680-690`):

```go
runType := runTypePregel                       // 默认 Pregel
cb := pregelChannelBuilder
if (opt != nil && opt.nodeTriggerMode == AllPredecessor) || isWorkflow(g.cmp) {
    runType = runTypeDAG                        // AllPredecessor 或 Workflow -> DAG
    cb = dagChannelBuilder
}
```

二者关键差异:

| 维度 | Pregel 模式 | DAG 模式 |
|---|---|---|
| 是否允许环 | **允许**(`graph.go:46`) | 拒绝,编译期 `findLoops` 检测,有环报 `DAGInvalidLoopErr`(`graph.go:1128`) |
| 触发模式 | `AnyPredecessor`(任一前驱就触发) | `AllPredecessor`(所有前驱就绪才触发) |
| 通道类型 | `pregelChannel`(`pregel.go:25`) | `dagChannel`(`dag.go:50`) |
| 步数上限 | 必须有 `MaxRunSteps` 兜底(`graph.go:884`) | 禁止设置(`graph.go:881`) |
| 默认 eager | 否 | 是(`graph.go:694`) |
| 适用 | ReAct 等有环迭代 | 固定 DAG 流水线、Workflow |

> Chain / Workflow 不接受 `WithNodeTriggerMode` 选项(`graph.go:682-685`):Chain 强制 Pregel 语义,Workflow 强制 DAG。

为什么需要两种?有环图必须靠"超步迭代 + 步数封顶"驱动,而无环图可以按拓扑序一次性跑完,且能用 `AllPredecessor` 做精确的 join 语义(等所有前驱到齐)。把两者分开,既能让 ReAct 跑起来,又不让普通流水线背上迭代开销与死循环风险。

## 3. 拓扑如何编码"环"

`graph` 结构把边分成两类(`graph.go:57-61`):

```go
type graph struct {
    nodes        map[string]*graphNode
    controlEdges map[string][]string   // 控制边:决定"何时触发"
    dataEdges    map[string][]string   // 数据边:决定"数据从哪来"
    branches     map[string][]*GraphBranch
    ...
}
```

控制边管"触发",数据边管"取值"。编译时据此构造每个节点的前驱表(`graph.go:759-783`):

```go
dataPredecessors    := make(map[string][]string)
controlPredecessors := make(map[string][]string)
// 遍历 controlEdges / dataEdges / branches,填充两张前驱表
```

**环不是用普通 `AddEdge` 画的,而是用"指向回上游的分支"画的**。以 ReAct 为例(`flow/agent/react/react.go`):

```
普通边:  START ──▶ chat                     (react.go:353)
         direct_return ──▶ END              (react.go:448)

分支①:   chat ──▶ { tools, END }            (react.go:378)
分支②:   tools ──▶ { chat, direct_return }  (react.go:428)   ← 回边
```

注意没有 `AddEdge(tools, chat)`。`chat ↔ tools` 的环完全由**分支②的 endNode 包含 `chat`** 构成--分支在运行时按条件把控制权路由回上游节点。普通边是确定后继,分支是条件后继(且可选回上游)。这就是"带环图"在拓扑层的编码方式。

## 4. 触发模型:AnyPredecessor vs AllPredecessor

每个节点编译后对应一个 `chanCall`(`graph_run.go:31`):

```go
type chanCall struct {
    action          *composableRunnable   // 节点的执行体(即 compute())
    writeTo         []string              // 数据后继:把输出写到它们的通道
    writeToBranches []*GraphBranch        // 分支后继:按条件选写谁
    controls        []string              // 受谁的控制边约束(branch must control)
    preProcessor, postProcessor *composableRunnable
}
```

`runner` 持有全部节点的订阅表与前驱表(`graph_run.go:43-48`):

```go
type runner struct {
    chanSubscribeTo     map[string]*chanCall
    successors          map[string][]string
    dataPredecessors    map[string][]string
    controlPredecessors map[string][]string
    ...
}
```

触发模式差异的**机械本质在于通道实现**。通道接口(`graph_manager.go:29`)有 `reportValues` / `reportDependencies` / `reportSkip` / `get` 等方法,两种通道实现得截然不同:

### 4.1 `pregelChannel`:有值就触发

```go
// pregel.go:25
type pregelChannel struct {
    Values      map[string]any   // key=前驱名, value=该前驱本次产出
    mergeConfig FanInMergeConfig
}

// pregel.go:48  上游产出全写入,不做依赖追踪
func (ch *pregelChannel) reportValues(ins map[string]any) error {
    for k, v := range ins { ch.Values[k] = v }
    return nil
}

// pregel.go:90  永不跳过;reportDependencies 是空操作
func (ch *pregelChannel) reportSkip(_ []string) bool { return false }
func (ch *pregelChannel) reportDependencies(_ []string) {}

// pregel.go:55  读取并清空;多个值则合并
func (ch *pregelChannel) get(...) (any, bool, error) {
    if len(ch.Values) == 0 { return nil, false, nil }   // 无值 -> 不触发
    defer func() { ch.Values = map[string]any{} }()      // 一步一清
    ...                                                  // 多值 -> mergeValues
}
```

`Values` 非空即返回 `true` 触发节点--**任一前驱写了值就触发**,正是 `AnyPredecessor`。没有"等所有前驱"的概念,所以天然支持环:下游不关心上游是否还会再来消息,来一条就跑一轮。

### 4.2 `dagChannel`:所有前驱就绪才触发

```go
// dag.go:42
type dependencyState uint8
const (
    dependencyStateWaiting  dependencyState = iota
    dependencyStateReady
    dependencyStateSkipped
)

// dag.go:50
type dagChannel struct {
    ControlPredecessors map[string]dependencyState   // 逐个前驱记状态
    DataPredecessors    map[string]bool
    Skipped             bool
    Values              map[string]any
    ...
}
```

`dagChannel` 给**每个控制前驱**维护一个状态机(Waiting/Ready/Skipped),`reportDependencies` 标记 Ready,只有当所有控制前驱都到位(或被跳过)时 `get` 才返回值--这正是 `AllPredecessor` 的 join 语义。它需要知道前驱总数,因此无法表达"前驱会反复触发"的环。

> 一句话对比:`pregelChannel` 是个**值袋子**,来一个就触发;`dagChannel` 是个**依赖追踪器**,凑齐才触发。前者允许环,后者拒绝环。

## 5. 数据载体:消息在 superstep 间传递

`pregelChannel.Values` 就是 Pregel 里"消息"的载体。它的"一步一清"语义(`pregel.go:60` 的 `defer`)正是 BSP 的体现:

- **superstep S**:节点 `compute()` 跑完,把输出经 `writeTo` / `writeToBranches` 用 `reportValues` 写入后继的 `pregelChannel.Values`。
- **屏障**:本步所有节点跑完,通道里有待读消息。
- **superstep S+1**:后继节点 `get` 读出并清空通道,作为本步输入。

所以"消息在 S 发出、S+1 收到"不是比喻,是 `Values` 的写入/读取被屏障隔开两步的直接结果。节点间从不直接调用,只通过通道解耦。

## 6. superstep 主循环

图运行器的主循环(`graph_run.go:241`):

```go
// graph_run.go:131
maxSteps := r.options.maxRunSteps
...
// graph_run.go:241
for step := 0; ; step++ {
    // graph_run.go:249  环的兜底
    if !r.dag && step >= maxSteps {
        return nil, newGraphRunError(ErrExceedMaxSteps)
    }
    err = tm.submit(nextTasks)                                  // :257  跑本轮就绪节点
    ...
    nextTasks, result, isEnd, err = r.calculateNextTasks(ctx, completedTasks, isStream, cm, optMap)  // :309
}
```

每一步:

1. `submit`:执行本轮所有就绪节点(其通道已有值)。
2. 节点完成后,`resolveCompletedTasks` 收集输出与控制信号(`graph_run.go:711`)。
3. 按 `writeTo` / `writeToBranches` / `controls` 把输出写入后继通道,更新依赖(`updateAndGet`,`graph_run.go:715`)。
4. `calculateNextTasks`:扫描各节点通道,`get` 返回 `true` 的即为下一批就绪节点。
5. `isEnd`(到 END)或无下一批 -> 结束;否则进入下一 superstep。

屏障在哪?不在显式的 `sync.WaitGroup`,而在于 `submit` 是**同步等待本轮所有任务完成**才返回,再 `calculateNextTasks` 算下一步--"跑完一轮才算下一步"就是屏障。

## 7. 终止与兜底

- **正常终止**:某轮 `calculateNextTasks` 算出 `isEnd`(路由到了 `compose.END`),或下一批就绪节点为空,循环退出。
- **死循环兜底**:`MaxRunSteps`(`graph_compile_options.go:53-58`,注释明言 "useful to prevent infinite loops in graphs with cycles")。Pregel 模式默认值 `len(chanSubscribeTo) + 10`(`graph.go:884`,即节点数 + 10);ReAct 用 `config.MaxStep` 覆盖(默认 12)。DAG 模式因无环,禁止设置该值(`graph.go:881`)。
- **与原版 Pregel 的差异**:原版靠顶点"投票停止"自然收敛;agent 循环不一定自然停(模型可能一直要调工具),所以 Eino 用步数硬上限替代,撞上限报 `ErrExceedMaxSteps`。

## 8. 时序图:一次 think-act 迭代

横轴为节点,纵轴为时间,每段横线是一个 superstep,`═══屏障═══` 是步间同步点。注意消息②在 S0 发出、S1 才收到。

```
  START       chat          tools         END
   │           │              │            │
   │ 消息①     │              │            │
   ├──────────▶│              │            │
   │       [S0] compute        │            │     ← superstep 0
   │           │  消息②       │            │       chat 跑模型,有 ToolCall
   │           ├─────────────▶│            │
   │       ══════════ 屏障 ═══════════════════     本步全部完成才进下一步
   │           │           [S1] compute    │     ← superstep 1
   │           │  消息③       │            │       tools 执行工具
   │           │◀─────────────┤            │       (消息② S0 发出, S1 收到)
   │       ══════════ 屏障 ═══════════════════
   │       [S2] compute        │            │     ← superstep 2
   │           │  无 ToolCall  │            │       chat 再跑模型,最终答案
   │           │  消息④        │            │       分支① -> END,不向 tools 发消息
   │           └──────────────────────────▶│
   │       ══════════ 屏障 ═══════════════════
   │           │              │            │     ← superstep 3
   │          停止            停止         完成     无在途消息 + 到 END -> 全局停止
```

把四个机制对到图上:

- **顶点为中心**:每个 `[Sk] compute` 是节点自跑,互不调用,只发消息。
- **超步 + 屏障**:`S0`/`S1`/`S2` 是 superstep,中间 `═══屏障═══` 保证本步全跑完、消息全投递,才进下一步。
- **消息 S -> S+1**:消息②在 S0 写入 `tools` 的 `pregelChannel.Values`,S1 才被 `get` 读出。
- **触发与终止**:节点收消息即激活;S2 的 chat 不再向 tools 发消息(改发 END),故 S3 里 tools 收不到消息、不激活,全局停止。

## 9. 与 State / ReAct 的关系

Pregel 解决的是"有环图怎么执行";要让 ReAct 真正可用,还需要 **State** 配合--跨超步累积对话历史,让每一轮模型调用都能看到之前所有消息。State 经 `WithGenLocalState` 注入、经 `WithStatePreHandler` 在节点执行前读写(`state.go`)。State + Pregel 的组合、以及完整的 ReAct 拓扑,见 [state_pregel.md](./state_pregel.md) 与 [react_agent.md](./react_agent.md)。

Pregel 带来的额外收益:因为每一"轮"就是普通的图 superstep,图层的能力**自动适用于循环内部**--

- **流式**:节点流式输出沿通道传递,分支用 `NewStreamGraphBranch` 边 peek 边转发。
- **中断/恢复**:`interruptBeforeNodes` / `interruptAfterNodes` 插在 `calculateNextTasks` 与 `submit` 之间(`graph_run.go:223`、`:317`),可在"工具执行前"暂停待人审批,恢复时从检查点续跑。
- **检查点**:每个 superstep 的通道值与 State 可持久化,断点续跑。

这些能力的统一挂载点正是"把循环从业务代码挪到执行引擎"的回报。

## 10. 小结

| 设计点 | 手段 | 位置 |
|---|---|---|
| 允许环 | Pregel 运行模式 + `AnyPredecessor` | `graph.go:46`、`:680` |
| 拒绝环 | DAG 运行模式 + `findLoops` | `graph.go:48`、`:1128` |
| 编码回边 | 分支的 endNode 指回上游 | `react.go:428` |
| 触发差异 | `pregelChannel`(值袋)vs `dagChannel`(依赖追踪) | `pregel.go:25`、`dag.go:50` |
| 消息传递 | `Values` 一步一写一读,屏障隔开两步 | `pregel.go:48`、`:55` |
| 超步循环 | `for step` + `submit` + `calculateNextTasks` | `graph_run.go:241` |
| 死循环兜底 | `MaxRunSteps`(默认节点数 + 10) | `graph.go:884` |

一句话:Pregel 在 Eino 里 = `pregelChannel`(值袋式通道)+ `AnyPredecessor`(任一前驱即触发)+ superstep 主循环(逐步 submit/calculateNextSteps)+ `MaxRunSteps` 兜底。它把"模型↔工具"的往复编码成节点间通过通道传值、引擎逐超步推进,从而业务代码不必写 `for`,还能白拿流式、中断、检查点能力。

> 配套最小实现见 [`demo/03_pregel_compile/pregel_compile.md`](./demo/03_pregel_compile/pregel_compile.md)--一份从零写的最小 Pregel MVP(含 Compile 阶段 + 可中断屏障)。
