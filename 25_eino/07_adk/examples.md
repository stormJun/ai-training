# 完整示例:带记忆的聊天智能体

```go
package main

import (
	"context"
	"fmt"
	"io"
	"errors"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/memory"
	"github.com/cloudwego/eino/adk/openai"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/schema"
)

func main() {
	ctx := context.Background()

	// 1. create chat model
	chatModel, err := openai.NewChatModel(ctx, openai.ChatModelConfig{
		APIKey:  "your-openai-api-key",
		Model:   "gpt-4o",
	})
	if err != nil {
		panic(err)
	}

	// 2. create a tool: get weather
	getWeather, err := utils.InferTool("get_weather", "get the weather of a city",
		func(ctx context.Context, city string) (string, error) {
			// your real business logic here
			return fmt.Sprintf("the weather of %s is 25°C", city), nil
		})
	if err != nil {
		panic(err)
	}

	// 3. create memory middleware
	memBackend := memory.NewInMemoryBackend()
	memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
		Backend:        memBackend,
		ConversationID:   "conversation-1",
		ContextConfig: memory.ContextConfig{
			MaxTokenSize:   4000,
			IncludeCurrent: true,
		},
		Strategy: memory.NewSlidingWindowStrategy(memory.SlidingWindowStrategyConfig{
			MessagesNum: 10,
		}),
	})

	// 4. create ChatModelAgent
	agent, err := adk.NewChatModelAgent(ctx, adk.ChatModelAgentConfig{
		ToolCallingModel: chatModel,
		Tools: []tool.BaseTool{getWeather},
		MaxIterations:  10,
		Middlewares: []adk.Middleware{memMiddleware}, // add memory middleware
	})
	if err != nil {
		panic(err)
	}

	// 5. run with Runner
	runner := adk.NewRunner(agent)

	// 6. chat
	userQuestion := "what's the weather in Beijing today?"
	iter := runner.Query(ctx, []*schema.Message{schema.UserMessage(userQuestion)})

	for {
		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			panic(err)
		}

		if event.Message != nil {
			fmt.Print(event.Message.Content)
		}
	}

	fmt.Println()
}
```

## 完整示例: HITL 人机交互审批工具

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/openai"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/schema"
)

func main() {
	ctx := context.Background()

	chatModel, err := openai.NewChatModel(ctx, openai.ChatModelConfig{
		APIKey: "your-api-key",
		Model:  "gpt-4o",
	})
	if err != nil {
		panic(err)
	}

	deleteFile, err := utils.InferTool("delete_file", "delete a file from disk",
		func(ctx context.Context, path string) error {
			// your delete logic here, we just print it
			fmt.Printf("delete file: %s\n", path)
			return nil
		})
	if err != nil {
		panic(err)
	}

	agent, err := adk.NewChatModelAgent(ctx, adk.ChatModelAgentConfig{
		ToolCallingModel: chatModel,
		Tools: []tool.BaseTool{deleteFile},
	})
	if err != nil {
		panic(err)
	}

	// wrap with HITL, interrupt before tool executes
	hitlAgent := adk.NewHITL(agent, adk.HitlConfig{
		InterruptBeforeTool: true,
	})

	runner := adk.NewRunner(hitlAgent)
	iter := runner.Query(ctx, []*schema.Message{schema.UserMessage("delete /tmp/test.txt")})

	for {
		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			panic(err)
		}

		if event.IsInterrupt() {
			// get interrupt info, you need to save checkpoint and ask human approve
			info := event.GetInterruptInfo()
			fmt.Printf("need human approve for tool: %s\n", info.ToolName)
			fmt.Printf("you can resume after approve with: \n"+
				"runner := adk.NewResumer(hitlAgent, info.CheckpointID, adk.ResumeConfig{Approved: true})\n"+
				"iter := runner.Resume(ctx)\n")
			break
		}

		if event.Message != nil {
			fmt.Print(event.Message.Content)
		}
	}
}
```
