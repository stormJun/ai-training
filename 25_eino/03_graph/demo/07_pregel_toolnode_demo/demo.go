// demo.go: ToolsNode 增量(7) — 把多个工具包成一个图顶点，内部分发。
//
// 06 用 per-tool 顶点 + fan-out 拓扑:
//
//	model → {search, calc} → model   (3条边, fan-out/fan-in, 需 edge handler 过滤)
//
// 07 引入 ToolsNode, 变成线性拓扑:
//
//	model → tools → model             (2条边, 无 fan-out/fan-in, 内部分发)
//
// ToolsNode 是编排层概念, 对应 eino compose.ToolsNode:
// 收到含 ToolCalls 的消息后, 按名字内部分发到对应工具函数, 并行执行, 汇总结果返回。
// 引擎层(Pregel)只看到一个顶点, 不知道内部有几个工具。
//
// 场景:
//   1. Run(Invoke): ToolsNode 基本ReAct(无LLM,快)
//   2. StreamRun(Transform): 真LLM流式
//   3. 对比: per-tool顶点(fan-out) vs ToolsNode(线性)
//   4. checkpoint: FlakyToolsNode 崩溃恢复
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

func (m *ModelVertex) ComponentType() component { return ComponentOfChatModel }

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

// ============================================================
// ToolsNode: 多工具包成一个图顶点，内部分发 (增量 7 核心)
// ============================================================

// ToolsNode 把多个工具包成一个图顶点。
// 收到含 ToolCalls 的消息后,按名字内部分发到对应工具函数,汇总结果返回。
// 对应 eino compose.ToolsNode(tool_node.go:79)。
//
// 与 06 的 per-tool 顶点对比:
//
//	06: 每个 ToolVertex 是独立 Pregel 顶点, model fan-out 到 N 个顶点
//	07: ToolsNode 是单个 Pregel 顶点, 内部按名字分发, model 只连一条边
//
// 引擎层(Pregel)不知道 ToolsNode 内部有几个工具——它就是一个 Vertex。
type ToolsNode struct {
	id    string
	tools map[string]func(ctx context.Context, arg string) (string, error)
}

// NewToolsNode 创建 ToolsNode。id 是图中的顶点标识(如 "tools")。
func NewToolsNode(id string) *ToolsNode {
	return &ToolsNode{
		id:    id,
		tools: make(map[string]func(ctx context.Context, arg string) (string, error)),
	}
}

// AddTool 注册一个工具函数。name 需与 ToolCall.Name 匹配。
func (tn *ToolsNode) AddTool(name string, fn func(ctx context.Context, arg string) (string, error)) {
	tn.tools[name] = fn
}

func (tn *ToolsNode) ID() string { return tn.id }

func (tn *ToolsNode) ComponentType() component { return ComponentOfToolsNode }

// Compute 内部分发:按 ToolCall.Name 查工具,并行执行,汇总结果。
// 对应 eino ToolsNode.Invoke(tool_node.go:1046) + parallelRunToolCall(tool_node.go:985)。
func (tn *ToolsNode) Compute(ctx context.Context, in Message) (Message, error) {
	if len(in.ToolCalls) == 0 {
		return Message{}, fmt.Errorf("ToolsNode: no tool calls in input")
	}

	// 并行执行(对应 eino parallelRunToolCall)
	type toolResult struct {
		name   string
		result string
		err    error
	}
	ch := make(chan toolResult, len(in.ToolCalls))
	for _, tc := range in.ToolCalls {
		fn, ok := tn.tools[tc.Name]
		if !ok {
			ch <- toolResult{name: tc.Name, err: fmt.Errorf("tool %q not found", tc.Name)}
			continue
		}
		go func(tc ToolCall) {
			r, err := fn(ctx, tc.Arg)
			ch <- toolResult{name: tc.Name, result: r, err: err}
		}(tc)
	}

	var results []string
	for i := 0; i < len(in.ToolCalls); i++ {
		r := <-ch
		if r.err != nil {
			return Message{}, r.err
		}
		fmt.Printf("  [tools] %s -> %s\n", r.name, r.result)
		results = append(results, r.result)
	}
	return Message{Results: results}, nil
}

// StreamCompute 流式版:逐个工具执行,每个结果立即发送。
// 对应 eino ToolsNode.Stream(tool_node.go:1148)。
func (tn *ToolsNode) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	out, w := Pipe[Message]()
	go func() {
		defer w.Close()
		msg, err := concatMsg(input)
		if err != nil {
			w.Send(Message{}, err)
			return
		}
		for _, tc := range msg.ToolCalls {
			fn, ok := tn.tools[tc.Name]
			if !ok {
				w.Send(Message{}, fmt.Errorf("tool %q not found", tc.Name))
				return
			}
			r, err := fn(ctx, tc.Arg)
			if err != nil {
				w.Send(Message{}, err)
				return
			}
			fmt.Printf("  [tools] 流式产出: %s -> %s\n", tc.Name, r)
			w.Send(Message{Results: []string{r}}, nil)
		}
	}()
	return out, nil
}

// FlakyToolsNode 不稳定 ToolsNode:首次 Compute 必崩,用于 checkpoint 演示。
type FlakyToolsNode struct {
	ToolsNode
	calls int
}

func (f *FlakyToolsNode) Compute(ctx context.Context, in Message) (Message, error) {
	f.calls++
	if f.calls == 1 {
		panic("模拟瞬时故障:首次必崩")
	}
	return f.ToolsNode.Compute(ctx, in)
}

// StreamCompute 流式版(不 flaky,checkpoint 只用 Run)
func (f *FlakyToolsNode) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	return f.ToolsNode.StreamCompute(ctx, input)
}

