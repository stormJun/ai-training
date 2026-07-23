// Package main: Pregel 最小可运行 MVP(含最小 Compile 阶段)。
//
// 在隐式拓扑版基础上引入 Compile:把构建期"声明式拓扑"(AddEdge/AddBranch)
// 编译成运行期路由表 + 做结构校验与环检测。对应 eino graph.go:674 的 compile。
//
// 核心变化:路由从"顶点填 To"改为"声明式边/分支路由"--顶点只产值,branch 路由
// (对应 eino:顶点只产出 *schema.Message,声明的 AddBranch 按消息内容路由)。
//
// 三层解耦(唯一耦合是 Message):
//
//	Message  ── 纯数据,无行为(不带 To,路由由声明决定)
//	Vertex   ── 纯行为(Compute),无调度、不路由
//	Engine   ── 纯调度 + 编译,无业务行为
//
// 五机制落点:
//
//	① 顶点为中心  -- Vertex 只写 Compute
//	② 超步 + 屏障 -- for step + taskManager(done 通道 + 计数 + select)
//	③ 消息 S->S+1 -- current/next 邮箱,屏障处交换
//	④ 触发与终止  -- 有消息才激活;邮箱空即止
//	⑤ Compile    -- 声明式拓扑 -> 后继表 + 校验 + 环检测(graph.go:674)
package main

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"
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
type Vertex interface {
	ID() string
	Compute(ctx context.Context, msgs []Message) Message
}

