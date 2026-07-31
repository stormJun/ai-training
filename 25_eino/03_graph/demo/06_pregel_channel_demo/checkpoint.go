// checkpoint.go:checkpoint 机制(从 04 恢复,改用 channel)。
//
// 对应 eino compose/checkpoint.go。区别:04 存 map[string][]Message,
// 06 存 map[string]*pregelChannel -- 快照的是 channel 状态。
//
// channel 接口的两个方法在此被调用:
//   - load:          恢复时把快照的 channel 状态装回运行期 channel
//   - convertValues: 流式 checkpoint 序列化时,把流 concat 成单值(流不能直接存)
//
// Run(Invoke)和 StreamRun(Transform)都接 checkpoint:
//   - Run:       Values 是 Message,直接克隆存/装回
//   - StreamRun: Values 是 *StreamReader,存前 convertValues concat 成 Message,
//                恢复后 wrap 回单元素流
package main

import (
	"context"
	"fmt"
	"sync"
)

// Checkpoint 一次屏障后的一致性快照。
type Checkpoint struct {
	Step     int                       // 下一个要执行的 superstep
	Channels map[string]*pregelChannel // 各节点的 channel 快照
}

// CheckPointStore 断点存储。对应 eino core.CheckPointStore(仅 Get/Set)+ Delete。
type CheckPointStore interface {
	Get(ctx context.Context, id string) (*Checkpoint, bool, error)
	Set(ctx context.Context, id string, cp *Checkpoint) error
	Delete(ctx context.Context, id string) error
}

// WithCheckPointStore 编译期装配 store。对应 eino WithCheckPointStore。
func WithCheckPointStore(store CheckPointStore) CompileOption {
	return func(c *Compiled) { c.store = store }
}

// memoryStore 内存实现(深拷贝保证快照值语义)。
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
	return cloneCheckpoint(cp), true, nil
}

func (s *memoryStore) Set(_ context.Context, id string, cp *Checkpoint) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.m[id] = cloneCheckpoint(cp)
	return nil
}

func (s *memoryStore) Delete(_ context.Context, id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.m, id)
	return nil
}

// cloneCheckpoint 深拷贝整个 Checkpoint(含 channels)。
// 调用前 StreamRun 应已 convertValues 把流转单值,这里 Values 都是可拷贝的。
func cloneCheckpoint(src *Checkpoint) *Checkpoint {
	cp := &Checkpoint{Step: src.Step, Channels: map[string]*pregelChannel{}}
	for k, ch := range src.Channels {
		cp.Channels[k] = clonePregelChannel(ch)
	}
	return cp
}

// clonePregelChannel 深拷贝 channel 的 Values。
// Message 是值类型直接拷;ToolCall/Results slice 单独拷。
func clonePregelChannel(src *pregelChannel) *pregelChannel {
	dst := newPregelChannel()
	for from, v := range src.Values {
		switch val := v.(type) {
		case Message:
			m := val
			m.ToolCalls = append([]ToolCall(nil), m.ToolCalls...)
			m.Results = append([]string(nil), m.Results...)
			dst.Values[from] = m
		default:
			dst.Values[from] = v // 流不应出现在这里(应先 convertValues)
		}
	}
	return dst
}

// snapshotChannels 把运行期 channelManager 的 channels 拷成快照(Invoke 用,Values 是 Message)。
func snapshotChannels(cm *channelManager) (map[string]*pregelChannel, error) {
	out := map[string]*pregelChannel{}
	for id, ch := range cm.channels {
		pc := ch.(*pregelChannel)
		out[id] = clonePregelChannel(pc)
	}
	return out, nil
}

// concatStreamValues 用 convertValues 把 channel 里的流值 concat 成 Message。
// 对应 eino streamConvertPair.concatStream。由 demoConvertValues 演示。
func concatStreamValues(ch *pregelChannel) error {
	return ch.convertValues(func(values map[string]any) error {
		for k, v := range values {
			if sr, ok := v.(*StreamReader[Message]); ok {
				msg, err := concatMsg(sr)
				if err != nil {
					return err
				}
				values[k] = msg
			}
		}
		return nil
	})
}

// restoreChannels 从快照恢复运行期 channelManager(Invoke 用,channel.load)。
func restoreChannels(cm *channelManager, snap map[string]*pregelChannel) {
	for id, pc := range snap {
		ch := newPregelChannel()
		ch.load(pc) // ★ 调 channel.load
		cm.channels[id] = ch
	}
}

// demoConvertValues 演示 channel.convertValues 机制(对应 eino stream checkpoint 序列化)。
// 造一个装流的 channel,用 convertValues 把流 concat 成单值,展示"批量转换 channel 值"。
//
// 为什么单独 demo:StreamRun 不做 per-barrier checkpoint(会消费流破坏执行),
// 但 convertValues 是真机制(eino 在 interrupt 时用它序列化流),这里直接演示它工作。
func demoConvertValues() error {
	fmt.Println("=== 场景5:channel.convertValues 演示 ===")
	ch := newPregelChannel()
	// 造一个流:发 3 个 chunk
	sr, w := Pipe[Message]()
	go func() {
		defer w.Close()
		w.Send(Message{Results: []string{"a"}}, nil)
		w.Send(Message{Results: []string{"b"}}, nil)
		w.Send(Message{Results: []string{"c"}}, nil)
	}()
	ch.reportValues(map[string]any{"model": sr}) // channel 里装个流

	fmt.Println("转换前: channel 里是 *StreamReader(流)")
	// ★ 调 convertValues:对流逐个 concat 成 Message
	if err := concatStreamValues(ch); err != nil {
		return err
	}
	fmt.Println("转换后: channel 里是 Message(单值,已 concat)")

	// 验证:取出看是不是合并后的 Message
	val, ok, err := ch.get(false, "demo", nil)
	if err != nil || !ok {
		return fmt.Errorf("get after convertValues fail: ok=%v err=%v", ok, err)
	}
	msg, _ := val.(Message)
	fmt.Printf("结果: Message{Results: %v} (3 个 chunk 已 concat)\n", msg.Results)
	return nil
}
