// Package main: Pregel + 屏障(并行 / 可中断,阶段 02)。
//
// 在 01_pregel_core(串行四机制)基础上引入 taskManager 屏障:
//
//	- Compute 并行(goroutine),步间屏障等齐
//	- panic 恢复:顶点 panic 转 error,不崩程序
//	- ctx 取消/超时:select 监听 ctx.Done(),可中断屏障 + in-flight Compute 被打断
//
// 拓扑仍内联(无 Graph/Compile,无环检测)。声明式拓扑 + Compile 在 03_pregel_compile。
// 对应 eino 的 taskManager(graph_manager.go:269)+ graph_run.go:241 的并行 execute。
//
// 屏障为什么不用裸 sync.WaitGroup:多两件--
//	① 顶点 panic 被 recover 转 error(不崩程序)
//	② context 取消/超时可在屏障处打断等待(select),并 drain 剩余完成信号
package main

import (
	"context"
	"fmt"
	"sort"
	"time"
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
	Compute(ctx context.Context, msgs []Message) Message
}

// ---------------- 引擎:隐式拓扑(同 01,本阶段不引入 Compile)----------------
type Engine struct {
	vertices map[string]Vertex
	edges    map[string][]string
	branches map[string]*Branch
	maxSteps int
}

type Branch struct {
	Cond     func(Message) []string
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

func (e *Engine) route(id string, out Message) []string {
	if b, ok := e.branches[id]; ok {
		return b.Cond(out)
	}
	return e.edges[id]
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
		tm.num++              // Owner 写 num
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
		case <-tm.done: // 收 worker 完成事件,值直接丢弃,只触发分支
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

// ---------------- 运行期:superstep 循环(并行 + 屏障)----------------
// 与 01 串行版的区别:Compute 并行(taskManager.submit),屏障等齐(tm.wait)后才串行路由。
// 并行只发生在 Compute(锁外),路由在屏障后串行做(无需 mutex)--"并行算 + 串行收"。
func (e *Engine) Run(ctx context.Context, initial Message) error {
	current := map[string][]Message{}
	for _, to := range e.edges[START] {
		current[to] = append(current[to], initial)
	}

	for step := 0; step < e.maxSteps; step++ {
		if len(current) == 0 {
			fmt.Println("无在途消息,计算结束")
			return nil
		}

		fmt.Printf("\n── superstep %d ── 活跃顶点: %v\n", step, sortedKeys(current))

		var tasks []*task
		for id, msgs := range current {
			if v, ok := e.vertices[id]; ok {
				tasks = append(tasks, &task{v: v, in: msgs})
			}
		}

		tm := newTaskManager(len(tasks))
		tm.submit(ctx, tasks)
		if !tm.wait(ctx) { // ② 屏障:本步全完成才进下一步(可中断)
			return ctx.Err() // 被取消/超时
		}

		next := map[string][]Message{} // ③ 在途消息池
		for _, t := range tasks {
			if t.err != nil {
				return t.err // 顶点 panic 等
			}
			for _, to := range e.route(t.v.ID(), t.out) {
				if to == END {
					fmt.Printf("  [%s] -> END(终端)\n", t.v.ID())
					continue
				}
				next[to] = append(next[to], t.out)
			}
		}
		current = next // ③ 交换
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
// Demo:mini-ReAct + 主动取消场景
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
		fmt.Println("  [model] 产出 ToolCalls=[search, calc]")
		return Message{ToolCalls: []ToolCall{
			{Name: "search", Arg: "eino pregel"},
			{Name: "calc", Arg: "2+3"},
		}}
	}
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
			if tc.Name == t.name {
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
	// === 场景一:mini-ReAct(model + search + calc),并行版 ===
	e := NewEngine(20)
	model := &ModelVertex{}
	e.AddVertex(model)
	e.AddVertex(&ToolVertex{id: "search", name: "search"})
	e.AddVertex(&ToolVertex{id: "calc", name: "calc"})

	e.AddEdge(START, "model")
	e.AddEdge("search", "model")
	e.AddEdge("calc", "model")
	e.AddBranch("model", &Branch{
		Cond: func(msg Message) []string {
			if len(msg.ToolCalls) > 0 {
				return []string{"search", "calc"}
			}
			return []string{END}
		},
		EndNodes: map[string]bool{"search": true, "calc": true, END: true},
	})

	if err := e.Run(context.Background(), Message{Answer: "user question"}); err != nil {
		fmt.Printf("run error: %v\n", err)
		return
	}
	fmt.Printf("\n最终答案: %s\n", model.Answer)

	// === 场景二:主动取消 ===
	// slow 顶点睡 0.5s 但响应 ctx;用 WithCancel 的 ctx,Run 起来后 100ms 取消。
	// ctx 透传进 Compute:slow 的 select 命中 ctx.Done() 提前返回(in-flight 被打断);
	// 屏障 wait 也命中 ctx.Done(),Run 立即返回 context.Canceled(不等 slow 睡完)。
	fmt.Println("\n=== 场景二:主动取消 ===")
	e2 := NewEngine(5)
	e2.AddVertex(&SlowVertex{})
	e2.AddEdge(START, "slow")
	ctx2, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(100 * time.Millisecond) // 等 Run 进入屏障等待
		fmt.Println("  (主动 cancel())")
		cancel()
	}()
	if err := e2.Run(ctx2, Message{Answer: "start"}); err != nil {
		fmt.Printf("Run 返回错误(被取消): %v\n", err)
	}
	// slow 的 Compute 在 cancel 后被 ctx 打断、提前返回,无需再等
}
