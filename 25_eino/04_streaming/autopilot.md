# 自动流式衔接:编排层替你做了什么

> 源码: `/Users/songxijun/workspace/otherProject/eino/compose/stream_concat.go`、`stream_reader.go`
> 本文讲:在 Chain/Graph 中，编排层怎么自动处理流式，为什么你不需要自己拼 chunk。

## 一、概述

Eino 编排层最舒服的一点就是:**你只需要每个节点产出流，框架自动把节点间流式衔接做好**，不需要你自己写 channel 循环拼 chunk。

不管你是:
- 上游流式产出，下游阻塞消费 → 自动拼接成完整结果
- 上游阻塞产出，下游流式消费 → 自动装箱成流
- 上游多流 → 下游合并成流自动合并
- 一个上游 → 多个下游需要消费 → 自动 Copy 扇出

这就是 Eino 的**流式自动驾驶**，你只需要关心每个节点做什么，不需要关心流式怎么接。

## 二、四种自动处理场景

### 2.1 流式 → 阻塞(拼)

上游节点产出 `StreamReader[T]`，下游节点需要 `T` (阻塞输入):

```
Node A (Stream output) → [框架自动拼] → Node B (block input)
```

框架会把上游所有 chunk 收集起来，拼成完整的 `T`，再传给下游。所以下游不需要改代码，就能消费上游流式输出。

例子:
```go
chain := compose.NewChain[string, string]()
// 1. ChatModel 流式输出 (返回 StreamReader[*schema.Message])
chain.AppendChatModel(chatModel) 
// 2. Lambda 需要完整 string (block input)
chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
	return msg.Content, nil
}))
```

运行:
- 调用 `runnable.Stream` → ChatModel 流式输出，Lambda 等完整消息拼好再执行，最终输出完整 string 流式吗？不，看下面...

### 2.2 阻塞 → 流式(装箱)

上游节点产出 `T` (阻塞输出)，下游节点需要 `StreamReader[T]` (流式输入):

```
Node A (block output) → [框架自动装箱] → Node B (stream input)
```

框架把单个值包装成单元素流，下游直接当流读。不需要上游改代码，直接适配流式下游。

### 2.3 流式 → 流式(拼接)

上游多个节点都是流式输出，汇到下游一个节点:

框架自动**合并**多个上游流，输出一个合并流给下游。

如果是线性:
```
Node A (stream T) → Node B (stream U)
```

框架自动把 `A` 的每个 chunk 传给 `B`，不需要等 `A` 完，`B` 就可以开始处理，真正端到端流式。

**真正的端到端流式**:模型第一个 chunk 出来，一路流到客户端，中间每个节点都可以 chunk 级处理，不需要等上游完。

### 2.4 一个流式 → 多个下游(复制)

一个上游流式输出要给多个下游，框架自动 `Copy`，每个下游拿到完整独立流，不需要你自己调用 `Copy`。

## 三、四种操作对应到自动处理

| 上游输出类型\下游输入类型 | 阻塞 `T` | 流式 `StreamReader[T]` |
|--------------------------|----------|----------------------|
| **阻塞 `T`** | 直接传 | 装箱为单元素流 |
| **流式 `StreamReader[T]`** | 收集拼为完整 `T` | 自动拼接/合并，保持流式 |

- 线性链条上多个节点都流式 → 全程保持流式，端到端逐块传递
- 混合模式自动适配，不需要用户写胶水代码

## 四、Stream 怎么拼给节点输入:字段映射

在 Graph 中用字段映射，上游输出 `StreamReader[T]` 直接映射到下游输入字段，框架自动适配：

```go
// 上游节点输出 struct { Content string; Stream *StreamReader[chunk] }
// 下游输入需要 StreamReader[chunk]，直接映射:
node.AddInput("upstream", compose.FromField("Stream"))
// 框架自动传递，不需要你拼
```

不管上游字段是流式还是阻塞，框架按下游需要自动转换。

## 五、InvokableLambda vs StreamableLambda

Lambda 有四种变体，对应流式不同需求:

