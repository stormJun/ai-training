// checkpoint.go:机制 ⑥ Checkpoint 的全部独立代码——快照结构、存储接口与内存实现。
//
// eino 的 checkpoint 结构(compose/checkpoint.go:107)有 7 个字段:
//
//	Channels / Inputs      -- 在途消息 + 各节点输入     ≈ demo 的 Current(一个 map 全包)
//	State                  -- 跨顶点共享 State          ← demo 无 State,缺(增量 3 补)
//	SkipPreHandler / RerunNodes            ← 服务动态中断(增量 2)
//	SubGraphs                                ← 服务子图
//	InterruptID2Addr / InterruptID2State     ← 服务动态中断寻址
//
// demo 单图、无流式、无 State、无动态中断,所以 checkpoint 极简:两个字段。
// 但核心思想一样:全图运行状态 = 屏障处的在途消息池,快照它 = 快照一切。
//
// 与引擎(Run 循环)的三个集成点仍留在 main.go,保持"机制即三处改动"的可读性:
//
//	① 恢复:循环前 store.Get,命中则跳过 START 播种
//	② 保存:屏障通过后 store.Set(一致性切点)
//	③ 清除:正常终止时 store.Delete
package main

import (
	"context"
	"sync"
)

// Checkpoint 一次屏障后的一致性快照。
type Checkpoint struct {
	Step    int                   // 下一个要执行的 superstep 号(快照存于 Step-1 的屏障)
	Current map[string][]Message  // 在途消息池 = 恢复后第一个超步的输入
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
	return &Checkpoint{Step: cp.Step, Current: cloneCurrent(cp.Current)}, true, nil
}

func (s *memoryStore) Set(_ context.Context, id string, cp *Checkpoint) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	// 存深拷贝:之后 Run 继续改 current,不污染已存的快照
	s.m[id] = &Checkpoint{Step: cp.Step, Current: cloneCurrent(cp.Current)}
	return nil
}

func (s *memoryStore) Delete(_ context.Context, id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.m, id)
	return nil
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
