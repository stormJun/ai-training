# Pregel Stream Demo: 增量 4 Streaming

> 源码：
> - [`main.go`](./main.go)：Pregel 引擎核心 + State + **StreamRun**（Transform 模式）
> - [`stream.go`](./stream.go)：**流基础设施**（StreamReader/Writer、Pipe、Copy、Merge、wrap、concat）
> - [`checkpoint.go`](./checkpoint.go)：Checkpoint 机制（不变）
> - [`demo.go`](./demo.go)：演示场景（顶点加 StreamCompute + 场景六 StreamRun）
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表（含 Streaming 术语）
>
> 上游：[`../04_pregel_checkpoint_demo`](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)（Checkpoint + Interrupt + State，本 demo 在其基础上新增增量 4）
>
> 本文仅介绍新增的机制 ⑧ Streaming；前七机制见上游文档。

## 一、概述

本 demo 在 04_pregel_checkpoint_demo 基础上新增 **Streaming** 能力（增量 4），约 350 行新增代码：

| 新增 | 内容 | 行数 |
|------|------|------|
| `stream.go` | 流基础设施：StreamReader/Writer、Pipe、wrap、concat、Copy(lazy)、Merge | ~220 |
| `main.go` | StreamVertex 接口、StreamRun 方法、mergeMessages/concatMsg | ~130 |
| `demo.go` | 各顶点 StreamCompute 实现、场景六 | ~70 |

核心能力：**端到端流式执行**。调用方调 `StreamRun`，逐块拿到最终输出流，中间经过 Copy（扇出）和 Merge（扇入）。

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/05_pregel_stream_demo
go run .
```

### 场景六：StreamRun 端到端流式

```
=== 场景六:StreamRun(流式执行)===

── stream superstep 0 ── 活跃顶点: [model]
  [model] 流式产出 ToolCalls=[search, calc]

── stream superstep 1 ── 活跃顶点: [calc search]

── stream superstep 2 ── 活跃顶点: [model]
  [search] 流式产出 Result: search(eino pregel)
  [calc] 流式产出 Result: calc(2+3)
  [model] 流式产出答案(分块): "done with 2 results: ..."
  [stream] 路由到 END,返回流给调用方

调用方逐块读取最终流:
  收到 chunk: Answer="done wit"
  收到 chunk: Answer="h 2 resu"
  收到 chunk: Answer="lts: [se"
  ... (共7块)
最终答案: done with 2 results: [search(eino pregel) calc(2+3)]
```

`go vet` 通过，`go run -race` 无数据竞争。

**观察要点：**

1. **流式分块输出**：调用方收到 7 个 chunk，逐块拼出完整答案。这是真实的流式，不是一次性返回。
2. **lazy 执行**：`[search]`/`[calc]` 的"流式产出"打印出现在 superstep 2，而非 superstep 1。因为 search/calc 的 goroutine 在 superstep 1 被 spawn（返回流 handle），但真正执行发生在 superstep 2 model 消费合并流时--数据流是 lazy 的，由下游 Recv() 驱动。
3. **Copy 扇出 + Merge 扇入**：model 的 ToolCalls 流 Copy 给 search 和 calc；search/calc 的结果流 Merge 回 model。

## 三、四范式与自动推导

### 四范式 = 2×2 矩阵

```
                 |  单值输出      |  流式输出
-----------------+----------------+----------------
  单值输入       |   Invoke       |   Stream
  流式输入       |   Collect      |   Transform
```

demo 的对应：

| 范式 | demo | 签名 |
|------|------|------|
| Invoke | `Compute` / `Run` | `(ctx, []Message) -> (Message, error)` |
| Transform | `StreamCompute` / `StreamRun` | `(ctx, *StreamReader[Message]) -> (*StreamReader[Message], error)` |
| Stream | 推导（Invoke + wrap） | 调用方单值入，引擎 wrap 输入成流 |
| Collect | 推导（Transform + concat） | 调用方流式入，引擎 concat 输出成单值 |

### 自动推导 = wrap + concat

两个原语让四种范式互通：

| 原语 | 作用 | 实现 |
|------|------|------|
| **wrap** | 单值 -> 流 | `StreamReaderFromArray([]T{val})`：长度1数组 + 下标遍历 |
| **concat** | 流 -> 单值 | 循环 `Recv()` 读所有 chunk，按类型合并 |

例如：只有 Invoke，推导 Transform = concat 输入流 + 调 Invoke + wrap 输出。

## 四、流基础设施（stream.go）

### 4.1 StreamReader / StreamWriter / Pipe

```go
// Pipe 创建一对 (reader, writer)，底层是 channel（缓冲1）
func Pipe[T any]() (*StreamReader[T], *StreamWriter[T])

