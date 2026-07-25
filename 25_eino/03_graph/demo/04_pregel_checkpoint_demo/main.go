// Package main: Pregel 最小可运行 MVP + Checkpoint(增量 1:每超步快照 + 断点续跑)
//   + Interrupt/Resume(增量 2:主动中断 + 恢复)
//   + State(增量 3:图级共享状态)。
//
// 三层解耦(唯一耦合是 Message):
//
//	Message  ── 纯数据,无行为(不带 To,路由由声明决定)
//	Vertex   ── 纯行为(Compute),无调度、不路由
//	Engine   ── 纯调度 + 编译,无业务行为
//
// 七机制落点:
//
//	① 顶点为中心  -- Vertex 只写 Compute
//	② 超步 + 屏障 -- for step + taskManager(done 通道 + 计数 + select)
//	③ 消息 S->S+1 -- current/next 邮箱,屏障处交换
//	④ 触发与终止  -- 有消息才激活;邮箱空即止
//	⑤ Compile    -- 声明式拓扑 -> 后继表 + 校验 + 环检测(graph.go:674)
//	⑥ Checkpoint -- 屏障后快照 current + 断点续跑(独立文件 checkpoint.go)
//	⑦ State      -- 图级共享可变状态,ProcessState 读写,mutex 保护,checkpoint 保存/恢复
package main

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"
)

const (
	START = "START"
	END   = "END"
)

// ---------------- 消息(纯数据)----------------
type Message struct {
	ToolCalls []ToolCall
	Results   []string
	Answer    string
}

type ToolCall struct {
	Name string
	Arg  string
}

// ---------------- 顶点(纯行为)----------------
type Vertex interface {
	ID() string
	Compute(ctx context.Context, msgs []Message) (Message, error)
}

// ---------------- 构建期:声明式拓扑 ----------------
type Graph struct {
	vertices map[string]Vertex
	edges    map[string][]string
	branches map[string]*Branch
	maxSteps int
}

