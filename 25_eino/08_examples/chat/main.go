package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/memory"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
	"github.com/joho/godotenv"
	"github.com/cloudwego/eino-ext/components/model/ark"
)

func main() {
	// 1. load env
	err := godotenv.Load()
	if err != nil {
		fmt.Printf("load .env failed: %v\n", err)
		return
	}

	// 2. get config from env
	apiKey := os.Getenv("ARK_API_KEY")
	baseURL := os.Getenv("ARK_BASE_URL")
	model := os.Getenv("ARK_MODEL")

	if apiKey == "" {
		fmt.Println("ARK_API_KEY is empty, please set it in .env")
		return
	}

	// 3. create context with interrupt handling
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// handle Ctrl+C
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigChan
		cancel()
	}()

	// 4. create chat model
	chatModel, err := ark.NewChatModel(ctx, ark.ChatModelConfig{
		APIKey:  apiKey,
		BaseURL: baseURL,
		Model:   model,
	})
	if err != nil {
		fmt.Printf("create ark chat model failed: %v\n", err)
		return
	}

	// 5. create memory backend
	// change to filesystem.NewFileSystemBackend("./data") if you want persistent
	memBackend := memory.NewInMemoryBackend()

	// 6. get conversation id from prompt
	// here we use "default" as conversation id
	convID := "default"

	// 7. create memory middleware
	memMiddleware := memory.NewMiddleware(memory.MiddlewareConfig{
		Backend:             memBackend,
		ConversationID:      convID,
		ContextConfig: memory.ContextConfig{
			MaxTokenSize:   4000,
			IncludeCurrent: true,
		},
		Strategy: memory.NewSlidingWindowStrategy(memory.SlidingWindowStrategyConfig{
			MessagesNum: 10,
		}),
	})

	// 8. create chat model agent
	agent, err := adk.NewChatModelAgent(ctx, adk.ChatModelAgentConfig{
		ToolCallingModel: chatModel,
		Tools:               []tool.BaseTool{}, // add your tools here
		MaxIterations:      10,
		Middlewares: []adk.Middleware{memMiddleware},
	})
	if err != nil {
		fmt.Printf("create chat model agent failed: %v\n", err)
		return
	}

	// 9. create runner
	runner := adk.NewRunner(adk.RunnerConfig{Agent: agent})

	// 10. start interactive chat
	reader := bufio.NewReader(os.Stdin)
	fmt.Println("=== Eino Chat Demo ===")
	fmt.Println("Enter your message, Ctrl+C to exit.")

	for {
		fmt.Print("> ")
		line, _, err := reader.ReadLine()
		if err != nil {
			fmt.Printf("read line failed: %v\n", err)
			break
		}

		if line == "" {
			continue
		}

		fmt.Print("\nAssistant: ")

		iter := runner.Query(ctx, []*schema.Message{schema.UserMessage(line)})

		hasError := false
		for {
			event, ok := iter.Next()
			if !ok {
				break
			}
			if event.Err != nil {
				fmt.Printf("\nerror: %v\n", event.Err)
				hasError = true
				break
			}
			if event.Message != nil {
				fmt.Print(event.Message.Content)
			}
		}

		if !hasError {
			fmt.Println()
		}
	}
}
