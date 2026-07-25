// Package main: Pregel 最小可运行内核(串行版,阶段 01)。
//
// 目标:用最少代码把 Pregel 四机制跑通--顶点为中心 + 超步循环 + 消息 S->S+1 +
// 触发与终止。Compute 串行、拓扑内联(无 Graph/Compile,无屏障/并行)。
//
// 这是整个 demo 序列的起点。后续阶段只增不改:
//
//	02_pregel_barrier -- 在本版基础上引入 taskManager 屏障:并行 Compute + 可中断
//	03_pregel_compile -- 引入 Graph/Compile:声明式拓扑 + 校验 + 环检测 + 冻结
//
// 三层解耦(唯一耦合是 Message):
//
//	Message  ── 纯数据,无行为(不带 To,路由由声明决定)
//	Vertex   ── 纯行为(Compute),无调度、不路由
//	Engine   ── 纯调度,无业务行为
//
// 四机制落点:
//
//	① 顶点为中心  -- Vertex 只写 Compute
//	② 超步        -- for step(本阶段串行,无屏障;屏障见 02)
//	③ 消息 S->S+1 -- current/next 邮箱,步末交换
//	④ 触发与终止  -- 有消息才激活;邮箱空即止
package main

import (
	"context"
	"fmt"
	"sort"
)

const (
	START = "START"
	END   = "END"
)

// ---------------- 消息(纯数据)----------------
// 顶点产出的值。不带 To--路由由声明的边/分支决定,不由顶点填。
type Message struct {
	ToolCalls []ToolCall // 模型要调的工具(模型产出时填)
	Results   []string   // 工具结果(工具产出时填)
	Answer    string     // 最终答案 / 用户问题
}

type ToolCall struct {
	Name string
	Arg  string
}

// ---------------- 顶点(纯行为)----------------
// 只写 Compute,不写循环、不路由。Compute 收消息、产出一个值。
// 接 ctx 是为后续阶段(02 的可中断)预留;本阶段用 Background,顶点不 watch。
type Vertex interface {
	ID() string
	Compute(ctx context.Context, msgs []Message) Message
}

// ---------------- 引擎:隐式拓扑(声明式边/分支内联)----------------
// 本阶段没有 Graph/Compile:拓扑(edges/branches)直接挂在 Engine 上,用 AddEdge/
// AddBranch 声明。Compile(校验 + 环检测 + 冻结)在 03 引入。
type Engine struct {
	vertices map[string]Vertex
	edges    map[string][]string // 普通边 from -> [to]
	branches map[string]*Branch  // 分支 from -> branch
	maxSteps int
}

// Branch 分支:看顶点产出值,决定发往哪些 endNode(可多个 = 下一超步并行)。
type Branch struct {
	Cond     func(Message) []string // 返回要发往的 endNode 列表
	EndNodes map[string]bool
}

func NewEngine(maxSteps int) *Engine {
	return &Engine{
		vertices: map[string]Vertex{},
		edges:    map[string][]string{},
		branches: map[string]*Branch{},
		maxSteps: maxSteps,
	}
}

func (e *Engine) AddVertex(v Vertex)               { e.vertices[v.ID()] = v }
func (e *Engine) AddEdge(from, to string)          { e.edges[from] = append(e.edges[from], to) }
func (e *Engine) AddBranch(from string, b *Branch) { e.branches[from] = b }

// route 按声明的拓扑决定 id 的产出 out 发往谁(顶点不选收件人)。
// 有分支:按 Cond(out) 选 endNode;无分支:发往所有普通边后继。
func (e *Engine) route(id string, out Message) []string {
	if b, ok := e.branches[id]; ok {
		return b.Cond(out)
	}
	return e.edges[id]
}

