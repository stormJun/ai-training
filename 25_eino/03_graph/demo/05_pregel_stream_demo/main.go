// Package main: Pregel 流式执行 demo(增量 4:Streaming)。
//
// 本 demo 专注验证流式执行(Transform 范式):
//   - StreamRun:流 handle 跨 superstep 传递
//   - Copy(扇出,lazy)+ Merge(扇入)
//   - wrap/concat:单值与流的桥
//
// Invoke 范式(Run/Compute)、Checkpoint、State 见上游 04_pregel_checkpoint_demo。
//
// 三层解耦(唯一耦合是 Message):
//
//	Message  ── 纯数据,无行为(不带 To,路由由声明决定)
//	Vertex   ── 纯行为(StreamCompute),收流产流
//	Engine   ── 纯调度 + 编译,无业务行为
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

// ---------------- 顶点(纯行为:流式)----------------
// Vertex 只实现 StreamCompute(Transform 范式:收流 -> 产流),对应 eino 的 Transform。
// Invoke 范式(Compute)见 04_pregel_checkpoint_demo。
type Vertex interface {
	ID() string
	StreamCompute(ctx context.Context, input *StreamReader[Message]) (*StreamReader[Message], error)
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

// ---------------- Compile:声明式拓扑 -> 运行期结构 ----------------
type Compiled struct {
	vertices map[string]Vertex
	edges    map[string][]string
	branches map[string]*Branch
	maxSteps int
}

func (g *Graph) Compile() (*Compiled, error) {
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

	return &Compiled{
		vertices: g.vertices,
		edges:    g.edges,
		branches: g.branches,
		maxSteps: g.maxSteps,
	}, nil
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

// ============================================================
// StreamRun:流式执行(Transform 模式)
// ============================================================
// 对应 eino runner.transform(isStream=true):流式入 -> 流式出。
//
// 核心机制:
//   - current/next 存流 handle(*StreamReader[Message]),不是单值
//   - 顶点走 StreamCompute(收流产流)
//   - 扇出用 Copy,扇入用 MergeStreamReaders
//   - 分支点:Copy 一份 concat 决定路由,另一份传给目标
//   - 流 handle 跨 superstep 屏障传递:屏障同步"任务返回 handle",不是"流消费完"
//   - 数据真正流动发生在下游 Recv() 时,是 lazy 的

// mergeMessages 把多个 Message 合并成一个(用于 concat)。
// ToolCalls/Results 拼接,Answer 取最后一个非空(eino string 拼接 / useLast 语义)。
func mergeMessages(items []Message) Message {
	var out Message
	for _, m := range items {
		out.ToolCalls = append(out.ToolCalls, m.ToolCalls...)
		out.Results = append(out.Results, m.Results...)
		if m.Answer != "" {
			out.Answer = m.Answer // useLast:最后一个非空覆盖
		}
	}
	return out
}

// concatMsg 流 -> 单值 Message 的便捷封装。
func concatMsg(sr *StreamReader[Message]) (Message, error) {
	return concatStreamReader(sr, mergeMessages)
}

// StreamRun 流式执行图,返回最终输出流。
func (c *Compiled) StreamRun(ctx context.Context, initial Message) (*StreamReader[Message], error) {
	// current:顶点ID -> 该顶点收到的多个前驱流(扇入)
	current := map[string][]*StreamReader[Message]{}

	// START 播种:把 initial 单值 wrap 成流,投递给 START 的后继
	startSucc := c.edges[START]
	if len(startSucc) == 1 {
		current[startSucc[0]] = []*StreamReader[Message]{wrap(initial)}
	} else if len(startSucc) > 1 {
		// 多后继:Copy 扇出
		copies := wrap(initial).Copy(len(startSucc))
		for i, to := range startSucc {
			current[to] = []*StreamReader[Message]{copies[i]}
		}
	}

	for step := 0; step < c.maxSteps; step++ {
		if len(current) == 0 {
			return nil, fmt.Errorf("stream run: no active vertex at step %d", step)
		}

		fmt.Printf("\n── stream superstep %d ── 活跃顶点: %v\n", step, sortedStreamKeys(current))

		// 执行:每个活跃顶点调 StreamCompute(收流产流)
		// 扇入:多个前驱流先 Merge 成一个
		type streamTask struct {
			v   Vertex
			out *StreamReader[Message]
		}
		var tasks []*streamTask
		for id, streams := range current {
			v := c.vertices[id]
			// 扇入:多流 Merge,单流直用
			var input *StreamReader[Message]
			if len(streams) == 1 {
				input = streams[0]
			} else {
				input = MergeStreamReaders(streams)
			}
			out, err := v.StreamCompute(ctx, input)
			if err != nil {
				return nil, fmt.Errorf("stream compute[%s] fail: %w", id, err)
			}
			tasks = append(tasks, &streamTask{v: v, out: out})
		}

		// 路由:屏障后串行处理(屏障=所有 StreamCompute 已返回 handle)
		next := map[string][]*StreamReader[Message]{}
		var endStream *StreamReader[Message]
		for _, t := range tasks {
			if _, hasBranch := c.branches[t.v.ID()]; hasBranch {
				// 分支点:Copy 一份,只读首个 chunk 决定路由(不 concat 整流,保持 lazy)。
				// model step1 首块带 ToolCalls -> 去工具;step2 首块是 Answer 无 ToolCalls -> 去 END。
				// 首块被 lazy Copy 缓存,copies[1] 仍能读到完整流(实时)。
				copies := t.out.Copy(2)
				firstChunk, err := copies[0].Recv()
				if err != nil && err != io.EOF {
					return nil, fmt.Errorf("stream peek[%s] fail: %w", t.v.ID(), err)
				}
				targets := c.route(t.v.ID(), firstChunk)
				if len(targets) == 1 && targets[0] == END {
					endStream = copies[1] // 原流(含首块,实时)返回给调用方
				} else {
					routeStreamTo(copies[1], targets, next)
				}
			} else {
				// 无分支:无条件边,直接路由(多后继则 Copy)
				routeStreamTo(t.out, c.edges[t.v.ID()], next)
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

// routeStreamTo 把一个流路由到多个目标(多目标时 Copy 扇出)。
func routeStreamTo(src *StreamReader[Message], targets []string, next map[string][]*StreamReader[Message]) {
	if len(targets) == 0 {
		return
	}
	if len(targets) == 1 {
		next[targets[0]] = append(next[targets[0]], src)
		return
	}
	copies := src.Copy(len(targets))
	for i, to := range targets {
		next[to] = append(next[to], copies[i])
	}
}

func sortedStreamKeys(m map[string][]*StreamReader[Message]) []string {
	ks := make([]string, 0, len(m))
	for k := range m {
		ks = append(ks, k)
	}
	sort.Strings(ks)
	return ks
}
