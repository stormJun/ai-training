# Memory Middleware:上下文裁剪

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/middlewares/summarization/`、`memory/`
> Memory Middleware 是 ADK ChatModelAgent 的一个中间件，负责从 Backend 加载历史对话、裁剪上下文、保存新消息。

## 一、配置

```go
import (
	memory "github.com/cloudwego/eino/adk/middlewares/memory"
)

mw := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend:             backend,        // Backend 实现，InMemory / FileSystem
	ConversationID:       "conv-001",    // 当前对话 ID
	ContextConfig:        memory.ContextConfig{
		MaxTokenSize:   4000,           // 最大 token 数，超过裁剪
		IncludeCurrent:  true,           // 裁剪后是否包含当前轮用户问题，一般都是 true
	},
	// 选择一个裁剪策略
	Strategy: memory.NewSlidingWindowStrategy(slidingWindowConfig),
	// or
	// Strategy: summarization.NewStrategy(summarizationConfig),
})

// 加入 ChatModelAgent
agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
	Middlewares: []adk.Middleware{mw},
	// ...
})
```

## 二、ContextConfig

```go
type ContextConfig struct {
	// MaxTokenSize is the maximum total token size the LLM context can hold.
	// When the total token size exceeds this value, the strategy will cut off earlier messages.
	// Required: you must set this.
	MaxTokenSize int

	// IncludeCurrent specifies whether to include the current user input in the context passed to the model.
	// Generally this should be true, so the model sees the user query plus the cut history.
	IncludeCurrent bool

	// TokenCounter is used to count the number of tokens in messages.
	// If not set, and the model implements CountTokens, we will use the model's counting.
	// If neither, we estimate by characters / 4.
	// Optional.
	TokenCounter TokenCounter
}
```

**要点**:
- `MaxTokenSize` 一定要设，就是你模型的上下文窗口大小
- `IncludeCurrent` 一般 `true`，这样模型看到`历史 + 当前问题`
- `TokenCounter` 可选，没有就用模型的，模型没有就按字符数估算

## 三、裁剪策略

### 3.1 Sliding Window Strategy（滑动窗口）

保留**最近 N 轮**对话，扔前边的。

```go
config := memory.SlidingWindowStrategyConfig{
	MessagesNum: 10, // 保留最近 10 轮
}
strategy := memory.NewSlidingWindowStrategy(config)
```

**特点**:
- ✅ 最简单，最快，不需要调用 LLM
- ❌ 直接扔前边对话，可能把关键信息扔了
- **适合**:对话轮数不多，你知道肯定不会超过 N 轮，或者测试

**计算**:
- 从最新一轮开始往前数，总 token 不超过 `MaxTokenSize` 就保留
- 超过了就停止，前边的扔掉

### 3.2 Summarization Strategy（摘要压缩）

保留最新 N 轮**完整**对话，前边的整合成一个摘要。这样总 token 比全保留小很多，还保留前边信息。

```go
import "github.com/cloudwego/eino/adk/middlewares/summarization"

config := summarization.StrategyConfig{
	// 最后保留完整对话的轮数，一般 2-5
	KeepRecent: 3,

	// 摘要模型，一般用你同一个 ChatModel
	Model: chatModel,

	// 摘要 prompt 模板，可选，默认有模板
	SummarizePromptTemplate: `你现在需要把用户和助手的多轮对话压缩成一段简洁的摘要，保留关键信息...`,

	// 最高总 token 超过多少才摘要，默认 0 总是摘要
	MinimalLength: 0,
}
strategy := summarization.NewStrategy(config)
```

**工作流程**:
1. 总 token 没超 `MaxTokenSize` → 直接用完整对话，不用摘要
2. 超过了 → 保留最近 `KeepRecent` 轮完整对话，前边所有对话压缩成一个摘要
3. 最终上下文 = `[摘要] + 最近 N 轮完整`，总 token 保证不超

**特点**:
- ✅ 比滑动窗口保留更多信息
- ❌ 每轮都要调用 LLM 生成摘要，增加延迟和 token 消耗
- **适合**:长对话，你不想丢前边信息，能接受一点额外耗时

## 四、TokenCounter 接口

如果你要自己提供 token 计数:

```go
type TokenCounter interface {
	// CountTokens counts the number of tokens in the given messages.
	CountTokens(ctx context.Context, messages []*schema.Message) (int, error)
}
```

默认行为:
1. 如果 `ContextConfig.TokenCounter` 被设置 → 用这个
2. 没设置，但 `ChatModel` 实现 `CountTokens` → 用模型的
3. 都没 → `len(text) / 4` 估算

## 五、完整配置示例

```go
// 1. 滑动窗口，保留最近 10 轮，最大 4000 token
mw := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend: memory.NewInMemoryBackend(),
	ConversationID: "conversation-1",
	ContextConfig: memory.ContextConfig{
		MaxTokenSize:   4000,
		IncludeCurrent: true,
	},
	Strategy: memory.NewSlidingWindowStrategy(memory.SlidingWindowStrategyConfig{
		MessagesNum: 10,
	}),
})

// 2. 摘要压缩，保留最近 3 轮，最大 4000 token
mw := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend: fsBackend,
	ConversationID: "conversation-1",
	ContextConfig: memory.ContextConfig{
		MaxTokenSize:   4000,
		IncludeCurrent: true,
	},
	Strategy: summarization.NewStrategy(summarization.StrategyConfig{
		KeepRecent: 3,
		Model: chatModel,
	}),
})
```

## 六、工作流程

Middleware 在 ChatModelAgent 中的执行顺序:

1. **Agent 开始** → Memory Middleware 进入
2. **从 Backend 加载** → 拿到完整历史对话
3. **计数** → 计算总 token 数
4. **裁剪** → 用策略裁剪得到给模型的上下文
5. **把裁剪后的上下文注入** → 给 ChatModel
6. **ChatModel 生成回复** → 得到新消息
7. **存入 Backend** → 把用户消息和模型回复追加到 Backend，保存
8. **给下一个 middleware** → 继续

整个过程对用户透明，你只需要构造 middleware 加到 middleware 链就行。

## 七、常见问题

| 问题 | 原因 | 解法 |
|------|------|------|
| **裁剪还是超了** | 就算只保留一轮也超了 | 调小 `KeepRecent`，或者升级模型上下文窗口 |
| **摘要很慢** | 每轮都要调用 LLM | 滑动窗口更快，摘要适合真的长对话 |
| **对话 ID 哪里来** | 你开新对话的时候生成唯一 ID 就行，可以存你业务的用户对话关联 | 一般你业务每个对话给一个 ID，传给 Middleware |
| **多用户怎么弄** | 每个用户每个对话一个 Middleware 实例，不同 `ConversationID` | 每个对话新建 Middleware，同一个 Backend 存所有对话 |

## 八、下一步

- 完整示例看 [examples.md](./examples.md)
- Backend 看 [backend.md](./backend.md)
