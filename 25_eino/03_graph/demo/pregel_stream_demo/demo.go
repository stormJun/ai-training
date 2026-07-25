// demo.go:演示场景代码——各种顶点实现与 main 函数。
//
// 包含五个场景:
//   - 场景一: 正常 ReAct 流程 + State(TokenCounter)
//   - 场景二: 主动取消 (slow 顶点响应 ctx)
//   - 场景三: 崩溃恢复 (FlakyToolVertex + checkpoint)
//   - 场景四: 中断恢复 (ApprovalToolVertex + Interrupt/Resume)
//   - 场景五: State checkpoint 恢复 (崩溃后 State 不丢失)
package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"time"
)

// ============================================================
// Demo 顶点实现
// ============================================================

// ModelVertex 模型顶点:模拟 LLM 的推理过程。
type ModelVertex struct {
	step   int
	Answer string
}

func (m *ModelVertex) ID() string { return "model" }
func (m *ModelVertex) Compute(ctx context.Context, msgs []Message) (Message, error) {
	m.step++
	fmt.Printf("  [model] 第 %d 次激活,收到 %d 条消息\n", m.step, len(msgs))

	// ⑦ 累加 token 用量(图级共享 State)
	ProcessState(ctx, func(s *GraphState) {
		s.TokenCount += 150
		fmt.Printf("  [model] TokenCount += 150 -> %d\n", s.TokenCount)
	})

	if m.step == 1 {
		fmt.Println("  [model] 产出 ToolCalls=[search, calc]")
		return Message{ToolCalls: []ToolCall{
			{Name: "search", Arg: "eino pregel"},
			{Name: "calc", Arg: "2+3"},
		}}, nil
	}
	var results []string
	for _, m := range msgs {
		results = append(results, m.Results...)
	}
	m.Answer = fmt.Sprintf("done with %d results: %v", len(results), results)
	fmt.Printf("  [model] 产出最终答案 %q,路由到 END\n", m.Answer)
	return Message{Answer: m.Answer}, nil
}

// StreamCompute 流式计算(Transform 范式):收流产流。
// async:启 goroutine 消费输入流、产出输出流,立即返回输出流 handle。
// 步骤判定不靠 m.step(流式下跨进程会丢),而是看输入内容:
//   - 输入无 Results(来自 START 的初始问题)-> 产出 ToolCalls(1 个 chunk)
//   - 输入有 Results(来自工具)-> 汇总产出 Answer(分多 chunk 流式吐出)
func (m *ModelVertex) StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error) {
	out, w := Pipe[Message]()
	go func() {
		defer w.Close()
		// concat 输入流,判断该产什么
		msg, err := concatMsg(input)
		if err != nil {
			w.Send(Message{}, err)
			return
		}
		if len(msg.Results) > 0 {
			// step 2:汇总工具结果,流式吐出最终答案(分多块,演示流式)
			answer := fmt.Sprintf("done with %d results: %v", len(msg.Results), msg.Results)
			m.Answer = answer
			fmt.Printf("  [model] 流式产出答案(分块): %q\n", answer)
			for _, chunk := range splitChunks(answer, 8) {
				w.Send(Message{Answer: chunk}, nil)
			}
		} else {
			// step 1:产出 ToolCalls(单个 chunk)
			fmt.Println("  [model] 流式产出 ToolCalls=[search, calc]")
			w.Send(Message{ToolCalls: []ToolCall{
				{Name: "search", Arg: "eino pregel"},
				{Name: "calc", Arg: "2+3"},
			}}, nil)
		}
	}()
	return out, nil
}

// splitChunks 把字符串按固定长度切成多块(模拟 LLM 逐块吐出)。
func splitChunks(s string, size int) []string {
	var chunks []string
	for i := 0; i < len(s); i += size {
		end := i + size
		if end > len(s) {
			end = len(s)
		}
		chunks = append(chunks, s[i:end])
	}
	if len(chunks) == 0 {
		chunks = []string{s}
	}
	return chunks
}

// ToolVertex 工具顶点:执行特定的工具调用。
type ToolVertex struct {
	id   string
	name string
}

