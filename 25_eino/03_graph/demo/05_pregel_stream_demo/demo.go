// demo.go:流式顶点实现 + StreamRun 场景。
//
// 场景:StreamRun 端到端流式(真 LLM)
//   model step1 产出 ToolCalls -> Copy 扇出给 search/calc ->
//   search/calc 产出结果 -> Merge 扇入回 model ->
//   model step2 调真 LLM(kimi-k3)流式回答 -> 调用方逐块读取
package main

import (
	"context"
	"fmt"
	"io"
	"strings"
	"time"
)

// ============================================================
// 流式顶点实现
// ============================================================

// ModelVertex 模型顶点。
// step1:记录用户问题,产出 ToolCalls(简化:固定调 search+calc)。
// step2:调真 LLM 流式回答(用户问题 + 工具结果)。
//
// 注:step1 简化没用 tool calling API--真 ReAct 会让 LLM 决定调哪些工具,
//     这里固定调 search+calc 以保持代码简短。真 LLM 流式在 step2 体现。
type ModelVertex struct {
	Answer   string
	question string // step1 记录用户问题,step2 拼进 prompt
}

func (m *ModelVertex) ID() string { return "model" }

func (m *ModelVertex) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	out, w := Pipe[Message]()
	go func() {
		defer w.Close()
		msg, err := concatMsg(input)
		if err != nil {
			w.Send(Message{}, err)
			return
		}
		if len(msg.Results) > 0 {
			// step 2:真 LLM 流式回答
			prompt := fmt.Sprintf("用户问题: %s\n\n已获取的工具结果:\n- %s\n请基于以上信息,用中文简洁回答用户问题。",
				m.question, strings.Join(msg.Results, "\n- "))
			sr, err := streamLLM(prompt)
			if err != nil {
				w.Send(Message{}, err)
				return
			}
			fmt.Println("  [model] 真 LLM 流式回答中...")
			for {
				chunk, err := sr.Recv()
				if err == io.EOF {
					break
				}
				if err != nil {
					w.Send(Message{}, err)
					return
				}
				m.Answer += chunk
				w.Send(Message{Answer: chunk}, nil) // 每个 LLM chunk 包成 Message 流式发出
			}
		} else {
			// step 1:记录问题,产出 ToolCalls
			m.question = msg.Answer
			fmt.Printf("  [model] 记录问题,产出 ToolCalls=[search, calc]\n")
			w.Send(Message{ToolCalls: []ToolCall{
				{Name: "search", Arg: m.question},
				{Name: "calc", Arg: "2+3"},
			}}, nil)
		}
	}()
	return out, nil
}

// ToolVertex 工具顶点:执行特定的工具调用,产出 Result(假工具,字符串拼接)。
type ToolVertex struct {
	id   string
	name string
}

func (t *ToolVertex) ID() string { return t.id }

// StreamCompute:concat 输入流,逐个 ToolCall 产出 Result chunk。
func (t *ToolVertex) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	out, w := Pipe[Message]()
	go func() {
		defer w.Close()
		msg, err := concatMsg(input)
		if err != nil {
			w.Send(Message{}, err)
			return
		}
		for _, tc := range msg.ToolCalls {
			if tc.Name == t.name {
				r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
				fmt.Printf("  [%s] 流式产出 Result: %s\n", t.id, r)
				w.Send(Message{Results: []string{r}}, nil)
			}
		}
	}()
	return out, nil
}

// ============================================================
// 场景:StreamRun 端到端流式(真 LLM)
// ============================================================

func main() {
	loadEnv() // 从同目录 .env 加载 ARK_API_KEY(IDE 调试器无需手动 source)
	fmt.Println("=== StreamRun(真 LLM 流式)===")
	g := NewGraph(20)
	model := &ModelVertex{}
	g.AddVertex(model)
	g.AddVertex(&ToolVertex{id: "search", name: "search"})
	g.AddVertex(&ToolVertex{id: "calc", name: "calc"})

	// 声明式拓扑:
	//   START ──▶ model ──branch──▶ {search, calc}(有 tool call)
	//                 ▲                │
	//                 │                └──▶ END(无 tool call)
	//                 └── edge ◀──────┘ (search/calc 结果回 model)
	g.AddEdge(START, "model")
	g.AddEdge("search", "model")
	g.AddEdge("calc", "model")
	g.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"} // 有 tool call -> 两个工具并行
			}
			return []string{END} // 否则 -> 结束
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})

	c, err := g.Compile()
	if err != nil {
		panic(err)
	}

	// 初始问题(传给 model step1)
	sr, err := c.StreamRun(context.Background(), Message{Answer: "eino 框架是什么？"})
	if err != nil {
		fmt.Printf("StreamRun 错误: %v\n", err)
		return
	}

	fmt.Println("\n调用方逐块读取最终流(每行首标时间戳,文本连续流动):")
	start := time.Now()
	atLineStart := true // 是否在新行开头(是则先打时间戳前缀)
	for {
		chunk, err := sr.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			fmt.Printf("\n读流出错: %v\n", err)
			break
		}
		s := chunk.Answer
		if atLineStart && s != "" {
			fmt.Printf("[+%5dms] ", time.Since(start).Milliseconds())
		}
		fmt.Print(s)
		// 内容末尾是换行 -> 下个 chunk 在新行开头,再标时间戳
		atLineStart = strings.HasSuffix(s, "\n")
	}
	if !atLineStart {
		fmt.Println() // 末尾补换行
	}
	fmt.Printf("\n最终答案: %s\n", model.Answer)
}
