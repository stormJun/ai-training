# 常见使用示例

> 本文给出几个最常见的回调使用场景:日志、耗时统计、Token 计数、链路追踪。

## 一、简单日志打印

打印每个组件调用的输入输出:

```go
package main

import (
	"context"
	"log"

	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components"
)

// 日志回调
logger := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		switch info.Component {
		case components.ComponentOfChatModel:
			mi := model.ConvCallbackInput(input)
			if mi != nil {
				log.Printf("[start] %s (%s) >> %d messages", info.Name, info.Type, len(mi.Messages))
			}
		default:
			log.Printf("[start] %s (%s)", info.Name, info.Type)
		}
		return ctx
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		switch info.Component {
		case components.ComponentOfChatModel:
			mo := model.ConvCallbackOutput(output)
			if mo != nil && mo.Message != nil && mo.Message.ResponseMeta != nil {
				log.Printf("[end] %s (%s) << %d tokens", info.Name, info.Type, mo.Message.ResponseMeta.Usage.TotalTokens)
			} else {
				log.Printf("[end] %s (%s)", info.Name, info.Type)
			}
		default:
			log.Printf("[end] %s (%s)", info.Name, info.Type)
		}
		return ctx
	}).
	OnErrorFn(func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
		log.Printf("[error] %s (%s) >> %v", info.Name, info.Type, err)
		return ctx
	}).
	Build()

// 作为全局回调添加
callbacks.AppendGlobalHandlers(logger)
```

## 二、耗时统计

统计每个组件调用的耗时，用于性能分析:

```go
package main

import (
	"context"
	"log"
	"time"

	"github.com/cloudwego/eino/callbacks"
)

// 计时回调
timer := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		start := time.Now()
		return context.WithValue(ctx, struct{}{"start"}, start) // 存开始时间
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		start := ctx.Value(struct{}{"start"}).(time.Time)
		elapsed := time.Since(start)
		log.Printf("[%s] elapsed: %v", info.Name, elapsed)
		return ctx
	}).
	OnErrorFn(func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
		start := ctx.Value(struct{}{"start"}).(time.Time)
		elapsed := time.Since(start)
		log.Printf("[%s] error after %v: %v", info.Name, elapsed, err)
		return ctx
	}).
	Build()

callbacks.AppendGlobalHandlers(timer)
```

## 三、ChatModel Token 计数

统计每个 ChatModel 调用 Token 使用量，方便计费和监控:

```go
package main

import (
	"context"
	"sync/atomic"

	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components"
)

// Token 计数器
type TokenCounter struct {
	promptTokens     atomic.Int64
	completionTokens atomic.Int64
	totalTokens      atomic.Int64
}

func (c *TokenCounter) Handler() callbacks.Handler {
	return callbacks.NewHandlerBuilder().
		OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
			if info.Component != components.ComponentOfChatModel {
				return ctx
			}
			mo := model.ConvCallbackOutput(output)
			if mo == nil || mo.Message == nil || mo.Message.ResponseMeta == nil {
				return ctx
			}
			usage := mo.Message.ResponseMeta.Usage
			c.promptTokens.Add(usage.PromptTokens)
			c.completionTokens.Add(usage.CompletionTokens)
			c.totalTokens.Add(usage.TotalTokens)
			return ctx
		}).
		Build()
}

// 使用
counter := &TokenCounter{}
callbacks.AppendGlobalHandlers(counter.Handler())

// 运行后看统计
fmt.Printf("prompt tokens: %d\n", counter.promptTokens.Load())
fmt.Printf("completion tokens: %d\n", counter.completionTokens.Load())
fmt.Sprintf("total tokens: %d\n", counter.totalTokens.Load())
```

## 四、流式 Token 统计

流式输出也要统计 Token，在 `OnEndWithStreamOutput` 处理:

```go
package main

import (
	"context"
	"errors"
	"io"
	"sync/atomic"

	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components"
	"github.com/cloudwego/eino/schema"
)

type StreamTokenCounter struct {
	promptTokens     atomic.Int64
	completionTokens atomic.Int64
	totalTokens      atomic.Int64
}

func (c *StreamTokenCounter) Handler() callbacks.Handler {
	return callbacks.NewHandlerBuilder().
		// 输入在 OnStart 已经有了
		OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
			if info.Component != components.ComponentOfChatModel {
				return ctx
			}
			mi := model.ConvCallbackInput(input)
			if mi == nil {
				return ctx
			}
			// prompt tokens 已经在 input 里，如果你的模型计算了可以这里统计
			// 多数模型prompt tokens 在输出 ResponseMeta 里，所以等 OnEndWithStreamOutput
			return ctx
		}).
		// 流式输出，在 OnEndWithStreamOutput 统计
		OnEndWithStreamOutputFn(func(ctx context.Context, info *callbacks.RunInfo, output *schema.StreamReader[callbacks.CallbackOutput]) context.Context {
			defer output.Close() // 必须关闭！！！

			if info.Component != components.ComponentOfChatModel {
				return ctx
			}

			var totalPrompt int64
			var totalCompletion int64

			for {
				out, err := output.Recv()
				if errors.Is(err, io.EOF) {
					break
				}
				if err != nil {
					return ctx
				}

				mo := model.ConvCallbackOutput(out)
				if mo == nil || mo.Message == nil || mo.Message.ResponseMeta == nil {
					continue
				}

				usage := mo.Message.ResponseMeta.Usage
				totalPrompt += usage.PromptTokens
				totalCompletion += usage.CompletionTokens
			}

			c.promptTokens.Add(totalPrompt)
			c.completionTokens.Add(totalCompletion)
			c.totalTokens.Add(totalPrompt + totalCompletion)

			return ctx
		}).
		Build()
}
```

**重要**: 你必须 `defer output.Close()`，否则 goroutine 泄漏。

## 五、OpenTelemetry 链路追踪

集成 OpenTelemetry，给每个组件调用创建 span:

```go
package main

import (
	"context"

	"github.com/cloudwego/eino/callbacks"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// OTel 回调
tracer := otel.Tracer("eino")

otelHandler := callbacks.NewHandlerBuilder().
	OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
		ctx, span := tracer.Start(ctx,
			info.Component+"."+info.Type,
			trace.WithAttributes(
				attribute.String("eino.component.name", info.Name),
				attribute.String("eino.component.type", info.Type),
			}))
		return ctx
	}).
	OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
		span := trace.SpanFromContext(ctx)
		span.End()
		return ctx
	}).
	OnErrorFn(func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
		span := trace.SpanFromContext(ctx)
		span.RecordError(err)
		span.End()
		return ctx
	}).
	// 流式输入处理类似，span 生命周期一样
	OnStartWithStreamInputFn(func(ctx context.Context, info *callbacks.RunInfo, input *schema.StreamReader[callbacks.CallbackInput]) context.Context {
		defer input.Close()
		ctx, span := tracer.Start(ctx,
			info.Component+"."+info.Type,
			trace.WithAttributes(
				attribute.String("eino.component.name", info.Name),
				attribute.String("eino.component.type", info.Type),
				attribute.Bool("streaming_input", true),
			}))
		return ctx
	}).
	OnEndWithStreamOutputFn(func(ctx context.Context, info *callbacks.RunInfo, output *schema.StreamReader[callbacks.CallbackOutput]) context.Context {
		defer output.Close()
		span := trace.SpanFromContext(ctx)
		span.End()
		return ctx
	}).
	Build()

callbacks.AppendGlobalHandlers(otelHandler)
```

## 六、单次调用添加回调

全局回调对所有调用生效，如果只想给**某次调用**加回调，可以在 `Invoke` / `Stream` 调用时传:

```go
// Runnable 调用时添加
result, err := runnable.Invoke(ctx, input,
	compose.WithCallbacks(myHandler1, myHandler2),
)
```

这些回调会和全局回调合并，本次调用生效。

## 七、给 Graph 某个节点单独加回调

在 Graph 添加节点的时候，可以给单个节点加回调:

```go
graph := compose.NewGraph[string, string]()
graph.AddChatModelNode("chat", chatModel,
	compose.WithCallbacks(nodeHandler), // 仅这个节点生效
)
```

## 八、完整示例:多个回调组合

```go
package main

import (
	"github.com/cloudwego/eino/callbacks"
)

func main() {
	// 多个全局回调
	logger := buildLogger()
	timer := buildTimer()
	tokenCounter := buildTokenCounter()
	otel := buildOTel()

	// 依次添加，都生效
	callbacks.AppendGlobalHandlers(logger, timer, tokenCounter, otel)
}
```

多个 Handler 按添加顺序执行，互不影响。

## 总结

回调机制非常灵活，你可以:
- 全局添加，对所有调用生效
- 单次调用添加，只对本次生效
- 单个节点添加，只对该节点生效
- 每个切点你只实现关心的，不增加 overhead

常见可观测性需求都能通过回调满足，Eino 不绑定特定监控系统，你自己集成就可以。
