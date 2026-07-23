# 核心概念:对话记忆与上下文裁剪

> 在多轮对话中，记忆管理解决两个问题:
> 1. 对话历史需要持久化，跨轮次/跨进程保留
> 2. LLM 上下文窗口有限，长对话需要裁剪才能放进去

## 一、什么是记忆

记忆 = **持久化的对话历史**。

用户和 Agent 每轮对话:
- 用户说一句话，加入记忆
- Agent 回复一句话，加入记忆
- 下一轮，Agent 能看到**所有历史**

没有记忆，每轮都是孤立对话，无法"记住"之前聊了什么。

## 二、为什么需要裁剪

每个 LLM 都有**固定的上下文窗口大小**（token 数量限制）:
- 比如 GPT-4o 是 128K token
- 开聊之后，每轮都会新增 token
- 聊多了总 token 就会超过限制 → 模型报错或者丢前边内容

所以需要**在把历史喂给模型之前裁剪**，保证总 token 不超过限制。

## 三、常见裁剪策略

| 策略 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **滑动窗口** | 保留最近 N 轮，扔掉前边的 | 实现简单，速度快 | 扔掉前边有用信息 |
| **摘要压缩** | 每轮把整个历史 summarize 成一段，保留最新几段 | 保留更多信息，不容易丢关键内容 | 每轮都要调用 LLM 生成摘要，增加耗时 |
| **检索插入** | 把历史切块存入向量库，提问时检索相关历史插入 | 长对话也能保留更多相关信息 | 增加 embedding 检索，复杂度高 |

Eino ADK 内置前两种: `slidingwindow` 和 `summarization`，检索插入需要自己组合。

## 四、Eino 记忆架构

Eino 把记忆分成两个独立概念:

```
┌─────────────┐   ┌─────────────┐
│ Backend     │   │ Middleware │
│ 存储完整历史 │   │ 裁剪给模型看 │
└─────────────┘   └─────────────┘
```

1. **Backend**: 存储**完整**对话历史
   - 支持持久化（文件系统），跨进程保留
   - Middleware 从这里读完整历史，裁剪后给模型

2. **Memory Middleware**: ADK 中间件，在模型调用前裁剪
   - 从 Backend 读完整历史
   - 根据配置策略裁剪出不超过限制大小
   - 把裁剪后的历史给 ChatModel

这样分工的好处:
- 你可以换裁剪策略不换存储
- 可以换存储不换裁剪策略
- 完整历史一直保存在 Backend，裁剪只是给模型看，原始信息不丢

## 五、基本流程

```go
// 1. 构造 Backend
backend := filesystem.NewBackend(...)

// 2. 构造 Memory Middleware
memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend:             backend,
	ContextConfig:       memory.ContextConfig{
		MaxTokenSize:   4000, // 最大 token 数
	},
	Strategy:            memory.NewSlidingWindowStrategy(), // 滑动窗口
})

// 3. 构造 ChatModelAgent
agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
	 Middlewares: []adk.Middleware{memMiddleware}, // 加入 middleware 链
	// ...
})
```

每轮对话:
1. Runner 调用 agent
2. Memory middleware 从 Backend 加载完整历史
3. 按策略裁剪得到 `messages`
4. 传给下一个 middleware，最后传给 ChatModel
5. ChatModel 生成回复
6. Memory middleware 把新的用户消息和模型回复存入 Backend
7. 输出回复

全程不用你管，middleware 自动读写存储。

## 六、Token 计数

要裁剪必须知道**当前消息多少 token**，Eino 支持两种方式:

1. **模型提供**: 如果你用的模型实现了 `ChatModel.CountTokens`，middleware 自动调用
2. **指定编码器**: 你可以提供一个 `encoding` 编码器，middleware 用它计数

如果都没提供，默认按 `字符数 / 4` 估算，凑合用。

## 七、下一步

- 后端实现看 [backend.md](./backend.md)
- 裁剪策略和中间件看 [middlewares.md](./middlewares.md)
- 完整示例看 [examples.md](./examples.md)
