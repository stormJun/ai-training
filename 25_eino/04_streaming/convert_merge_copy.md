# Convert / Merge / Copy:流的常见操作

> 源码: `/Users/songxijun/workspace/otherProject/eino/schema/stream.go`
> 本文讲三个最常用的流操作：类型转换、多路合并、扇出复制。

## 一、Convert:类型转换

`schema.StreamReaderWithConvert` 把 `StreamReader[T]` 转换成 `StreamReader[U]`，给每个 chunk 应用转换函数。

```go
// 把 StreamReader[int] 转成 StreamReader[string]
srInt := schema.StreamReaderFromArray([]int{1, 2, 3})
srStr := schema.StreamReaderWithConvert(srInt, func(i int) (string, error) {
	return fmt.Sprintf("num-%d", i), nil
})
// 现在 srStr 是 StreamReader[string]
```

### 1.1 过滤

转换函数返回 `schema.ErrNoValue` 可以**过滤掉**这个 chunk：

```go
srInt := schema.StreamReaderFromArray([]int{1, 2, 3, 4, 5})
srEven := schema.StreamReaderWithConvert(srInt, func(i int) (int, error) {
	if i%2 != 0 {
		return 0, schema.ErrNoValue // 奇数跳过
	}
	return i, nil
})
// srEven 只包含偶数 2, 4
```

### 1.2 完整签名

```go
func StreamReaderWithConvert[T, D any](
	sr *StreamReader[T],
	convert func(T) (D, error),
	opts ...ConvertOption,
) *StreamReader[D]
```

选项支持：
- `WithOnEOF`: EOF 前注入一个值或错误
- `WithErrWrapper`:错误包装

## 二、Merge:多路合并

`schema.MergeStreamReaders` 把多个 `StreamReader[T]` 合并成一个，按**就绪顺序**输出 chunk：

```go
sr1 := schema.StreamReaderFromArray([]string{"a1", "a2", "a3"})
sr2 := schema.StreamReaderFromArray([]string{"b1", "b2"})

merged, _ := schema.MergeStreamReaders([]*schema.StreamReader[string]{sr1, sr2})
// merged 输出: a1, a2, a3, b1, b2 (或 b1, b2 先，取决于谁先就绪)
```

### 2.1 并行读取

合并过程中，多个输入流**并行读取**，哪个流有 chunk 就绪就先输出哪个，所以顺序不固定。如果需要保序，不能用这个。

### 2.2 命名合并:感知哪个流结束

`schema.MergeNamedStreamReaders` 会在某个源流结束时发出 `schema.SourceEOF` 错误，让你知道哪个流结束了：

```go
merged, _ := schema.MergeNamedStreamReaders(map[string]*schema.StreamReader[string]{
	"stream-1": sr1,
	"stream-2": sr2,
})

for {
	chunk, err := merged.Recv()
	if err != nil {
		var se *schema.SourceEOF
		if errors.As(err, &se) {
			fmt.Printf("stream %s finished\n", se.SourceName)
			continue
		}
		break
	}
	// ...
}
```

### 2.3 性能:select 表大小限制

- 输入流 ≤ 5:用代码生成的 select 表，无反射开销
- 输入流 > 5:降级到 `reflect.Select`，有反射开销

所以一般单个节点输出不要合并太多流，性能会下降。

## 三、Copy:扇出复制

`sr.Copy(n)` 把一个流复制成 `n` 个独立的流，每个都能完整读一遍，给多个消费者用：

```go
// 一个输入流，要分给两个消费者不同处理
sr := getOriginalStream()

// 复制成 2 个独立 reader
copies := sr.Copy(2)
sr1 := copies[0]
sr2 := copies[1]

// 两个 goroutine 可以各自独立读
go consumer1(sr1)
go consumer2(sr2)
```

### 3.1 工作原理:惰性链表

Copy 不是一开始把整个流全读进内存，而是：
- 每个 reader 独立读，谁慢谁等
- 第一个读到 chunk 的节点把 chunk 存在链表，后面的 reader 直接复用
- 空间换时间，每个 chunk 只读一次，多个消费者共享

