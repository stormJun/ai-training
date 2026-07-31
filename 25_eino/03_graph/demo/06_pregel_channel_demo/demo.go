// demo.go:顶点实现(Compute + StreamCompute)+ 4 个场景。
//
// 场景:
//   1. Run(Invoke):基本 ReAct,演示 channel + merge(无 LLM,快)
//   2. StreamRun(Transform):真 LLM 流式(从 05)
//   3. edge handler:Run + 边转换(model->search 过滤 ToolCall)
//   4. checkpoint:Run + FlakyToolVertex 崩溃恢复(演示 channel.load)
package main

import (
	"context"
	"fmt"
	"io"
	"strings"
	"time"
)

// ============================================================
// 顶点实现
// ============================================================

// ModelVertex 模型顶点。
// Compute(Invoke):step1 产 ToolCalls,step2 产 Answer(假,无 LLM)。
// StreamCompute(Transform):step2 调真 LLM 流式回答。
type ModelVertex struct {
	Answer   string
	question string // step1 记录,step2 拼 prompt
}

func (m *ModelVertex) ID() string { return "model" }

func (m *ModelVertex) Compute(ctx context.Context, in Message) (Message, error) {
	if len(in.Results) > 0 {
		// step 2:汇总结果,产 Answer(Invoke 模式,假)
		m.Answer = fmt.Sprintf("done with %d results: %v", len(in.Results), in.Results)
		fmt.Printf("  [model] 产出 Answer: %q\n", m.Answer)
		return Message{Answer: m.Answer}, nil
	}
	// step 1:记录问题,产 ToolCalls
	m.question = in.Answer
	fmt.Printf("  [model] 记录问题,产 ToolCalls=[search, calc]\n")
	return Message{ToolCalls: []ToolCall{
		{Name: "search", Arg: m.question},
		{Name: "calc", Arg: "2+3"},
	}}, nil
}

// StreamCompute 流式(Transform):step2 调真 LLM。
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
			// step 2:真 LLM 流式
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
				w.Send(Message{Answer: chunk}, nil)
			}
		} else {
			// step 1:记录问题,产 ToolCalls
			m.question = msg.Answer
			fmt.Println("  [model] 记录问题,产 ToolCalls=[search, calc]")
			w.Send(Message{ToolCalls: []ToolCall{
				{Name: "search", Arg: m.question},
				{Name: "calc", Arg: "2+3"},
			}}, nil)
		}
	}()
	return out, nil
}

// ToolVertex 工具顶点。Compute/StreamCompute 都过滤自己的 ToolCall 执行。
// (有 edge handler 时,过滤已在边上做,这里 if 是 no-op)
type ToolVertex struct {
	id   string
	name string
}

func (t *ToolVertex) ID() string { return t.id }

func (t *ToolVertex) Compute(ctx context.Context, in Message) (Message, error) {
	var results []string
	for _, tc := range in.ToolCalls {
		if tc.Name == t.name {
			r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
			fmt.Printf("  [%s] 执行 -> %s\n", t.id, r)
			results = append(results, r)
		}
	}
	return Message{Results: results}, nil
}

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

// FlakyToolVertex 不稳定工具:首次必崩,用于 checkpoint 演示。
type FlakyToolVertex struct {
	id    string
	name  string
	calls int
}

func (t *FlakyToolVertex) ID() string { return t.id }

func (t *FlakyToolVertex) Compute(ctx context.Context, in Message) (Message, error) {
	t.calls++
	if t.calls == 1 {
		panic("模拟瞬时故障:首次必崩")
	}
	var results []string
	for _, tc := range in.ToolCalls {
		if tc.Name == t.name {
			r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
			fmt.Printf("  [%s] 执行(第%d次) -> %s\n", t.id, t.calls, r)
			results = append(results, r)
		}
	}
	return Message{Results: results}, nil
}

func (t *FlakyToolVertex) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	// checkpoint demo 只用 Run,这里简单复用 ToolVertex 逻辑(不 flaky)
	out, w := Pipe[Message]()
	go func() {
		defer w.Close()
		msg, _ := concatMsg(input)
		for _, tc := range msg.ToolCalls {
			if tc.Name == t.name {
				w.Send(Message{Results: []string{fmt.Sprintf("%s(%s)", t.name, tc.Arg)}}, nil)
			}
		}
	}()
	return out, nil
}

// ============================================================
// 场景
// ============================================================

