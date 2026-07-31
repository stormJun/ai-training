# Pregel Channel Demo

从零手写最小 Pregel 引擎，逐步逼近 eino 内部机制。
本 demo 在 05（流式）基础上引入 **channel 抽象（增量 6）**：channel 接口 + edge handler + 可配置 merge，统一 Invoke + Transform。Invoke/Checkpoint/State 的基础见上游 [04_pregel_checkpoint_demo](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)，流式基础见 [05_pregel_stream_demo](../05_pregel_stream_demo/pregel_stream_demo.md)。

本文档是术语表，只定义概念是什么。机制原理、对比说明见 [pregel_channel_demo.md](./pregel_channel_demo.md)。

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
流式顶点的计算方法，收流产流。本 demo 的 Vertex 接口含 Compute（Invoke）+ StreamCompute（Transform），顶点同时实现两者。
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

## Channel（增量 6）

**channel**:
数据流中枢。收前驱值（reportValues）、取合并值带边转换（get）、流转换（convertValues）、恢复（load）、配置 merge（setMergeConfig）。Run 和 StreamRun 都通过 channel 走数据。对应 eino channel 接口（去掉 DAG 的 reportSkip/reportDependencies，5 方法）。
_Avoid_: 通道、管道（与 stream 混淆）

**pregelChannel**:
channel 的 Pregel 实现。`Values map[string]any` 按来源节点存值（Message 或 *StreamReader）。get 时对每个值应用边 handler，多值 merge。对应 eino pregelChannel。
_Avoid_: 消息池（05 的裸 map 已被 channel 替代）

**channelManager**:
`map[nodeKey]channel`，每个节点一个 channel 收前驱值。Run/StreamRun 的 current/next 就是 channelManager。替代 05 的裸 `map[string][]*StreamReader`。
_Avoid_: channelMap

**edge handler**:
挂在边上的转换函数。数据从 from 过边到 to 时被转换（Invoke 走 Invoke 函数，Transform 走 Transform 函数）。解耦：产出节点和消费节点互不认识，边负责转换。对应 eino edgeHandlerManager + handlerPair。
_Avoid_: 边转换、过滤器（handler 是通用转换，不只是过滤）

**EdgeHandler**:
一条边的转换函数结构，含 Invoke（单值 Message->Message）和 Transform（流 StreamReader->StreamReader）两个函数。对应 eino handlerPair。
_Avoid_: 边处理器

**可配置 merge（RegisterMergeFunc）**:
扇入时多前驱值合并成一个。不同类型合并方式不同（Message 拼接、流交错），用户按类型注册 merge 函数，channel 类型无关。对应 eino RegisterValuesMergeFunc + mergeValues。
_Avoid_: 合并函数（太宽泛）

**mergeValues**:
多值合并。流用 MergeStreamReaders 交错，单值用注册的 merge 函数。channel.get 多前驱时调。
_Avoid_: 扇入合并（mergeValues 是实现，扇入是拓扑）

**channel.load**:
从另一个 channel 恢复值（checkpoint 恢复用）。Run checkpoint restore 时调。对应 eino channel.load。
_Avoid_: 加载（太宽泛）

**channel.convertValues**:
批量转换 channel 里的值（流 -> 单值）。checkpoint 序列化流用（流不能直接存，先 concat）。对应 eino channel.convertValues + streamConvertPair。demo 由 demoConvertValues 演示（StreamRun 不做 per-barrier checkpoint，会消费流破坏执行）。
_Avoid_: 转换值（太宽泛）

**node 收合并后的单值（不是 slice）**:
有 channel merge 后，节点收单个合并值（Message/流），不是 []Message slice。合并逻辑从节点内移到 channel。Compute(ctx, Message) / StreamCompute(ctx, *StreamReader) 都收单个。
_Avoid_: 单输入（不准确，是"已合并的单值"）
