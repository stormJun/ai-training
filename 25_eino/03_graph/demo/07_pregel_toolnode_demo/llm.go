// llm.go:真 LLM 流式调用(火山方舟 Ark,OpenAI 兼容)。
//
// 用 net/http 直连,无外部依赖。读 ARK_API_KEY 环境变量。
// 配置可放同目录 .env 文件(loadEnv 自动加载),或用环境变量注入。
//   - BaseURL: https://ark.cn-beijing.volces.com/api/plan/v3
//   - Model:   kimi-k3
//
// 返回 *StreamReader[string],每个 chunk 是 LLM 产出的一段文本。
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
)

// loadEnv 从同目录 .env 文件加载环境变量(不覆盖已存在的)。
// 让 demo 在 IDE 调试器里也能跑(无需手动 source .env)。
// 支持: export KEY=VALUE / KEY=VALUE / 引号 / # 注释 / 空行。
func loadEnv() {
	data, err := os.ReadFile(".env")
	if err != nil {
		return // 无 .env 文件,跳过(依赖已存在的环境变量)
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "export ")
		idx := strings.Index(line, "=")
		if idx < 0 {
			continue
		}
		key := strings.TrimSpace(line[:idx])
		val := strings.Trim(strings.TrimSpace(line[idx+1:]), `"'`)
		if _, exists := os.LookupEnv(key); !exists { // 不覆盖已存在的
			os.Setenv(key, val)
		}
	}
}

const (
	arkBaseURL = "https://ark.cn-beijing.volces.com/api/plan/v3"
	arkModel   = "kimi-k3"
)

// streamLLM 流式调用 LLM,prompt 作为单条 user 消息。返回文本 chunk 流。
func streamLLM(prompt string) (*StreamReader[string], error) {
	apiKey := os.Getenv("ARK_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("ARK_API_KEY 未设置(见 eino-examples/.env)")
	}

	body, _ := json.Marshal(map[string]any{
		"model":    arkModel,
		"messages": []map[string]string{{"role": "user", "content": prompt}},
		"stream":   true,
	})

	req, err := http.NewRequest("POST", arkBaseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != 200 {
		resp.Body.Close()
		return nil, fmt.Errorf("LLM API 返回 %d", resp.StatusCode)
	}

	out, w := Pipe[string]()
	go func() {
		defer w.Close()
		defer resp.Body.Close()
		// SSE:每行 "data: {json}",最后 "data: [DONE]"
		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024) // LLM 单行可能较长
		for scanner.Scan() {
			line := scanner.Text()
			if !strings.HasPrefix(line, "data: ") {
				continue
			}
			data := strings.TrimPrefix(line, "data: ")
			if data == "[DONE]" {
				break
			}
			var chunk struct {
				Choices []struct {
					Delta struct {
						Content string `json:"content"`
					} `json:"delta"`
				} `json:"choices"`
			}
			if err := json.Unmarshal([]byte(data), &chunk); err != nil {
				continue
			}
			if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
				w.Send(chunk.Choices[0].Delta.Content, nil)
			}
		}
		if err := scanner.Err(); err != nil {
			w.Send("", err)
		}
	}()
	return out, nil
}
