# Handler:回调接口与构造

> 源码:`/Users/songxijun/workspace/otherProject/eino/callbacks/interface.go`、`handler_builder.go`
> 本文讲 Handler 接口、五个切点、NewHandlerBuilder 用法。

## 一、Handler 接口

```go
type Handler interface {
	// OnStart 组件开始执行前
	OnStart(ctx context.Context, info *RunInfo, input CallbackInput) context.Context
	// OnEnd 组件成功执行完成后
	OnEnd(ctx context.Context, info *RunInfo, output CallbackOutput) context.Context
	// OnError 组件执行出错时
	OnError(ctx context.Context, info *RunInfo, err error) context.Context
	// OnStartWithStreamInput 输入是流式，开始前
	OnStartWithStreamInput(ctx context.Context, info *RunInfo, input *schema.StreamReader[CallbackInput]) context.Context
	// OnEndWithStreamOutput 输出是流式，完成后
	OnEndWithStreamOutput(ctx context.Context, info *RunInfo, output *schema.StreamReader[CallbackOutput]) context.Context
	// Needed 判断该切点是否需要处理，返回 false 框架跳过，省去 overhead
	Needed(ctx context.Context, info *RunInfo, timing CallbackTiming) bool
}
```

### 输入输出类型

- `CallbackInput` / `CallbackOutput` 是 `any` 类型，不同组件有不同具体类型
- 需要类型转换，用对应组件包提供的 `ConvCallbackInput` / `ConvCallbackOutput`
- 类型不匹配会返回 `nil`，你可以直接 skip 不处理

## 二、五个切点详解

### 2.1 OnStart

**时机**: 组件开始执行之前

**参数**:
- `ctx`: 当前上下文
- `info`: 运行信息(`Name`/`Type`/`Component`)
- `input`: 组件输入，具体类型看组件

**返回**: 更新后的 context，你可以把 start 时间存入 context，`OnEnd` 取出算耗时

### 2.2 OnEnd

**时机**: 组件**成功**执行完成之后（出错不会进）

**参数**:
- `ctx`: OnStart 返回的 context
- `info`: 运行信息
- `output`: 组件输出

**返回**: 更新后的 context

### 2.3 OnError

**时机**: 组件执行返回 error 时

**参数**:
- `ctx`: OnStart 返回的 context
- `info`: 运行信息
- `err`: 组件返回的错误

### 2.4 OnStartWithStreamInput

**时机**: 组件输入本身是流式（比如 `CollectableLambda` 输入流式）

**重要**: 框架给你的 `input` 是**已经 Copy 过**的独立流，你**必须 Close**，否则 goroutine 泄漏。

### 2.5 OnEndWithStreamOutput

**时机**: 组件输出流式（比如 ChatModel.Stream）

**重要**: 框架给你的 `output` 是**已经 Copy 过**的独立流，你**必须 Close**，否则 goroutine 泄漏。

这是最常用的打点位置——统计 ChatModel 流式输出的 Token 数量就在这里。

## 三、TimingChecker 接口:按需开启减少开销

```go
type TimingChecker interface {
	Needed(ctx context.Context, info *RunInfo, timing CallbackTiming) bool
}
```

如果你没实现某个切点，框架会跳过对该切点的所有处理，不会分配 goroutine 也不会 Copy 流，节省 overhead。

`NewHandlerBuilder` 自动帮你实现 `Needed` 方法——只在你设置过的切点返回 true，其他返回 false。所以一般不需要自己实现 `Needed`。

## 四、构造 Handler:NewHandlerBuilder

大多数情况下，你不需要自己从头实现 `Handler` 接口，用 `NewHandlerBuilder` 只设置你关心的切点即可:

```go
package main

import (
	"context"
	"log"

	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
)

// 只关心 ChatModel 的 OnStart 和 OnEnd
handler := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		mi := model.ConvCallbackInput(input) // 类型转换
		if mi == nil {
			return ctx // 不是 ChatModel 输入，跳过
		}
		log.Printf("[start] %s: %d messages", info.Name, len(mi.Messages))
		return ctx
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		mo := model.ConvCallbackOutput(output)
		if mo == nil {
			return ctx
		}
		if mo.Message != nil && mo.Message.ResponseMeta != nil {
			usage := mo.Message.ResponseMeta.Usage
			log.Printf("[end] %s: %d tokens", info.Name, usage.TotalTokens)
		}
		return ctx
	}).
	Build()
```

`NewHandlerBuilder` 自动实现 `Needed`，你没设置的方法自动返回 false，框架跳过。

## 五、类型转换:ConvCallbackInput / ConvCallbackOutput

每个组件包都提供两个辅助函数:

```go
// model 包
func ConvCallbackInput(in callbacks.CallbackInput) *model.CallbackInput
func ConvCallbackOutput(out callbacks.CallbackOutput) *model.CallbackOutput

// tool 包
func ConvCallbackInput(in callbacks.CallbackInput) *tool.CallbackInput
func ConvCallbackOutput(out callbacks.CallbackOutput) *tool.CallbackOutput {
```

如果输入是对应类型，返回指针；否则返回 `nil`。你判断 `nil` 就跳过，非常方便。

例子:

```go
// 在 OnStart 处理多种组件
handler := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		switch info.Component {
		case components.ComponentOfChatModel:
			mi := model.ConvCallbackInput(input)
			// 处理 ChatModel 输入...
		case components.ComponentOfTool:
			ti := tool.ConvCallbackInput(input)
			// 处理 Tool 输入...
		}
		return ctx
	}).
	Build()
```

## 六、完整示例:简单日志 Handler

```go
// 日志回调，打印每个组件调用
logger := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		log.Printf("[callback] start: component=%s type=%s name=%s\n",
			info.Component, info.Type, info.Name)
		return ctx
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		log.Printf("[callback] end: component=%s type=%s name=%s\n",
			info.Component, info.Type, info.Name)
		return ctx
	}).
	OnErrorFn(func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
		log.Printf("[callback] error: component=%s type=%s name=%s err=%v\n",
			info.Component, info.Type, info.Name, err)
		return ctx
	}).
	Build()
```

## 七、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **流式处理完 goroutine 泄漏** | `OnStartWithStreamInput` / `OnEndWithStreamOutput` 忘记 Close 流 | 这两个切点拿到流必须 Close |
| **类型转换总是 nil** | 用错了包的 `Conv*` | 看 `info.Component` 用对应组件包的转换函数 |
| **没用到的切点也有开销** | 自己实现 Handler 但是没正确实现 `Needed` | 用 `NewHandlerBuilder` 构造，它自动实现 |
| **全局回调不生效** | `AppendGlobalHandlers` 在 graph 编译之后调用 | `AppendGlobalHandlers` 必须在程序初始化调用，执行前 |

## 八、下一步

- 切面注入机制看 [inject.md](./inject.md)
- 完整示例看 [examples.md](./examples.md)
