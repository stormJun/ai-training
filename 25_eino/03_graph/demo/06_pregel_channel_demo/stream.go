// stream.go:流式执行的基础设施(增量 4)。
//
// 对应 eino:
//   - schema/stream.go: StreamReader[T] / StreamWriter[T] / Pipe / StreamReaderFromArray / Copy / MergeStreamReaders
//   - compose/stream_concat.go: concatStreamReader(流->单值)
//   - compose/runnable.go: wrap(单值->流,用 StreamReaderFromArray)
//
// 四范式靠两个原语互通:
//
//	wrap   -- 单值 -> 流(StreamReaderFromArray,长度1数组+下标遍历)
//	concat -- 流 -> 单值(循环 Recv + 按类型合并)
//
// Copy(扇出)用 lazy 实现(sync.Once + 链表),对齐 eino:
// 谁先到谁触发从源读,后来的读缓存;不预读整流。
//
// Merge(扇入)用 goroutine-per-source:每个源一个 goroutine 转发 chunk,全部 EOF 关闭输出。
package main

import (
	"fmt"
	"io"
	"sync"
)

// ============================================================
// 流的底层:channel-based stream + arrayReader
// ============================================================

// streamItem 一个数据块或一个错误(EOF 也是一种,用 io.EOF)。
type streamItem[T any] struct {
	chunk T
	err   error
}

// stream channel-based 流:1 个 writer 写,1 个 reader 读。
// closed 由 reader 侧关闭(提前终止时),writer 的 Send 据此感知并停止。
type stream[T any] struct {
	items  chan streamItem[T]
	closed chan struct{}
}

func (s *stream[T]) recv() (T, error) {
	select {
	case item, ok := <-s.items:
		if !ok {
			// items 被 close(writer.Close) -> 流结束
			var t T
			return t, io.EOF
		}
		return item.chunk, item.err
	case <-s.closed:
		// reader 侧主动关闭 -> 提前终止
		var t T
		return t, fmt.Errorf("stream closed by receiver")
	}
}

func (s *stream[T]) close() {
	// 用 sync.Once 保证 close(closed) 幂等(多次 close channel 会 panic)
	// 这里简化:closed 是无缓冲 channel,close 一次即可,由调用方保证只调一次
	close(s.closed)
}

// ============================================================
// StreamWriter:发送端
// ============================================================

// StreamWriter 流的发送端。Send 写一个 chunk,Close 结束流。
type StreamWriter[T any] struct {
	stm *stream[T]
}

// Send 发送一个 chunk(或错误)。返回 false 表示 reader 已关闭,不再接收。
func (w *StreamWriter[T]) Send(chunk T, err error) bool {
	select {
	case w.stm.items <- streamItem[T]{chunk: chunk, err: err}:
		return true
	case <-w.stm.closed:
		return false
	}
}

// Close 关闭流。reader 之后 Recv 得到 io.EOF。
// 用 once 保证幂等(多次 Close 不 panic)。
func (w *StreamWriter[T]) Close() {
	close(w.stm.items)
}

// ============================================================
// Pipe:创建一对 (reader, writer)
// ============================================================

// Pipe 创建一个流,返回 (reader, writer)。对应 eino schema.Pipe[T]。
func Pipe[T any]() (*StreamReader[T], *StreamWriter[T]) {
	s := &stream[T]{
		items:  make(chan streamItem[T], 1), // 缓冲1:允许writer先发一块再被消费
		closed: make(chan struct{}),
	}
	return &StreamReader[T]{st: s, typ: readerTypeStream}, &StreamWriter[T]{stm: s}
}

// ============================================================
// StreamReader:接收端(带多种内部实现)
// ============================================================

type readerType int

const (
	readerTypeStream readerType = iota // channel-based(Pipe / Merge 输出)
	readerTypeArray                    // 数组-based(wrap 创建,长度1)
	readerTypeChild                    // Copy 出来的子流(lazy)
)

