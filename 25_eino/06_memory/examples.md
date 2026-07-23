# 完整使用示例

## 示例一:内存滑动窗口

单进程对话，不需要持久化，用滑动窗口:

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/memory"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/adk/openai"
)

func main() {
	ctx := context.Background()

	// 1. 构造 ChatModel
	chatModel, err := openai.NewChatModel(ctx, openai.ChatModelConfig{
		APIKey: "your-api-key",
		Model:  "gpt-4o",
	})
	if err != nil { panic(err) }

	// 2. 构造 Memory Backend
	backend := memory.NewInMemoryBackend()

	// 3. 构造 Memory Middleware
	memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
		Backend:       backend,
		ConversationID: "demo-001",
		ContextConfig: memory.ContextConfig{
			MaxTokenSize:   4000, // GPT-4o 上下文窗口 128K，我们留 4K 演示
			IncludeCurrent: true,
		},
		// 滑动窗口策略，保留最近 10 轮
		Strategy: memory.NewSlidingWindowStrategy(memory.SlidingWindowStrategyConfig{
			MessagesNum: 10,
		}),
	})

	// 4. 构造 ChatModelAgent
	agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Model: chatModel,
		ToolsConfig: adk.ToolsConfig{
			Tools: []tool.BaseTool{yourTool},
		},
		Middlewares: []adk.Middleware{memMiddleware}, // 挂上 memory middleware
	})
	if err != nil { panic(err) }

	// 5. 运行
	runner := adk.NewRunner(adk.RunnerConfig{Agent: agent})

	// 第一轮
	iter := runner.Query(ctx, []*schema.Message{schema.UserMessage("你好")})
	for {
		event, ok := iter.Next()
		if !ok { break }
		if event.Err != nil { panic(err) }
		fmt.Print(event.Message.Content)
	}
	fmt.Println()

	// 第二轮，直接继续，middleware 自动记住上一轮
	iter = runner.Query(ctx, []*schema.Message{schema.UserMessage("帮我算一下 1+1 等于多少")})
	for {
		event, ok := iter.Next()
		if !ok { break }
		if event.Err != nil { panic(err) }
		fmt.Print(event.Message.Content)
	}
	fmt.Println()

	// 之后每轮这么用就行，middleware 自动存历史自动裁剪
}
```

## 示例二:文件系统持久化 + 摘要压缩

需要持久化，对话比较长，用摘要压缩:

```go
package main

import (
	"context"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/memory"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/adk/openai"
)

func main() {
	ctx := context.Background()

	chatModel, err := openai.NewChatModel(ctx, openai.ChatModelConfig{
		APIKey: "your-api-key",
		Model:  "gpt-4o",
	})
	if err != nil { panic(err) }

	// 持久化到 ./data/conversations
	backend, err := filesystem.NewFileSystemBackend(filesystem.Config{
		RootDir: "./data/conversations",
	})
	if err != nil { panic(err) }

	// 摘要压缩策略，保留最后 3 轮完整，前边压缩
	memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
		Backend:       backend,
		ConversationID: "long-conversation-001",
		ContextConfig: memory.ContextConfig{
			MaxTokenSize:   4000,
			IncludeCurrent: true,
		},
		Strategy: summarization.NewStrategy(summarization.StrategyConfig{
			KeepRecent: 3,                // 最后 3 轮完整保留
			Model:       chatModel,         // 用同一个 model 做摘要
			MinimalLength: 2000,         // 总 token 超过 2000 才摘要，小于不摘要
		}),
	})

	agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Model: chatModel,
		Middlewares: []adk.Middleware{memMiddleware},
	})
	if err != nil { panic(err) }

	// 运行和之前一样，持久化到磁盘，进程重启对话还在
	runner := adk.NewRunner(adk.RunnerConfig{Agent: agent})
	// ...
}
```

## 示例三:自定义 Token 计数

如果你用开源分词器，可以精确计数:

```go
mw := memory.NewMiddleware(memory.MiddlewareConfig{
	// ...
	ContextConfig: memory.ContextConfig{
		MaxTokenSize: 4000,
		TokenCounter: func(ctx context.Context, messages []*schema.Message) (int, error) {
			// 用你的分词器 count
			total := 0
			for _, msg := range messages {
				total += yourTokenizer.Encode(msg.Content).Len()
			}
			return total, nil
		},
	},
	// ...
})
```

## 示例四:自定义 Backend

用 Redis 存储对话:

```go
package mypackage

import (
	"context"
	"encoding/json"
	"errors"

	"github.com/cloudwego/eino/adk/memory"
	"github.com/cloudwego/eino/schema"
	"github.com/go-redis/redis/v8"
)

type RedisBackend struct {
	client *redis.Client
}

func NewRedisBackend(client *redis.Client) *RedisBackend {
	return &RedisBackend{client: client}
}

func (b *RedisBackend) Get(ctx context.Context, convID string) (*memory.Conversation, error) {
	data, err := b.client.Get(ctx, convID).Result()
	if err != nil {
		if errors.Is(err, redis.Nil) {
			return nil, os.ErrNotExist
		}
		return nil, err
	}

	var conv memory.Conversation
	err = json.Unmarshal([]byte(data), &conv)
	if err != nil {
		return nil, err
	}
	return &conv, nil
}

func (b *RedisBackend) Create(ctx context.Context, convID string, userID string) (*memory.Conversation, error) {
	conv := &memory.Conversation{
		ID:      convID,
		UserID:  userID,
		Messages: make([]*schema.Message, 0),
	}
	return conv, nil
}

func (b *RedisBackend) Save(ctx context.Context, conv *memory.Conversation) error {
	data, err := json.Marshal(conv)
	if err != nil {
		return err
	}
	return b.client.Set(ctx, conv.ID, string(data), 0).Err()
}

func (b *RedisBackend) Delete(ctx context.Context, convID string) error {
	return b.client.Del(ctx, convID).Err()
}
```

// 使用
backend := mypackage.NewRedisBackend(redisClient)
mw := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend: backend,
	// ...
})
```

## 总结

| 场景 | 推荐配置 |
|------|----------|
| 短对话 / 测试 | InMemory + SlidingWindow |
| 长对话 / 需要持久 | FileSystem + SlidingWindow |
| 很长对话 / 要保留信息 | FileSystem + Summarization |
| 生产 / 你有数据库 | 自定义 Backend + Summarization |
