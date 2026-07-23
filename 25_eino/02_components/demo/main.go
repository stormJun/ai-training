package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/joho/godotenv"
)

// 本 demo 演示 ChatModel 的基本使用（生产级写法）：
//   - buildChatModel / generate / stream 拆成独立函数，错误向上返回（不用 log.Fatal）
//   - 流式 reader 用 defer Close 保证释放
//   - main 只负责装配与顶层错误处理
//
// 运行：先配置 .env（见 .env.example），再 go run .
func main() {
	// 加载 .env（不存在则忽略；不覆盖已设置的环境变量）。
	if err := godotenv.Load(); err == nil {
		fmt.Println(">> 已加载 .env")
	}

	ctx := context.Background()

	// 返回接口类型 model.BaseChatModel：后续 generate/stream 只依赖接口，
	// 换其他实现（OpenAI、Ollama 等）时这两个函数无需改动。
	chatModel, err := buildChatModel(ctx)
	if err != nil {
		log.Fatalf("构造 ChatModel 失败: %v", err)
	}

	msgs := []*schema.Message{
		schema.SystemMessage("你是一名简洁的助手。"),
		schema.UserMessage("你好，用一句话介绍 Go 语言。"),
	}

	fmt.Println("=== Generate ===")
	if err := generate(ctx, chatModel, msgs); err != nil {
		log.Fatalf("Generate: %v", err)
	}

	fmt.Println("\n=== Stream ===")
	if err := stream(ctx, chatModel, msgs); err != nil {
		log.Fatalf("Stream: %v", err)
	}
}

// buildChatModel 从 .env（或环境变量）读取配置，构造 Ark ChatModel。
func buildChatModel(ctx context.Context) (model.BaseChatModel, error) {
	apiKey := os.Getenv("ARK_API_KEY")
	modelID := os.Getenv("ARK_MODEL_ID")
	if apiKey == "" || modelID == "" {
		return nil, fmt.Errorf("缺少配置：请在 .env 中设置 ARK_API_KEY 和 ARK_MODEL_ID（参考 .env.example）")
	}

	// 构造配置对象：把环境变量收拢成 *ark.ChatModelConfig。
	// ChatModelConfig 集中存放建模型所需的全部参数（APIKey/Model/BaseURL/Temperature…），
	// 只填关心的字段，其余留零值走默认。& 取地址是因为 NewChatModel 形参是指针。
	cfg := &ark.ChatModelConfig{
		APIKey: apiKey,  // 鉴权凭证，作为 Authorization: Bearer <key> 发给 Ark
		Model:  modelID, // 调哪个模型（如 ark-code-latest），Ark 据此路由，必填
	}
	// BaseURL 默认是普通 Ark (https://ark.cn-beijing.volces.com/api/v3)；
	// Agent Plan 需覆盖为 /api/plan/v3，并使用 Agent Plan 专属 Key。
	if baseURL := os.Getenv("ARK_BASE_URL"); baseURL != "" {
		cfg.BaseURL = baseURL
	}

	// 构造模型客户端：内部用 cfg 建底层 HTTP 客户端（设好鉴权与端点），返回 *ark.ChatModel。
	// Go 惯用多返回值（结果 + error）：成功则 chatModel 可用（实现 model.BaseChatModel，可 Generate/Stream）；
	// 失败则 err 非 nil，需紧接着检查。
	return ark.NewChatModel(ctx, cfg)
}

// generate 阻塞调用，打印完整回复。
func generate(ctx context.Context, m model.BaseChatModel, msgs []*schema.Message) error {
	resp, err := m.Generate(ctx, msgs, model.WithTemperature(0.3))
	if err != nil {
		return fmt.Errorf("调用 Generate: %w", err) // 错误向上抛，由 main 决定怎么处理
	}
	fmt.Println(resp.Content)
	return nil
}

// stream 流式调用，逐块打印，体现“增量转发至调用方”。
func stream(ctx context.Context, m model.BaseChatModel, msgs []*schema.Message) error {
	reader, err := m.Stream(ctx, msgs, model.WithTemperature(0.3))
	if err != nil {
		return fmt.Errorf("调用 Stream: %w", err)
	}
	defer reader.Close() // ① 必须关闭，避免连接/goroutine 泄漏

	// reader.Recv() 每次返回一个 chunk，io.EOF 表示流结束。
	var chunkCount int
	for {
		chunk, err := reader.Recv()
		if errors.Is(err, io.EOF) {
			break // ② io.EOF = 流正常结束，不是错误
		}
		if err != nil {
			return fmt.Errorf("Recv: %w", err) // ③ 真实错误，向上抛（不要 Fatal，否则 defer 不执行）
		}
		fmt.Print(chunk.Content) // ④ 收到一块就输出一块，不等待整体完成
		chunkCount++
	}
	fmt.Printf("\n(流式共收到 %d 个 chunk)\n", chunkCount)
	return nil
}
