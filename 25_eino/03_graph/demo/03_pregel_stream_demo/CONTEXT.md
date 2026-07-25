# Pregel Stream Demo

从零手写最小 Pregel 引擎，逐步逼近 eino 内部机制。每个 increment 用最少代码实现最核心机制逻辑。
本 demo 在 02_pregel_checkpoint_demo 基础上新增增量 4: Streaming（四范式 + StreamReader/Writer + Copy + Merge）。

## Language

**Superstep**:
Pregel 的一个执行步：所有就绪顶点并行 Compute，屏障同步后路由消息到下一步。
_Avoid_: 轮次、步骤、iteration

**Barrier**:
超级步末尾的同步点——所有 Compute 完成后才进入下一步。屏障时刻的 `current` 消息池是图的一致性快照。
_Avoid_: 同步点、栅栏

**Checkpoint**:
屏障时刻对图可观察状态的快照（消息池 + 共享 State），用于崩溃恢复和中断恢复。
_Avoid_: 断点、快照（快照是 checkpoint 的实现手段，不是同义词）

**Vertex Private Field**:
顶点 struct 的内部字段（如 `ModelVertex.step`），只有该顶点的 Compute 能访问。属于实现细节，不进 checkpoint。
_Avoid_: 顶点状态（与 Graph State 混淆）

**Graph State**:
图级共享可变状态，所有顶点通过 `ProcessState` 读写，mutex 保护并发安全，进 checkpoint 深拷贝。
_Avoid_: 全局状态、共享状态（不够精确——"图级"限定了作用域）

**State 机制 vs State 应用**:
State 的**核心机制**只有一个：所有顶点通过 `ProcessState` 读写同一个 struct 实例，mutex 保护并发安全，checkpoint 保存/恢复。至于 struct 里放什么字段——`TokenCounter` 还是 `Messages`——是**应用层的选择**，不是机制本身。demo 用 `TokenCounter` 展示机制即可，无需引入 eino ADK 层面 `State.Messages` 累积的复杂度。

**eino 的 State 真实用法**:
eino ADK 的 ReAct Agent 用 State 做消息累积（`State.Messages`），所有节点往同一个 `[]Message` 追加——这是"沿边传消息"之外的**第二条数据通道**。此外还用 State 做循环次数控制（`RemainingIterations`）、工具直接返回标记（`ReturnDirectlyToolCallID`）等。这些属于 ADK 层面的设计选择，不是 compose 引擎层面的机制。

**GenLocalState（工厂函数）**:
编译时传入的"造 State 的函数"——不是 State 实例本身。每次 Run 调用此函数产出全新实例，避免多次 Run 共享同一个 State 被污染。`Gen` = Generate，不是传入。
_Avoid_: State 构造函数（不是构造函数，没有接收者）

**State 生命周期**:
编译时存工厂函数 → Run 开头调用工厂函数造实例 → 放进 ctx → 所有顶点从 ctx 取同一个指针 → Run 结束随 ctx 回收。共享的根源：Run 只造一次，所有顶点拿到同一个 `*GraphState` 指针。

**ProcessState**:
并发安全地访问 Graph State 的函数——从 ctx 取出 State 指针，加锁，调用户 handler，解锁。是顶点读写 State 的唯一入口。
_Avoid_: getState、readState

**Interrupt**:
顶点主动暂停执行（如等待人工审批），引擎保存 interrupt checkpoint，返回 `InterruptError` 给调用方。
_Avoid_: 暂停、挂起

**Resume**:
从中断 checkpoint 恢复执行——注入审批数据，清除 interrupt checkpoint，重新 Run。
_Avoid_: 继续、恢复（太宽泛）

**At-least-once**:
崩溃恢复语义：屏障粒度快照意味着崩溃步内已成功的顶点会被重跑。顶点必须幂等。
_Avoid_: 至少一次、重试语义

**Compile**:
声明式拓扑（Graph）→ 运行期结构（Compiled）+ 校验 + 环检测。一次性转换，之后只调 Run。
_Avoid_: 编译（太通用）

**Message Pool（邮箱）**:
`current map[string][]Message`——每个顶点一个"邮箱"，存放前驱发来的所有消息。有邮件的顶点才被激活（Pregel 触发条件）。
_Avoid_: 消息映射、消息表

**沿边传消息**:
顶点不选收件人，路由完全由编译时声明的 `edges`（无条件）和 `branches`（条件）决定。顶点只管 Compute 产出值，引擎负责投递到后继邮箱。这是 demo 和 eino 共有的数据通道。
_Avoid_: 消息路由（路由是动作，"沿边传"强调声明式）