func (t *ToolVertex) ID() string { return t.id }
func (t *ToolVertex) Compute(ctx context.Context, msgs []Message) (Message, error) {
	var results []string
	for _, m := range msgs {
		for _, tc := range m.ToolCalls {
			if tc.Name == t.name {
				r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
				fmt.Printf("  [%s] 执行 %s -> %s\n", t.id, tc.Arg, r)
				results = append(results, r)
			}
		}
	}
	// ⑦ 累加 token 用量(图级共享 State)
	ProcessState(ctx, func(s *GraphState) {
		s.TokenCount += 30
		fmt.Printf("  [%s] TokenCount += 30 -> %d\n", t.id, s.TokenCount)
	})
	return Message{Results: results}, nil
}

// StreamCompute 流式计算:concat 输入流,逐个 ToolCall 产出 Result chunk。
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

// FlakyToolVertex 不稳定工具顶点:第一次调用必崩溃,模拟瞬时故障。
type FlakyToolVertex struct {
	id    string
	name  string
	calls int
}

func (t *FlakyToolVertex) ID() string { return t.id }
func (t *FlakyToolVertex) Compute(ctx context.Context, msgs []Message) (Message, error) {
	t.calls++
	if t.calls == 1 {
		panic("模拟瞬时故障:首次调用必崩(如进程崩溃/网络超时)")
	}
	var results []string
	for _, m := range msgs {
		for _, tc := range m.ToolCalls {
			if tc.Name == t.name {
				r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
				fmt.Printf("  [%s] 执行 %s -> %s(第 %d 次调用)\n", t.id, tc.Arg, r, t.calls)
				results = append(results, r)
			}
		}
	}
	return Message{Results: results}, nil
}

// SlowVertex 慢顶点:Compute 睡 0.5s 但响应 ctx,模拟耗时顶点(如 LLM 调用)。
type SlowVertex struct{}

func (s *SlowVertex) ID() string { return "slow" }
func (s *SlowVertex) Compute(ctx context.Context, msgs []Message) (Message, error) {
	fmt.Println("  [slow] 开始计算(睡 0.5s,但响应 ctx)...")
	select {
	case <-time.After(500 * time.Millisecond):
		fmt.Println("  [slow] 计算完成")
		return Message{}, nil
	case <-ctx.Done():
		fmt.Println("  [slow] 被 ctx 取消,提前返回(in-flight Compute 被打断)")
		return Message{}, nil
	}
}

// ApprovalToolVertex 审批工具顶点:需要人工审批的工具。
type ApprovalToolVertex struct {
	id       string
	name     string
	calls    int
	approved bool
}

func (t *ApprovalToolVertex) ID() string { return t.id }
func (t *ApprovalToolVertex) Compute(ctx context.Context, msgs []Message) (Message, error) {
	t.calls++

	var tc ToolCall
	for _, m := range msgs {
		for _, c := range m.ToolCalls {
			tc = c
		}
	}

	if t.calls == 1 && !t.approved {
		fmt.Printf("  [%s] 需要人工审批,tool call: %s(%s)\n", t.id, tc.Name, tc.Arg)
		return Message{}, Interrupt(t.id, "need human approval", tc)
	}

	fmt.Printf("  [%s] 审批通过,执行: %s(%s)\n", t.id, tc.Name, tc.Arg)
	return Message{Results: []string{fmt.Sprintf("%s(%s) approved", tc.Name, tc.Arg)}}, nil
}

// ============================================================
// Resume 函数(增量 2)
// ============================================================

