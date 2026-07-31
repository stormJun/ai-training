# Pregel Channel Demo: channel 抽象（增量 6）

> 源码：
> - [`channel.go`](./channel.go)：**channel 抽象核心**（channel 接口 + pregelChannel + edgeHandlerManager + EdgeHandler + mergeValues + RegisterMergeFunc）
> - [`main.go`](./main.go)：Graph/Compile + Run(Invoke) + StreamRun(Transform)，都用 channel
> - [`checkpoint.go`](./checkpoint.go)：Checkpoint + channel.load 恢复 + convertValues 演示
> - [`stream.go`](./stream.go)：流基础设施（不变，从 05）
> - [`llm.go`](./llm.go)：真 LLM 流式（不变，从 05）
> - [`demo.go`](./demo.go)：顶点（Compute + StreamCompute）+ 5 场景
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表
>
> 上游：[05_pregel_stream_demo](../05_pregel_stream_demo/pregel_stream_demo.md)（流式），[04_pregel_checkpoint_demo](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)（Invoke/checkpoint 基础）
>
> 本 demo 引入 **channel 作为数据流中枢**，统一 Invoke + Transform，补全 eino 引擎一直被简化掉的核心层。

## 一、概述

05 之前，数据流是裸 `map[string][]Message`（Invoke）/ `map[string][]*StreamReader`（Transform）+ 硬编码 append/Merge。**eino 的 channel 接口（`graph_manager.go:29`）这一核心抽象一直没做。**

本增量引入 channel，约 600 行代码：

| 文件 | 内容 | 行数 |
|------|------|------|
| `channel.go` | channel 接口(5方法) + pregelChannel + edgeHandlerManager + EdgeHandler + mergeValues + RegisterMergeFunc | ~230 |
| `main.go` | Graph(加 edge handler) + Run(Invoke,重新引入) + StreamRun(改用 channel) + taskManager | ~430 |
| `checkpoint.go` | Checkpoint(Channels 字段) + channel.load + convertValues demo | ~140 |
| `demo.go` | ModelVertex/ToolVertex/FlakyToolVertex(Compute+StreamCompute) + 5 场景 | ~290 |

