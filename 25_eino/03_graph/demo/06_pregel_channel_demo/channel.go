// channel.go:channel 抽象(增量 6 核心)。
//
// 对应 eino:
//   - graph_manager.go: channel 接口 + channelManager + edgeHandlerManager
//   - pregel.go:        pregelChannel 实现
//   - values_merge.go:  mergeValues + RegisterValuesMergeFunc
//
// 06 的 channel 是数据流中枢:收前驱值(reportValues)、取合并值带边转换(get)、
// 流转换(convertValues,checkpoint 序列化用)、恢复(load,checkpoint 恢复用)、
// 配置 merge(setMergeConfig)。Run 和 StreamRun 都通过 channel 走数据。
//
// 不做 DAG:无 reportSkip / reportDependencies。
package main

import (
	"fmt"
	"reflect"
)

// ============================================================
// 可配置 merge(对应 eino RegisterValuesMergeFunc + mergeValues)
// ============================================================
//
// 扇入时多前驱值要合并成一个。不同类型合并方式不同:
//   - Message: 拼接 ToolCalls/Results,Answer 取最后(mergeMessages)
//   - 流:      交错合并(MergeStreamReaders)
//
// 用户按类型注册 merge 函数,channel 类型无关。和 edge handler 同样的解耦哲学。

// mergeFunc 把多个值合并成一个。
type mergeFunc func([]any) (any, error)

// mergeFuncs 按类型注册的 merge 函数表。
var mergeFuncs = map[reflect.Type]mergeFunc{}

// RegisterMergeFunc 注册某类型的 merge 函数。对应 eino RegisterValuesMergeFunc[T]。
// 用法: RegisterMergeFunc(mergeMessages)  // 注册 Message 的 merge
func RegisterMergeFunc[T any](fn func([]T) (T, error)) {
	var t T
	typ := reflect.TypeOf(t)
	mergeFuncs[typ] = func(vs []any) (any, error) {
		ts := make([]T, len(vs))
		for i, v := range vs {
			tv, ok := v.(T)
			if !ok {
				return nil, fmt.Errorf("merge type mismatch: want %v, got %T", typ, v)
			}
			ts[i] = tv
		}
		return fn(ts)
	}
}

// getMergeFunc 查类型的注册 merge 函数。
func getMergeFunc(t reflect.Type) mergeFunc {
	return mergeFuncs[t]
}

// mergeValues 多值合并。流用 MergeStreamReaders,单值用注册的 merge 函数。
// 对应 eino mergeValues。
func mergeValues(vs []any, isStream bool) (any, error) {
	if len(vs) == 0 {
		return nil, fmt.Errorf("merge: no values")
	}
	if isStream {
		// 流合并:交错成一个流
		srs := make([]*StreamReader[Message], 0, len(vs))
		for _, v := range vs {
			sr, ok := v.(*StreamReader[Message])
			if !ok {
				return nil, fmt.Errorf("stream merge: not a StreamReader, got %T", v)
			}
			srs = append(srs, sr)
		}
		return MergeStreamReaders(srs), nil
	}
	// 单值合并:查注册表
	fn := getMergeFunc(reflect.TypeOf(vs[0]))
	if fn == nil {
		return nil, fmt.Errorf("no merge func registered for %T (call RegisterMergeFunc)", vs[0])
	}
	return fn(vs)
}

// ============================================================
// EdgeHandler + edgeHandlerManager(对应 eino handlerPair + edgeHandlerManager)
// ============================================================
//
// edge handler 是"数据过边时转换"的机制。挂在边上,数据从 from 过边到 to 时被转换。
// Invoke 模式调 Invoke(单值),Transform 模式调 Transform(流)。
// 解耦:产出节点和消费节点互不认识,边负责转换。

// EdgeHandler 一条边的转换函数(两种范式各一个)。
type EdgeHandler struct {
	Invoke    func(Message) (Message, error)                                          // 单值转换(Run 模式)
	Transform func(*StreamReader[Message]) (*StreamReader[Message], error)           // 流转换(StreamRun 模式)
}

// edgeHandlerManager 管 all 边的 handler:map[from]map[to]EdgeHandler。
// 对应 eino edgeHandlerManager。
type edgeHandlerManager struct {
	h map[string]map[string]EdgeHandler
}

func newEdgeHandlerManager() *edgeHandlerManager {
	return &edgeHandlerManager{h: map[string]map[string]EdgeHandler{}}
}

// add 注册一条边的 handler。
func (e *edgeHandlerManager) add(from, to string, eh EdgeHandler) {
	if e.h[from] == nil {
		e.h[from] = map[string]EdgeHandler{}
	}
	e.h[from][to] = eh
}

