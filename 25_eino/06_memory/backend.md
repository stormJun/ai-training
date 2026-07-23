# Memory Backend:存储对话历史

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/filesystem/`
> Backend 负责存储**完整**对话历史，Middleware 只负责裁剪。

## 一、Backend 接口

```go
package memory

import (
	"context"

	"github.com/cloudwego/eino/schema"
)

// Conversation represents a full conversation history.
type Conversation struct {
	ID      string                 `json:"id"`
	UserID string                 `json:"user_id"`
	Messages []*schema.Message    `json:"messages"`
}

// Backend is the interface for storing conversation history.
//
// All methods accept context for cancellation and timeout.
type Backend interface {
	// Get retrieves a conversation by ID.
	// Returns nil, os.ErrNotExist if conversation not found.
	Get(ctx context.Context, conversationID string) (*Conversation, error)

	// Create creates a new empty conversation and returns it.
	Create(ctx context.Context, conversationID string, userID string) (*Conversation, error)

	// Save saves the updated conversation.
	Save(ctx context.Context, conv *Conversation) error

	// Delete deletes a conversation.
	Delete(ctx context.Context, conversationID string) error
}
```

**契约要点:**
- `Conversation` 包含完整对话，所有消息都存在这里
- `Get` 拿到完整对话，Middleware 裁剪后给模型
- `Save` 新增消息后保存，Middleware 自动调用

## 二、内置实现

Eino 内置两个实现，满足不同场景:

### 2.1 InMemoryBackend

**内存存储，适合:**
- 单进程测试
- 不需要持久化，对话只在本次运行有效

```go
import "github.com/cloudwego/eino/adk/memory"

backend := memory.NewInMemoryBackend()
```

**特点:**
- 全内存，无磁盘 IO，速度快
- 进程重启对话丢失
- 并发安全，多个 goroutine 读写没问题

### 2.2 FileSystemBackend (filesystem 包)

**文件系统存储，适合:**
- 需要持久化，对话跨进程保留
- 生产环境多轮对话

```go
import "github.com/cloudwego/eino/adk/filesystem"

backend, err := filesystem.NewFileSystemBackend(filesystem.Config{
	RootDir: "./conversations", // 根目录，所有对话存在这
})
```

**特点:**
- 每个对话一个 JSON 文件
- 天然持久，进程重启对话还在
- 自动创建目录
- 并发安全

## 三、完整示例:FileSystemBackend

```go
package main

import (
	"context"
	"github.com/cloudwego/eino/adk/filesystem"
)

func main() {
	ctx := context.Background()

	backend, err := filesystem.NewFileSystemBackend(filesystem.Config{
		RootDir: "./data/conversations",
	})
	if err != nil { panic(err) }

	// 新建对话
	conv, err := backend.Create(ctx, "conv-001", "user-001")
	if err != nil { panic(err) }

	// 添加消息
	conv.Messages = append(conv.Messages, schema.UserMessage("Hello"))
	conv.Messages = append(conv.Messages, schema.AssistantMessage("Hi, how can I help you"))

	// 保存
	err = backend.Save(ctx, conv)
	if err != nil { panic(err) }

	// 取出对话
	conv, err = backend.Get(ctx, "conv-001")
	if err != nil { panic(err) }

	// 删除对话
	err = backend.Delete(ctx, "conv-001")
	if err != nil { panic(err) }
}
```

## 四、怎么自定义 Backend

如果你想用 Redis / PostgreSQL / 你的业务数据库存储对话，只需要实现 `Backend` 接口:

```go
type MyBackend struct {}

func (b *MyBackend) Get(ctx context.Context, convID string) (*memory.Conversation, error) {
	// 从你的数据库读
}

func (b *MyBackend) Create(ctx context.Context, convID string, userID string) (*memory.Conversation, error) {
	// 创建新对话
}

func (b *MyBackend) Save(ctx context.Context, conv *memory.Conversation) error {
	// 保存
}

func (b *MyBackend) Delete(ctx context.Context, convID string) error {
	// 删除
}
```

然后直接给 Middleware 用:

```go
memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
	Backend: myBackend, // 你的自定义 backend
	// ...
})
```

## 五、常见坑

| 问题 | 原因 | 解法 |
|------|------|------|
| **并发读没问题，写冲突** | FileSystemBackend 每个文件独立写，不同对话不冲突；同一对话并发写会有竞争 | 同一个对话不要并发写；`InMemoryBackend` 用了 `sync.RWMutex`，读并发安全 |
| **JSON 序列化失败** | 你的 `schema.Message` 有无法序列化的字段 | 原生 `schema.Message` 所有字段都是可序列化的，不要加不能序列化的东西 |
| **大对话慢** | FileSystemBackend 每次全读写，对话特别大性能会差 | 千万级别对话一个文件几 K，一般场景没问题；对话特别大考虑数据库 backend |

## 六、参考

- 中间件用法: [middlewares.md](./middlewares.md)
- 完整示例: [examples.md](./examples.md)
