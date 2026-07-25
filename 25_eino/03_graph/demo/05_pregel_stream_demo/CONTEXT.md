# Pregel Stream Demo

从零手写最小 Pregel 引擎，逐步逼近 eino 内部机制。
本 demo 专注**流式执行（Transform 范式）**：StreamRun + Copy（扇出）+ Merge（扇入）+ wrap/concat + 真 LLM 流式调用。
Invoke 范式（Run/Compute）、Checkpoint、State 见上游 [04_pregel_checkpoint_demo](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)。

本文档是术语表，只定义概念是什么。机制原理、对比说明见 [pregel_stream_demo.md](./pregel_stream_demo.md)。

## Language

**Superstep**:
Pregel 的一个执行步：所有就绪顶点并行执行，屏障同步后路由到下一步。
_Avoid_: 轮次、步骤、iteration

**Barrier**:
超级步末尾的同步点--所有顶点返回后才进入下一步。流式下同步的是"返回流 handle"，不是"流消费完"。
_Avoid_: 同步点、栅栏

**Compile**:
声明式拓扑（Graph）-> 运行期结构（Compiled）+ 校验 + 环检测。一次性转换。
_Avoid_: 编译（太通用）

## Streaming

**四范式（Four Paradigms）**:
Runnable 的四种执行方式，2×2 矩阵：Invoke（单值->单值）、Stream（单值->流）、Collect（流->单值）、Transform（流->流）。本 demo 实现 Transform（StreamRun/StreamCompute）；Invoke 见 04。
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
流式顶点的计算方法，收流产流。本 demo 的 Vertex 接口只要求此方法。
_Avoid_: 流式计算（太宽泛）

**StreamRun**:
Transform 模式的图执行入口。current/next 存流 handle，顶点走 StreamCompute，扇出用 Copy，扇入用 Merge，调用方拿流。对应 eino runner.transform（isStream=true）。
_Avoid_: 同步/异步运行（不准确）

**流 handle 跨 superstep**:
StreamRun 下流 handle 像单值一样存进 `next`，跨屏障传递；数据真正流动发生在下游 Recv() 时，是 lazy 的。
_Avoid_: 流式屏障（易误解为屏障处消费流）

**分支点 peek 首块**:
分支的 Cond 需要 Message 决定路由，但顶点产出的是流。demo 只读首个 chunk 决定路由（不 concat 整流），保持后续 chunk 实时流式。对应 eino StreamGraphBranch 的思路。
_Avoid_: 流式分支（太宽泛）

**真 LLM 流式**:
demo 通过 net/http 直连火山方舟 Ark（OpenAI 兼容），SSE 流式解析 LLM 输出。无外部依赖，读 `ARK_API_KEY` 环境变量。延迟来自真实 LLM 推理，无需模拟。