// handle 对从 from 到 to 的值应用边 handler。无 handler 则原值返回。
// 对应 eino edgeHandlerManager.handle。
func (e *edgeHandlerManager) handle(from, to string, value any, isStream bool) (any, error) {
	if e == nil {
		return value, nil
	}
	if e.h[from] == nil {
		return value, nil
	}
	eh, ok := e.h[from][to]
	if !ok {
		return value, nil
	}
	if isStream {
		sr, ok := value.(*StreamReader[Message])
		if !ok {
			return value, nil // 不是流,不转
		}
		return eh.Transform(sr)
	}
	m, ok := value.(Message)
	if !ok {
		return value, nil // 不是 Message,不转
	}
	return eh.Invoke(m)
}

// ============================================================
// channel 接口(对应 eino channel interface,去掉 DAG 的 2 个方法)
// ============================================================
//
// 5 个方法(无 reportSkip / reportDependencies -- 那是 DAG 的):
//   - reportValues: 收前驱输出(from -> value)
//   - get:          取合并值(对每个值应用边 handler,多值 merge)
//   - convertValues: 批量转换值(checkpoint 序列化流用)
//   - load:         从另一个 channel 恢复(checkpoint 恢复用)
//   - setMergeConfig: 配置 per-channel merge 覆盖

type channel interface {
	reportValues(map[string]any) error
	get(isStream bool, name string, eh *edgeHandlerManager) (any, bool, error)
	convertValues(fn func(map[string]any) error) error
	load(channel) error
	setMergeConfig(mergeFunc)
}

// ============================================================
// pregelChannel(对应 eino pregelChannel)
// ============================================================
//
// Values: map[from]any -- 按来源节点存值(Message 或 *StreamReader)。
// get 时对每个值应用边 handler,多值调 mergeValues 合并成一个。

type pregelChannel struct {
	Values   map[string]any
	mergeCfg mergeFunc // 可选:per-channel merge 覆盖(默认走全局注册表)
}

func newPregelChannel() *pregelChannel {
	return &pregelChannel{Values: map[string]any{}}
}

func (ch *pregelChannel) reportValues(in map[string]any) error {
	for k, v := range in {
		ch.Values[k] = v
	}
	return nil
}

// get 取值:对每个 from 的值应用边 handler,单值直接返回,多值 merge。
// 取走后清空(对应 eino get 的 defer 清空)。
func (ch *pregelChannel) get(isStream bool, name string, eh *edgeHandlerManager) (any, bool, error) {
	if len(ch.Values) == 0 {
		return nil, false, nil
	}
	defer func() { ch.Values = map[string]any{} }()
	values := make([]any, 0, len(ch.Values))
	for from, v := range ch.Values {
		resolved, err := eh.handle(from, name, v, isStream)
		if err != nil {
			return nil, false, err
		}
		values = append(values, resolved)
	}
	if len(values) == 1 {
		return values[0], true, nil
	}
	// 多值:per-channel 覆盖优先,否则全局注册表
	if ch.mergeCfg != nil {
		v, err := ch.mergeCfg(values)
		return v, err == nil, err
	}
	v, err := mergeValues(values, isStream)
	return v, err == nil, err
}

// convertValues 批量转换值(checkpoint 序列化用:流 -> 单值)。
func (ch *pregelChannel) convertValues(fn func(map[string]any) error) error {
	return fn(ch.Values)
}

// load 从另一个 channel 恢复值(checkpoint 恢复用)。
func (ch *pregelChannel) load(c channel) error {
	dc, ok := c.(*pregelChannel)
	if !ok {
		return fmt.Errorf("load: not pregelChannel, got %T", c)
	}
	ch.Values = dc.Values
	return nil
}

func (ch *pregelChannel) setMergeConfig(cfg mergeFunc) {
	ch.mergeCfg = cfg
}

// ============================================================
// channelManager(对应 eino channelManager,简化)
// ============================================================
//
// map[nodeKey]channel -- 每个节点一个 channel,收它的前驱值。
// Run/StreamRun 的 current/next 就是 channelManager。

type channelManager struct {
	channels map[string]channel
}

func newChannelManager() *channelManager {
	return &channelManager{channels: map[string]channel{}}
}

// report 投递一个值到 to 节点的 channel(from -> value)。
func (cm *channelManager) report(to, from string, value any) {
	if cm.channels[to] == nil {
		cm.channels[to] = newPregelChannel()
	}
	cm.channels[to].reportValues(map[string]any{from: value})
}