type Branch struct {
	Cond     func(Message) []string
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

// ---------------- ⑦ State:图级共享可变状态 ----------------
// 对应 eino compose/state.go: WithGenLocalState[S] + ProcessState[S]。
// 核心机制:所有顶点通过 ProcessState 读写同一个 struct 实例,
// mutex 保护并发安全,checkpoint 保存/恢复。
// demo 用具体类型 *GraphState(TokenCounter),不用泛型(最少代码原则)。

// GraphState 图级共享状态。demo 用 TokenCounter 展示机制,
// eino ADK 用 State.Messages 做消息累积——那是应用层选择,不是机制本身。
type GraphState struct {
	mu         sync.Mutex
	TokenCount int
}

// stateKey 用于 context.WithValue 的 key 类型(对应 eino stateKey struct{})
type stateKey struct{}

// ProcessState 并发安全地访问 GraphState。
// 对应 eino compose.ProcessState[S](ctx, handler)。
// 从 ctx 取出 State 指针,加锁,调用户 handler,解锁。
// 所有顶点拿到同一个 *GraphState 指针——这就是"共享"的来源。
// 如果图未声明 State(genState==nil),静默跳过——顶点无需关心 State 是否存在。
func ProcessState(ctx context.Context, fn func(*GraphState)) {
	s, ok := ctx.Value(stateKey{}).(*GraphState)
	if !ok || s == nil {
		return // 图未声明 State,静默跳过
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	fn(s)
}

// GenLocalState 工厂函数类型:每次 Run 调用,产出全新 GraphState 实例。
// 对应 eino GenLocalState[S any] func(ctx context.Context) (state S)。
// 用工厂函数而非直接传实例:同一 Compiled 多次 Run 时,每次需要全新 State,防污染。
type GenLocalState func() *GraphState

// WithGenLocalState 编译期选项:注册"造 State 的工厂函数"。
// 对应 eino compose.WithGenLocalState。
func WithGenLocalState(gen GenLocalState) CompileOption {
	return func(c *Compiled) { c.genState = gen }
}

// ---------------- Compile:声明式拓扑 -> 运行期结构 ----------------
type Compiled struct {
	vertices map[string]Vertex
	edges    map[string][]string
	branches map[string]*Branch
	maxSteps int
	store    CheckPointStore // ⑥ 可选:装了才支持 checkpoint
	genState GenLocalState   // ⑦ 可选:装了才支持 State
}

type CompileOption func(*Compiled)

func (g *Graph) Compile(opts ...CompileOption) (*Compiled, error) {
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

	succ := g.successors()
	if loops := findLoops(succ); len(loops) > 0 {
		fmt.Printf("[compile] 检测到环: %s(Pregel 允许,继续编译)\n", formatLoops(loops))
	} else {
		fmt.Println("[compile] 无环")
	}

	c := &Compiled{
		vertices: g.vertices,
		edges:    g.edges,
		branches: g.branches,
		maxSteps: g.maxSteps,
	}
	for _, opt := range opts {
		opt(c)
	}
	return c, nil
}

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

func findLoops(succ map[string][]string) [][]string {
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
				indeg[n] = -1
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
			dfs(append(append([]string{}, path...), next))
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

func formatLoops(loops [][]string) string {
	parts := make([]string, 0, len(loops))
	for _, l := range loops {
		parts = append(parts, "["+strings.Join(l, "->")+"]")
	}
	return strings.Join(parts, "")
}

func (c *Compiled) route(id string, out Message) []string {
	if b, ok := c.branches[id]; ok {
		return b.Cond(out)
	}
	return c.edges[id]
}

// ---------------- 屏障 ----------------
type task struct {
	v   Vertex
	in  []Message
	out Message
	err error
}

type taskManager struct {
	done chan *task
	num  int
}

func newTaskManager(n int) *taskManager {
	return &taskManager{done: make(chan *task, n)}
}

func (tm *taskManager) submit(ctx context.Context, tasks []*task) {
	for _, t := range tasks {
		tm.num++
		go tm.execute(ctx, t)
	}
}

func (tm *taskManager) execute(ctx context.Context, t *task) {
	defer func() {
		if r := recover(); r != nil {
			t.err = fmt.Errorf("vertex[%s] panic: %v", t.v.ID(), r)
		}
		tm.done <- t
	}()
	t.out, t.err = t.v.Compute(ctx, t.in)
}

func (tm *taskManager) wait(ctx context.Context) bool {
	for tm.num > 0 {
		select {
		case <-tm.done:
			tm.num--
		case <-ctx.Done():
			for tm.num > 0 {
				<-tm.done
				tm.num--
			}
			return false
		}
	}
	return true
}

// ---------------- 运行期:superstep 循环 ----------------
func (c *Compiled) Run(ctx context.Context, initial Message, checkPointID string) error {
	if checkPointID != "" && c.store == nil {
		return fmt.Errorf("receive checkpoint id %q but have not set checkpoint store", checkPointID)
	}
	useCP := checkPointID != ""

	// ⑦ State 初始化:调用工厂函数造实例,放进 ctx
	// 对应 eino graph_run.go:411-418: context.WithValue(ctx, stateKey{}, &internalState{...})
	var state *GraphState
	if c.genState != nil {
		state = c.genState() // 每次 Run 造全新实例,防污染
		ctx = context.WithValue(ctx, stateKey{}, state)
	}

	current := map[string][]Message{}
	startStep := 0
	resumed := false

	// ⑥ 恢复
	if useCP {
		cp, ok, err := c.store.Get(ctx, checkPointID)
		if err != nil {
			return fmt.Errorf("load checkpoint fail: %w", err)
		}
		if ok {
			current, startStep, resumed = cp.Current, cp.Step, true
			// ⑦ 恢复 State:从 checkpoint 写回
			if cp.State != nil && state != nil {
				state.TokenCount = cp.State.TokenCount
			}
			fmt.Printf("[checkpoint] 命中断点:从 superstep %d 续跑,在途消息 %v(START 播种被跳过)\n",
				startStep, sortedKeys(current))
		}
	}
	if !resumed {
		for _, to := range c.edges[START] {
			current[to] = append(current[to], initial)
		}
	}

	for step := startStep; step < c.maxSteps; step++ {
		if len(current) == 0 {
			fmt.Println("无在途消息,计算结束")
			if useCP {
				_ = c.store.Delete(ctx, checkPointID)
				fmt.Println("[checkpoint] 正常结束,断点已清除")
			}
			// ⑦ Run 结束,打印 State
			if state != nil {
				fmt.Printf("[state] TokenCount = %d\n", state.TokenCount)
			}
			return nil
		}

		fmt.Printf("\n── superstep %d ── 活跃顶点: %v\n", step, sortedKeys(current))

		var tasks []*task
		for id, msgs := range current {
			if v, ok := c.vertices[id]; ok {
				tasks = append(tasks, &task{v: v, in: msgs})
			}
		}

		tm := newTaskManager(len(tasks))
		tm.submit(ctx, tasks)
		if !tm.wait(ctx) {
			return ctx.Err()
		}

		next := map[string][]Message{}
		for _, t := range tasks {
			if t.err != nil {
				var intErr *InterruptError
				if errors.As(t.err, &intErr) {
					if useCP {
						cp := &Checkpoint{
							Step:          step + 1,
							Current:       current,
							State:         cloneState(state), // ⑦ 中断时保存 State
							InterruptInfo: intErr.Info,
							RerunNodes:    []string{t.v.ID()},
						}
						if err := c.store.Set(ctx, checkPointID, cp); err != nil {
							return fmt.Errorf("save interrupt checkpoint fail: %w", err)
						}
						fmt.Printf("  [interrupt] 节点 %s 请求中断: %s\n", t.v.ID(), intErr.Info.Message)
						fmt.Printf("  [checkpoint] 已保存中断断点(Resume 可继续)\n")
					}
					return intErr
				}
				if useCP {
					fmt.Printf("[checkpoint] superstep %d 失败,断点保留在上一屏障(同 ID 重跑将重跑本超步)\n", step)
				}
				return t.err
			}
			for _, to := range c.route(t.v.ID(), t.out) {
				if to == END {
					fmt.Printf("  [%s] -> END(终端)\n", t.v.ID())
					continue
				}
				next[to] = append(next[to], t.out)
			}
		}
		current = next

		// ⑥ 保存
		if useCP && len(current) > 0 {
			if err := c.store.Set(ctx, checkPointID, &Checkpoint{
				Step:    step + 1,
				Current: current,
				State:   cloneState(state), // ⑦ 屏障后保存 State
			}); err != nil {
				return fmt.Errorf("save checkpoint fail: %w", err)
			}
			fmt.Printf("  [checkpoint] 屏障通过,已存快照(下次从 superstep %d 续跑,在途 %v)\n",
				step+1, sortedKeys(current))
		}
	}

	fmt.Println("达到 maxSteps 上限,强制停止(断点保留,可续跑)")
	return nil
}

// cloneState 深拷贝 GraphState 进 checkpoint。
// 对应 eino graph_run.go:518-526: state.mu.Lock(); copiedState = deepCopyState(state.state); state.mu.Unlock()
func cloneState(s *GraphState) *GraphState {
	if s == nil {
		return nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return &GraphState{TokenCount: s.TokenCount} // 只拷数据字段;新 struct 自带零值 mutex(合法、未锁定),避免拷贝锁值
}

func sortedKeys(m map[string][]Message) []string {
	ks := make([]string, 0, len(m))
	for k := range m {
		ks = append(ks, k)
	}
	sort.Strings(ks)
	return ks
}