// StreamReader 流的接收端。对应 eino schema.StreamReader[T]。
// typ 决定 Recv 走哪个内部实现。
// 注:demo 的 Merge 输出复用 readerTypeStream(goroutine 转发到 Pipe),
//    不像 eino 有专用 MultiStream 类型。
type StreamReader[T any] struct {
	typ readerType
	st  *stream[T]            // readerTypeStream
	ar  *arrayReader[T]       // readerTypeArray
	csr *childStreamReader[T] // readerTypeChild
}

// Recv 读一个 chunk。返回 (chunk, io.EOF) 表示流结束。
func (r *StreamReader[T]) Recv() (T, error) {
	switch r.typ {
	case readerTypeStream:
		return r.st.recv()
	case readerTypeArray:
		return r.ar.recv()
	case readerTypeChild:
		return r.csr.recv()
	}
	var t T
	return t, fmt.Errorf("unknown reader type: %d", r.typ)
}

// Close 主动关闭(reader 不再读)。通知 writer 停止。
func (r *StreamReader[T]) Close() {
	switch r.typ {
	case readerTypeStream:
		r.st.close()
	case readerTypeChild:
		r.csr.close()
		// array 无需关闭
	}
}

// ============================================================
// arrayReader:wrap 的实现(单值 -> 流)
// ============================================================

// arrayReader 数组-based reader:按下标遍历,到头返回 io.EOF。
// 用于 wrap:把单值放进长度1的数组,模拟一个只含1个chunk的流。
type arrayReader[T any] struct {
	arr   []T
	index int
}

func (ar *arrayReader[T]) recv() (T, error) {
	if ar.index < len(ar.arr) {
		ret := ar.arr[ar.index]
		ar.index++
		return ret, nil
	}
	var t T
	return t, io.EOF
}

// StreamReaderFromArray 从数组创建 reader。对应 eino schema.StreamReaderFromArray。
// wrap 的实现:StreamReaderFromArray([]T{val})。
func StreamReaderFromArray[T any](arr []T) *StreamReader[T] {
	return &StreamReader[T]{ar: &arrayReader[T]{arr: arr}, typ: readerTypeArray}
}

// ============================================================
// wrap:单值 -> 流
// ============================================================

// wrap 把单值变成只含一个元素的流。= StreamReaderFromArray([]T{val})。
func wrap[T any](val T) *StreamReader[T] {
	return StreamReaderFromArray([]T{val})
}

// ============================================================
// concat:流 -> 单值
// ============================================================

// concatStreamReader 把流的所有 chunk 攒成单值。对应 eino compose.concatStreamReader。
// 循环 Recv 读出所有 chunk,按类型合并(此处 demo 用 Message 合并)。
func concatStreamReader[T any](sr *StreamReader[T], merge func([]T) (T, error)) (T, error) {
	defer sr.Close()
	var items []T
	for {
		chunk, err := sr.Recv()
		if err != nil {
			if err == io.EOF {
				break
			}
			var t T
			return t, err
		}
		items = append(items, chunk)
	}
	if len(items) == 0 {
		var t T
		return t, fmt.Errorf("stream reader is empty, concat fail")
	}
	if len(items) == 1 {
		return items[0], nil
	}
	return merge(items)
}

// ============================================================
// Copy:扇出(lazy,sync.Once + 链表,对齐 eino)
// ============================================================
//
// 一个流复制成 n 个独立子流,让多个消费者各读各的。
// lazy:不预读整流。谁先到某个位置,谁触发从源读一次(sync.Once 保证只读一次);
// 后到的读缓存。源只被读一次,不管多少消费者。
//
// 实现:共享一个链表,每个元素用 sync.Once 标记"是否已从源读过"。
// 各子流维护自己的当前指针,独立前进。EOF 时不前进(没有 next)。
//
//	源 ──Recv──▶ [elem0] ──next──▶ [elem1] ──next──▶ ... ──next──▶ [EOF]
//	               ▲                  ▲
//	            子流0.cur          子流1.cur(各走各的,once 保证 elem 只读一次)

