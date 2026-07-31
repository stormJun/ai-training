// Package main: Pregel 引擎 + channel 抽象(增量 6) + ToolsNode 感知(增量 7)。
//
// 在 05(流式)基础上,引入 channel 作为数据流中枢,统一 Invoke + Transform:
//   - channel 接口(5 方法): reportValues / get / convertValues / load / setMergeConfig
//   - edge handler: 数据过边时转换(解耦产出/消费节点)
//   - 可配置 merge: 扇入合并多前驱,按类型注册
//   - Run(Invoke) + StreamRun(Transform) 都通过 channel 走数据
//   - checkpoint: 用 channel.load 恢复,用 channel.convertValues 序列化流
//
// 增量 7: Vertex 接口加 ComponentType(),引擎运行时感知顶点类型。
// 对应 eino component 常量(ComponentOfChatModel/ComponentOfToolsNode/...)。
//
// 三层解耦(唯一耦合是 Message):
//
//	Message  ── 纯数据
//	Vertex   ── Compute(单值,已merge) + StreamCompute(流,已merge) + ComponentType()
//	Engine   ── Run/StreamRun 通过 channel 调度,日志带顶点类型
//
// 不做 DAG(无 reportSkip/reportDependencies)、无 State、无 Interrupt。
package main

import (
	"context"
	"fmt"
	"io"
	"sort"
	"strings"
)

const (
	START = "START"
	END   = "END"
)

// 组件类型常量。对应 eino compose/types.go 的 ComponentOf* 常量。
const (
	ComponentOfChatModel component = "ChatModel"
	ComponentOfToolsNode  component = "ToolsNode"
	ComponentOfTool       component = "Tool"
)

type component string

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
// Compute 和 StreamCompute 都收单个合并后的值(channel.get 已 merge 多前驱)。
// ComponentType 返回顶点的组件类型,引擎运行时感知。对应 eino graphNode.componentType。
type Vertex interface {
	ID() string
	ComponentType() component
	Compute(ctx context.Context, in Message) (Message, error)
	StreamCompute(ctx context.Context, in *StreamReader[Message]) (*StreamReader[Message], error)
}

// ---------------- 构建期:声明式拓扑 ----------------
type Graph struct {
	vertices     map[string]Vertex
	edges        map[string][]string
	branches     map[string]*Branch
	edgeHandlers map[string]map[string]EdgeHandler // from -> to -> handler
	maxSteps     int
}

type Branch struct {
	Cond     func(Message) []string
	EndNodes map[string]bool
}

func NewGraph(maxSteps int) *Graph {
	return &Graph{
		vertices:     map[string]Vertex{},
		edges:        map[string][]string{},
		branches:     map[string]*Branch{},
		edgeHandlers: map[string]map[string]EdgeHandler{},
		maxSteps:     maxSteps,
	}
}

func (g *Graph) AddVertex(v Vertex)               { g.vertices[v.ID()] = v }
func (g *Graph) AddEdge(from, to string)          { g.edges[from] = append(g.edges[from], to) }
func (g *Graph) AddBranch(from string, b *Branch) { g.branches[from] = b }

// AddToolsNode 加 ToolsNode 顶点。语法糖:校验 ComponentType 后调 AddVertex。
// 对应 eino graph.AddToolsNode(key, toolsNode)(graph.go:399)。
func (g *Graph) AddToolsNode(v Vertex) error {
	if v.ComponentType() != ComponentOfToolsNode {
		return fmt.Errorf("AddToolsNode: vertex %q has ComponentType %q, want %q",
			v.ID(), v.ComponentType(), ComponentOfToolsNode)
	}
	g.AddVertex(v)
	return nil
}

// AddEdgeWithHandler 加一条带转换 handler 的边。对应 eino AddEdge + MapFields。
func (g *Graph) AddEdgeWithHandler(from, to string, eh EdgeHandler) {
	g.AddEdge(from, to)
	if g.edgeHandlers[from] == nil {
		g.edgeHandlers[from] = map[string]EdgeHandler{}
	}
	g.edgeHandlers[from][to] = eh
}

