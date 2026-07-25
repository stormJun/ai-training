# Chain:线性编排

> 源码:`/Users/songxijun/workspace/otherProject/eino/compose/chain.go`、`types_lambda.go`
> Chain 是编排层最简单的原语:把组件按线性顺序串成一条流水线。

## 一、概述

Chain 是**线性序列**:一进一出,前一个节点的输出是后一个节点的输入。适合步骤固定、无分支的流程,例如:

```
模板渲染 -> ChatModel -> 提取内容
```

它的定位是 Graph 的线性特例--Chain 内部即一个线性 Graph,但提供更简洁的 fluent API。

## 二、API:fluent builder + 泛型

```go
// chain.go:37
func NewChain[I, O any](opts ...NewGraphOption) *Chain[I, O]

// chain.go:157
func (c *Chain[I, O]) Compile(ctx context.Context, opts ...GraphCompileOption) (Runnable[I, O], error)
```

- **`NewChain[I, O]`** -- 泛型参数 `I`、`O` 是整条链的输入、输出类型,编译期确定。
- **`AppendXxx`** -- 每个方法**返回 `*Chain[I, O]` 自身**(fluent builder),可链式调用。
- **`Compile`** -- 编译产出 `Runnable[I, O]`,提供 `Invoke` / `Stream` / `Collect`。

支持的节点(`chain.go`):

| 方法 | 接入组件 |
|---|---|
| `AppendChatModel`(`:171`) | ChatModel |
| `AppendChatTemplate`(`:198`) | ChatTemplate(模板渲染) |
| `AppendToolsNode`(`:224`) | ToolsNode |
| `AppendRetriever`(`:297`) | Retriever |
| `AppendEmbedding`(`:278`) | Embedding |
| `AppendDocumentTransformer`(`:250`) | 文档变换(切分等) |
| `AppendLoader`(`:309`) / `AppendIndexer`(`:327`) | 加载 / 索引 |
| `AppendLambda`(`:266`) | Lambda(任意 Go 函数) |
| `AppendPassthrough`(`:533`) | 透传(原样传递) |
| `AppendGraph`(`:522`) | 嵌套另一个图 |
| `AppendBranch`(`:342`) / `AppendParallel`(`:459`) | 分支 / 并行(见 §6) |

另有 `AppendAgenticModel` / `AppendAgenticChatTemplate` / `AppendAgenticToolsNode` 等 agentic 变体。

## 三、类型流转

Chain 是**强类型**的:每个节点有固定的输入/输出类型,相邻节点必须类型匹配(编译期 `Compile` 校验)。常见组件的 in/out:

| 组件 | 输入 | 输出 |
|---|---|---|
| ChatModel | `[]*schema.Message` | `*schema.Message` |
| ChatTemplate | 模板变量(如 `map[string]any`) | `[]*schema.Message` |
| ToolsNode | `*schema.Message`(含 ToolCalls) | `[]*schema.Message` |
| Lambda | `I`(自定义) | `O`(自定义) |

两种典型衔接:

1. **类型自然对齐**--如 `ChatTemplate -> ChatModel`(都是 `[]*schema.Message`),无需胶水。
2. **类型不匹配**--用 **Lambda** 做转换,如把 `string` 转成 `[]*schema.Message`。

## 四、Lambda:类型胶水与自定义逻辑

Lambda 把任意 Go 函数接入链(`types_lambda.go:56`)。按对流式的处理方式分四种:

| 构造器 | 函数签名 | 语义 |
|---|---|---|
| `InvokableLambda[I,O]`(`:105`) | `func(ctx, I) (O, error)` | 阻塞:单值进、单值出 |
| `StreamableLambda[I,O]`(`:119`) | `func(ctx, I) (*StreamReader[O], error)` | 单值进、流式出 |
| `CollectableLambda` | `func(ctx, *StreamReader[I]) (O, error)` | 流式进、单值出(收集) |
| `TransformableLambda` | `func(ctx, *StreamReader[I]) (*StreamReader[O], error)` | 流式进、流式出(变换) |

另有 `AnyLambda`(`:174`)可同时提供 invoke + stream 实现,以及带 `TOption` 的 `*WithOption` 变体。

> 关键(`chain.go:263` 注释):若希望该节点在流式调用中**真正产出流**,需用 `StreamableLambda` 或 `TransformableLambda`;只用 `InvokableLambda` 时,流式模式下该节点会退化为"先算完再一次性发出"。

## 五、完整示例

### 5.1 用 Lambda 做类型胶水

把一个 `string` 问题,经 ChatModel 生成,再取回 `string` 内容:

```go
chain := compose.NewChain[string, string]()

// string -> []*schema.Message（Lambda 做转换）
chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
    return []*schema.Message{schema.UserMessage(q)}, nil
}))

// []*schema.Message -> *schema.Message
chain.AppendChatModel(chatModel)

// *schema.Message -> string（Lambda 提取内容）
chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
    return msg.Content, nil
}))

runnable, err := chain.Compile(ctx)
if err != nil {
    return err
}

out, err := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
// out 是 string，即模型回复内容
```

`NewChain[string, string]` 表明整条链:输入 string,输出 string。两个 Lambda 把 ChatModel 的 `[]*Message` / `*Message` 适配回 string。

