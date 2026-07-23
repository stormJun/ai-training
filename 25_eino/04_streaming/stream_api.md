# StreamReader / StreamWriter:基础 API

> 源码: `/Users/songxijun/workspace/otherProject/eino/schema/stream.go`
> 底层设计: [source_notes/stream_design.md](../source_notes/stream_design.md)
> 本文讲基础 API 用法。

## 一、核心类型

Eino 流式的核心是两个泛型类型:

```go
// StreamReader[T] 读端:消费者从中读取 chunk
type StreamReader[T] any

// StreamWriter[T] 写端:生产者往里面写 chunk
type StreamWriter[T] any

// 创建一对读写端
func Pipe[T any](cap int) (*StreamReader[T], *StreamWriter[T])
```

**本质**: `Pipe` 创建一个带缓冲的 channel，把发送/接收封装成干净的 API。

## 二、基本用法:发送和接收

### 2.1 生产者(写)

```go
sr, sw := schema.Pipe[string](3) // 缓冲大小 3

go func() {
	defer sw.Close() // 发送完一定要关闭，接收方才能收到 EOF

	for i := 0; i < 10; i++ {
		// Send 发送一个 chunk
		// 如果出错返回 false，说明接收端已经关闭，应该停止发送
		if !sw.Send(fmt.Sprintf("chunk-%d", i), nil) {
			return
		}
	}
}()
```

要点:
- `cap` 是缓冲区大小，对应 channel 容量
- `Send(chunk, err)`:第二个参数传 error 表示发送失败，会直接把错误传给接收方
- `defer sw.Close()`:必须关闭，否则接收方会一直等下去，goroutine 泄漏

### 2.2 消费者(读)

```go
defer sr.Close() // 读完一定要关闭，否则发送端可能泄漏

for {
	chunk, err := sr.Recv()
	if errors.Is(err, io.EOF) {
		break // 结束
	}
	if err != nil {
		return err // 错误处理
	}
	// 处理 chunk
	fmt.Println(chunk)
}
```

要点:
- `Recv()` 返回 `(chunk, err)`
- `err == io.EOF` 表示正常结束
- 其他 err 是传输错误
- **必须 `defer sr.Close()`**，否则底层 channel/goroutine 泄漏

## 三、关键属性

### 3.1 单次消费

`StreamReader[T]` 是**只读一次**:
- 只能被一个 goroutine 从头到尾 Recv
- 不能并发读
- 如果需要多个消费者读同一个流，用 `sr.Copy(n)` 生成 n 个独立 reader，见 [convert_merge_copy.md](./convert_merge_copy.md)

### 3.2 关闭配合

| 谁关闭 | 对另一方的影响 |
|--------|----------------|
| 调用者 `sr.Close()` | 发送端 `sw.Send` 会返回 false，知道接收端提前退出，可以停止发送 |
| 发送端 `sw.Close()` | 接收端读完所有 chunk 后得到 `io.EOF`，正常结束 |

所以:
- 发送端负责 `Close()` writer
- 接收端负责 `Close()` reader
- 双向配合防止泄漏

### 3.3 错误传递

如果发送过程中出错:
```go
// 发送时出错了
if err := doSomething(); err != nil {
	sw.Send("", err) // 把错误传给接收端
	return
}
```

接收端 `Recv()` 直接得到这个错误，不需要额外处理。

## 四、从数组创建 StreamReader

如果已经有完整数组，可以直接转成 `StreamReader`:

```go
// 从 []T 创建 StreamReader
// 零 goroutine，零分配，直接读数组
sr := schema.StreamReaderFromArray([]string{"a", "b", "c"})
```

优缺点:
- ✅ 没有 goroutine，性能更好
- ✅ 适合已经有完整结果需要转换成流的场景
- ❌ 已经是完整结果，不需要等待，所以就是"伪流式"

## 五、完整示例

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"io"

	"github.com/cloudwego/eino/schema"
)

func main() {
	// 1. 创建流
	sr, sw := schema.Pipe[int](3)

	// 2. 生产者:发送 0-9
	go func() {
		defer sw.Close()

		for i := 0; i < 10; i++ {
			if i == 7 {
				// 模拟错误
				sw.Send(0, fmt.Errorf("something wrong at i=%d", i))
				return
			}
			if !sw.Send(i, nil) {
				return // 接收端关闭了
			}
		}
	}()

	// 3. 消费者:接收
	defer sr.Close()

	for {
		chunk, err := sr.Recv()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			fmt.Printf("got error: %v\n", err)
			break
		}
		fmt.Printf("got chunk: %d\n", chunk)
	}
}
```

输出:
```
got chunk: 0
got chunk: 1
got chunk: 2
got chunk: 3
got chunk: 4
got chunk: 5
got chunk: 6
got error: something wrong at i=7
```

## 六、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **程序卡住不退出** | 忘记 `sw.Close()` 或 `sr.Close()` | 一定 `defer` 关闭 |
| **goroutine 泄漏** | 接收端退出了，发送端还在一直 Send | 检查 `sw.Send` 返回值，false 就停止发送 |
| **同一个流被读两次** | `StreamReader` 是单次消费，读完一次内部指针已经走完 | 需要多读者用 `Copy(n)` |
| **错误被吞** | 发送方不把 err 传给 `Send`，直接 return | 出错要 `Send(zero, err)`，接收端才能收到 |

## 七、下一步

- 学会基础 API 之后，看 [convert_merge_copy.md](./convert_merge_copy.md) 学习类型转换、多路合并、扇出
- 然后看 [autopilot.md](./autopilot.md) 学习编排层怎么自动处理流式
