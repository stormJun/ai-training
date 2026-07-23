# ADK 中间件机制与内置中间件

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/middlewares/`
> 中间件给 ChatModelAgent 横切增加功能，不需要改 ChatModelAgent 核心代码。

## 一、什么是中间件

ADK 中间件就是 `adk.Middleware`，一个函数包装 Agent:

```go
type Middleware func(next adk.Agent) adk.Agent
```

就是“洋葱模型”——你包装 Agent，返回一个新 Agent。

这样:
- 你可以在 Agent 运行**前后**增加自定义逻辑
- 多个中间件可以层层包装
- 不用改 ChatModelAgent 代码，就能加功能

## 二、内置中间件

Eino 已经内置很多常用中间件，拿来即用:

### 2.1 记忆: `memory.Middleware`

已经在 [../06_memory/](../06_memory/) 写完整文档了。

用法:
```go
memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend:       backend,
	ConversationID: convID,
	ContextConfig: memory.ContextConfig{
		MaxTokenSize:   4000,
		IncludeCurrent: true,
	},
	Strategy: memory.NewSlidingWindowStrategy(...),
})

agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
	Middlewares: []adk.Middleware{memMiddleware}, // 加上
	// ...
})
```

### 2.2 摘要压缩: `summarization.Middleware`

当你用摘要压缩策略裁剪对话历史，这个中间件已经做好了。

详见 [../06_memory/middlewares.md](../06_memory/middlewares.md#summarization-strategy摘要压缩)

### 2.3 技能: `skill.Middleware`

技能让你的 Agent 能直接读文件系统，ls/cat/grep 这些系统命令直接当工具用。

```go
skillMiddleware, err := skill.NewMiddleware(skill.Config{
	Backend: filesystem.NewInMemoryBackend(), // 内存文件系统，放你的技能文件
})
```

技能就是**把静态文档变成 Agent 可以调用的工具**，方便用户管理知识库技能。

### 2.4 计划任务: `plantask.Middleware`

给 Agent 添加计划任务管理能力，支持:
- 创建任务
- 更新任务
- 获取任务列表
- 获取任务结果

适合需要分步执行长任务，人工介入审批场景。

### 2.5 工具搜索: `dynamictoolsearch.Middleware`

**动态工具搜索**——当你有很多工具，模型可能搞错工具名，动态从你的工具列表里模糊搜索找到正确工具再调用。提高工具调用正确率。

### 2.6 结果缩减: `reduction.Middleware`

大工具返回结果太大，上下文放不下，自动缩减成不超过token限制的大小。支持两种策略:
- `legacy` —— 直接截断
- `constrained` —— 让模型自己总结工具结果缩减大小

## 三、怎么写自定义中间件

```go
// 日志中间件，打印每个事件
loggingMiddleware := func(next adk.Agent) adk.Agent {
	return func(ctx context.Context, input *adk.AgentInput, opts ...adk.AgentRunOption) *adk.AsyncIterator[*adk.AgentEvent] {
		fmt.Println("agent run start, input messages length:", len(input.Input))
		return next.Run(ctx, input, opts...)
	}
}

// 加到 ChatModelAgent
agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
	Middlewares: []adk.Middleware{loggingMiddleware},
	// ...
})
```

就是这么简单，输入 Agent，输出 Agent，在 `next.Run` 前后加你逻辑。

## 四、中间件顺序

中间件**越先加越先执行**:
```go
Middlewares: []adk.Middleware{mw1, mw2, mw3}
```

包装顺序:
```
mw1(mw2(mw3(agent)))
```

运行顺序:
- mw1 开始 → mw2 开始 → mw3 开始 → 核心agent → mw3 结束 → mw2 结束 → mw1 结束

所以:
- 最外层第一个中间件，最先看到输入，最后看到输出
- 适合日志、监控这种全局横切

## 五、总结

- 中间件是 ADK 核心扩展机制
- 内置常用中间件，开箱即用，特别是记忆
- 自定义中间件写起来简单，任意横切增加功能

## 参考

- ChatModelAgent: [chatmodel_agent.md](./chatmodel_agent.md)