// StreamWriter: Send 写 chunk，Close 结束流
// StreamReader: Recv 读 chunk（io.EOF 表示结束），Close 主动终止
```

StreamReader 有 4 种内部实现（`typ` 字段区分）：

| typ | 实现 | 用途 |
|-----|------|------|
| `readerTypeStream` | channel-based | Pipe 创建的流 |
| `readerTypeArray` | 数组+下标 | wrap 创建的流 |
| `readerTypeChild` | lazy 链表 | Copy 出来的子流 |
| `readerTypeMerged` | channel-based | Merge 的输出 |

### 4.2 扇出与扇入：为什么需要 Copy 和 Merge

场景一的图里，model 同时面对两个拓扑结构：

```
START ──▶ model ──┬──▶ search ──┐
                   │             ├──▶ model ──▶ END
                   └──▶ calc  ──┘
                   扇出          扇入
```

- **扇出（fan-out）**：一个节点的输出分给多个后继（model 的输出给 search 和 calc）
- **扇入（fan-in）**：多个前驱的输出汇入一个节点（search 和 calc 的结果汇回 model）

**单值模式下这俩很简单**，因为值是不可变的"死数据"，复制无成本：

| | 单值（Run 模式） | 做法 |
|---|---|---|
| 扇出 | `next["search"]=append(...,out)`<br>`next["calc"]=append(...,out)` | append 把值复制进两个 slice，各读各的 |
| 扇入 | `next["model"] = []Message{search结果, calc结果}` | 收成数组 |

**流式模式下这俩成了问题**，因为流是"活管道"，有状态，chunk 取走就没：

- **扇出问题**：model 产出一个流，直接给 search 和 calc 两个接收方。流里的 chunk 被先读的接收方取走，后读的拿空。**流只能被消费一次。**
- **扇入问题**：search 和 calc 各产一个流，但 model 的 StreamCompute 只收一个流。**两个流不能直接当一个用。**

所以流式下需要两个专门机制：

| | 流式（StreamRun 模式） | 机制 |
|---|---|---|
| 扇出 | 把一个流复制成多个独立管道，各读各的 | **Copy** |
| 扇入 | 把多个流合并成一个管道给消费者 | **Merge** |

**本质区别**：值是死数据，复制无成本（append 随便复制）；流是活管道，有状态，取走就没。这是 Copy 和 Merge 存在的根本理由。

### 4.3 Copy（扇出，lazy）

一个流复制成 n 个独立子流。**lazy 实现（对齐 eino）：sync.Once + 链表。**

```
源 ──Recv──▶ [elem0] ──next──▶ [elem1] ──next──▶ ... ──▶ [EOF]
               ▲                  ▲
            子流0.cur          子流1.cur
```

- 每个链表节点用 `sync.Once` 保证只从源读一次
- 谁先到谁触发读取，后来的读缓存
- 不预读整流，按需读
- 各子流独立前进（`cur` 指针各自维护）

```go
type cpElement[T any] struct {
    once sync.Once
    item streamItem[T]
    next *cpElement[T]
}

func (r *StreamReader[T]) Copy(n int) []*StreamReader[T]
```

### 4.4 Merge（扇入）

多个流合并成一个，chunk 按到达顺序交错。**goroutine-per-source 实现：**

```go
func MergeStreamReaders[T any](srs []*StreamReader[T]) *StreamReader[T]
```

每个源一个 goroutine 转发 chunk 到输出流，全部 EOF 时关闭输出。比 eino 的 `select`（手写 1-5 路 + reflect.Select）更简单，支持任意 N，非确定交错。

### 4.5 concat（流 -> 单值）

```go
func concatStreamReader[T any](sr, merge func([]T) T) (T, error)
```

循环 `Recv()` 读出所有 chunk，1 个直接返回，多个调 `merge` 合并。demo 的 `mergeMessages`：ToolCalls/Results 拼接，Answer 取最后非空（对应 eino string 拼接 / useLast 语义）。

## 五、StreamRun（Transform 模式）

### 5.1 与 Run 的核心区别

| | Run（Invoke） | StreamRun（Transform） |
|---|---|---|
| current/next 存 | `[]Message`（单值） | `[]*StreamReader[Message]`（流 handle） |
| 顶点走 | `Compute` | `StreamCompute` |
| 扇出 | append 到多个后继 | `Copy` |
| 扇入 | append 到 `[]Message` | `MergeStreamReaders` |
| 屏障同步 | Compute 完成 | StreamCompute 返回 handle（不是流消费完） |
| 数据流动 | 即时 | lazy，下游 Recv() 驱动 |
| checkpoint | 集成 | 不集成（超出范围） |

### 5.2 流 handle 跨 superstep 传递

StreamRun 的核心：流 handle 像单值一样存在 `next` 里，跨屏障传递。

```
superstep 0: model.StreamCompute -> 流 handle
              屏障:所有 StreamCompute 返回 handle(不等流消费完)
              next["search"] = [流 handle 的 Copy], next["calc"] = [流 handle 的 Copy]