// ---------------- 构建期:声明式拓扑 ----------------
type Graph struct {
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

func NewGraph(maxSteps int) *Graph {
	return &Graph{
		vertices: map[string]Vertex{},
		edges:    map[string][]string{},
		branches: map[string]*Branch{},
		maxSteps: maxSteps,
	}
}

func (g *Graph) AddVertex(v Vertex)               { g.vertices[v.ID()] = v }
func (g *Graph) AddEdge(from, to string)          { g.edges[from] = append(g.edges[from], to) }
func (g *Graph) AddBranch(from string, b *Branch) { g.branches[from] = b }

// ---------------- Compile:声明式拓扑 -> 运行期结构 ----------------
// 对应 eino graph.go:674 的 compile:把 edges/branches 翻译成运行期后继表,
// 做结构校验,跑环检测。产出 *Compiled 供 Run 使用。
type Compiled struct {
	vertices map[string]Vertex
	edges    map[string][]string // 普通边后继
	branches map[string]*Branch
	maxSteps int
}

func (g *Graph) Compile() (*Compiled, error) {
	// 1. 结构校验:边/分支的源与目标必须是已注册顶点或 START/END
	for from, tos := range g.edges {
		if _, ok := g.vertices[from]; !ok && from != START {
			return nil, fmt.Errorf("edge source %q is not a registered vertex", from)
		}
		for _, to := range tos {
			if _, ok := g.vertices[to]; !ok && to != END {
				return nil, fmt.Errorf("edge target %q is not a registered vertex (from %q)", to, from)
			}
		}
	}
	for from, b := range g.branches {
		if _, ok := g.vertices[from]; !ok {
			return nil, fmt.Errorf("branch source %q is not a registered vertex", from)
		}
		for end := range b.EndNodes {
			if _, ok := g.vertices[end]; !ok && end != END {
				return nil, fmt.Errorf("branch endNode %q is not a registered vertex (from %q)", end, from)
			}
		}
	}

	// 2. 环检测(Kahn 入度法 + 路径 DFS,对应 eino validateDAG + findLoops)。
	//    Pregel 允许环(ReAct 需要),这里只报告不拒绝。
	succ := g.successors() // 合并普通边 + 分支 endNodes 的后继表
	if loops := findLoops(succ); len(loops) > 0 {
		fmt.Printf("[compile] 检测到环: %s(Pregel 允许,继续编译)\n", formatLoops(loops))
	} else {
		fmt.Println("[compile] 无环")
	}

	return &Compiled{
		vertices: g.vertices,
		edges:    g.edges,
		branches: g.branches,
		maxSteps: g.maxSteps,
	}, nil
}

// successors 合并普通边与分支 endNodes,返回完整后继表(供环检测)。
//
// 例(demo 的数据):
//
//	edges    = { START:["model"], search:["model"], calc:["model"] }
//	branches = { model: {search, calc, END} }
//
// 合并后:
//
//	succ = {
//	    START:  ["model"],
//	    search: ["model"],
//	    calc:   ["model"],
//	    model:  ["search", "calc", "END"],   // 分支 endNodes
//	}
//
// 分开看时 model->search(在 branches)和 search->model(在 edges)分属两表,
// 看不出环;合并后 model->search->model 落在同一张表里,detectCycle 才能发现环。
func (g *Graph) successors() map[string][]string {
	succ := map[string][]string{}
	for from, tos := range g.edges {
		succ[from] = append(succ[from], tos...)
	}
	for from, b := range g.branches {
		for end := range b.EndNodes {
			succ[from] = append(succ[from], end)
		}
	}
	return succ
}

// findLoops 检测并提取图中所有环。两阶段,对应 eino validateDAG(graph.go:1080)+ findLoops(graph.go:1131)。
//
//	阶段 1 Kahn 入度法:入度 0 的节点不在环上,摘掉它并减后继入度;反复摘到摘不动,
//	                 剩下入度仍 >0 的节点就是环上的(它们互相指着,入度永远降不到 0)。
//	阶段 2 路径 DFS:从起点出发,后继已在当前路径上 = 回到祖先 = 环,提取环路径。
//	         visited 防止从已探索的起点重复出发(对应 eino 的外层剪枝)。
func findLoops(succ map[string][]string) [][]string {
	// 阶段 1:Kahn 入度法
	indeg := map[string]int{}
	for from, tos := range succ {
		if _, ok := indeg[from]; !ok {
			indeg[from] = 0
		}
		for _, to := range tos {
			if to != END {
				indeg[to]++
			}
		}
	}
	for changed := true; changed; {
		changed = false
		for n, d := range indeg {
			if d == 0 {
				changed = true
				for _, to := range succ[n] {
					if to != END {
						indeg[to]--
					}
				}
				indeg[n] = -1 // 标记已摘除
			}
		}
	}
	var starts []string
	for n, d := range indeg {
		if d > 0 {
			starts = append(starts, n)
		}
	}
	if len(starts) == 0 {
		return nil
	}

	// 阶段 2:路径 DFS
	var loops [][]string
	visited := map[string]bool{}
	var dfs func(path []string)
	dfs = func(path []string) {
		end := path[len(path)-1]
		for _, next := range succ[end] {
			if next == END {
				continue
			}
			visited[next] = true
			looped := false
			for i, n := range path {
				if n == next {
					loops = append(loops, append(append([]string{}, path[i:]...), next))
					looped = true
					break
				}
			}
			if looped {
				continue
			}
			dfs(append(append([]string{}, path...), next)) // 拷贝 path,避免 append 别名
		}
	}
	sort.Strings(starts)
	for _, s := range starts {
		if !visited[s] {
			dfs([]string{s})
		}
	}
	return loops
}

// formatLoops 把环列表拼成 [a->b->a][c->d->c] 形式(对应 eino formatLoops,graph.go:1184)。
func formatLoops(loops [][]string) string {
	parts := make([]string, 0, len(loops))
	for _, l := range loops {
		parts = append(parts, "["+strings.Join(l, "->")+"]")
	}
	return strings.Join(parts, "")
}

// route 按声明的拓扑决定 id 的产出 out 发往谁(顶点不选收件人)。
// 有分支:按 Cond(out) 选 endNode;无分支:发往所有普通边后继。
func (c *Compiled) route(id string, out Message) []string {
	if b, ok := c.branches[id]; ok {
		return b.Cond(out)
	}
	return c.edges[id]
}

// ---------------- 屏障:done 通道 + 计数(对应 eino taskManager,graph_manager.go:269)--
// num 用「单一所有者」模型保证无锁安全:只由 Owner(Run 协程)读写,worker 只发 done 信号 -> 裸 int 无需 mutex。
// 比 sync.WaitGroup 多两件:顶点 panic 转 error(不崩程序)、context 取消/超时可打断等待(select)。
type task struct {
	v   Vertex
	in  []Message
	out Message
	err error // 顶点 panic 等
}

type taskManager struct {
	done chan *task // 完成信号:worker 发,Owner 收(通道本身并发安全)
	num  int        // 未完成计数。唯一所有者 = Owner 协程;worker 禁止读写
}

func newTaskManager(n int) *taskManager {
	return &taskManager{done: make(chan *task, n)} // 缓冲 = 任务数,worker 发送不阻塞
}

// submit 由 Owner 协程调用:在屏障前串行累加 num,无并发。
func (tm *taskManager) submit(ctx context.Context, tasks []*task) {
	for _, t := range tasks {
		tm.num++         // Owner 写 num
		go tm.execute(ctx, t) // 启动 worker(注意:worker 不碰 num;ctx 透传给 Compute)
	}
}

func (tm *taskManager) execute(ctx context.Context, t *task) {
	defer func() {
		if r := recover(); r != nil { // ① panic 恢复:转 error,不崩程序
			t.err = fmt.Errorf("vertex[%s] panic: %v", t.v.ID(), r)
		}
		tm.done <- t // ② 仅发完成信号。⚠️ 禁止在此 num--:多 worker 并发改 num 会竞争,须加锁--那是大忌
	}()
	t.out = t.v.Compute(ctx, t.in) // ctx 透传进 Compute,顶点可 watch ctx 实现中途打断
}

// wait 由 Owner 协程独占读写 num:收 done 信号后自己 num--(单消费者,无竞争)。
// select 同时监听 done(任务完成)与 ctx.Done()(取消/超时),实现可中断屏障。
func (tm *taskManager) wait(ctx context.Context) bool {
	for tm.num > 0 { // Owner 读 num
		select {
		case <-tm.done: // 收 worker 完成事件 从通道接收信号，值直接丢弃，只触发分支
			tm.num-- // Owner 写 num
		case <-ctx.Done(): // ③ 取消/超时:协作式--不立即返回,等 worker 响应 ctx 后收尾(对应 eino "wait for current tasks")
			for tm.num > 0 { // drain 剩余 done:worker 因 ctx 提前返回后会发完成信号
				<-tm.done
				tm.num--
			}
			return false
		}
	}
	return true
}

// ---------------- 运行期:superstep 循环 ----------------
func (c *Compiled) Run(ctx context.Context, initial Message) error {
	// START 产出 initial,按声明的边投递给后继(对应 eino 的 START 入边)
	current := map[string][]Message{}
	for _, to := range c.edges[START] {
		current[to] = append(current[to], initial)
	}

	for step := 0; step < c.maxSteps; step++ { // ② 超步
		if len(current) == 0 {
			fmt.Println("无在途消息,计算结束")
			return nil // ④ 终止
		}

		fmt.Printf("\n── superstep %d ── 活跃顶点: %v\n", step, sortedKeys(current))

		// 构造本超步任务(每个活跃顶点一个)
		var tasks []*task
		for id, msgs := range current { // ④ 触发:有消息的顶点才跑
			if v, ok := c.vertices[id]; ok {
				tasks = append(tasks, &task{v: v, in: msgs})
			}
		}

		// 并行执行(屏障:done 通道 + 计数,可中断)
		tm := newTaskManager(len(tasks))
		tm.submit(ctx, tasks)
		if !tm.wait(ctx) { // ② 屏障
			return ctx.Err() // 被取消/超时
		}

		// 串行路由进 next(屏障后,无需锁;对应 eino resolveCompletedTasks)
		next := map[string][]Message{} // ③ 在途消息池
		for _, t := range tasks {
			if t.err != nil {
				return t.err // 顶点 panic 等
			}
			for _, to := range c.route(t.v.ID(), t.out) { // 声明式路由(顶点不选)
				if to == END {
					fmt.Printf("  [%s] -> END(终端)\n", t.v.ID())
					continue
				}
				next[to] = append(next[to], t.out)
			}
		}
		current = next // ③ 交换:S 发的 = S+1 收的
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
		// 第一轮:产出带两个 tool call 的消息。分支会据此路由到 search+calc(并行)
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

// SlowVertex 演示用:Compute 睡 0.5s 但响应 ctx,模拟耗时顶点(如 LLM 调用)。用于"主动取消"场景。
type SlowVertex struct{}

func (s *SlowVertex) ID() string { return "slow" }
func (s *SlowVertex) Compute(ctx context.Context, msgs []Message) Message {
	fmt.Println("  [slow] 开始计算(睡 0.5s,但响应 ctx)...")
	select {
	case <-time.After(500 * time.Millisecond):
		fmt.Println("  [slow] 计算完成")
		return Message{}
	case <-ctx.Done(): // watch ctx:取消时提前返回,in-flight Compute 被打断
		fmt.Println("  [slow] 被 ctx 取消,提前返回(in-flight Compute 被打断)")
		return Message{}
	}
}

func main() {
	g := NewGraph(20)
	model := &ModelVertex{}
	g.AddVertex(model)
	g.AddVertex(&ToolVertex{id: "search", name: "search"})
	g.AddVertex(&ToolVertex{id: "calc", name: "calc"})

	// 声明式拓扑(对应 eino AddEdge / AddBranch):
	//
	//	START ──AddEdge(无条件)──▶ model ──AddBranch(条件)──▶ {search, calc}(有 tool call)
	//	                              ▲                      │
	//	                              │                      └──▶ END(无 tool call)
	//	              AddEdge ◀───────┴──────────────────┘
	//	              (search/calc 结果无条件回 model)
	//
	// 工具结果总要回模型(无条件)-> AddEdge;模型按产出决定去工具还是结束(条件)-> AddBranch。
	g.AddEdge(START, "model") // 用户问题 -> model
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

	// Compile:声明式拓扑 -> 运行期结构 + 校验 + 环检测
	c, err := g.Compile()
	if err != nil {
		panic(err)
	}

	// 运行(context 支持取消/超时,这里用 Background)
	if err := c.Run(context.Background(), Message{Answer: "user question"}); err != nil {
		fmt.Printf("run error: %v\n", err)
		return
	}

	fmt.Printf("\n最终答案: %s\n", model.Answer)

	// === 场景二:主动取消 ===
	// slow 顶点睡 0.5s 但响应 ctx;用 WithCancel 的 ctx,Run 起来后 100ms 取消。
	// ctx 透传进 Compute:slow 的 select 命中 ctx.Done() 提前返回(in-flight 被打断);
	// 屏障 wait 也命中 ctx.Done(),Run 立即返回 context.Canceled(不等 slow 睡完)。
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
		time.Sleep(100 * time.Millisecond) // 等 Run 进入屏障等待
		fmt.Println("  (主动 cancel())")
		cancel()
	}()
	if err := c2.Run(ctx2, Message{Answer: "start"}); err != nil {
		fmt.Printf("Run 返回错误(被取消): %v\n", err)
	}
	// slow 的 Compute 在 cancel 后被 ctx 打断、提前返回,无需再等
}
