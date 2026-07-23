package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/joho/godotenv"
)

// 本 demo 验证 Workflow 声明式编排：用 AddInput 声明数据流（替代 Graph 的 AddEdge）。
// 运行（在 demo/ 目录下）：go run ./workflow_demo

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

	// 声明式工作流：每个节点声明自己的输入来源，拓扑由声明推导。
	wf := compose.NewWorkflow[string, string]()

	buildMsgs := wf.AddLambdaNode("build_msgs", compose.InvokableLambda(func(ctx context.Context, q string) ([]*schema.Message, error) {
		return []*schema.Message{schema.UserMessage(q)}, nil
	}))
	chat := wf.AddChatModelNode("chat", chatModel)
	toText := wf.AddLambdaNode("to_text", compose.InvokableLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
		return msg.Content, nil
	}))

	// 数据流声明（替代 AddEdge）
	buildMsgs.AddInput(compose.START) // build_msgs 接收工作流初始输入
	chat.AddInput("build_msgs")      // chat 的输入来自 build_msgs（整个输出，类型自然匹配）
	toText.AddInput("chat")          // to_text 的输入来自 chat
	wf.AddEnd("to_text")             // 结束节点取 to_text 的输出

	runnable, err := wf.Compile(ctx)
	if err != nil {
		log.Fatalf("Compile 失败: %v", err)
	}

	out, err := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
	if err != nil {
		log.Fatalf("Invoke 失败: %v", err)
	}
	fmt.Println("输出:", out)
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
