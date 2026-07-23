package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/joho/godotenv"
)

// 本 demo 演示完整的工具调用闭环（手动 ReAct 循环）：
//   1. 用 utils.InferTool 从 Go 函数 + struct tag 创建天气工具
//   2. 构造真实 Ark ChatModel（复用 .env 配置）
//   3. 把工具绑定给模型，用户提问
//   4. 循环：模型决定调工具 → 执行工具 → 结果回传 → 模型再生成，直到给出最终回复
//
// 运行（在 demo/ 目录下）：
//   go run ./tool_demo
//
// 说明：这里手写 ReAct 循环是为了讲清机制；生产中该循环由 ToolsNode（compose）
// 或 ADK 的 ChatModelAgent 自动驱动，无需手写。

// 天气工具输入。tag 会被 InferTool 反射成参数 JSON Schema。
type WeatherInput struct {
	City string `json:"city" jsonschema:"required" jsonschema_description:"城市名，如 Beijing"`
}

// 天气工具输出。
type WeatherOutput struct {
	City        string `json:"city"`
	Temperature int    `json:"temperature"`
	Weather     string `json:"weather"`
}

// getWeather 工具逻辑（假数据；真实场景调天气 API）。
// InferTool 会自动把模型给的 JSON 参数解码成 WeatherInput，再把 WeatherOutput 编码成 JSON 返回。
func getWeather(ctx context.Context, in WeatherInput) (WeatherOutput, error) {
	return WeatherOutput{City: in.City, Temperature: 28, Weather: "晴"}, nil
}

const maxRounds = 5 // 防止模型反复调工具导致死循环

func main() {
	// 加载 .env（兼容从 demo/ 或 demo/tool_demo/ 作为工作目录运行）。
	for _, p := range []string{".env", "../.env"} {
		if err := godotenv.Load(p); err == nil {
			fmt.Printf(">> 已加载 %s\n", p)
			break
		}
	}

	ctx := context.Background()

	// 1. 构造 ChatModel
	chatModel, err := buildChatModel(ctx)
	if err != nil {
		log.Fatalf("构造 ChatModel 失败: %v", err)
	}

	// 2. 从函数 + struct tag 创建天气工具
	weatherTool, err := utils.InferTool("get_weather", "查询指定城市的天气", getWeather)
	if err != nil {
		log.Fatalf("创建工具失败: %v", err)
	}
	toolInfo, err := weatherTool.Info(ctx)
	if err != nil {
		log.Fatalf("获取工具信息失败: %v", err)
	}

	// 3. 用户提问（应触发模型调用天气工具）
	msgs := []*schema.Message{
		schema.UserMessage("北京今天天气怎么样？请用工具查询后再回答。"),
	}

	// 4. 手动 ReAct 循环
	for round := 1; round <= maxRounds; round++ {
		fmt.Printf("\n----- 第 %d 轮 -----\n", round)

		// 调模型，带上工具（model.WithTools 为调用时选项）
		resp, err := chatModel.Generate(ctx, msgs, model.WithTools([]*schema.ToolInfo{toolInfo}))
		if err != nil {
			log.Fatalf("Generate 失败: %v", err)
		}

		// 模型未调用工具：给出最终回复，结束
		if len(resp.ToolCalls) == 0 {
			fmt.Println("模型最终回复:", resp.Content)
			return
		}

		// 模型要调工具：先把 assistant 的 ToolCall 消息加入对话
		msgs = append(msgs, resp)

		// 逐个执行 ToolCall
		for _, tc := range resp.ToolCalls {
			fmt.Printf("调用工具 %s，参数 %s\n", tc.Function.Name, tc.Function.Arguments)
			// InvokableRun 自动：JSON 参数 → WeatherInput → 调函数 → WeatherOutput → JSON
			result, err := weatherTool.InvokableRun(ctx, tc.Function.Arguments)
			if err != nil {
				log.Fatalf("工具执行失败: %v", err)
			}
			fmt.Printf("工具结果: %s\n", result)
			// 工具结果作为 tool 消息回传，用 ToolCallID 关联上一步的 ToolCall
			msgs = append(msgs, schema.ToolMessage(result, tc.ID))
		}
		// 继续循环：让模型基于工具结果生成回复
	}

	log.Fatalf("超过最大轮次 %d 仍未结束", maxRounds)
}

// buildChatModel 从 .env/环境变量构造 Ark ChatModel（与 chat_model demo 同构）。
func buildChatModel(ctx context.Context) (model.BaseChatModel, error) {
	apiKey := os.Getenv("ARK_API_KEY")
	modelID := os.Getenv("ARK_MODEL_ID")
	if apiKey == "" || modelID == "" {
		return nil, fmt.Errorf("缺少配置：请在 .env 中设置 ARK_API_KEY 和 ARK_MODEL_ID（参考 .env.example）")
	}
	cfg := &ark.ChatModelConfig{
		APIKey: apiKey,  // 鉴权凭证
		Model:  modelID, // 模型（如 ark-code-latest）
	}
	if baseURL := os.Getenv("ARK_BASE_URL"); baseURL != "" {
		cfg.BaseURL = baseURL // Agent Plan 覆盖为 /api/plan/v3
	}
	return ark.NewChatModel(ctx, cfg)
}
