package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/joho/godotenv"
)

// 本 demo 演示 Chain 线性编排：string -> Lambda -> ChatModel -> Lambda -> string。
// 对照 workflow_demo（声明式），体会 Chain 的 fluent Append 风格。
// 运行（在 demo/ 目录下）：go run ./chain_demo

func main() {
	for _, p := range []string{".env", "../.env"} {
		if err := godotenv.Load(p); err == nil {
			fmt.Printf(">> 已加载 %s\n", p)
			break
		}
	}
	ctx := context.Background()

	chatModel, err := buildChatModel(ctx)
	if err != nil {
		log.Fatalf("构造模型失败: %v", err)
	}

	// fluent 拼接：每个 Append 返回 *Chain 自身
	chain := compose.NewChain[string, string]()
	chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
		return []*schema.Message{schema.UserMessage(q)}, nil // string -> []*Message
	}))
	chain.AppendChatModel(chatModel) // []*Message -> *Message
	chain.AppendLambda(compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
		return msg.Content, nil // *Message -> string
	}))

	runnable, err := chain.Compile(ctx)
	if err != nil {
		log.Fatalf("Compile 失败: %v", err)
	}

	out, err := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
	if err != nil {
		log.Fatalf("Invoke 失败: %v", err)
	}
	fmt.Println("输出:", out)

	// 流式：同一 Runnable 直接调 Stream
	fmt.Println("\n=== Stream ===")
	reader, err := runnable.Stream(ctx, "再用一句话介绍 Go 的并发")
	if err != nil {
		log.Fatalf("Stream 失败: %v", err)
	}
	defer reader.Close()
	var n int
	for {
		chunk, err := reader.Recv()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			log.Fatalf("Recv: %v", err)
		}
		fmt.Print(chunk)
		n++
	}
	fmt.Printf("\n(共 %d 个 chunk)\n", n)
}

func buildChatModel(ctx context.Context) (model.BaseChatModel, error) {
	apiKey := os.Getenv("ARK_API_KEY")
	modelID := os.Getenv("ARK_MODEL_ID")
	if apiKey == "" || modelID == "" {
		return nil, fmt.Errorf("缺少配置：请在 .env 设置 ARK_API_KEY 和 ARK_MODEL_ID")
	}
	cfg := &ark.ChatModelConfig{APIKey: apiKey, Model: modelID}
	if baseURL := os.Getenv("ARK_BASE_URL"); baseURL != "" {
		cfg.BaseURL = baseURL
	}
	return ark.NewChatModel(ctx, cfg)
}