// ============================================================
// 对比用: 06 方式的 per-tool 顶点 (保留用于场景 3)
// ============================================================

// ToolVertex 单工具顶点(06 方式)。只处理匹配自己名字的 ToolCall。
type ToolVertex struct {
	id   string
	name string
}

func (t *ToolVertex) ID() string { return t.id }

func (t *ToolVertex) ComponentType() component { return ComponentOfTool }

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

// ============================================================
// 场景
// ============================================================

func main() {
	loadEnv()

	// === 场景 1: ToolsNode Run(Invoke) 基本 ReAct ===
	fmt.Println("=== 场景1: ToolsNode Run(Invoke) ===")
	g := NewGraph(20)
	model := &ModelVertex{}
	tools := NewToolsNode("tools")
	tools.AddTool("search", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("search(%s)", arg), nil
	})
	tools.AddTool("calc", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("calc(%s)", arg), nil
	})
	g.AddVertex(model)
	if err := g.AddToolsNode(tools); err != nil {
		panic(err)
	}
	addReActEdgesWithToolsNode(g)
	c, err := g.Compile()
	if err != nil {
		panic(err)
	}
	if err := c.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, ""); err != nil {
		fmt.Printf("Run 错误: %v\n", err)
	}
	fmt.Printf("最终答案: %s\n", model.Answer)

	// === 场景 2: StreamRun(Transform) 真LLM流式 ===
	fmt.Println("\n=== 场景2: StreamRun(真LLM流式) ===")
	g2 := NewGraph(20)
	model2 := &ModelVertex{}
	tools2 := NewToolsNode("tools")
	tools2.AddTool("search", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("search(%s)", arg), nil
	})
	tools2.AddTool("calc", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("calc(%s)", arg), nil
	})
	g2.AddVertex(model2)
	if err := g2.AddToolsNode(tools2); err != nil {
		panic(err)
	}
	addReActEdgesWithToolsNode(g2)
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

	// === 场景 3: 对比 per-tool 顶点 vs ToolsNode 拓扑 ===
	// 06: model → {search, calc} (fan-out, 每个工具是独立顶点)
	// 07: model → tools (线性, ToolsNode 内部分发)
	fmt.Println("\n=== 场景3: 对比 — per-tool顶点 vs ToolsNode ===")

	// 3a: 06 方式 — 每个工具一个顶点(fan-out)
	fmt.Println("\n--- 3a: per-tool顶点(fan-out, 06方式) ---")
	g3a := NewGraph(20)
	model3a := &ModelVertex{}
	g3a.AddVertex(model3a)
	g3a.AddVertex(&ToolVertex{id: "search", name: "search"})
	g3a.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	addReActEdges(g3a) // fan-out: model → {search, calc}
	c3a, _ := g3a.Compile()
	c3a.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "")
	fmt.Printf("最终答案: %s\n", model3a.Answer)

	// 3b: 07 方式 — ToolsNode(单节点内部分发)
	fmt.Println("\n--- 3b: ToolsNode(单节点, 07方式) ---")
	g3b := NewGraph(20)
	model3b := &ModelVertex{}
	tools3b := NewToolsNode("tools")
	tools3b.AddTool("search", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("search(%s)", arg), nil
	})
	tools3b.AddTool("calc", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("calc(%s)", arg), nil
	})
	g3b.AddVertex(model3b)
	if err := g3b.AddToolsNode(tools3b); err != nil {
		panic(err)
	}
	addReActEdgesWithToolsNode(g3b) // 线性: model → tools
	c3b, _ := g3b.Compile()
	c3b.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "")
	fmt.Printf("最终答案: %s\n", model3b.Answer)

	// === 场景 4: checkpoint + FlakyToolsNode 崩溃恢复 ===
	fmt.Println("\n=== 场景4: checkpoint 崩溃恢复 ===")
	store := newMemoryStore()
	g4 := NewGraph(20)
	model4 := &ModelVertex{}
	flakyTools := &FlakyToolsNode{ToolsNode: *NewToolsNode("tools")}
	flakyTools.AddTool("search", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("search(%s)", arg), nil
	})
	flakyTools.AddTool("calc", func(_ context.Context, arg string) (string, error) {
		return fmt.Sprintf("calc(%s)", arg), nil
	})
	g4.AddVertex(model4)
	if err := g4.AddToolsNode(flakyTools); err != nil {
		panic(err)
	}
	addReActEdgesWithToolsNode(g4)
	c4, err := g4.Compile(WithCheckPointStore(store))
	if err != nil {
		panic(err)
	}
	fmt.Println("── Run 1(FlakyToolsNode 首次必崩)──")
	if err := c4.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "thread-1"); err != nil {
		fmt.Printf("Run 1 返回错误: %v\n", err)
	}
	fmt.Println("── Run 2(同 ID,从 checkpoint 续跑)──")
	if err := c4.Run(context.Background(), Message{Answer: "eino 框架是什么？"}, "thread-1"); err != nil {
		fmt.Printf("Run 2 返回错误: %v\n", err)
	}
	fmt.Printf("最终答案: %s\n", model4.Answer)
}

// addReActEdgesWithToolsNode 加 ToolsNode 版 ReAct 拓扑:
//
//	model → tools → model (线性, 无 fan-out/fan-in)
//
// 对应 eino react agent 的 nodeKeyTools(nodeKeyTools="tools")。
func addReActEdgesWithToolsNode(g *Graph) {
	g.AddEdge(START, "model")
	g.AddEdge("tools", "model")
	g.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"tools"} // 单一目标,不需要 fan-out
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"tools": true, END: true},
	})
}

// addReActEdges 加 06 方式 ReAct 拓扑:
//
//	model → {search, calc} (fan-out, 需要 edge handler 或内部过滤)
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
