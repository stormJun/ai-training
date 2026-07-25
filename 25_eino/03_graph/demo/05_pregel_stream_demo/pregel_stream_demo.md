# Pregel Stream Demo: 流式执行 + 真 LLM

> 源码：
> - [`main.go`](./main.go)：Pregel 引擎核心（Graph/Compile/**StreamRun**、分支 peek 首块）
> - [`stream.go`](./stream.go)：流基础设施（StreamReader/Writer、Pipe、wrap、concat、**Copy(lazy)**、**Merge**）
> - [`llm.go`](./llm.go)：**真 LLM 流式调用**（火山方舟 Ark，OpenAI 兼容，net/http 直连）
> - [`demo.go`](./demo.go)：流式顶点（ModelVertex/ToolVertex）+ StreamRun 场景
> - [`CONTEXT.md`](./CONTEXT.md)：领域术语表
>
> 上游：[`../04_pregel_checkpoint_demo`](../04_pregel_checkpoint_demo/pregel_checkpoint_demo.md)（Invoke/Checkpoint/State，本 demo 只做流式）
>
> 本 demo 专注验证 **Transform 范式**（StreamRun）的流式执行机制，并接真 LLM 展示真实逐块流式。

## 一、概述

本 demo 是纯流式 demo（增量 4），约 600 行代码：

| 文件 | 内容 | 行数 |
|------|------|------|
| `stream.go` | 流基础设施：StreamReader/Writer、Pipe、wrap、concat、Copy(lazy)、Merge | ~220 |
| `main.go` | Graph/Compile/Compiled、Vertex(StreamCompute)、StreamRun、分支 peek 首块 | ~350 |
| `llm.go` | 真 LLM 流式调用（Ark/kimi-k3，SSE 解析） | ~75 |
| `demo.go` | ModelVertex（step1 假 ToolCalls / step2 真 LLM）、ToolVertex、场景 | ~130 |

核心能力：**端到端真 LLM 流式执行**。调用方调 `StreamRun`，逐块拿到 LLM 实时产出的答案，中间经过 Copy（扇出）和 Merge（扇入）。

Invoke 范式（Run/Compute）、Checkpoint、State 不在本 demo--见 04。

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/05_pregel_stream_demo

# 设置 API Key（用 eino-examples 的 .env）
source /Users/songxijun/workspace/otherProject/eino-examples/.env

go run .
```

### 运行输出（真 LLM 逐块流式）

```
=== StreamRun(真 LLM 流式)===
[compile] 检测到环: [model->search->model][calc->model->calc](Pregel 允许)

── stream superstep 0 ── 活跃顶点: [model]
  [model] 记录问题,产出 ToolCalls=[search, calc]

── stream superstep 1 ── 活跃顶点: [calc search]

── stream superstep 2 ── 活跃顶点: [model]
  [search] 流式产出 Result: search(eino 框架是什么？)
  [calc] 流式产出 Result: calc(2+3)
  [model] 真 LLM 流式回答中...
  [stream] 路由到 END,返回流给调用方

调用方逐块读取最终流(真 LLM 逐块到达):
  [+    0ms] **Eino（音同 "I know"）是字节跳动 CloudWeGo 团队...
  [+ 423ms] ...
  [+1338ms] ...
  ...
  [+8987ms] ...主流的选择之一。

最终答案: **Eino（音同 "I know"）是字节跳动 CloudWeGo 团队开源的...
```

`go vet` 通过，`go run -race` 无数据竞争。

**观察要点：**

1. **真 LLM 流式**：chunk 间隔 0~400ms 不等（真实推理+网络延迟），调用方逐块拿到答案，不是一次性返回。
2. **lazy 执行**：`[search]`/`[calc]` 的产出打印在 superstep 2，不是 superstep 1--它们在 superstep 1 被 spawn，真正执行发生在 superstep 2 model 消费合并流时（下游 Recv 驱动）。
3. **Copy 扇出 + Merge 扇入**：model 的 ToolCalls 流 Copy 给 search/calc；search/calc 结果流 Merge 回 model。

## 三、四范式与自动推导

### 四范式 = 2×2 矩阵

```
                 |  单值输出      |  流式输出
-----------------+----------------+----------------
  单值输入       |   Invoke       |   Stream
  流式输入       |   Collect      |   Transform
```

本 demo 只实现 **Transform**（`StreamCompute` / `StreamRun`）。Invoke 见 04。Stream/Collect 靠 wrap/concat 推导（概念存在，demo 未单独实现入口）。

### 自动推导 = wrap + concat

两个原语让四种范式互通：

| 原语 | 作用 | 实现 |
|------|------|------|
| **wrap** | 单值 -> 流 | `StreamReaderFromArray([]T{val})`：长度1数组 + 下标遍历 |
| **concat** | 流 -> 单值 | 循环 `Recv()` 读所有 chunk，按类型合并 |

demo 中 wrap 用于 START 播种（单值问题 -> 流），concat 用于顶点读输入流、分支点 peek。

## 四、流基础设施（stream.go）

### 4.1 StreamReader / StreamWriter / Pipe

```go
func Pipe[T any]() (*StreamReader[T], *StreamWriter[T])  // channel 缓冲1
// StreamWriter: Send 写 chunk，Close 结束流
// StreamReader: Recv 读 chunk（io.EOF 表结束），Close 主动终止
```

StreamReader 有 3 种内部实现（`typ` 字段）：

| typ | 实现 | 用途 |
|-----|------|------|
| `readerTypeStream` | channel-based | Pipe 创建的流 / Merge 的输出（Merge 用 goroutine 转发到 Pipe） |
| `readerTypeArray` | 数组+下标 | wrap 创建的流 |
| `readerTypeChild` | lazy 链表 | Copy 出来的子流 |

### 4.2 扇出与扇入：为什么需要 Copy 和 Merge

场景拓扑：

```
START ──▶ model ──┬──▶ search ──┐
                   │             ├──▶ model ──▶ END
                   └──▶ calc  ──┘
                   扇出          扇入
```

- **扇出（fan-out）**：一个节点输出分给多个后继（model -> search + calc）
- **扇入（fan-in）**：多个前驱输出汇入一个节点（search + calc -> model）

**单值下简单**（值不可变，append 复制无成本）；**流式下是问题**（流有状态，chunk 取走就没）：

| | 单值 | 流式 |
|---|---|---|
| 扇出 | `append` 复制值 | 流不能直接给两份，需 **Copy** 复制成独立管道 |
| 扇入 | 收成 `[]Message` | 多流不能收成数组，需 **Merge** 合成一个管道 |

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
- 各子流独立前进

### 4.4 Merge（扇入）

多个流合并成一个，chunk 按到达顺序交错。**goroutine-per-source 实现**：每个源一个 goroutine 转发 chunk，全部 EOF 关闭输出。比 eino 的 `select`+`reflect.Select` 简单，支持任意 N。

### 4.5 concat（流 -> 单值）

```go
func concatStreamReader[T any](sr, merge func([]T) T) (T, error)
```

循环 `Recv()` 读所有 chunk，1 个直接返回，多个调 `merge` 合并。demo 的 `mergeMessages`：ToolCalls/Results 拼接，Answer 取最后非空。

## 五、StreamRun（Transform 模式）

### 5.1 StreamRun 的执行模型

```
current/next 存流 handle(*StreamReader[Message]),不是单值
顶点走 StreamCompute(收流产流)
扇出用 Copy,扇入用 MergeStreamReaders
分支点:peek 首块决定路由(不 concat 整流)
流 handle 跨 superstep 屏障传递:屏障同步"返回 handle",不是"流消费完"
数据真正流动发生在下游 Recv() 时,lazy
```

### 5.2 流 handle 跨 superstep 传递

流 handle 像单值一样存进 `next`，跨屏障传递：

```
superstep 0: model.StreamCompute -> 流 handle
              屏障:所有 StreamCompute 返回 handle(不等流消费完)
              next["search"] = [流 handle 的 Copy], next["calc"] = [流 handle 的 Copy]

superstep 1: search.StreamCompute(流 handle) -> 新流 handle
              next["model"] = [search 流, calc 流]  (扇入,待 Merge)

superstep 2: Merge([search 流, calc 流]) -> 合并流
              model.StreamCompute(合并流) -> 真 LLM 流
              路由到 END -> 返回流给调用方
```

### 5.3 分支点：peek 首块（不 concat 整流）

分支的 `Cond` 需要 `Message` 决定路由，但顶点产出的是流。**只读首个 chunk 决定路由**（不 concat 整流）：

```go
copies := t.out.Copy(2)
firstChunk, _ := copies[0].Recv()   // 只读首块
targets := c.route(t.v.ID(), firstChunk)
if 单一 END 目标:
    endStream = copies[1]            // 原流(含首块,lazy 缓存)实时返回给调用方
else:
    routeStreamTo(copies[1], targets, next)
```

**为什么可行**：model step1 首块带 ToolCalls（->去工具），step2 首块是 Answer 无 ToolCalls（->去 END）。首块就够决定路由。

**为什么不 concat 整流**：concat 会阻塞着读完全部 chunk 才能决定路由，导致整流被缓冲，调用方拿不到实时流。peek 首块只读一块，后续 chunk 实时流给调用方。这是 eino `StreamGraphBranch` 的思路。

### 5.4 屏障的语义

流式下屏障等所有 `StreamCompute` 返回 handle（异步，数据尚未流动）。图的结构（流 handle 连接）在 superstep 循环中瞬间建立，数据随后 lazy 流过，由下游 Recv() 或分支点 peek 驱动。

## 六、真 LLM 流式（llm.go）

`streamLLM(prompt)` 用 net/http 直连火山方舟 Ark（OpenAI 兼容）：

- **配置**：BaseURL `https://ark.cn-beijing.volces.com/api/plan/v3`，Model `kimi-k3`，Key 读 `ARK_API_KEY` 环境变量
- **流式**：POST `/chat/completions` 带 `stream: true`，响应是 SSE（每行 `data: {json}`，末尾 `data: [DONE]`）
- **解析**：逐行扫描，`json.Unmarshal` 提取 `choices[0].delta.content`，每个 content chunk 发进取的流
- **无外部依赖**：纯标准库（net/http、encoding/json、bufio）

ModelVertex step2 调 `streamLLM`，把每个 LLM content chunk 包成 `Message{Answer: chunk}` 流式发出。延迟来自真实 LLM 推理，无需 `time.Sleep` 模拟。

## 七、语义边界与注意事项

1. **只做 Transform 范式**。Invoke（Run/Compute）、Checkpoint、State 不在本 demo，见 04。StreamRun 不集成 checkpoint。
2. **分支点 peek 首块依赖"首块可决定路由"**。model step1/step2 的首块恰好能区分（有无 ToolCalls）。若分支条件需要完整 Message 才能判断，需 concat 整流（会破坏该处 lazy）或用 eino 的 StreamGraphBranch。
3. **StreamCompute 必须 async**。启 goroutine 消费输入流、产出输出流，立即返回 handle。同步会破坏 lazy 链路导致死锁。
4. **step1 简化没用 tool calling API**。真 ReAct 会让 LLM 决定调哪些工具（tool calling API，需流式累积 tool_call fragments）。demo 固定调 search+calc 以保持代码简短；真 LLM 流式在 step2 体现。
5. **Copy 的 lazy 特性**：消费者速度不同步时，慢的拖住缓存增长，快的能读已缓存部分。源只读一次。
6. **Merge 顺序非确定**：chunk 按到达顺序交错，不保证 search 结果在 calc 之前。
7. **真 LLM 需联网 + API Key**。无 Key 时 `streamLLM` 返回明确错误。非演示环境可换其他 OpenAI 兼容提供方（改 BaseURL/Model）。

## 八、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `StreamReader[T]` / `StreamWriter[T]` | `schema.StreamReader[T]` / `StreamWriter[T]` | 结构一致，demo 3 种内部类型 vs eino 5 种 |
| `Pipe[T]()` | `schema.Pipe[T]()` | channel-based 流 |
| `StreamReaderFromArray` / `wrap` | `schema.StreamReaderFromArray` | 单值->流 |
| `concatStreamReader` + `mergeMessages` | `concatStreamReader` + `ConcatItems` | 流->单值 |
| `Copy(n)` lazy（sync.Once+链表） | `StreamReader.Copy(n)` lazy | 实现一致 |
| `MergeStreamReaders`（goroutine-per-source） | `MergeStreamReaders`（select+reflect.Select） | demo 简化 |
| `StreamCompute` / `StreamRun` | `Transform[I,O]` / `runner.transform` | Transform 范式 |
| 分支点 peek 首块 | `StreamGraphBranch`（流式条件） | 思路一致：用首块决定路由 |
| `streamLLM`（net/http+SSE） | `ark.NewChatModel`（eino-ext） | demo 直连，eino 用组件封装 |
| 不实现 Invoke/Checkpoint/State | `Run`/`checkpoint`/`state.go` | 见 04 |

## 九、简化说明

| # | 简化点 | eino | demo | 影响 |
|---|---|---|---|---|
| 1 | Merge | select + reflect.Select | goroutine-per-source | 无（功能等价） |
| 2 | 分支路由 | StreamGraphBranch | peek 首块 | 思路一致，实现简化 |
| 3 | 范式 | 四范式全实现 + 12 推导 | 只实现 Transform | Invoke 见 04 |
| 4 | LLM 调用 | eino-ext 组件封装 | net/http 直连 | 无（OpenAI 兼容） |
| 5 | StreamReader 类型 | 5 种（含 WithConvert、MultiStream） | 3 种 | 无 WithConvert；Merge 复用 Stream |
| 6 | concat 合并 | 类型注册表 + reflect | 单一 mergeMessages | 只支持 Message |
| 7 | Copy 清理 | close 计数回收 | 无 | 短运行无影响 |
| 8 | tool calling | 流式累积 tool_call fragments | step1 固定 ToolCalls | 真 ReAct 见后续 |

**核心机制全部保留**：StreamReader/Writer、wrap/concat、lazy Copy、Merge、流 handle 跨 superstep、分支 peek 首块、真 LLM 流式。

## 十、后续规划

| 内容 | 状态 |
|------|------|
| 流式执行（Transform + Copy + Merge + 真 LLM） | ✅ |
| 真 tool calling（LLM 决定工具，流式累积 fragments） | 📋 |
| DAG Channel（skip 传播） | 📋 |
| 流式 + checkpoint（concatStream/restoreStream 物化） | 📋 |

## 十一、总结

**流式执行的核心：StreamReader/Writer 是流的载体，wrap/concat 是单值与流的桥，Copy 是扇出，Merge 是扇入，StreamRun 让流 handle 跨 superstep 传递，分支点 peek 首块保持实时流。** demo 接真 LLM（火山方舟 kimi-k3）展示真实逐块流式，延迟来自 LLM 推理本身。Invoke/checkpoint/state 在 04；真 tool calling、流式 checkpoint 留作后续。
