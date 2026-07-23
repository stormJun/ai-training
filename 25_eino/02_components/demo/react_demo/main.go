package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/flow/agent/react"
	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/joho/godotenv"
)

// 本 demo 用 flow/agent/react 的 ReAct agent 替代手写循环：
//   - 把 ChatModel + 天气工具交给 react.NewAgent
//   - 框架内部用 Pregel 驱动的 Graph 自动跑“模型↔工具”循环
//   - 调用方只需 agent.Generate，无需手写 ReAct
//
// 对比 demo/tool_demo（手写循环），体会“框架自动跑 ReAct”。
//
// 运行（在 demo/ 目录下）：go run ./react_demo

// 天气工具
type WeatherInput struct {
	City string `json:"city" jsonschema:"required" jsonschema_description:"城市名，如 Beijing"`
}

type WeatherOutput struct {
	City        string `json:"city"`
	Temperature int    `json:"temperature"`
	Weather     string `json:"weather"`
}

func getWeather(ctx context.Context, in WeatherInput) (WeatherOutput, error) {
	return WeatherOutput{City: in.City, Temperature: 28, Weather: "晴"}, nil
}

func main() {
	for _, p := range []string{".env", "../.env"} {
		if err := godotenv.Load(p); err == nil {
			fmt.Printf(">> 已加载 %s\n", p)
			break
		}
	}
	ctx := context.Background()

	// 1. 构造 ToolCallingChatModel（ark.ChatModel 实现了该接口，见 chatmodel.go:34）
	chatModel, err := buildToolCallingModel(ctx)
	if err != nil {
		log.Fatalf("构造模型失败: %v", err)
	}

	// 2. 创建天气工具
	weatherTool, err := utils.InferTool("get_weather", "查询指定城市的天气", getWeather)
	if err != nil {
		log.Fatalf("创建工具失败: %v", err)
	}

	// 3. 一行配置构建 ReAct agent：模型 + 工具交给框架，自动跑循环。
	//    内部构建 Pregel 驱动的 Graph（chat 节点 <-> tools 节点），见 react.go:128 nodeKeyTools/nodeKeyModel。
	agent, err := react.NewAgent(ctx, &react.AgentConfig{
		ToolCallingModel: chatModel,
		ToolsConfig: compose.ToolsNodeConfig{
			Tools: []tool.BaseTool{weatherTool},
		},
	})
	if err != nil {
		log.Fatalf("创建 agent 失败: %v", err)
	}

	// 4. 提问。agent 自主决定调工具 -> 执行 -> 回传 -> 再生成，直到给出最终回复。
	msgs := []*schema.Message{
		schema.UserMessage("北京今天天气怎么样？请用工具查询后回答。"),
	}
	resp, err := agent.Generate(ctx, msgs)
	if err != nil {
		log.Fatalf("agent.Generate 失败: %v", err)
	}
	fmt.Println("最终回复:", resp.Content)
}

// buildToolCallingModel 从 .env 构造 ark ChatModel，返回为 ToolCallingChatModel 接口。
func buildToolCallingModel(ctx context.Context) (model.ToolCallingChatModel, error) {
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