核心能力：**channel 统一 Invoke+Transform 数据流 + edge handler 边转换 + 可配置 merge 扇入 + checkpoint 通过 channel.load/convertValues 存恢复。**

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/06_pregel_channel_demo
source /Users/songxijun/workspace/otherProject/eino-examples/.env  # ARK_API_KEY
go run .
```

5 个场景：Run(Invoke) / StreamRun(真 LLM) / edge handler / checkpoint 崩溃恢复 / convertValues 演示。`go vet` 通过，`go run -race` 无数据竞争。

## 三、channel 抽象（核心）

### 3.1 channel 接口（5 方法，对齐 eino 去 DAG）

```go
type channel interface {
    reportValues(map[string]any) error                                          // 收前驱值
    get(isStream bool, name string, eh *edgeHandlerManager) (any, bool, error)  // 取合并值(带边转换)
    convertValues(fn func(map[string]any) error) error                          // 批量转换(checkpoint 序列化流)
    load(channel) error                                                         // 从快照恢复(checkpoint 恢复)
    setMergeConfig(mergeFunc)                                                   // 配置 per-channel merge
}
```

eino 有 7 方法，去掉 DAG 的 `reportSkip`/`reportDependencies`（06 不做 DAG），剩 5 个。

### 3.2 pregelChannel 实现

```go
type pregelChannel struct {
    Values   map[string]any  // from -> value(Message 或 *StreamReader)
    mergeCfg mergeFunc       // 可选:per-channel merge 覆盖
}
```

`get` 是核心：对每个 from 的值调 `edgeHandler.handle(from, name, value, isStream)`（边转换），单值直接返回，多值调 `mergeValues`（可配置 merge）。取走后清空。

### 3.3 channelManager

```go
type channelManager struct { channels map[string]channel }
```

每个节点一个 channel 收前驱值。Run/StreamRun 的 current/next 就是 channelManager。替代 05 的裸 map。

## 四、edge handler（边转换）

### 4.1 机制

数据从 from 过边到 to 时被转换。EdgeHandler 含两个函数：

```go
type EdgeHandler struct {
    Invoke    func(Message) (Message, error)                              // Run 模式
    Transform func(*StreamReader[Message]) (*StreamReader[Message], error) // StreamRun 模式
}
```

`channel.get` 取值时调 `edgeHandler.handle(from, to, value, isStream)` 应用转换。

### 4.2 为什么在边上

转换放边上，产出节点和消费节点互不认识（解耦）。详见 CONTEXT.md `edge handler` 条目。demo 场景 3：model->search 边挂过滤 handler，search 收到的已是自己的 ToolCall。

### 4.3 注册

```go
g.AddEdgeWithHandler("model", "search", EdgeHandler{
    Invoke: filterToolCall("search"),  // 只留 search 的 ToolCall
})
```

## 五、可配置 merge（扇入）

### 5.1 机制

扇入时多前驱值合并成一个。不同类型合并方式不同，用户按类型注册：

```go
RegisterMergeFunc(mergeMessages)  // 注册 Message 的 merge:拼接 Results,Answer 取最后
```

`channel.get` 多前驱时调 `mergeValues` -> 查注册表 -> 调用户函数。流用 `MergeStreamReaders`，单值用注册函数。

### 5.2 node 收合并后的单值

有 merge 后，节点收单个合并值，不是 slice：

```go
// 05(无 merge): Compute(ctx, []Message)  遍历 slice 自己合
// 06(有 merge): Compute(ctx, Message)    收已合并的单值,直接用
```

合并逻辑从节点内移到 channel。和 edge handler 同样的解耦哲学。

## 六、Run / StreamRun 都用 channel

### 6.1 统一的执行模型

Run（Invoke）和 StreamRun（Transform）结构一致，只是 `isStream` 不同：

```
current = channelManager
loop:
  for each channel: val = channel.get(isStream, name, edgeHandlers)  // merge + 边转换
  vertex.Compute(val) 或 vertex.StreamCompute(val)                    // 单个合并值
  route: next.report(to, from, output)                                // 投递到后继 channel
  current = next
