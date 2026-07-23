# 切面注入:组件如何集成回调

> 源码:`/Users/songxijun/workspace/otherProject/eino/callbacks/aspect_inject.go`
> 本文讲组件实现者如何在组件中调用回调，上下文传递规则。

## 一、概览

回调注入是**组件实现者**的工作:你实现一个组件（比如自定义 ChatModel），需要在正确的地方调用 `callbacks.OnStart` / `callbacks.OnEnd` 等方法，框架才能把回调切进去。

如果你用的是 eino 官方提供的组件，已经集成好了，你不需要改。只有**自定义组件实现**的时候需要看本文。

## 二、基本流程

一个组件的正确回调集成:

```go
func (m *MyChatModel) Generate(
	ctx context.Context,
	input []*schema.Message,
	opts ...model.Option,
) (*schema.Message, error) {
	// 1. 开头: EnsureRunInfo + OnStart
	ctx = callbacks.EnsureRunInfo(ctx, m.GetType(), components.ComponentOfChatModel)
	ctx = callbacks.OnStart(ctx, &model.CallbackInput{
		Messages: input,
	})

	// 2. 真正执行...
	resp, err := m.doGenerate(ctx, input, opts...)

	// 3. 如果出错: OnError
	if err != nil {
		ctx = callbacks.OnError(ctx, err)
		return nil, err
	}

	// 4. 成功: OnEnd
	ctx = callbacks.OnEnd(ctx, &model.CallbackOutput{
		Message: resp,
	})

	return resp, nil
}
```

就是这么简单:
- `EnsureRunInfo` 在最开头保证 context 有 `RunInfo`
- 开始前 `OnStart`
- 出错 `OnError`
- 成功 `OnEnd`

## 三、各种情况示例

### 3.1 普通阻塞组件（上面已经说了）

```go
// 完整示例
func (m *MyChatModel) Generate(
	ctx context.Context,
	input []*schema.Message,
	opts ...model.Option,
) (*schema.Message, error) {
	ctx = callbacks.EnsureRunInfo(ctx, m.GetType(), components.ComponentOfChatModel)
	ctx = callbacks.OnStart(ctx, &model.CallbackInput{
		Messages: input,
	})

	resp, err := m.inner.Generate(ctx, input, opts...)
	if err != nil {
		callbacks.OnError(ctx, err)
		return nil, err
	}

	ctx = callbacks.OnEnd(ctx, &model.CallbackOutput{
		Message: resp,
	})

	return resp, nil
}
```

### 3.2 流式输出组件

组件输出是 `*schema.StreamReader[T]`:

```go
func (m *MyChatModel) Stream(
	ctx context.Context,
	input []*schema.Message,
	opts ...model.Option,
) (*schema.StreamReader[*schema.Message], error) {
	ctx = callbacks.EnsureRunInfo(ctx, m.GetType(), components.ComponentOfChatModel)
	ctx = callbacks.OnStart(ctx, &model.CallbackInput{
		Messages: input,
	})

	// 流式输出，调用 do Stream
	output, err := m.inner.Stream(ctx, input, opts...)
	if err != nil {
		callbacks.OnError(ctx, err)
		return nil, err
	}

	// 流式输出，用 OnEndWithStreamOutput
	ctx, output = callbacks.OnEndWithStreamOutput(ctx, output)
	return output, nil
}
```

关键:
- `OnEndWithStreamOutput` 不是 `OnEnd`
- 返回的 `output` 是框架包装过的，直接返回给上层就可以
- 每个 Handler 会拿到流的 Copy，各自 Close，你不用管关闭

### 3.3 流式输入组件

组件输入是 `*schema.StreamReader[T]`（比如 `CollectableLambda`）:

```go
func (t *MyTransformer) Transform(
	ctx context.Context,
	input *schema.StreamReader[*schema.Document],
	opts ...document.TransformerOption,
) (*schema.StreamReader[*schema.Document], error) {
	ctx = callbacks.EnsureRunInfo(ctx, "MyTransformer", components.ComponentOfTransformer)
	// 流式输入，用 OnStartWithStreamInput
	ctx, input = callbacks.OnStartWithStreamInput(ctx, input)

	// 处理...
	output, err := t.doTransform(ctx, input)
	if err != nil {
		callbacks.OnError(ctx, err)
		return nil, err
	}

	ctx, output = callbacks.OnEndWithStreamOutput(ctx, output)
	return output, nil
}
```

关键:
- 输入是流式 → `OnStartWithStreamInput`
- 输出是流式 → `OnEndWithStreamOutput`
- 拿到的 `newStreamReader` 是框架包装过的，直接用

### 3.4 组件调用组件:内部调用如何继承回调

如果你的组件内部调用另一个组件，需要用 `ReuseHandlers` 继承回调，同时给内部组件设置新的 `RunInfo`:

```go
// 外层组件内部调用内层组件
func (outer *OuterComponent) DoSomething(ctx context.Context, input Input) (Output, error) {
	// outer 自己已经走了 EnsureRunInfo / OnStart
	// ...

	// 内部组件需要复用当前 context 里的 handlers，重新设置 RunInfo
	innerCtx := callbacks.ReuseHandlers(ctx, &callbacks.RunInfo{
		Type:      inner.GetType(),
		Component: components.ComponentOfChatModel,
		Name:      "inner-chat-model",
	})

	// 用 innerCtx 调用内层组件
	// 内层组件自己的 EnsureRunInfo / OnStart 会继承 handlers
	output, err := outer.inner.Generate(innerCtx, ...)
	// ...
	return output, err
}
```

这样全局回调会同时命中外层和内层组件，都有回调。

### 3.5 独立使用组件（不在 Graph 里）

如果你单独调用一个组件，需要自己 `InitCallbacks`:

```go
ctx := callbacks.InitCallbacks(context.Background(), &callbacks.RunInfo{
	Type:      chatModel.GetType(),
	Component: components.ComponentOfChatModel,
	Name:      "my-chat",
}, myHandler1, myHandler2)

// 然后直接调用，你的 handlers 会被调用
resp, err := chatModel.Generate(ctx, input)
```

Graph/Chain 编排会自动做 `InitCallbacks`，不用你手动调用。

## 四、IsCallbacksEnabled 组件开关

组件可以实现 `components.Checker` 接口:

```go
type Checker interface {
	IsCallbacksEnabled() bool
}
```

返回 `false` 表示组件**自己处理回调**，框架不会自动注入，组件实现者自己调用 `OnStart` 等方法。**几乎所有组件都应该返回 true**，让框架自动注入。

什么时候返回 `false`?
- 组件自己已经在内部调用了 `callbacks.OnStart` 等（就是你现在看本文实现自定义组件）
- 性能原因，完全不需要回调

Eino 官方组件都返回 `true`，框架自动处理。

## 五、上下文传递规则

- `OnStart` 返回 `ctx`，这个 `ctx` 必须传给后面的 `OnEnd` / `OnError`
- Handler 可以把自己的状态存在 `ctx` 里（比如 `startTime`），`OnEnd` 从 `ctx` 拿出来用
- 不同 Handler 之间 context 不共享，每个 Handler 自己的 context 链式传递
- 同一个 Handler 的 `OnStart` → `OnEnd` 能拿到 context

```go
// 示例:计时 Handler
handler := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		return context.WithValue(ctx, "startTime", time.Now()) // 存进去
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		start := ctx.Value("startTime").(time.Time) // 拿出来
		elapsed := time.Since(start)
		log.Printf("[%s] elapsed: %v", info.Name, elapsed)
		return ctx
	}).
	Build()
```

## 六、CallbackInput / CallbackOutput 定义

每个组件定义自己的 `CallbackInput` / `CallbackOutput`，放在组件包内。例如:

**model 包:**
```go
// model/callback.go
type CallbackInput struct {
	Messages []*schema.Message
	Tools    []*schema.ToolInfo
	Extra    map[string]any
}

type CallbackOutput struct {
	Message        *schema.Message
	ResponseMeta   *schema.ResponseMeta
	Extra          map[string]any
}

func ConvCallbackInput(in callbacks.CallbackInput) *CallbackInput {
	// 类型断言，不匹配返回 nil
	mi, ok := in.(*CallbackInput)
	if !ok {
		return nil
	}
	return mi
}

func ConvCallbackOutput(out callbacks.CallbackOutput) *CallbackOutput {
	// ...
}
```

你的自定义组件也应该按照这个模式提供 `ConvCallbackInput` / `ConvCallbackOutput`，方便用户写 Handler。

## 七、常见坑

| 问题 | 原因 | 解法 |
|------|------|------|
| **回调没触发** | 忘记 `EnsureRunInfo` | 开头必须 `ctx = callbacks.EnsureRunInfo(ctx, typ, component)` |
| **流式回调 goroutine 泄漏** | Handler 没 Close 复制的流 | `OnStartWithStreamInput` / `OnEndWithStreamOutput` 里得到流，处理完一定要 Close |
| **内部组件没触发回调** | 没有用 `ReuseHandlers` 包装 context | 内部调用必须用 `callbacks.ReuseHandlers` 继承 |
| **所有切点都触发， overhead 大** | 自己实现 `Handler` 没实现 `TimingChecker.Needed` | 用 `NewHandlerBuilder` 构造，自动实现，只开你设置的切点 |

## 八、总结

组件集成回调其实很简单，记住步骤:

1. **开头**: `ctx = callbacks.EnsureRunInfo(ctx, type, component)`
2. **开始前**: `ctx = callbacks.OnStart(ctx, input)`
3. **执行**: 你的逻辑
4. **出错**: `callbacks.OnError(ctx, err)` → return
5. **成功结束**: `ctx = callbacks.OnEnd(ctx, output)` → return
6. **输入流式**: `ctx, input = callbacks.OnStartWithStreamInput(ctx, input)`
7. **输出流式**: `ctx, output = callbacks.OnEndWithStreamOutput(ctx, output)`

按照这个流程，你的组件就完美集成了 Eino 回调切面，用户加的所有 Handler 都会在正确切点触发。

## 九、参考

- Handler 构造: [handler.md](./handler.md)
- 使用示例: [examples.md](./examples)