func main() {
	loadEnv()

	// === 场景 1:Run(Invoke)基本 ReAct ===
	fmt.Println("=== 场景1:Run(Invoke) ===")
	g := NewGraph(20)
	model := &ModelVertex{}
	g.AddVertex(model)
	g.AddVertex(&ToolVertex{id: "search", name: "search"})
	g.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	addReActEdges(g)
	c, err := g.Compile()
	if err != nil {
		panic(err)
	}
	if err := c.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, ""); err != nil {
		fmt.Printf("Run 错误: %v\n", err)
	}
	fmt.Printf("最终答案: %s\n", model.Answer)

	// === 场景 2:StreamRun(Transform)真 LLM 流式 ===
	fmt.Println("\n=== 场景2:StreamRun(真 LLM 流式) ===")
	g2 := NewGraph(20)
	model2 := &ModelVertex{}
	g2.AddVertex(model2)
	g2.AddVertex(&ToolVertex{id: "search", name: "search"})
	g2.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	addReActEdges(g2)
	c2, err := g2.Compile()
	if err != nil {
		panic(err)
	}
	sr, err := c2.StreamRun(context.Background(), Message{Answer: "eino 框架是什么？"})
	if err != nil {
		fmt.Printf("StreamRun 错误: %v\n", err)
		return
	}
	fmt.Println("\n调用方逐块读取(每行首标时间戳):")
	start := time.Now()
	atLineStart := true
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
		atLineStart = strings.HasSuffix(s, "\n")
	}
	if !atLineStart {
		fmt.Println()
	}
	fmt.Printf("\n最终答案: %s\n", model2.Answer)

	// === 场景 3:edge handler(边转换)===
	// model->search 边挂 handler:过滤出 search 的 ToolCall。
	// model->calc 边挂 handler:过滤出 calc 的 ToolCall。
	// 演示"数据过边时被转换",search/calc 收到的已是自己的 ToolCall。
	fmt.Println("\n=== 场景3:edge handler(边转换) ===")
	g3 := NewGraph(20)
	model3 := &ModelVertex{}
	g3.AddVertex(model3)
	g3.AddVertex(&ToolVertex{id: "search", name: "search"})
	g3.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	g3.AddEdge(START, "model")
	g3.AddEdge("search", "model")
	g3.AddEdge("calc", "model")
	// ★ 边上挂 handler:过滤 ToolCall
	g3.AddEdgeWithHandler("model", "search", EdgeHandler{
		Invoke: filterToolCall("search"),
	})
	g3.AddEdgeWithHandler("model", "calc", EdgeHandler{
		Invoke: filterToolCall("calc"),
	})
	g3.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})
	c3, err := g3.Compile()
	if err != nil {
		panic(err)
	}
	fmt.Println("(model->search/calc 边挂了过滤 handler)")
	if err := c3.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, ""); err != nil {
		fmt.Printf("Run 错误: %v\n", err)
	}
	fmt.Printf("最终答案: %s\n", model3.Answer)

	// === 场景 4:checkpoint 崩溃恢复 ===
	// FlakyToolVertex 首次必崩。Run1 崩,Run2 同 ID 从 checkpoint 续跑(演示 channel.load)。
	fmt.Println("\n=== 场景4:checkpoint 崩溃恢复 ===")
	store := newMemoryStore()
	g4 := NewGraph(20)
	model4 := &ModelVertex{}
	flaky := &FlakyToolVertex{id: "flaky_search", name: "search"}
	g4.AddVertex(model4)
	g4.AddVertex(flaky)
	g4.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	g4.AddEdge(START, "model")
	g4.AddEdge("flaky_search", "model")
	g4.AddEdge("calc", "model")
	g4.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"flaky_search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"flaky_search": true, "calc": true, END: true},
	})
	c4, err := g4.Compile(WithCheckPointStore(store))
	if err != nil {
		panic(err)
	}
	fmt.Println("── Run 1(flaky_search 首次必崩)──")
	if err := c4.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "thread-1"); err != nil {
		fmt.Printf("Run 1 返回错误: %v\n", err)
	}
	fmt.Println("── Run 2(同 ID,从 checkpoint 续跑,channel.load 恢复)──")
	if err := c4.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "thread-1"); err != nil {
		fmt.Printf("Run 2 返回错误: %v\n", err)
	}
	fmt.Printf("最终答案: %s\n", model4.Answer)

	// === 场景 5:channel.convertValues 演示 ===
	fmt.Println()
	if err := demoConvertValues(); err != nil {
		fmt.Printf("convertValues demo 错误: %v\n", err)
	}
}

// addReActEdges 加 ReAct 拓扑:model + search + calc,model 按有无 ToolCall 分支。
func addReActEdges(g *Graph) {
	g.AddEdge(START, "model")
	g.AddEdge("search", "model")
	g.AddEdge("calc", "model")
	g.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})
}

// filterToolCall 造一个边 handler:只留指定 name 的 ToolCall。
// 演示 edge handler 的"数据过边时转换"。
func filterToolCall(name string) func(Message) (Message, error) {
	return func(m Message) (Message, error) {
		var filtered []ToolCall
		for _, tc := range m.ToolCalls {
			if tc.Name == name {
				filtered = append(filtered, tc)
			}
		}
		return Message{ToolCalls: filtered}, nil
	}
}