func (c *Compiled) Resume(ctx context.Context, checkPointID string, approvalData any) error {
	if c.store == nil {
		return fmt.Errorf("no checkpoint store")
	}

	cp, ok, err := c.store.Get(ctx, checkPointID)
	if err != nil {
		return fmt.Errorf("load checkpoint fail: %w", err)
	}
	if !ok {
		return fmt.Errorf("no checkpoint found: %s", checkPointID)
	}
	if cp.InterruptInfo == nil {
		return fmt.Errorf("checkpoint is not an interrupt")
	}

	fmt.Printf("\n=== Resume: 从中断恢复 ===\n")
	fmt.Printf("[resume] 中断节点: %s, 原因: %s\n", cp.InterruptInfo.NodeID, cp.InterruptInfo.Message)
	fmt.Printf("[resume] 注入审批数据: %v\n", approvalData)

	if v, ok := c.vertices[cp.InterruptInfo.NodeID]; ok {
		if atv, ok := v.(*ApprovalToolVertex); ok {
			atv.approved = true
		}
	}

	_ = c.store.Delete(ctx, checkPointID)
	fmt.Println("[resume] 审批已注入,可重新执行")
	return nil
}

// ============================================================
// 演示场景
// ============================================================

func main() {
	// === 场景一:正常 ReAct 流程 + State(TokenCounter) ===
	fmt.Println("=== 场景一:正常 ReAct 流程 + State ===")
	g := NewGraph(20)
	model := &ModelVertex{}
	g.AddVertex(model)
	g.AddVertex(&ToolVertex{id: "search", name: "search"})
	g.AddVertex(&ToolVertex{id: "calc", name: "calc"})

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

	// ⑦ 编译时注册 State 工厂函数
	c, err := g.Compile(WithGenLocalState(func() *GraphState {
		return &GraphState{TokenCount: 0}
	}))
	if err != nil {
		panic(err)
	}

	if err := c.Run(context.Background(), Message{Answer: "user question"}, ""); err != nil {
		fmt.Printf("run error: %v\n", err)
		return
	}
	fmt.Printf("\n最终答案: %s\n", model.Answer)

	// === 场景二:主动取消 ===
	fmt.Println("\n=== 场景二:主动取消 ===")
	g2 := NewGraph(5)
	g2.AddVertex(&SlowVertex{})
	g2.AddEdge(START, "slow")
	c2, err := g2.Compile()
	if err != nil {
		panic(err)
	}
	ctx2, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(100 * time.Millisecond)
		fmt.Println("  (主动 cancel())")
		cancel()
	}()
	if err := c2.Run(ctx2, Message{Answer: "start"}, ""); err != nil {
		fmt.Printf("Run 返回错误(被取消): %v\n", err)
	}

	// === 场景三:断点续跑(checkpoint)===
	fmt.Println("\n=== 场景三:断点续跑(checkpoint)===")
	store := newMemoryStore()
	g3 := NewGraph(20)
	model3 := &ModelVertex{}
	flaky := &FlakyToolVertex{id: "flaky_search", name: "search"}
	g3.AddVertex(model3)
	g3.AddVertex(flaky)
	g3.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	g3.AddEdge(START, "model")
	g3.AddEdge("flaky_search", "model")
	g3.AddEdge("calc", "model")
	g3.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"flaky_search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"flaky_search": true, "calc": true, END: true},
	})
	c3, err := g3.Compile(WithCheckPointStore(store))
	if err != nil {
		panic(err)
	}

	fmt.Println("\n── Run 1(flaky_search 首次调用必崩)──")
	if err := c3.Run(context.Background(), Message{Answer: "user question"}, "thread-1"); err != nil {
		fmt.Printf("Run 1 返回错误: %v\n", err)
	}

	fmt.Println("\n── Run 2(同 checkpoint ID,从断点续跑)──")
	if err := c3.Run(context.Background(), Message{Answer: "user question"}, "thread-1"); err != nil {
		fmt.Printf("Run 2 返回错误: %v\n", err)
		return
	}
	fmt.Printf("\n最终答案: %s\n", model3.Answer)

	// === 场景四:Interrupt/Resume(HITL 人工审批)===
	fmt.Println("\n=== 场景四:Interrupt/Resume(HITL 人工审批)===")
	store4 := newMemoryStore()
	g4 := NewGraph(20)
	approvalTool := &ApprovalToolVertex{id: "approval_tool", name: "approval_tool"}
	g4.AddVertex(approvalTool)
	g4.AddEdge(START, "approval_tool")
	g4.AddEdge("approval_tool", END)
	c4, err := g4.Compile(WithCheckPointStore(store4))
	if err != nil {
		panic(err)
	}

	fmt.Println("\n── Run 1:请求中断等待审批 ──")
	err = c4.Run(context.Background(), Message{ToolCalls: []ToolCall{{Name: "approval_tool", Arg: "dangerous operation"}}}, "thread-interrupt")
	if err != nil {
		var intErr *InterruptError
		if errors.As(err, &intErr) {
			fmt.Printf("[demo] 收到中断: %s, 数据: %v\n", intErr.Info.Message, intErr.Info.Data)
		}
	}

	fmt.Println("\n── Resume:审批通过后继续执行 ──")
	err = c4.Resume(context.Background(), "thread-interrupt", "approved")
	if err != nil {
		fmt.Printf("[demo] Resume 错误: %v\n", err)
	}
	fmt.Println("[demo] Resume 演示完成")

	// === 场景五:State checkpoint 恢复 ===
	// 演示:崩溃恢复后 State 不丢失。
	// Run 1: model(150) + flaky_search(崩溃) -> checkpoint 保存 State.TokenCount=150
	// Run 2: 从 checkpoint 恢复,State.TokenCount=150 被保留,后续累加在此基础上继续
	fmt.Println("\n=== 场景五:State checkpoint 恢复 ===")
	store5 := newMemoryStore()
	g5 := NewGraph(20)
	model5 := &ModelVertex{}
	flaky5 := &FlakyToolVertex{id: "flaky_search", name: "search"}
	g5.AddVertex(model5)
	g5.AddVertex(flaky5)
	g5.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	g5.AddEdge(START, "model")
	g5.AddEdge("flaky_search", "model")
	g5.AddEdge("calc", "model")
	g5.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"flaky_search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"flaky_search": true, "calc": true, END: true},
	})
	c5, err := g5.Compile(
		WithCheckPointStore(store5),
		WithGenLocalState(func() *GraphState { return &GraphState{TokenCount: 0} }),
	)
	if err != nil {
		panic(err)
	}

	fmt.Println("\n── Run 1:flaky_search 崩溃,State 已存入 checkpoint ──")
	if err := c5.Run(context.Background(), Message{Answer: "user question"}, "thread-state"); err != nil {
		fmt.Printf("Run 1 返回错误: %v\n", err)
	}

	fmt.Println("\n── Run 2:从断点续跑,State 从 checkpoint 恢复 ──")
	if err := c5.Run(context.Background(), Message{Answer: "user question"}, "thread-state"); err != nil {
		fmt.Printf("Run 2 返回错误: %v\n", err)
		return
	}
	fmt.Printf("\n最终答案: %s\n", model5.Answer)

	// === 场景六:StreamRun(流式执行,增量 4)===
	// 演示端到端流式:model 流式产出 -> Copy 扇出给 search/calc ->
	// search/calc 流式产出 -> Merge 扇入回 model -> model 流式产出最终答案 ->
	// 调用方逐块读取。
	fmt.Println("\n=== 场景六:StreamRun(流式执行)===")
	g6 := NewGraph(20)
	model6 := &ModelVertex{}
	g6.AddVertex(model6)
	g6.AddVertex(&ToolVertex{id: "search", name: "search"})
	g6.AddVertex(&ToolVertex{id: "calc", name: "calc"})
	g6.AddEdge(START, "model")
	g6.AddEdge("search", "model")
	g6.AddEdge("calc", "model")
	g6.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})
	c6, err := g6.Compile()
	if err != nil {
		panic(err)
	}

	sr, err := c6.StreamRun(context.Background(), Message{Answer: "user question"})
	if err != nil {
		fmt.Printf("StreamRun 错误: %v\n", err)
		return
	}
	fmt.Println("\n调用方逐块读取最终流:")
	for {
		chunk, err := sr.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			fmt.Printf("读流出错: %v\n", err)
			break
		}
		fmt.Printf("  收到 chunk: Answer=%q\n", chunk.Answer)
	}
	fmt.Printf("\n最终答案: %s\n", model6.Answer)
}