所以：
- ✅ 不需要提前把整个流读进内存
- ✅ 支持流式，第一个 chunk 出来就能处理，不需要等全部
- ✅ 每个消费者速度不同，天然支持

### 3.2 使用场景

- 同一个流要输出到多个地方（比如既要存日志，还要返回给客户端）
- 多个节点需要同一个输入流，不能抢

## 四、完整示例

### 4.1 Convert 过滤 + 转换

```go
sr := schema.StreamReaderFromArray([]int{1, 2, 3, 4, 5, 6, 7, 8, 9, 10})

// 转成字符串，只保留偶数
srConv := schema.StreamReaderWithConvert(sr, func(i int) (string, error) {
	if i%2 != 0 {
		return "", schema.ErrNoValue
	}
	return fmt.Sprintf("even-%d", i), nil
})

defer srConv.Close()
for {
	chunk, err := srConv.Recv()
	if errors.Is(err, io.EOF) {
		break
	}
	fmt.Println(chunk)
}
// Output:
// even-2
// even-4
// even-6
// even-8
// even-10
```

### 4.2 Merge 两个流

```go
sr1 := schema.StreamReaderFromArray([]string{"fast", "fast", "fast"})
sr2 := schema.StreamReaderFromArray([]string{"slow", "slow"})

merged, err := schema.MergeStreamReaders([]*schema.StreamReader[string]{sr1, sr2})
if err != nil { panic(err) }
defer merged.Close()

for {
	chunk, err := merged.Recv()
	if errors.Is(err, io.EOF) {
		break
	}
	if err != nil { panic(err) }
	fmt.Println(chunk)
}
// 输出顺序不一定，取决于调度
```

### 4.3 Copy 扇出

```go
original := schema.StreamReaderFromArray([]int{1, 2, 3})
copies := original.Copy(2)

var wg sync.WaitGroup
wg.Add(2)

go func() {
	defer wg.Done()
	defer copies[0].Close()
	for {
		c, err := copies[0].Recv()
		if errors.Is(err, io.EOF) { break }
		fmt.Printf("consumer 1 got: %d\n", c)
	}
}()

go func() {
	defer wg.Done()
	defer copies[1].Close()
	for {
		c, err := copies[1].Recv()
		if errors.Is(err, io.EOF) { break }
		fmt.Printf("consumer 2 got: %d\n", c)
	}
}()

wg.Wait()
// Output (顺序不一定，但两个消费者都能拿到全部):
// consumer 1 got: 1
// consumer 1 got: 2
// consumer 1 got: 3
// consumer 2 got: 1
// consumer 2 got: 2
// consumer 2 got: 3
```

## 五、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **Merge 很慢** | 合并超过 5 个流，触发 reflect.Select 反射 | 尽量不要合并太多流，拆分多次合并 |
| **Copy 内存泄漏** | 有一个 consumer 一直不读，链表一直增长 | 速度差太多不要用 Copy，考虑分开读 |
| **Convert 吞掉错误** | 转换函数没正确返回 err | 转换出错直接 return 错误，不会被吞 |
| **Merge 顺序和预期不一样** | Merge 是并行读，按就绪顺序输出 | 需要保序不要用 Merge，自己串起来 |

## 六、小结

| 操作 | 作用 | 使用场景 |
|------|------|----------|
| `Convert` | 类型转换 + 过滤 | 把一种 chunk 转成另一种，过滤掉不需要的 chunk |
| `Merge` | 多路合并 | 多个流并行读取，合并成一个输出 |
| `Copy` | 扇出复制 | 一个输入给多个消费者，每个都能读完整流 |

这三个操作是构建流式处理流水线的基础积木，编排层自动流式衔接就是用这些积木拼出来的。

## 七、下一步

接下来看 [autopilot.md](./autopilot.md)，了解编排层怎么自动处理流式衔接。