**消息传递三步骤**:
① 激活：`for id, msgs := range current`——有邮件的顶点才跑
② 路由：`c.route(id, out)` → `next[to] = append(next[to], out)`——产出沿边/分支投递到后继邮箱
③ 交换：`current = next`——这一步发的 = 下一步收的（Pregel S→S+1 语义）

**eino 的两条数据通道**:
1. **沿边传**（Channel）——和 demo 一样，前驱产出→后继输入，superstep-local
2. **写进 State**（ADK 层面）——所有节点往 `State.Messages` 追加，图级共享、跨 superstep 累积
demo 只实现了通道 1。通道 2 是 Graph State 的应用层用法，机制本身已在 State 条目中描述。

## Streaming（增量 4）

**四范式（Four Paradigms）**:
Runnable 的四种执行方式，由"输入单值/流式"×"输出单值/流式"构成 2×2 矩阵：
- **Invoke**：单值入 -> 单值出（demo 的 `Run` / `Compute`）
- **Stream**：单值入 -> 流式出
- **Collect**：流式入 -> 单值出
- **Transform**：流式入 -> 流式出（demo 的 `StreamRun` / `StreamCompute`）
_Avoid_: 四种模式、执行模式（太宽泛）

**自动推导（Auto-derivation）**:
组件只实现一种范式，引擎推导出其余三种。核心靠两个原语：**wrap**（单值->流）和 **concat**（流->单值）。例如只有 Invoke，推导 Stream = Invoke + wrap；只有 Stream，推导 Invoke = Stream + concat。
_Avoid_: 范式转换、推导（太宽泛）

**wrap**:
把单值变成只含一个元素的流的操作。实现：`StreamReaderFromArray([]T{val})`--存进长度 1 的数组，用下标遍历模拟流。
_Avoid_: 包装（太通用）

**concat**:
把流的所有 chunk 攒成单值的操作。实现：循环调 `Recv()` 读出所有 chunk，按类型合并（string 拼接、数值取最后、map 递归合并）。
_Avoid_: 合并流（与 Merge 混淆--concat 是流->单值，Merge 是多流->一流）

**StreamReader / StreamWriter**:
流的接收端 / 发送端。Pipe 创建一对：writer 写 chunk，reader 逐块读，EOF 表示流结束。底层是 channel（生产者-消费者）。
_Avoid_: 流、管道（太宽泛）

**Copy（扇出）**:
一个流复制成多个独立流，让多个消费者各读各的。eino 用 lazy 实现（sync.Once + 链表）：谁先到谁触发从源读，后来的读缓存；不预读整流。demo 对齐 eino 的 lazy 实现。
_Avoid_: 流复制、克隆

**Merge（扇入）**:
多个流合并成一个流，chunk 按到达顺序交错。实现：`select` 同时监听多个 channel，哪个先来先输出，全部 EOF 才结束。
_Avoid_: 流合并、合并流（与 concat 混淆）

**StreamCompute（Transform 范式）**:
流式顶点的计算方法。签名：`StreamCompute(ctx, *StreamReader[Message]) -> (*StreamReader[Message], error)`--收流、产流。对应 eino 的 Transform。与 `Compute`（Invoke，收 []Message 产 Message）并存，顶点可同时实现两者。
_Avoid_: 流式计算（太宽泛）

**流 handle 跨 superstep 传递**:
StreamRun 模式下，流 handle（StreamReader 指针）像单值一样存在 `next` 里，跨 superstep 屏障传递。屏障同步的是"任务返回 handle"，不是"流被消费完"。数据真正流动发生在下游调 `Recv()` 时，是 lazy 的。
_Avoid_: 流式屏障（易误解为屏障处消费流）

**Run vs StreamRun**:
- **Run**（Invoke 模式）：current/next 存 []Message，顶点走 Compute，遇到流式输出就 concat。调用方拿单值。
- **StreamRun**（Transform 模式）：current/next 存流 handle，顶点走 StreamCompute，流式输出原样传递，扇出用 Copy，扇入用 Merge。调用方拿流。
节奏由调用方选哪个方法 + 顶点实现了什么共同决定。
_Avoid_: 同步运行 / 异步运行（不准确）

**Copy 与 Merge 的对偶**:
Copy 是扇出（一流->多流），Merge 是扇入（多流->一流）。两者都是流的拓扑操作，不涉及单值转换（那是 wrap/concat 的事）。