```

`isStream=false` 走 Compute（Message），`isStream=true` 走 StreamCompute（StreamReader）。channel 的 `get` 用同一个 `isStream` 决定边转换和 merge 走哪条。

### 6.2 Run（Invoke）

重新引入（从 04）。taskManager 并行 Compute + 屏障。channel.get(false) 取 Message。checkpoint 集成（见七）。

### 6.3 StreamRun（Transform）

从 05 改用 channel。channel.get(true) 取流。分支点 peek 首块（保持最终输出实时流式）。**不做 per-barrier checkpoint**（会消费流破坏执行，见七）。

## 七、checkpoint + channel.load / convertValues

### 7.1 Checkpoint 存 channel 状态

```go
type Checkpoint struct {
    Step     int                       // 下一个 superstep
    Channels map[string]*pregelChannel // 各节点 channel 快照
}
```

04 存 `map[string][]Message`，06 存 `map[string]*pregelChannel`——快照的是 channel 状态。

### 7.2 channel.load（恢复）

Run checkpoint restore 时调 `channel.load`：

```go
restoreChannels(current, cp.Channels)  // 对每个 channel: ch.load(snapshotted)
```

场景 4 演示：FlakyToolVertex 首次崩，Run2 从 checkpoint 续跑，channel.load 恢复 superstep 1 的 channel 状态。

### 7.3 channel.convertValues（流序列化）

流不能直接存 checkpoint（有状态、消费即没）。`convertValues` 批量转换 channel 值（流 -> 单值 Message）：

```go
ch.convertValues(func(values map[string]any) error {
    for k, v := range values {
        if sr, ok := v.(*StreamReader[Message]); ok {
            values[k] = concatMsg(sr)  // 流 concat 成 Message
        }
    }
    return nil
})
```

对应 eino `streamConvertPair.concatStream`。场景 5（demoConvertValues）演示。

### 7.4 为什么 StreamRun 不做 per-barrier checkpoint

per-barrier 流 checkpoint 会 concat 流（消费它），破坏下一步的流执行。eino 只在 **interrupt** 时做（执行已停止，消费流安全）。06 无 interrupt，所以 StreamRun 不做 checkpoint，convertValues 由 demoConvertValues 单独演示。

Run（Invoke）的 Values 是 Message（可拷贝），per-barrier checkpoint 安全，正常做。

## 八、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `channel` 接口(5方法) | `channel` 接口(7方法) | 去掉 DAG 的 reportSkip/reportDependencies |
| `pregelChannel` | `pregelChannel` | Values map[string]any + get 带 edgeHandler + merge |
| `channelManager` | `channelManager` | map[nodeKey]channel |
| `edgeHandlerManager` + `EdgeHandler` | `edgeHandlerManager` + `handlerPair` | 边转换,Invoke+Transform 两函数 |
| `AddEdgeWithHandler` | `AddEdge` + `MapFields` 选项 | 边上挂 handler |
| `RegisterMergeFunc` + `mergeValues` | `RegisterValuesMergeFunc` + `mergeValues` | 按类型注册扇入 merge |
| `channel.load` | `channel.load` | checkpoint 恢复 |
| `channel.convertValues` | `channel.convertValues` + `streamConvertPair` | 流序列化 |
| Run(Invoke)+StreamRun 用 channel | `runner.run`(isStream) | 统一两范式 |
| Vertex: Compute+StreamCompute 收单值 | 节点收合并后单值 | merge 在 channel,不在节点 |

## 九、简化说明

| # | 简化点 | eino | demo | 影响 |
|---|---|---|---|---|
| 1 | channel 方法数 | 7(含 DAG) | 5(无 DAG) | 不做 skip 传播 |
| 2 | edge handler | 完整 field mapping(MapFields/FromField/ToField) | 单值转换函数 | 不做 struct 字段映射 |
| 3 | merge 注册 | RegisterValuesMergeFunc(多类型) | RegisterMergeFunc(只 Message) | 单类型够用 |
| 4 | StreamRun checkpoint | interrupt 时做 | 不做 | 无 interrupt |
| 5 | preNode/preBranch handler | 有 | 无 | 06 不做 State pre/post |
| 6 | setMergeConfig | StreamMergeWithSourceEOF 等配置 | per-channel 覆盖(可用,demo 用全局) | 功能等价 |

**核心机制全部保留**：channel 接口、pregelChannel、edge handler、可配置 merge、channel.load/convertValues、Invoke+Transform 统一。

## 十、后续规划

| 内容 | 状态 |
|------|------|
| channel 抽象(接口+edge handler+merge+load/convertValues) | ✅ |
| DAG channel（skip 传播 + AllPredecessor 触发） | 📋（需加 reportSkip/reportDependencies） |
| 完整 field mapping（MapFields/FromField/ToField） | 📋 |
| State pre/post handler（preNodeHandlerManager） | 📋 |
| Sub-graph（channel 递归） | 📋 |

## 十一、总结

**channel 是数据流中枢：收值(reportValues)、取合并值带边转换(get)、流转换(convertValues)、恢复(load)、配置 merge(setMergeConfig)。** edge handler 让数据过边时转换（解耦节点），可配置 merge 让扇入按类型合并（节点收单值），channel.load/convertValues 让 checkpoint 存恢复。Run 和 StreamRun 通过 `isStream` 统一在同一套 channel 机制上。这是 05 之前一直被裸 map 简化掉的核心层，补全后引擎的数据流终于对齐 eino。