// cpElement 链表节点:一个缓存的数据块 + once(保证只从源读一次) + next 指针。
type cpElement[T any] struct {
	once sync.Once
	item streamItem[T]
	next *cpElement[T]
}

// childStreamReader Copy 出来的子流。
type childStreamReader[T any] struct {
	source *StreamReader[T] // 原始流(所有子流共享)
	cur    *cpElement[T]    // 当前所在链表节点
	closed bool
}

func (c *childStreamReader[T]) recv() (T, error) {
	if c.closed {
		var t T
		return t, fmt.Errorf("child stream closed")
	}
	elem := c.cur
	// once.Do:第一个到达此节点的子流触发从源读;其余子流直接读缓存。
	elem.once.Do(func() {
		chunk, err := c.source.Recv()
		elem.item = streamItem[T]{chunk: chunk, err: err}
		elem.next = &cpElement[T]{} // 为下一个节点预占位
	})
	if elem.item.err == io.EOF {
		// EOF:不前进(没有下一个),之后 Recv 仍返回 EOF
		return elem.item.chunk, io.EOF
	}
	c.cur = elem.next // 前进到下一节点
	return elem.item.chunk, elem.item.err
}

func (c *childStreamReader[T]) close() {
	c.closed = true
}

// Copy 把一个流复制成 n 个独立子流。原始流之后不可直接使用(由子流消费)。
// 对应 eino schema.StreamReader.Copy。
func (r *StreamReader[T]) Copy(n int) []*StreamReader[T] {
	if n < 1 {
		return nil
	}
	// array 快速路径:array 不可变,直接共享底层数组(各自独立下标)
	if r.typ == readerTypeArray {
		readers := make([]*StreamReader[T], n)
		for i := 0; i < n; i++ {
			readers[i] = &StreamReader[T]{
				ar:  &arrayReader[T]{arr: r.ar.arr, index: r.ar.index},
				typ: readerTypeArray,
			}
		}
		return readers
	}
	// 通用路径:lazy 链表
	head := &cpElement[T]{}
	readers := make([]*StreamReader[T], n)
	for i := 0; i < n; i++ {
		csr := &childStreamReader[T]{source: r, cur: head}
		readers[i] = &StreamReader[T]{csr: csr, typ: readerTypeChild}
	}
	return readers
}

// ============================================================
// Merge:扇入(goroutine-per-source)
// ============================================================
//
// 多个流合并成一个,chunk 按到达顺序交错(非确定)。
// 实现:每个源一个 goroutine 转发 chunk 到输出流,全部 EOF 时关闭输出。
// 对应 eino schema.MergeStreamReaders(用 select;demo 用 goroutine-per-source 更简单,支持任意 N)。

// MergeStreamReaders 合并多个流为一个。
func MergeStreamReaders[T any](srs []*StreamReader[T]) *StreamReader[T] {
	if len(srs) == 0 {
		return wrap[T](zero[T]()) // 空合并:返回一个立即 EOF 的流
	}
	if len(srs) == 1 {
		return srs[0] // 单源:直接返回,无需合并
	}
	out, w := Pipe[T]()
	var wg sync.WaitGroup
	for _, sr := range srs {
		wg.Add(1)
		go func(sr *StreamReader[T]) {
			defer wg.Done()
			for {
				chunk, err := sr.Recv()
				if err == io.EOF {
					return
				}
				if err != nil {
					w.Send(zero[T](), err)
					return
				}
				if !w.Send(chunk, nil) {
					// 输出端关闭,停止
					return
				}
			}
		}(sr)
	}
	go func() {
		wg.Wait()
		w.Close()
	}()
	return out
}

// zero 返回类型 T 的零值。
func zero[T any]() T {
	var t T
	return t
}