### 5.2 类型自然对齐(用 ChatTemplate)

ChatTemplate 产出 `[]*schema.Message`,正好是 ChatModel 的输入,无需 Lambda 胶水:

```go
// 模板：map[string]any -> []*schema.Message
tpl, _ := prompt.FromMessages(schema.FString,
    &schema.Message{Role: schema.User, Content: "用一句话介绍 {topic}"})

chain := compose.NewChain[map[string]any, string]()
chain.AppendChatTemplate(tpl)        // map -> []*Message
chain.AppendChatModel(chatModel)     // []*Message -> *Message
chain.AppendLambda(compose.InvokableLambda(   // *Message -> string
    func(ctx context.Context, msg *schema.Message) (string, error) {
        return msg.Content, nil
    }))

runnable, _ := chain.Compile(ctx)
out, _ := runnable.Invoke(ctx, map[string]any{"topic": "Go 语言"})
```

## 六、流式:Chain 自动衔接

调用 `runnable.Stream(ctx, input)` 时,Chain 自动处理跨节点的流式衔接(拼接、装箱,见 [`../source_notes/stream_design.md`](../source_notes/stream_design.md)):

```go
reader, err := runnable.Stream(ctx, "用一句话介绍 Go 语言")
defer reader.Close()
for {
    chunk, err := reader.Recv()
    if errors.Is(err, io.EOF) { break }
    // chunk 是 string，逐块产出
}
```

但要注意 §4 的提醒:链中若有 Lambda,只有用 `StreamableLambda`/`TransformableLambda` 实现的节点才真正逐块产出;`InvokableLambda` 节点在流式下会阻塞到算完再发。因此**整条链的流式效果取决于最"不流式"的节点**。

## 七、超越线性:Branch 与 Parallel

Chain 虽是线性,但通过 `AppendBranch`(`chain.go:342`)和 `AppendParallel`(`:459`)支持条件分支与并行:

- **`AppendBranch`** -- 接 `ChainBranch`,按条件选下一条边(详见 `graph_basics.md` 的分支)。
- **`AppendParallel`** -- 接 `Parallel`,同时跑多个分支并合并结果。

这两者本质是 Graph 的分支/并行能力在 Chain 上的暴露。需要复杂拓扑时,建议直接用 Graph(见 `graph_basics.md`)。

## 八、与 Graph 的关系

Chain 是 Graph 的线性特例:

- Chain 内部即一个线性 Graph(`Chain.compile` 委托给底层 graph 编译,`chain.go:88`)。
- Chain 的 fluent API(`AppendXxx`)比 Graph 的 `AddXxxNode + AddEdge` 更简洁,但表达力限于线性(+ 分支/并行扩展)。
- 需要任意 DAG 拓扑、多输入多输出、显式字段映射时,用 Graph。

## 九、常见坑与排错

- **节点间类型不匹配 -> Compile 报错** -- Chain 编译期校验相邻节点 in/out 类型;如 `ChatModel`(出 `*Message`)后接期望 `string` 的 Lambda 会失败。中间插 Lambda 做类型转换(见 §5.1)。
- **`InvokableLambda` 导致流式退化** -- 链中 `InvokableLambda` 节点在 `Stream` 模式下会读尽上游流、算完再一次性发出,**整链流式被压成一块**(本目录 `../02_components/demo/chain_demo/` 实测 Stream 仅 1 个 chunk)。需真正逐块流式用 `StreamableLambda`/`TransformableLambda`。
- **`AppendLambda` 顺序即连接顺序** -- Chain 靠 Append 顺序隐式连边;漏 Append 或顺序错会导致类型/逻辑错乱,且无显式 key 可查。
- **`WithTemperature` 等调用时选项不传到组件** -- 选项要在 `Invoke`/`Stream` 调用时传(`runnable.Invoke(ctx, in, compose.WithCallbacks(...))` 等),不是 Append 时;Append 时只能传 `GraphAddNodeOpt`。
- **Branch/Parallel 在 Chain 中是 `AppendBranch`/`AppendParallel`** -- 不是 `AddBranch`;且 `ChainBranch`/`Parallel` 需单独构造后 Append,复杂拓扑建议直接用 Graph。

## 十、小结

| 关注点 | Chain 的解法 |
|---|---|
| 线性流程 | fluent `AppendXxx` 链式拼接 |
| 类型安全 | 泛型 `Chain[I,O]` + 编译期校验节点间类型匹配 |
| 类型不匹配 | `Lambda` 做转换胶水 |
| 自定义逻辑 | `InvokableLambda` / `StreamableLambda` 等 |
| 流式 | `Stream` 自动衔接;Lambda 需选对流式变体 |
| 分支/并行 | `AppendBranch` / `AppendParallel`(复杂场景用 Graph) |

Chain 适合"固定步骤、无分支"的流水线,是把组件快速串成可运行流程的最简方式。一旦流程需要复杂拓扑或有环循环(如 ReAct),就该上 Graph 或 Agent。

## 十一、参考

- [Chain & Graph 介绍](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/chain_graph_introduction/)
- [编排设计原则](https://www.cloudwego.io/zh/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/compose/chain.go`
