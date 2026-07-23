# Pregel MVP 增量 1:Checkpoint(每超步快照 + 断点续跑)

> 源码:[`main.go`](./main.go)(Pregel 引擎 + Demo 场景) + [`checkpoint.go`](./checkpoint.go)(Checkpoint 机制独立文件)
> 上游:[`../pregel_demo`](../pregel_demo/README.md)(Pregel 四机制 + Compile,本 demo 在其上**只增不改**)
> 配套概念文档:[`../pregel.md`](../pregel.md)
>
> 本文仅介绍新增的机制 ⑥ Checkpoint;Pregel 前五机制的完整拆解见上游 README,此处不再重复。

## 一、概述

本 demo 在 pregel_demo 基础上新增约 120 行代码,为执行引擎引入**断点(Checkpoint)能力**:

- 每个超步屏障通过后,将**全图运行状态**快照写入 `CheckPointStore`;
- `Run` 启动时若发现同 ID 断点,则跳过 START 播种,直接从快照恢复执行;
- 正常执行完毕后清除断点;发生崩溃、取消或达到 maxSteps 时,断点予以保留。

演示场景(场景三):一个"首次调用必然失败"的工具顶点(`FlakyToolVertex`,模拟进程崩溃、网络超时等瞬时故障)。Run 1 在 superstep 1 失败,Run 2 使用同一 checkpoint ID 从断点恢复,继续执行至 END。

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/03_graph/demo/pregel_checkpoint_demo
go run .
```

场景三预期输出(Run 1 失败、Run 2 恢复):

```
── Run 1(flaky_search 首次调用必崩)──

── superstep 0 ── 活跃顶点: [model]
  [model] 第 1 次激活,收到 1 条消息
  [model] 产出 ToolCalls=[search, calc]
  [checkpoint] 屏障通过,已存快照(下次从 superstep 1 续跑,在途 [calc flaky_search])

── superstep 1 ── 活跃顶点: [calc flaky_search]
  [calc] 执行 2+3 -> calc(2+3)
[checkpoint] superstep 1 失败,断点保留在上一屏障(同 ID 重跑将重跑本超步)
Run 1 返回错误: vertex[flaky_search] panic: 模拟瞬时故障:首次调用必崩(如进程崩溃/网络超时)

── Run 2(同 checkpoint ID,从断点续跑)──
[checkpoint] 命中断点:从 superstep 1 续跑,在途消息 [calc flaky_search](START 播种被跳过)

── superstep 1 ── 活跃顶点: [calc flaky_search]
  [calc] 执行 2+3 -> calc(2+3)                              ◀ 失败超步内已成功的 calc 被重复执行
  [flaky_search] 执行 eino pregel -> search(eino pregel)(第 2 次调用)
  [checkpoint] 屏障通过,已存快照(下次从 superstep 2 续跑,在途 [model])

── superstep 2 ── 活跃顶点: [model]
  [model] 第 2 次激活,收到 2 条消息                          ◀ model 未从头重新执行
  [model] 产出最终答案 ...,路由到 END