superstep 1: search.StreamCompute(流 handle) -> 新流 handle
              next["model"] = [search 流, calc 流]  (扇入,待 Merge)

superstep 2: Merge([search 流, calc 流]) -> 合并流
              model.StreamCompute(合并流) -> 最终流 handle
              路由到 END -> 返回最终流给调用方
```

### 5.3 分支点的处理：Copy-for-peek

分支的 `Cond` 需要 `Message` 决定路由，但顶点产出的是流。解法：

```go
// 分支点:Copy 一份 concat 决定路由,另一份传给目标
copies := t.out.Copy(2)
msg := concatMsg(copies[0])        // 驱动流完整产出,得 Message 决定路由
targets := c.route(t.v.ID(), msg)
if 单一 END 目标:
    endStream = copies[1]          // 原流(另一份)返回给调用方
else:
    routeStreamTo(copies[1], targets, next)  // 多目标再 Copy
```

**Copy 保证原流数据不丢**：concat(copy1) 驱动流的完整产出（lazy Copy 缓存所有 chunk），copy2 读缓存即可。

### 5.4 屏障的语义变化

- **Run 模式**：屏障等所有 `Compute` 完成（同步，数据已产出）
- **StreamRun 模式**：屏障等所有 `StreamCompute` 返回 handle（异步，数据尚未流动）。真正的数据流动发生在下游 `Recv()` 或分支点 `concat` 时。

这是流式执行的关键：图的结构（流 handle 的连接）在 superstep 循环中瞬间建立，数据随后 lazy 流过。

## 六、语义边界与注意事项

1. **StreamRun 不集成 checkpoint**。流式 + checkpoint 需要 concatStream/restoreStream 在 checkpoint 时把流物化成单值、恢复时再变回流（eino 的 `streamConvertPair`）。超出 demo 范围。崩溃恢复仍由 Run + checkpoint 覆盖。
2. **分支点 concat 会驱动流完整产出**。因为 `Cond` 需要完整 `Message` 决定路由，分支点的流必须 concat（读完全部 chunk）。非分支路径保持 lazy。这是 demo 用 `Branch.Cond(Message)` 的代价--eino 的 `StreamGraphBranch` 用流式条件可避免，但更复杂。
3. **StreamCompute 必须 async**。启 goroutine 消费输入流、产出输出流，立即返回 handle。若同步（阻塞到流完成），会破坏 lazy 链路导致死锁。
4. **顶点步骤判定不靠私有字段**。`ModelVertex.StreamCompute` 不用 `m.step`（流式下跨进程会丢），而是看输入内容（有无 Results）。这与 State 增量的"顶点私有字段不进 checkpoint"一脉相承。
5. **Copy 的 lazy 特性**：消费者速度不同步时，慢的拖住缓存增长，但快的能读已缓存的部分。源只读一次。
6. **Merge 顺序非确定**：chunk 按到达顺序交错，不保证 search 结果在 calc 之前。需要顺序的场景应用 concat 或自定义合并。

## 七、简化说明：demo 对 eino 做了哪些简化

本 demo 的原则是"最少代码实现最核心机制"。以下逐项说明 demo 在哪些地方简化了 eino，eino 原本怎么做，demo 怎么做，简化了什么，为什么。

### 7.1 Merge 实现：select → goroutine-per-source

| | eino | demo |
|---|---|---|
| 做法 | `select` 同时监听多 channel；1-5 路手写 select 优化，6+ 路用 `reflect.Select` | 每个源启一个 goroutine 转发 chunk 到输出流，`sync.WaitGroup` 等全部 EOF |
| 代码 | ~80 行（含 select.go 的 receiveN 手写分支） | ~25 行 |
| 简化了什么 | select 的手写优化路径、reflect.Select 回退 | |
| 为什么 | demo 的 Merge 只用于 search+calc 两路扇入，goroutine-per-source 更直观、支持任意 N，足以展示"多流交错合并"的核心机制 |

### 7.2 分支点路由：StreamGraphBranch → Copy-for-peek（concat 决定）

| | eino | demo |
|---|---|---|
| 做法 | `NewStreamGraphBranch`：条件函数收 `*StreamReader[T]`，可**只读首个 chunk** 决定路由，流原样传给目标（不 concat 整流） | `Branch.Cond` 收 `Message`；分支点 `Copy(2)` 一份 `concat` 得 Message 决定路由，另一份传给目标 |
| 代码 | StreamGraphBranchCondition 类型 + 流式条件逻辑 | Copy-for-peek ~10 行 |
| 简化了什么 | 流式条件（基于首块决定，保持端到端 lazy） | |
| 代价 | demo 分支点必须 concat 完整流才能决定路由，破坏了该处的 lazy | |
| 为什么 | demo 的 `Branch.Cond(Message)` 与 Run 模式共用，不改签名最省代码；分支点 concat 在 demo 场景下可接受（model 输出就一两块） |

### 7.3 checkpoint 集成：streamConvertPair → 不集成

| | eino | demo |
|---|---|---|
| 做法 | `streamConvertPair{concatStream, restoreStream}`：checkpoint 时 `concatStream` 把流物化成单值持久化，恢复时 `restoreStream` 把单值变回流 | StreamRun 完全不碰 checkpoint |
| 代码 | generic_helper.go 的 streamConvertPair + checkpoint.go 的 streamConverter | 0 行 |
| 简化了什么 | 流的物化/反物化、流式 checkpoint 的存取 | |
| 为什么 | 流式 + checkpoint 极复杂，超出"最少代码"范围；崩溃恢复已由 Run + checkpoint 覆盖 |

### 7.4 范式存储：只存 i 和 t（推导） → 直接存 Compute + StreamCompute

| | eino | demo |
|---|---|---|
| 做法 | `composableRunnable` 只存 `i`（invoke）和 `t`（transform）；Stream/Collect 在入口处用 wrap/concat 桥接到 i 或 t；12 个推导函数 + 优先级选择 | 顶点直接实现 `Compute`（Invoke）+ `StreamCompute`（Transform）；Run 走 Compute，StreamRun 走 StreamCompute |
| 代码 | 12 个 `xxxByYyy` 推导函数 + newRunnablePacker 优先级 | 0 推导函数（顶点两方法并存） |
| 简化了什么 | 12 个推导闭包、优先级选择、只存两个的工程优化 | |
| 为什么 | demo 顶点数量少，直接存两方法最省事；自动推导的"wrap+concat 桥接"机制在 StreamRun 内部（wrap 输入、concat 决定路由）已自然体现 |

### 7.5 StreamReader 内部类型：5 种 → 4 种

| | eino | demo |
|---|---|---|
| 内部类型 | Stream / Array / MultiStream / WithConvert / Child（5 种） | Stream / Array / Child / Merged（4 种） |
| 简化了什么 | `WithConvert`（流的逐块转换 + 过滤 + OnEOF 注入） | |
| 为什么 | demo 不需要流转换/过滤；Merge 的输出复用 Stream 类型（channel-based），不需要单独 MultiStream 类型 |

### 7.6 concat 类型合并：注册表 → 单一 mergeMessages

| | eino | demo |
|---|---|---|
| 做法 | `ConcatItems` + 类型注册表：string 拼接、数值 useLast、bool useLast、map 递归合并、struct 用户注册 `RegisterStreamChunkConcatFunc` | `concatStreamReader` 接收 `merge func([]T) T` 参数；demo 传 `mergeMessages`（ToolCalls/Results 拼接、Answer useLast） |
| 代码 | internal/concat.go ~200 行（含 reflect） | mergeMessages ~10 行 |
| 简化了什么 | 多类型合并策略、reflect 反射、用户注册机制 | |
| 为什么 | demo 只有 Message 一种类型，不需要通用合并注册表；传 merge 函数既灵活又省代码 |

### 7.7 Copy 清理：close 计数 → 无清理

| | eino | demo |
|---|---|---|
| 做法 | `parentStreamReader.close(idx)` 设 nil + `closedNum` 原子计数，全部子流关闭才关源 | demo 的 childStreamReader.close 只设 closed 标志，不关源 |
| 简化了什么 | 子流关闭计数、源的资源回收 | |
| 代价 | demo 的源流不会被主动关闭（依赖 GC）；长时间运行的流可能延迟释放 | |
| 为什么 | demo 是短运行教学程序，无资源泄漏问题；清理逻辑不影响理解 Copy 的 lazy 核心机制 |

### 7.8 简化总览

| # | 简化点 | eino 机制 | demo 替代 | 影响 |
|---|---|---|---|---|
| 1 | Merge | select + reflect.Select | goroutine-per-source | 无（功能等价） |
| 2 | 分支路由 | StreamGraphBranch（流式条件） | Copy-for-peek（concat） | 分支点失去 lazy |
| 3 | checkpoint | streamConvertPair | 不集成 | 流式无崩溃恢复 |
| 4 | 范式存储 | 只存 i/t + 12 推导 | 直接存两方法 | 无（功能等价） |
| 5 | StreamReader 类型 | 5 种 | 4 种 | 无 WithConvert |
| 6 | concat 合并 | 类型注册表 | 单一 merge 函数 | 只支持 Message |
| 7 | Copy 清理 | close 计数回收 | 无 | 短运行无影响 |

**核心机制全部保留**：StreamReader/Writer、wrap/concat、lazy Copy、Merge、流 handle 跨 superstep、四范式。简化的是工程优化（select 手写、类型注册表）、高级特性（StreamGraphBranch、WithConvert）、生产能力（checkpoint 物化、资源回收）。

## 八、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `StreamReader[T]` / `StreamWriter[T]` | `schema.StreamReader[T]` / `StreamWriter[T]` | 结构一致，demo 4 种内部类型 vs eino 5 种 |
| `Pipe[T]()` | `schema.Pipe[T]()` | channel-based 流 |
| `StreamReaderFromArray` | `schema.StreamReaderFromArray` | wrap 实现 |
| `wrap(val)` | `StreamReaderFromArray([]T{val})` | 单值->流 |
| `concatStreamReader` + `mergeMessages` | `concatStreamReader` + `ConcatItems` | 流->单值，按类型合并 |
| `Copy(n)` lazy（sync.Once+链表） | `StreamReader.Copy(n)` lazy（sync.Once+链表） | 实现一致 |
| `MergeStreamReaders`（goroutine-per-source） | `MergeStreamReaders`（select + reflect.Select） | demo 简化，支持任意 N |
| `StreamVertex.StreamCompute` | `Transform[I,O]` | 流式入->流式出 |
| `StreamRun`（Transform 模式） | `runner.transform`（isStream=true） | 流 handle 跨 superstep |
| 分支点 Copy-for-peek | `StreamGraphBranch`（流式条件） | demo 简化：用 concat 决定路由 |
| 不集成 checkpoint | `streamConvertPair`（concatStream/restoreStream） | 超出 demo 范围 |
| `mergeMessages`（拼接/useLast） | `ConcatItems`（string 拼接/数值 useLast/map 递归） | demo 用 Message 合并 |

## 九、后续规划

| 增量 | 内容 | 状态 |
|------|------|------|
| 1 | Checkpoint | ✅ |
| 2 | Interrupt/Resume | ✅ |
| 3 | State | ✅ |
| 4 | Streaming（四范式 + Copy + Merge + StreamRun） | ✅ |
| 5 | DAG Channel（skip 传播 + AllPredecessor 触发） | 📋 |
| 6 | StreamGraphBranch（流式分支条件，避免分支点 concat） | 📋 |

## 十、总结

**Streaming 的核心机制可概括为：StreamReader/Writer 是流的载体，wrap/concat 是单值与流的桥，Copy 是扇出，Merge 是扇入，StreamRun 让流 handle 跨 superstep 传递。** 四范式不是四种实现，而是 wrap+concat 组合出的四种调用方式。分支点因 `Cond` 需要完整 Message 而触发 concat，是 demo 简化的代价；eino 用 StreamGraphBranch 避免之。流式 + checkpoint 的物化（concatStream/restoreStream）留作后续。
