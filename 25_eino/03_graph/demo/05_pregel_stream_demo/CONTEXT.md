# Pregel Stream Demo

从零手写最小 Pregel 引擎，逐步逼近 eino 内部机制。每个 increment 用最少代码实现最核心机制逻辑。
本 demo 在 04_pregel_checkpoint_demo 基础上新增增量 4: Streaming。
详细设计与机制说明见 [pregel_stream_demo.md](./pregel_stream_demo.md)；State 相关详见上游 [04_pregel_checkpoint_demo](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)。

本文档是术语表，只定义概念是什么。机制原理、生命周期、对比说明见上述设计文档。

## Language

**Superstep**:
Pregel 的一个执行步：所有就绪顶点并行 Compute，屏障同步后路由消息到下一步。
_Avoid_: 轮次、步骤、iteration

**Barrier**:
超级步末尾的同步点--所有 Compute 完成后才进入下一步。
_Avoid_: 同步点、栅栏

**Checkpoint**:
屏障时刻对图可观察状态的快照（消息池 + 共享 State），用于崩溃/中断恢复。
_Avoid_: 断点、快照（快照是实现手段，不是同义词）

**Vertex Private Field**:
顶点 struct 的内部字段（如 `ModelVertex.step`），只有该顶点能访问，不进 checkpoint。
_Avoid_: 顶点状态（与 Graph State 混淆）

**Graph State**:
图级共享可变状态，所有顶点通过 `ProcessState` 读写，mutex 保护，进 checkpoint 深拷贝。
_Avoid_: 全局状态、共享状态（"图级"限定了作用域）

**GenLocalState**:
编译时传入的"造 State 的工厂函数"，每次 Run 调用产出全新实例，防多次 Run 共享污染。`Gen` = Generate。
_Avoid_: State 构造函数（无接收者）

**ProcessState**:
并发安全访问 Graph State 的函数（取指针->加锁->调 handler->解锁），顶点读写 State 的唯一入口。
_Avoid_: getState、readState

**Interrupt**:
顶点主动暂停执行（如等待审批），引擎保存 interrupt checkpoint，返回 `InterruptError`。
_Avoid_: 暂停、挂起

**Resume**:
从中断 checkpoint 恢复--注入数据，清除 interrupt checkpoint，重新 Run。
_Avoid_: 继续、恢复（太宽泛）

**At-least-once**:
崩溃恢复语义：屏障粒度快照意味着崩溃步内已成功的顶点会被重跑，顶点必须幂等。
_Avoid_: 至少一次、重试语义

**Compile**:
声明式拓扑（Graph）-> 运行期结构（Compiled）+ 校验 + 环检测。一次性转换。
_Avoid_: 编译（太通用）

**Message Pool（邮箱）**:
`current map[string][]Message`--每个顶点一个邮箱，存前驱发来的消息。有邮件才激活。
_Avoid_: 消息映射、消息表

**沿边传消息**:
顶点不选收件人，路由由声明的 `edges`/`branches` 决定，引擎投递到后继邮箱。
_Avoid_: 消息路由（路由是动作，"沿边传"强调声明式）

## Streaming（增量 4）

**四范式（Four Paradigms）**:
Runnable 的四种执行方式，2×2 矩阵：Invoke（单值->单值）、Stream（单值->流）、Collect（流->单值）、Transform（流->流）。
_Avoid_: 四种模式、执行模式（太宽泛）

**自动推导（Auto-derivation）**:
组件只实现一种范式，引擎靠 wrap/concat 推导出其余三种。
_Avoid_: 范式转换、推导（太宽泛）

**wrap**:
单值 -> 流 的操作。
_Avoid_: 包装（太通用）

**concat**:
流 -> 单值 的操作（循环 Recv 读所有 chunk，按类型合并）。
_Avoid_: 合并流（concat 是流->单值，Merge 是多流->一流）

**StreamReader / StreamWriter**:
流的接收端 / 发送端。Pipe 创建一对，底层 channel，EOF 表流结束。
_Avoid_: 流、管道（太宽泛）

**扇出（fan-out）**:
一个节点的输出分给多个后继（一发多）。单值用 append 复制，流式用 Copy。
_Avoid_: 分发、广播（语义偏差）

**扇入（fan-in）**:
多个前驱的输出汇入一个节点（多发一）。单值收成数组，流式用 Merge。
_Avoid_: 汇聚、聚合（太宽泛）

**Copy（扇出）**:
一个流复制成多个独立流，让多消费者各读各的。lazy 实现（sync.Once + 链表），对齐 eino。
_Avoid_: 流复制、克隆

**Merge（扇入）**:
多个流合并成一个，chunk 按到达顺序交错。demo 用 goroutine-per-source。
_Avoid_: 流合并、合并流（与 concat 混淆）

**StreamCompute（Transform 范式）**:
流式顶点的计算方法，收流产流。与 `Compute`（Invoke）并存，顶点可同时实现两者。
_Avoid_: 流式计算（太宽泛）

**Run / StreamRun**:
Run=Invoke 模式（current 存 []Message，走 Compute，拿单值）；StreamRun=Transform 模式（current 存流 handle，走 StreamCompute，扇出 Copy 扇入 Merge，拿流）。
_Avoid_: 同步/异步运行（不准确）

**流 handle 跨 superstep**:
StreamRun 下流 handle 像单值一样存进 `next`，跨屏障传递；屏障同步"返回 handle"而非"流消费完"。
_Avoid_: 流式屏障（易误解为屏障处消费流）
