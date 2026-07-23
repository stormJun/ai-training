# Agent 接口与 Runner 运行时

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/interface.go`、`runner.go`
> ADK 所有智能体都实现 `TypedAgent` 接口，用 `Runner` 运行。

## 一、TypedAgent 接口

```go
// 对于普通消息 `*schema.Message`
type Agent = TypedAgent[*schema.Message]

// TypedAgent 是 ADK 核心智能体接口，参数化消息类型。
// 只有两种消息类型满足 `MessageType` 约束:
//   - *schema.Message
//   - *schema.AgenticMessage
// 用户一般只用 `Agent` = TypedAgent[*schema.Message]
type TypedAgent[M schema.MessageType] interface {
	// Name returns the name of the agent.
	Name(ctx context.Context) string

	// Description returns the description of the agent.
	// Used when this agent is used as a tool by another agent.
	Description(ctx context.Context) string

	// Run runs the agent with the given input, returns an async iterator of events.
	//
	// Each event is a `TypedAgentEvent[M]` that carries an output chunk (can be streaming).
	// Events are yielded in order, and iteration stops when the iterator is done.
	Run(ctx context.Context, input *TypedAgentInput[M], opts ...adk.AgentRunOption) *AsyncIterator[*TypedAgentEvent[M]]
}
```

**要点**:
- `Name` / `Description` 用于当这个 Agent 被当成工具给另一个 Agent 用
- `Run` 返回异步迭代器，就是事件流，支持流式输出

## 二、AgentRunOption

运行选项，你可以:
```go
// WithInterruptInfo sets the interrupt info for resume from interruption.
func WithInterruptInfo(info *adk.ResumeInfo) AgentRunOption

// WithCallbacks adds extra callback handlers for this run.
func WithCallbacks(handlers ...callbacks.Handler) AgentRunOption
```

主要用于**中断恢复**，从中断点恢复执行，人机交互需要。

## 三、TypedAgentEvent 事件

一次运行产出多个事件，每个事件是:

```go
type TypedAgentEvent[M schema.MessageType] struct {
	// Output is the main output of this step.
	Output *TypedAgentOutput[M]

	// Action is the action this agent wants to take after this event.
	// Currently used for agent transfer and exit.
	Action *adk.AgentAction
}

type TypedAgentOutput[M schema.MessageType] struct {
	// Message is the output message content.
	// Is nil if this event doesn have complete message content (streaming).
	Message       M
	// MessageStream is the streaming output content.
	// Is nil if this event doesn have streaming output (complete output is in Message).
	MessageStream *schema.StreamReader[M]
	// Role is the role of this message output.
	// Only meaningful for M = *schema.Message.
	Role          schema.RoleType
	// ToolName is the name of the tool that this output is from.
	// Only non-empty when this agent is called as a tool.
	ToolName        string
}
```

**为什么分 Message / MessageStream**:
- 非流式: `Message` 有完整内容，`MessageStream = nil`
- 流式: `Message = nil`，`MessageStream` 给流，每个 chunk 一个事件

## 四、AsyncIterator 迭代器

就是一个简单的异步迭代器:

```go
type AsyncIterator[T any] struct {
	// Next blocks until the next event is available or we're done.
	// Returns (event, ok) — ok is false when done.
	Next func() (T, bool)
}
```

用法:
```go
iter := agent.Run(ctx, input)
for {
	event, ok := iter.Next()
	if !ok {
		break
	}
	// process event
}
```

## 五、Runner 运行时

```go
// Runner runs an Agent and gives you simpler way to consume events.
type Runner interface {
	// Query runs the agent with the given input messages and returns an iterator over the output events.
	Query(ctx context.Context, input []*schema.Message, opts ...adk.RunnerOption) *adk.Iterator[*adk.AgentEvent]
}

// NewRunner creates a new Runner from an Agent.
func NewRunner(agent adk.Agent, opts ...adk.RunnerOption) *runner
```

**RunnerOption** 选项:
```go
// WithCallbacks adds extra callback handlers that will be called with each event.
func WithCallbacks(callbacks ...callbacks.Callback) RunnerOption
```

使用:
```go
runner := adk.NewRunner(agent)
iter := runner.Query(ctx, []*schema.Message{schema.UserMessage("hello")})
for {
	event, ok := iter.Next()
	if !ok {
		break
	}
	if event.Err != nil {
		return err
	}
	// event.Message 是完整消息，event.MessageStream 是流式
}
```

## 六、设计思想

### 为什么是事件流

LLM 天然流式输出，客户端希望逐块拿到内容，给用户更好体验。事件流模型天然支持流式，每个 chunk 一个事件。

### 为什么 Agent 接口这么设计

- **可组合** — Agent 可以当工具给别的 Agent 用，因为有 Name/Description
- **可流式** — 天然支持流式输出，不需要改接口
- **可中断** — 支持暂停保存检查点，人工恢复

### 底层还是编排

所有 ADK Agent 底层都是 `compose.Graph`，你随时可以导出图自己编排，所以可大可小，可定制可组合。

## 七、参考

- ChatModelAgent 用法: [chatmodel_agent.md](./chatmodel_agent.md)
- 中间件机制: [middlewares.md](./middlewares.md)
- 预置智能体: [prebuilt.md](./prebuilt.md)
