// checkpoint.go:机制 ⑥ Checkpoint 的全部独立代码——快照结构、存储接口与内存实现。
//
// eino 的 checkpoint 结构(compose/checkpoint.go:107)有 7 个字段:
//
//	Channels / Inputs      -- 在途消息 + 各节点输入     ≈ demo 的 Current(一个 map 全包)
//	State                  -- 跨顶点共享 State          ← 增量 3 新增
//	SkipPreHandler / RerunNodes            ← 服务动态中断(增量 2)
//	SubGraphs                                ← 服务子图
//	InterruptID2Addr / InterruptID2State     ← 服务动态中断寻址
//
// demo 单图、无流式,checkpoint 极简。
// 增量 2 新增 InterruptInfo 和 RerunNodes 字段,支持主动中断与恢复。
// 增量 3 新增 State 字段,支持图级共享状态的快照与恢复。
//
// 与引擎(Run 循环)的集成点仍留在 main.go:
//
//	① 恢复:循环前 store.Get,命中则跳过 START 播种
//	② 保存:屏障通过后 store.Set(一致性切点) 或 中断时保存
//	③ 清除:正常终止时 store.Delete
//	④ 中断:顶点返回 InterruptError,Run 保存 checkpoint 并返回
//	⑤ 恢复中断:Resume() 从断点恢复,注入数据继续执行
package main

import (
	"context"
	"fmt"
	"sync"
)

// Checkpoint 一次屏障后的一致性快照。
// 增量 2 新增 InterruptInfo 和 RerunNodes,支持主动中断与恢复。
// 增量 3 新增 State,支持图级共享状态的快照与恢复。
type Checkpoint struct {
	Step          int                   // 下一个要执行的 superstep 号
	Current       map[string][]Message  // 在途消息池
	State         *GraphState           // 图级共享状态快照(增量 3)
	InterruptInfo *InterruptInfo        // 中断信息(增量 2)
	RerunNodes    []string              // 需要重跑的节点(增量 2)
}

// InterruptInfo 中断信息,由顶点在中断时提供。
type InterruptInfo struct {
	NodeID  string // 哪个节点请求中断
	Message string // 中断原因
	Data    any    // 携带数据(如 tool call 详情),Resume 时可注入
}

// InterruptError 中断错误。顶点返回此错误触发中断。
type InterruptError struct {
	Info *InterruptInfo
}

func (e *InterruptError) Error() string {
	return fmt.Sprintf("interrupt at node %s: %s", e.Info.NodeID, e.Info.Message)
}

// Interrupt 顶点调用此函数返回中断错误。
// 用法: if needApproval { return Message{}, Interrupt("node", "reason", data) }
func Interrupt(nodeID string, message string, data any) error {
	return &InterruptError{
		Info: &InterruptInfo{
			NodeID:  nodeID,
			Message: message,
			Data:    data,
		},
	}
}

// CheckPointStore 断点存储。对应 eino core.CheckPointStore(仅 Get/Set)。
// demo 多一个 Delete:demo 逐超步写入,正常跑完须主动清;
// eino 只在 interrupt 时写(graph_run.go:561/701),断点随 resume 消耗,无需 Delete。
type CheckPointStore interface {
	Get(ctx context.Context, id string) (*Checkpoint, bool, error)
	Set(ctx context.Context, id string, cp *Checkpoint) error
	Delete(ctx context.Context, id string) error
}

// WithCheckPointStore 给 Compiled 装配断点存储。对应 eino WithCheckPointStore(checkpoint.go:60)。
func WithCheckPointStore(store CheckPointStore) CompileOption {
	return func(c *Compiled) { c.store = store }
}

// memoryStore 内存版实现。生产换持久化(Redis/DB)+ 序列化——
// 那是 eino Serializer / schema.RegisterName 要解决的问题,见文档「语义边界与注意事项」。
type memoryStore struct {
	mu sync.Mutex
	m  map[string]*Checkpoint
}

func newMemoryStore() *memoryStore { return &memoryStore{m: map[string]*Checkpoint{}} }

func (s *memoryStore) Get(_ context.Context, id string) (*Checkpoint, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cp, ok := s.m[id]
	if !ok {
		return nil, false, nil
	}
	// 返回深拷贝:调用方拿到的快照与店里存的互不影响
	return cloneCheckpoint(cp), true, nil
}

func (s *memoryStore) Set(_ context.Context, id string, cp *Checkpoint) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	// 存深拷贝:之后 Run 继续改 current,不污染已存的快照
	s.m[id] = cloneCheckpoint(cp)
	return nil
}

func (s *memoryStore) Delete(_ context.Context, id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.m, id)
	return nil
}

// cloneCheckpoint 深拷贝整个 Checkpoint(包括 State)。
func cloneCheckpoint(src *Checkpoint) *Checkpoint {
	cp := &Checkpoint{
		Step:    src.Step,
		Current: cloneCurrent(src.Current),
	}
	// 增量 3:深拷贝 State
	if src.State != nil {
		s := *src.State // 值拷贝 GraphState(int 字段自动深拷贝)
		cp.State = &s
	}
	if src.InterruptInfo != nil {
		info := *src.InterruptInfo
		cp.InterruptInfo = &info
	}
	if src.RerunNodes != nil {
		cp.RerunNodes = append([]string(nil), src.RerunNodes...)
	}
	return cp
}

// cloneCurrent 深拷贝在途消息池(map -> slice -> Message 内的 slice)。
// 快照必须具备值语义:不拷的话,存进 store 的"快照"会被后续执行原地修改,断点失去意义。
func cloneCurrent(src map[string][]Message) map[string][]Message {
	dst := make(map[string][]Message, len(src))
	for id, msgs := range src {
		cp := make([]Message, len(msgs))
		for i, m := range msgs {
			m.ToolCalls = append([]ToolCall(nil), m.ToolCalls...)
			m.Results = append([]string(nil), m.Results...)
			cp[i] = m
		}
		dst[id] = cp
	}
	return dst
}