| 构造 | 函数签名 | 流式行为 |
|------|----------|----------|
| `InvokableLambda` | `func(ctx, I) (O, error)` | 阻塞，如果输入是流会先拼完整 |
| `StreamableLambda` | `func(ctx, I) (*StreamReader[O], error)` | 流式，产出流 |
| `CollectableLambda` | `func(ctx, *StreamReader[I]) (O, error)` | 输入流式，输出阻塞 |
| `TransformableLambda` | `func(ctx, *StreamReader[I]) (*StreamReader[O], error)` | 输入流式，输出流式 |

编排层自动根据你选的变体处理流式，不需要额外处理。

例子:
```go
// 输入完整文本，输出流式转换
lambda := compose.TransformableLambda(
	func(ctx context.Context, sr *schema.StreamReader[string]) (*schema.StreamReader[string], error) {
		return schema.StreamReaderWithConvert(sr, func(s string) (string, error) {
			return fmt.Sprintf("> %s", s), nil
		}), nil
	})
```

放进 Chain，上游流式输入，下游直接拿到转换后的流式输出，全程流式。

## 六、完整示例:端到端流式 ChatModel

```go
chain := compose.NewChain[string, string]()

// 1. string → []*schema.Message (block)
chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
	return []*schema.Message{schema.UserMessage(q)}, nil
}))

// 2. ChatModel.Stream → *schema.StreamReader[*schema.Message] (stream output)
chain.AppendChatModel(chatModel) // ChatModel 本身支持 Stream

// 3. *schema.Message → string (block input, 框架自动拼完整 message)
chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
	return msg.Content, nil
}))

runnable, _ := chain.Compile(ctx)

// 调用 Stream → 输出  string 的流，逐块产出
// ChatModel 每个 chunk → 框架直接透传 → 最终输出就是逐块的
reader, err := runnable.Stream(ctx, "讲个故事")
if err != nil { panic(err) }
defer reader.Close()

for {
	chunk, err := reader.Recv()
	if errors.Is(err, io.EOF) {
		break
	}
	if err != nil { panic(err) }
	fmt.Print(chunk) // 逐块打印，和 ChatModel 输出节奏一致
}
```

整个过程你只需要:
- ChatModel 支持 Stream
- 最后一步接收完整 string
- 调用 `runnable.Stream` 得到输出流

框架自动把 ChatModel 的流式输出拼给最后 Lambda，Lambda 输出完整 string 再装箱成流给你。全程流式，你没写一行流式拼接代码。

## 七、和手动流式对比

| 对比 | 手动流式 | Eino 自动流式 |
|------|----------|----------------|
| 节点间衔接 | 需要自己写 channel 循环拼 chunk | 自动适配 |
| 混合阻塞/流式 | 需要自己写胶水 | 自动转换 |
| 多流合并 | 需要自己处理 select | 自动 Merge |
| 扇出多消费者 | 需要自己 Copy 实现 | 自动 Copy |

Eino 把流式变成"每个节点管好自己，框架接管子间"，大幅减少样板代码。

## 八、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **InvokableLambda 让流式退化** | 你用了 `InvokableLambda` 接收流式输入，它会拼完整 | 需要接收流用 `CollectableLambda` / `TransformableLambda` |
| **全程流式但最后还是一块出来** | 最后一步是 `InvokableLambda` 返回阻塞，编译器没地方装箱 | 最后一步用 `StreamableLambda` 输出流 |
| **多个上游流到下游，顺序不对** | 多个上游并行，框架按就绪顺序合并，不是固定顺序 | 需要顺序不要合并，自己拼 |
| **流式节点比阻塞慢很多** | 多个大缓冲chunk，框架每次都走 select 调度 | 正常，流式就是这样，用户看到内容更快 |

## 九、小结

Eino 流式的核心设计哲学:

> **流式是贯穿全栈的抽象，每个节点只需要说清楚自己输入输出是流还是block，框架搞定一切衔接**。

你不需要:
- 自己写 channel 循环拼 chunk
- 自己处理多流合并
- 自己处理扇出复制
- 自己适配阻塞/流式转换

编排层的"流式自动驾驶"让你既得到流式的用户体验，又不用写流式的样板代码。

## 十、参考

- 基础 API: [stream_api.md](./stream_api.md)
- 流操作: [convert_merge_copy.md](./convert_merge_copy.md)
- 底层设计: [source_notes/stream_design.md](../source_notes/stream_design.md)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/compose/stream_concat.go`
