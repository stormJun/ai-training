# ChatModelAgent:开箱即用 ReAct 智能体

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/chatmodel.go`
> ChatModelAgent 是 ADK 给你做好的开箱即用 ReAct 智能体，你只需要给它一个 ChatModel + 工具列表，它就自动跑 ReAct 循环。

## 一、概述

ReAct 是最常用的工具调用智能体模式:
```
模型推理 → 决定要不要调工具 → 调工具 → 拿工具结果 → 再推理 → 直到给出最终答案
```

ChatModelAgent 把这个循环自动给你做好了，你只需要:
1. 给它一个 `ToolCallingChatModel`
2. 给它一堆工具
3. 可选加中间件（比如记忆）

就能用。

## 二、配置

```go
package main

import (
	"context"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
)

func main() {
	ctx := context.Background()

	agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		// Required: your chat model
		// Must implement model.ToolCallingChatModel
		ToolCallingModel: yourChatModel,

		// Required: your tools
		// Empty means no tools, pure chat completion
		Tools: []tool.BaseTool{yourTool1, yourTool2},

		// Optional: maximum number of ReAct iterations
		// Default: 20
		MaxIterations: 10,

		// Optional: message modifier before calling model
		// You can inject system prompt here
		MessageModifier: modifier,

		// Optional: message rewriter before adding to memory
		// You can compress long history here (if not using memory middleware)
		MessageRewriter: rewriter,

		// Optional: middlewares
		// Memory middleware is typically added here
		Middlewares: []adk.Middleware{memoryMiddleware},
	})
}
```

## 三、配置字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `ToolCallingModel` | 是 | 你的聊天模型，必须实现 `model.ToolCallingChatModel` 接口，就是支持 `WithTools` 绑定工具 |
| `Tools` | 否 | 你的工具列表，空就是纯聊天不工具 |
| `MaxIterations` | 否 | 最大迭代轮次，防止死循环，默认 20 |
| `MessageModifier` | 否 | 在调用模型前修改消息，你可以在这里注入 system prompt，或者加你自定义前缀 |
| `MessageRewriter` | 否 | 生成回复之后保存进记忆之前改写消息，你可以在这里压缩历史 |
| `Middlewares` | 否 | 中间件列表，一般会把 memory 中间件放这里 |

## 四、完整示例

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/memory"
	"github.com/cloudwego/eino/adk/openai"
	"github.com/cloudwego/eino/components/tool/utils"
)

func main() {
	ctx := context.Background()

	// 1. create chat model
	chatModel, err := openai.NewChatModel(ctx, openai.ChatModelConfig{
		APIKey: "your-api-key",
		Model:  "gpt-4o",
	})
	if err != nil { panic(err) }

	// 2. create your tool
	getWeatherTool, err := utils.InferTool("get_weather", "get the weather of a city",
		func(ctx context.Context, city string) (string, error) {
			// your tool logic
			return fmt.Sprintf("the weather of %s is 25°C", city), nil
		})
	if err != nil { panic(err) }

	// 3. create in-memory memory middleware
	memBackend := memory.NewInMemoryBackend()
	memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
		Backend:             memBackend,
		ConversationID:    "conv-001",
		ContextConfig: memory.ContextConfig{
			MaxTokenSize:   4000,
			IncludeCurrent: true,
		},
		Strategy: memory.NewSlidingWindowStrategy(memory.SlidingWindowStrategyConfig{
			MessagesNum: 10,
		}),
	})

	// 4. create ChatModelAgent
	agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		ToolCallingModel: chatModel,
		Tools: []tool.BaseTool{getWeatherTool},
		MaxIterations: 10,
		Middlewares: []adk.Middleware{memMiddleware}, // add memory middleware
	})
	if err != nil { panic(err) }

	// 5. run with Runner
	runner := adk.NewRunner(agent)

	// 6. chat
	userQuestion := "what's the weather in Beijing today?"
	iter := runner.Query(ctx, []*schema.Message{schema.UserMessage(userQuestion)})

	for {
		event, ok := iter.Next()
		if !ok { break }
		if event.Err != nil { panic(err) }

		if event.Message != nil {
			fmt.Print(event.Message.Content) // streaming output, print chunk by chunk
		}
	}
}
```

## 五、与记忆中间件配合

就像上面示例，记忆中间件给 ChatModelAgent 提供对话持久化 + 上下文裁剪，你不用自己做，只需要构造好给 ChatModelAgent 就行。

流程:
1. 你提问
2. 记忆中间件从 Backend 加载历史，裁剪
3. 模型拿裁剪后的历史 + 当前提问
4. 模型产出回复
5. 记忆中间件把新的提问 + 回复存进 Backend

全程自动，你不用管。

## 六、与 Retry / Failover 配合

ChatModelAgent 内置支持 failover，你可以这么加:

```go
agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
	// 重试包装器
	RetryConfig: &adk.RetryConfig{
		MaxRetries: 3,
	},
	// 失败转移，主模型不行切备用
	FailoverConfig: &adk.FailoverConfig{
		Enabled: true,
		Models: []model.ToolCallingChatModel{backupModel},
	},
})
```

## 七、底层

ChatModelAgent 底层用 ADK `newReact` 构建 ReAct 图，还是 Eino 编排层，所以你可以:
- 导出图自己改
- 嵌到大图里当子智能体

```go
// GetGraph returns the underlying graph of the agent.
// You can embed this graph into a larger graph as a sub-agent.
g := agent.GetGraph()
```

## 八、常见坑

| 问题 | 原因 | 解法 |
|------|------|------|
| **迭代超了** | 达到 `MaxIterations` 还没结束，说明你的模型一直在调工具停不下来 | 调大 `MaxIterations`，或者你的工具定义有问题 |
| **忘了加记忆中间件** | 对话没有持久化，进程重启就丢了 | 记得加，空对话当我没说 |
| **工具没给对类型** | 工具必须实现 `tool.InvokableTool`，你用 `utils.InferTool` 从普通函数创建就对了 | 不要自己手写接口，用 `utils.InferTool` |

## 九、参考

- ReAct 设计深读: [../03_graph/react_design.md](../03_graph/react_design.md)
- 记忆中间件: [../06_memory/middlewares.md](../06_memory/middlewares.md)