// ---------------- Compile ----------------
type Compiled struct {
	vertices     map[string]Vertex
	edges        map[string][]string
	branches     map[string]*Branch
	edgeHandlers *edgeHandlerManager
	maxSteps     int
	store        CheckPointStore
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

	ehm := newEdgeHandlerManager()
	for from, tos := range g.edgeHandlers {
		for to, eh := range tos {
			ehm.add(from, to, eh)
		}
	}

	c := &Compiled{
		vertices:     g.vertices,
		edges:        g.edges,
		branches:     g.branches,
		edgeHandlers: ehm,
		maxSteps:     g.maxSteps,
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

// ---------------- merge + concat ----------------

// mergeMessages Message 的 merge 函数:拼接 ToolCalls/Results,Answer 取最后非空。
// 通过 init 注册到全局表,channel.get 多前驱时自动用。
func mergeMessages(items []Message) (Message, error) {
	var out Message
	for _, m := range items {
		out.ToolCalls = append(out.ToolCalls, m.ToolCalls...)
		out.Results = append(out.Results, m.Results...)
		if m.Answer != "" {
			out.Answer = m.Answer // useLast
		}
	}
	return out, nil
}

func concatMsg(sr *StreamReader[Message]) (Message, error) {
	return concatStreamReader(sr, mergeMessages)
}

func init() {
	RegisterMergeFunc(mergeMessages) // 注册 Message 的 merge
}

// ---------------- 屏障(Invoke 用)----------------
type task struct {
	v   Vertex
	in  Message
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

// ============================================================
// Run(Invoke 模式)+ checkpoint
// ============================================================
// current/next 是 channelManager。每个 channel 收前驱值,get 时 merge + 边转换。
// 顶点走 Compute,收单个合并后的 Message。

func (c *Compiled) Run(ctx context.Context, initial Message, checkPointID string) error {
	if checkPointID != "" && c.store == nil {
		return fmt.Errorf("receive checkpoint id %q but have not set checkpoint store", checkPointID)
	}
	useCP := checkPointID != ""

	current := newChannelManager()
	startStep := 0
	resumed := false

	if useCP {
		cp, ok, err := c.store.Get(ctx, checkPointID)
		if err != nil {
			return fmt.Errorf("load checkpoint fail: %w", err)
		}
		if ok {
			restoreChannels(current, cp.Channels) // channel.load
			startStep, resumed = cp.Step, true
			fmt.Printf("[checkpoint] 命中:从 superstep %d 续跑\n", startStep)
		}
	}
	if !resumed {
		for _, to := range c.edges[START] {
			current.report(to, START, initial)
		}
	}

	for step := startStep; step < c.maxSteps; step++ {
		if len(current.channels) == 0 {
			fmt.Println("无在途消息,计算结束")
			if useCP {
				_ = c.store.Delete(ctx, checkPointID)
				fmt.Println("[checkpoint] 正常结束,断点已清除")
			}
			return nil
		}

		fmt.Printf("\n── superstep %d ── 活跃: %v\n", step, sortedChanLabels(current, c.vertices))

		var tasks []*task
		for id, ch := range current.channels {
			val, ok, err := ch.get(false, id, c.edgeHandlers) // isStream=false
			if err != nil {
				return fmt.Errorf("channel get[%s] fail: %w", id, err)
			}
			if !ok {
				continue
			}
			msg, _ := val.(Message)
			tasks = append(tasks, &task{v: c.vertices[id], in: msg})
		}

		tm := newTaskManager(len(tasks))
		tm.submit(ctx, tasks)
		if !tm.wait(ctx) {
			return ctx.Err()
		}

		next := newChannelManager()
		for _, t := range tasks {
			if t.err != nil {
				if useCP {
					fmt.Printf("[checkpoint] superstep %d 失败,断点保留\n", step)
				}
				return t.err
			}
			for _, to := range c.route(t.v.ID(), t.out) {
				if to == END {
					fmt.Printf("  [%s] -> END\n", t.v.ID())
					continue
				}
				next.report(to, t.v.ID(), t.out)
			}
		}

		if useCP && len(next.channels) > 0 {
			snap, err := snapshotChannels(next)
			if err != nil {
				return fmt.Errorf("snapshot fail: %w", err)
			}
			if err := c.store.Set(ctx, checkPointID, &Checkpoint{Step: step + 1, Channels: snap}); err != nil {
				return fmt.Errorf("save checkpoint fail: %w", err)
			}
			fmt.Printf("  [checkpoint] 屏障通过,已存快照(下次从 superstep %d 续跑)\n", step+1)
		}
		current = next
	}

	fmt.Println("达到 maxSteps 上限")
	return nil
}

// ============================================================
// StreamRun(Transform 模式)
// ============================================================
// current/next 是 channelManager,Values 是 *StreamReader。
// 顶点走 StreamCompute,收单个合并后的流。分支点 peek 首块决定路由。
//
// 不做 per-barrier checkpoint:流式 checkpoint 需 concat 流(消费它),
// 破坏下一步的流。eino 只在 interrupt 时做(06 无 interrupt)。
// channel.convertValues 的机制由 demoConvertValues 单独演示。

func (c *Compiled) StreamRun(ctx context.Context, initial Message) (*StreamReader[Message], error) {
	current := newChannelManager()
	for _, to := range c.edges[START] {
		current.report(to, START, wrap(initial))
	}

	type streamTask struct {
		v   Vertex
		out *StreamReader[Message]
	}

	for step := 0; step < c.maxSteps; step++ {
		if len(current.channels) == 0 {
			return nil, fmt.Errorf("stream run: no active vertex at step %d", step)
		}

		fmt.Printf("\n── stream superstep %d ── 活跃: %v\n", step, sortedChanLabels(current, c.vertices))

		var tasks []streamTask
		for id, ch := range current.channels {
			val, ok, err := ch.get(true, id, c.edgeHandlers) // isStream=true
			if err != nil {
				return nil, fmt.Errorf("channel get[%s] fail: %w", id, err)
			}
			if !ok {
				continue
			}
			sr, _ := val.(*StreamReader[Message])
			out, err := c.vertices[id].StreamCompute(ctx, sr)
			if err != nil {
				return nil, fmt.Errorf("stream compute[%s] fail: %w", id, err)
			}
			tasks = append(tasks, streamTask{v: c.vertices[id], out: out})
		}

		next := newChannelManager()
		var endStream *StreamReader[Message]
		for _, t := range tasks {
			if _, hasBranch := c.branches[t.v.ID()]; hasBranch {
				copies := t.out.Copy(2)
				firstChunk, err := copies[0].Recv()
				if err != nil && err != io.EOF {
					return nil, fmt.Errorf("stream peek[%s] fail: %w", t.v.ID(), err)
				}
				targets := c.route(t.v.ID(), firstChunk)
				if len(targets) == 1 && targets[0] == END {
					endStream = copies[1]
				} else {
					routeStream(copies[1], t.v.ID(), targets, next)
				}
			} else {
				routeStream(t.out, t.v.ID(), c.edges[t.v.ID()], next)
			}
		}

		if endStream != nil {
			fmt.Printf("  [stream] 路由到 END,返回流给调用方\n")
			return endStream, nil
		}
		current = next
	}

	return nil, fmt.Errorf("stream run: maxSteps exceeded")
}

// routeStream 把流路由到多个目标(多目标 Copy 扇出)。
func routeStream(src *StreamReader[Message], from string, targets []string, next *channelManager) {
	if len(targets) == 0 {
		return
	}
	if len(targets) == 1 {
		next.report(targets[0], from, src)
		return
	}
	copies := src.Copy(len(targets))
	for i, to := range targets {
		next.report(to, from, copies[i])
	}
}

// sortedChanLabels 返回 "id/ComponentType" 格式的活跃顶点标签。
// 如 [tools/ToolsNode]、[model/ChatModel]。对应 eino 运行时日志。
func sortedChanLabels(cm *channelManager, vertices map[string]Vertex) []string {
	ks := make([]string, 0, len(cm.channels))
	for k := range cm.channels {
		if v, ok := vertices[k]; ok {
			ks = append(ks, fmt.Sprintf("%s/%s", k, v.ComponentType()))
		} else {
			ks = append(ks, k)
		}
	}
	sort.Strings(ks)
	return ks
}