// ---------------- 运行期:superstep 循环(串行版)----------------
// 串行 Compute:逐个调活跃顶点的 Compute,无 goroutine、无屏障。
// 屏障/并行/可中断在 02_pregel_barrier;本阶段只把四机制跑通。
func (e *Engine) Run(ctx context.Context, initial Message) error {
	// START 产出 initial,按声明的边投递给后继
	current := map[string][]Message{}
	for _, to := range e.edges[START] {
		current[to] = append(current[to], initial)
	}

	for step := 0; step < e.maxSteps; step++ { // ② 超步(只是个号)
		if len(current) == 0 {
			fmt.Println("无在途消息,计算结束")
			return nil // ④ 终止:无在途消息
		}

		fmt.Printf("\n── superstep %d ── 活跃顶点: %v\n", step, sortedKeys(current))

		next := map[string][]Message{} // ③ 在途消息池:S 发的,S+1 才送达
		for _, id := range sortedKeys(current) { // ④ 触发:有消息的顶点才跑(串行,按 ID 排序保证输出确定)
			msgs := current[id]
			v := e.vertices[id]
			out := v.Compute(ctx, msgs) // ① 顶点为中心:只调 Compute,顶点不路由
			for _, to := range e.route(v.ID(), out) {
				if to == END {
					fmt.Printf("  [%s] -> END(终端)\n", v.ID())
					continue
				}
				next[to] = append(next[to], out) // 进 next,本步不读
			}
		}
		current = next // ③ 交换:S 发的 = S+1 收的(BSP 节奏压在这一行两侧)
	}

	fmt.Println("达到 maxSteps 上限,强制停止")
	return nil
}

func sortedKeys(m map[string][]Message) []string {
	ks := make([]string, 0, len(m))
	for k := range m {
		ks = append(ks, k)
	}
	sort.Strings(ks)
	return ks
}

// ============================================================
// Demo:mini-ReAct(model + search + calc),声明式拓扑
// ============================================================

type ModelVertex struct {
	step   int
	Answer string
}

func (m *ModelVertex) ID() string { return "model" }
func (m *ModelVertex) Compute(ctx context.Context, msgs []Message) Message {
	m.step++
	fmt.Printf("  [model] 第 %d 次激活,收到 %d 条消息\n", m.step, len(msgs))

	if m.step == 1 {
		// 第一轮:产出带两个 tool call 的消息。分支据此路由到 search+calc(下一超步两个顶点)
		fmt.Println("  [model] 产出 ToolCalls=[search, calc]")
		return Message{ToolCalls: []ToolCall{
			{Name: "search", Arg: "eino pregel"},
			{Name: "calc", Arg: "2+3"},
		}}
	}
	// 第二轮:汇总工具结果,产出最终答案。分支据此路由到 END
	var results []string
	for _, m := range msgs {
		results = append(results, m.Results...)
	}
	m.Answer = fmt.Sprintf("done with %d results: %v", len(results), results)
	fmt.Printf("  [model] 产出最终答案 %q,路由到 END\n", m.Answer)
	return Message{Answer: m.Answer}
}

type ToolVertex struct {
	id   string
	name string
}

func (t *ToolVertex) ID() string { return t.id }
func (t *ToolVertex) Compute(ctx context.Context, msgs []Message) Message {
	var results []string
	for _, m := range msgs {
		for _, tc := range m.ToolCalls {
			if tc.Name == t.name { // 只执行属于自己的 tool call
				r := fmt.Sprintf("%s(%s)", t.name, tc.Arg)
				fmt.Printf("  [%s] 执行 %s -> %s\n", t.id, tc.Arg, r)
				results = append(results, r)
			}
		}
	}
	return Message{Results: results}
}

func main() {
	e := NewEngine(20)
	model := &ModelVertex{}
	e.AddVertex(model)
	e.AddVertex(&ToolVertex{id: "search", name: "search"})
	e.AddVertex(&ToolVertex{id: "calc", name: "calc"})

	// 声明式拓扑(本阶段内联,无 Compile):
	//
	//	START ──AddEdge──▶ model ──AddBranch──▶ {search, calc}(有 tool call)
	//	                      ▲                    │
	//	                      │                    └──▶ END(无 tool call)
	//	        AddEdge ◀────┴─────────────────┘ (search/calc 结果回 model)
	e.AddEdge(START, "model") // 用户问题 -> model
	e.AddEdge("search", "model")
	e.AddEdge("calc", "model")
	e.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"} // 有 tool call -> 两个工具
			}
			return []string{END} // 否则 -> 结束
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})

	// 运行(本阶段用 Background;ctx 取消见 02)
	if err := e.Run(context.Background(), Message{Answer: "user question"}); err != nil {
		fmt.Printf("run error: %v\n", err)
		return
	}

	fmt.Printf("\n最终答案: %s\n", model.Answer)
}