无在途消息,计算结束
[checkpoint] 正常结束,断点已清除
```

`go vet` 通过,`go run -race` 无数据竞争。

输出中三个观察要点:

1. **Run 2 未重新执行 model**:superstep 0 的执行结果由快照保留,`[model] 第 2 次激活`属于"继续执行"而非"重新开始"。在真实场景中 model 通常对应 LLM 调用,避免重复执行即节省一次推理开销。
2. **calc 被重复执行**:断点以屏障为粒度,失败超步内已执行成功的兄弟顶点不会被豁免。这属于 at-least-once 语义,**要求顶点具备幂等性**(与 LangGraph 逐超步 checkpoint 的语义一致)。
3. **执行完毕后断点自动清除**:此后以同 ID 再次运行即为全新执行,不会发生误恢复。

## 三、Pregel 模型与一致性快照

这是本增量的核心论点,也是将 checkpoint 列为 Pregel demo 首个扩展项的原因。

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
| `State` | 跨顶点共享 State | 未实现(demo 无 State)→ 增量 3 |
| `SkipPreHandler` / `RerunNodes` | 恢复时需重跑 / 跳过 preHandler 的节点 | 未实现,服务于动态中断 → 增量 2 |
| `SubGraphs` | 子图的嵌套断点 | 未实现(demo 无子图) |
| `InterruptID2Addr` / `InterruptID2State` | 动态中断信号的寻址与状态 | 未实现 → 增量 2 |

可见,**demo 的两个字段(Step + Current)已覆盖 eino checkpoint 的主体骨架**;其余 5 个字段各自对应一项尚未实现的机制,该结构将随后续增量逐步补齐。

### 两种写入时机:逐超步 vs 仅中断时

| | demo(本增量) | eino | LangGraph |
|---|---|---|---|
| 何时写 checkpoint | 每个屏障通过后 | **仅在 interrupt 时**(`graph_run.go:561` 与 `:701`,全库仅此两个写点) | 每个 superstep |
| 主要用途 | 崩溃恢复(断点续跑) | HITL 人机中断恢复 | 两者兼有,另支持 time travel |
| 正常结束 | 主动删除断点(故 store 增加 `Delete`) | 不涉及(断点随 resume 消耗) | 保留历史 |

需要明确的事实:**在 eino 中,checkpoint 并非独立功能,而是 interrupt/resume 的持久化机制**。因此 demo 的演进路径为:增量 1 先实现快照与恢复(面向崩溃恢复场景),增量 2 再引入 interrupt/resume(checkpoint 的设计目标场景)。

## 五、实现要点:新增的 5 块代码

> 以下 5 块代码位于独立文件 [`checkpoint.go`](./checkpoint.go)，与 `main.go` 中的 Run 循环通过三处集成点串联。

### 5.1 `Checkpoint` + `CheckPointStore` + `memoryStore`

```go
type Checkpoint struct {
    Step    int                   // 下一个要执行的 superstep 号
    Current map[string][]Message  // 在途消息池 = 恢复后第一个超步的输入
}

type CheckPointStore interface {          // 对应 eino core.CheckPointStore(仅 Get/Set)
    Get(ctx context.Context, id string) (*Checkpoint, bool, error)
    Set(ctx context.Context, id string, cp *Checkpoint) error
    Delete(ctx context.Context, id string) error   // demo 特有:逐超步写入,正常结束后须主动清除
}
```

`memoryStore` 为内存实现,**读写均执行深拷贝**(`cloneCurrent`,map -> slice -> Message 内层 slice)。若省略拷贝,已存入 store 的快照会被后续执行原地修改,断点即失去意义。这是 checkpoint 实现中最典型的错误——快照必须具备值语义,不得共享引用。

### 5.2 编译期装配 store(对应 eino `WithCheckPointStore`,`checkpoint.go:60`)

```go
type CompileOption func(*Compiled)

func WithCheckPointStore(store CheckPointStore) CompileOption {
    return func(c *Compiled) { c.store = store }
}
```

`Compiled` 因此新增 `store` 字段——**拓扑与存储均在编译期确定,运行期只读**。

### 5.3 `Run` 的三处改动(即本机制的全部改动)

```
Run(ctx, initial, checkPointID):
  ┌─ ① 恢复(循环前):同 ID 断点存在 -> current = 快照, startStep = 快照.Step
  │                    跳过 START 播种         (对应 eino graph_run.go:173-184)
  │
  │  for step := startStep; ... {     ← 唯一修改的循环头
  │      ...屏障、路由、current = next(保持原样)...
  │
  │      ② 保存(屏障后):store.Set({Step: step+1, Current: current})
  │         —— 一致性切点位于此处
  │  }
  │
  └─ ③ 清除:len(current)==0 正常终止 -> store.Delete(id)
       崩溃 / ctx 取消 / maxSteps    -> 断点保留,支持恢复
```

另有一处校验:传入 checkpoint ID 但未装配 store 时直接报错——与 eino 行为一致(`graph_run.go:146-147`:"receive checkpoint id but have not set checkpoint store")。

### 5.4 文件拆分与串联

```
checkpoint.go                          main.go
─────────────────────────────────────────────────────────────
Checkpoint 结构体         ──────►  Run 中恢复/保存时使用
CheckPointStore 接口      ──────►  Compiled.store 字段
WithCheckPointStore()     ──────►  Compile(opts...) 注入
memoryStore               ──────►  main() 中 newMemoryStore()
cloneCurrent()            ──────►  Get/Set 时深拷贝
```

**使用方式（main 函数）:**

```go
// 装配 store
store := newMemoryStore()
c, _ := g.Compile(WithCheckPointStore(store))

// Run 1：崩溃时保存断点
c.Run(ctx, initial, "thread-1")  // superstep 0 存快照，1 崩溃

// Run 2：同 ID 续跑
c.Run(ctx, initial, "thread-1")  // 从快照恢复，跳过 superstep 0
```

## 六、语义边界与注意事项

1. **断点以屏障为粒度,语义为 at-least-once**。失败超步内已执行成功的顶点会被重复执行(场景三中 calc 执行了两次)。顶点须具备幂等性;具有副作用的顶点(写库、发送消息)应自行实现去重。该语义与 LangGraph 逐超步 checkpoint 一致。
2. **仅在正常结束时清除断点**。崩溃、ctx 取消(场景二的取消同理)、maxSteps 强制停止时,断点均保留——这三类"非正常退出"因此都支持恢复执行。
3. **顶点私有状态不纳入快照**。`ModelVertex.step` 记录于结构体字段,不在快照范围内:demo 中 Run 2 显示"第 2 次激活",依赖的是同一进程内同一对象仍然存活;**若跨进程从持久化 store 恢复,该计数归零,执行行为将出错**。此为刻意保留的设计引子——eino 通过 `WithGenLocalState` + `checkpoint.State`(`state.go`、`checkpoint.go:110`)解决该问题,即增量 3 的内容。
4. **store 为内存实现,未涉及序列化**。生产环境需要持久化(Redis/DB),则必须处理类型注册与流转换——即 eino `Serializer` / `schema.RegisterName` / `normalizeCheckpointTypedNilInputs`(`checkpoint.go`)所解决的问题。demo 的 `Message` 为纯值 struct,可直接以 JSON 等通用方式序列化,故该部分从略。
5. **一个 ID 对应一条执行线**。同 ID 并发执行会相互覆盖断点(memoryStore 的锁仅保证单次读写的原子性,不保证单执行线语义)。eino 同样假设 checkpoint ID 由调用方按会话维度管理。

## 七、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `Checkpoint{Step, Current}` | `checkpoint`(`checkpoint.go:107`) | demo 仅覆盖其 Channels+Inputs 骨架 |
| `CheckPointStore` / `memoryStore` | `core.CheckPointStore`(`checkpoint.go:52`) | demo 增加 `Delete`(逐超步写入,故需清除) |
| `WithCheckPointStore` | 同名(`checkpoint.go:60`) | 编译期装配存储 |
| `Run(..., checkPointID)` | `WithCheckPointID`(`checkpoint.go:74`) | 调用期指定断点 ID |
| 循环前的恢复 | `getCheckPointFromStore` + `restoreCheckPointState`(`graph_run.go:173-184`) | 存在断点则跳过初始化 |
| 屏障后 `store.Set` | `handleInterrupt` 内的 `checkPointer.set`(`graph_run.go:561/701`) | 时机不同:demo 逐超步写入,eino 仅在 interrupt 时写入 |
| 传入 ID 未装配 store 报错 | 同款(`graph_run.go:146-147`) | |
| 未实现:序列化 / 流转换 | `Serializer`、`convertCheckPoint`(`checkpoint.go:301+`) | demo 无流式、消息为纯值,无需处理 |

## 八、后续规划:增量 2 = Interrupt/Resume(HITL)

在 eino 中,checkpoint 仅服务于 interrupt/resume,因此下一步是将断点能力从**被动恢复**扩展为**主动暂停**:

- 顶点(或编译期声明 `WithInterruptBeforeNodes`)请求暂停 -> 引擎在屏障处写入断点,返回携带 `Info` 的 `InterruptError`;
- 调用方完成审批或补充输入后调用 `Resume(ctx, id, data)`:恢复断点,并将数据注入被中断的顶点;
- 场景四(规划):将 `calc` 替换为"危险工具",模型发起调用时图中断、等待人工审批,Resume 携带 "approved" 继续执行。

届时 `Checkpoint` 将新增 `RerunNodes` 等字段——对照第四节的对照表,即逐步补齐 eino 结构中的其余字段。

## 九、总结

**屏障提供了一致性切点,`current` 单个 map 即构成全图状态——checkpoint 的全部实现可概括为:屏障后写入、循环前读取、结束后清除。其余复杂度(序列化、State、中断寻址)均属于后续增量需要补齐的机制,而非 Pregel 模型本身的成本。**
