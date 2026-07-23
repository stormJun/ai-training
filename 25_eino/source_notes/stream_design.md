# `schema/stream.go` 设计分析

> 源码:`/Users/songxijun/workspace/otherProject/eino/schema/stream.go`(1025 行)
> 配套:`schema/select.go`(select 表)。
> 本文逐层拆解 Eino 流式抽象的设计。

## 0. 一句话定位

`stream.go` 实现了 Eino 贯穿全栈的流式抽象:用一套统一的泛型 `StreamReader[T]` / `StreamWriter[T]` API,把**管道、数组、多路合并、类型转换、扇出**五种底层实现隐藏在同一个类型背后,供组件层、编排层、ADK 层统一使用。

## 1. 顶层抽象:读写分离的单向流

整个文件围绕两个对外的泛型类型:

- `StreamWriter[T]`(`stream.go:115`)-- 生产者端,只有 `Send(chunk, err)`(`:126`)和 `Close()`(`:139`)。
- `StreamReader[T]`(`stream.go:168`)-- 消费者端,有 `Recv()`(`:195`)、`Close()`(`:229`)、`Copy(n)`(`:261`)、`SetAutomaticClose()`(`:279`)。

两者通过 `Pipe[T](cap)`(`stream.go:99`)成对创建,底层共享一个 `stream[T]`。这是 **SPSC(单生产者单消费者)** 模型,文档明确写"read-once, only one goroutine should call Recv"(`:145`)。

典型用法:

```go
sr, sw := schema.Pipe[string](3)
go func() {
    defer sw.Close()           // 发完一定要 Close,接收方才能收到 io.EOF
    for i := 0; i < 10; i++ {
        sw.Send(i, nil)
    }
}()
defer sr.Close()               // 读端也一定要 Close
for {
    chunk, err := sr.Recv()
    if errors.Is(err, io.EOF) { break }
    if err != nil { return err }
    fmt.Println(chunk)
}
```

## 2. 底层原语:`stream[T]`

```go
// stream.go:375
type stream[T any] struct {
    items chan streamItem[T]   // 数据通道,带缓冲(cap)
    closed chan struct{}        // 接收方取消信号
    automaticClose bool
    closedFlag     *uint32      // 仅 automaticClose 时用,0=未关 1=已关
}

type streamItem[T any] struct {  // stream.go:384
    chunk T
    err   error
}
```

两个通道各司其职:

- `items` 传数据。`closeSend()`(`:428`)关闭它,接收方 `<-s.items` 收到零值 + `ok==false`,于是返回 `io.EOF`(`recv` 在 `:401-408`)。
- `closed` 是**接收方主动取消**的信号。

### 2.1 为什么 `send` 要 select 两次 `closed`?

```go
// stream.go:410
func (s *stream[T]) send(chunk T, err error) (closed bool) {
    select {
    case <-s.closed:        // 第一次:快速路径,已关则立刻返回
        return true
    default:
    }
    item := streamItem[T]{chunk, err}
    select {
    case <-s.closed:        // 第二次:阻塞发送期间若被取消,也能退出
        return true
    case s.items <- item:
        return false
    }
}
```

关键在于:如果只写 `s.items <- item`,当接收方不再读且缓冲已满时,生产者会**永久阻塞**,goroutine 泄漏。第二次 `select <-s.closed` 让生产者在接收方 `closeRecv()` 后能及时退出。这是整个流避免 goroutine 泄漏的核心。

### 2.2 `closeRecv` 的 CAS 保护

```go
// stream.go:432
func (s *stream[T]) closeRecv() {
    if s.automaticClose {
        if atomic.CompareAndSwapUint32(s.closedFlag, 0, 1) {  // 保证只关一次
            close(s.closed)
        }
        return
    }
    close(s.closed)
}
```

`automaticClose` 场景下,`runtime.SetFinalizer` 可能在不确定时机触发 `Close()`,与用户手动 Close 竞争。CAS 保证 `close(s.closed)` 只执行一次,避免重复 close channel 的 panic。

## 3. 判别式联合:一个 `StreamReader[T]` 包装五种后端

这是整个文件**最关键的设计**。`StreamReader[T]` 不是接口,而是带类型标签的结构体:

```go
// stream.go:168
type StreamReader[T any] struct {
    typ readerType   // 判别字段
    st  *stream[T]                       // readerTypeStream
    ar  *arrayReader[T]                  // readerTypeArray
    msr *multiStreamReader[T]            // readerTypeMultiStream
    srw *streamReaderWithConvert[T]      // readerTypeWithConvert
    csr *childStreamReader[T]            // readerTypeChild
}

// stream.go:357
const (
    readerTypeStream readerType = iota
    readerTypeArray
    readerTypeMultiStream
    readerTypeWithConvert
    readerTypeChild
)
```

`Recv()` / `Close()` / `toStream()` 都是 `switch sr.typ` 派发(`:196` / `:229` / `:338`)。

**为什么不用接口?** 因为:
1. 对外类型稳定,始终是 `*StreamReader[T]`,可作为返回值直接传递(eino 的 graph 节点间拼装需要)。
2. 避免接口分配,保持值语义。
3. 五种后端可以零成本互换,调用方无感知。

| `readerType` | 后端 | 创建入口 | 用途 |
|---|---|---|---|
| `readerTypeStream` | `stream[T]` | `Pipe` | 真管道 |
| `readerTypeArray` | `arrayReader` | `StreamReaderFromArray`(`:461`) | 数组,零 goroutine、零拷贝 |
| `readerTypeMultiStream` | `multiStreamReader` | `MergeStreamReaders`(`:912`)/ `MergeNamedStreamReaders`(`:990`) | 多路 fan-in 合并 |
| `readerTypeWithConvert` | `streamReaderWithConvert` | `StreamReaderWithConvert`(`:691`) | 类型转换 + 过滤装饰器 |
| `readerTypeChild` | `childStreamReader` | `Copy`(`:261`) | 扇出的子 reader |

## 4. `iStreamReader` 接口:内部类型擦除

判别式联合解决"同类型多后端",但跨类型(任意 `T`)操作(如 Convert、Copy、Merge)还需要类型擦除。于是有一个内部接口:

```go
// stream.go:365
type iStreamReader interface {
    recvAny() (any, error)
    copyAny(int) []iStreamReader
    Close()
    SetAutomaticClose()
}
```

`StreamReader[T]` 通过 `recvAny`(`:312`)、`copyAny`(`:316`)实现它。`streamReaderWithConvert` 内部持的就是 `iStreamReader`(`:597`),所以它能套在任意 reader 外面--**装饰器模式**的基础。

## 5. 数组后端:`arrayReader`

```go
// stream.go:465
type arrayReader[T any] struct {
    arr   []T
    index int
}
```

`recv()`(`:470`)就是按 index 递增取,取完返回 `io.EOF`。无 channel、无 goroutine,适合"已知全部结果"的场景(如 `StreamReaderFromArray([]int{1,2,3})`)。

`copy(n)`(`:482`)直接复制 `arr` 和 `index` 给 n 个独立 reader--**数组的 Copy 是零成本的**,这也是 `Copy` 对 `readerTypeArray` 走特殊快路径的原因(`:266`)。

## 6. 转换装饰器:`StreamReaderWithConvert`

`StreamReaderWithConvert[T,D]`(`:691`)把 `StreamReader[T]` 包成 `StreamReader[D]`,四个扩展点:

1. **转换** `convert(T)(D,error)`
2. **过滤** -- 返回 `ErrNoValue`(`:47`)的元素被静默丢弃,继续读下一个。
3. **错误包装** `WithErrWrapper`(`:653`)-- 包装上游来的非 EOF 错误;若返回 nil 则跳过该错误块。
4. **EOF 钩子** `WithOnEOF`(`:664`)-- 在最终 EOF 前注入一个值或错误。

核心是 `recv()` 的 for 循环(`:699`),把"跳过"逻辑内联:

```go
// stream.go:699 (简化)
func (srw *streamReaderWithConvert[T]) recv() (T, error) {
    for {
        out, err := srw.sr.recvAny()
        if err != nil {
            // EOF 时触发 onEOF 钩子;非 EOF 走 errWrapper(返回 nil 则 continue)
            ...
        }
        t, err := srw.convert(out)
        if err == nil { return t, nil }
        if !errors.Is(err, ErrNoValue) { return t, err }  // ErrNoValue 则继续循环
    }
}
```

过滤示例:

```go
strReader := schema.StreamReaderWithConvert(intReader,
    func(i int) (string, error) {
        if i == 0 { return "", schema.ErrNoValue } // 跳过 0
        return fmt.Sprintf("val_%d", i), nil
    })
// Recv 得到 "val_1", "val_2", "val_3"
```

## 7. 扇出:`Copy` 与 `parentStreamReader` 的惰性链表

`Copy(n)`(`:261`)把一个流复制成 n 个独立消费者。难点:**原始流只能读一次,但要分发给 n 个 reader,且各 reader 速度不同**。

设计用一个**惰性求值的单向链表**:

```go
// stream.go:784
type cpStreamElement[T any] struct {
    once sync.Once
    next *cpStreamElement[T]
    item streamItem[T]
}

// stream.go:823
type parentStreamReader[T any] struct {
    sr            *StreamReader[T]
    subStreamList []*cpStreamElement[T]   // 每个 child 当前的"读指针"
    closedNum     uint32                   // 已关闭 child 计数
}
```

工作原理(`peek` 在 `:837`):

- 每个 child 持有自己"当前读到哪个节点"的指针(`subStreamList[idx]`)。
- `peek` 用 `sync.Once` 保证某个节点**只由第一个到达的 child 触发 `sr.Recv()`** 拉取真实数据,其它 child 直接复用 `elem.item`。
- 拉到非 EOF 数据时,预先挂一个空 `next` 节点,并把该 child 的指针前移到 `next`。

```go
// stream.go:848 (核心)
elem.once.Do(func() {
    t, err = p.sr.Recv()                       // 只拉一次
    elem.item = streamItem[T]{chunk: t, err: err}
    if err != io.EOF {
        elem.next = &cpStreamElement[T]{}      // 预挂下一节点
        p.subStreamList[idx] = elem.next
    }
})
```

效果:**多消费者共享一份已读数据,谁慢谁自己缓存指针,快的不会等慢的**。节点内容写定后不再修改,因此 children 可并发读。

`close(idx)`(`:868`)用原子计数,所有 child 都关闭才关掉上游 `sr.Close()`,避免某个 child 提前关闭导致上游被掐断。

`elem == nil` 表示该 child 已关闭,此时再 `recv` 返回 `ErrRecvAfterClosed`(`:51`)。

## 8. 多路合并:`multiStreamReader`

`MergeStreamReaders`(`:912`)把多个 reader 扇入一个。先把各种后端统一 `toStream()` 成 `[]*stream[T]`,再用 select 读。

```go
// stream.go:504
type multiStreamReader[T any] struct {
    sts               []*stream[T]
    itemsCases        []reflect.SelectCase   // 仅当源数 > maxSelectNum 时构建
    nonClosed         []int                   // 未关闭的源下标
    sourceReaderNames []string                // 命名合并时用
}
```

### 8.1 性能分水岭:`maxSelectNum`

Go 的 `select` 是关键字,case 数量必须在编译期固定。所以要动态选 N 路 channel,要么手写 N 个分支,要么用 `reflect.Select`(慢)。eino 的策略(`recv` 在 `:538`):

- 源数 `<= maxSelectNum`(=5,定义在 `select.go:19`)时,用**代码生成的 `receiveN`**(`select.go:21`)-- 一张按 `len(chosenList)` 索引的 select 函数表(1~5 路),无反射开销。
- 源数 `> 5` 时,降级到 `reflect.Select`(`:544`),并在某路关闭后把它的 case 置零(`msr.itemsCases[chosen].Chan = reflect.Value{}`),避免重复选到已关闭通道。

某一路 EOF 时,从 `nonClosed` 删除该下标(`:559`),全部关闭后返回 `io.EOF`。

### 8.2 命名合并:`MergeNamedStreamReaders`

普通 `MergeStreamReaders` 对子流 EOF 是静默跳过。`MergeNamedStreamReaders`(`:990`)则增强:某一路 EOF 时发一个 `*SourceEOF` 错误(带源名),让调用方能感知"哪个源先结束"。

```go
// stream.go:56
type SourceEOF struct{ sourceName string }
// stream.go:67
func GetSourceName(err error) (string, bool) { ... errors.As ... }
```

`recv` 里在删除关闭源后检查 `sourceReaderNames`,若有则返回 `&SourceEOF{...}`(`:566-569`)。调用方:

```go
for {
    chunk, err := merged.Recv()
    if errors.Is(err, io.EOF) { break }
    if name, ok := schema.GetSourceName(err); ok {
        fmt.Printf("%s finished\n", name)   // 某源结束了
        continue
    }
    if err != nil { return err }
    process(chunk)
}
```

## 9. 统一降级:`toStream[T,Reader]`

不同后端有时需要被拉平成同一个 `*stream[T]`(比如 Merge 时把 WithConvert/Child 后端统一)。`toStream`(`:747`)是泛型辅助:

```go
// stream.go:742
type reader[T any] interface {
    recv() (T, error)
    close()
}

// stream.go:747
func toStream[T any, Reader reader[T]](r Reader) *stream[T] {
    ret := newStream[T](5)
    go func() {
        defer func() {
            if panicErr := recover(); panicErr != nil {     // 捕获生产 goroutine 的 panic
                e := safe.NewPanicErr(panicErr, debug.Stack())
                _ = ret.send(/*零值*/, e)                    // 转成流上的 error
            }
            ret.closeSend()
            r.close()
        }()
        for {
            out, err := r.recv()
            if err == io.EOF { break }
            if ret.send(out, err) { break }                  // 接收方取消则退出
        }
    }()
    return ret
}
```

两个亮点:
1. **panic 跨 goroutine 传递**:用 `recover()` 捕获后包成 `safe.NewPanicErr` 发到流上,避免生产者 panic 导致消费者无感知的死锁。
2. **起一个 goroutine 把任意 reader 抽干到真 stream**--这是 WithConvert / Child 后端能参与 Merge 的桥梁(见 `:780`、`:892`)。

## 10. 资源安全:自动关闭

`SetAutomaticClose()`(`:279`)用 `runtime.SetFinalizer` 在 reader 被 GC 时自动 `Close()`:

```go
// stream.go:286
runtime.SetFinalizer(sr, func(s *StreamReader[T]) { s.Close() })
```

针对不同后端递归设置(multiStream 给每个子流、child 找 parent、withConvert 找内层 sr),防止用户忘记 close 导致生产者 goroutine 泄漏。文档注明 "NOT concurrency safe"。

## 11. 设计总结

| 关注点 | 解法 | 位置 |
|---|---|---|
| 统一 API,多变体 | 判别式 `StreamReader[T]` + `readerType` tag(非接口,零分配) | `:168` / `:357` |
| 跨类型操作 | 内部 `iStreamReader` 类型擦除接口 | `:365` |
| SPSC 反压/取消 | `items` + `closed` 双通道,send 两次 select | `:375` / `:410` |
| 流转换/过滤 | `WithConvert` 装饰器 + `ErrNoValue` 哨兵 | `:691` / `:47` |
| 扇出(1→N) | `sync.Once` 惰性链表,共享拉取 | `:784` / `:837` |
| 扇入(N→1) | `receiveN` select 表(≤5)/ `reflect.Select`(>5) | `select.go:19` / `:538` |
| 命名感知合并 | `SourceEOF` + `GetSourceName` | `:56` / `:990` |
| 资源泄漏 | finalizer 自动 close + panic→error 转换 | `:279` / `:747` |

整体是一个**面向 graph 节点拼接**的流抽象:每个节点产出/消费 `StreamReader[T]`,中间可以 Convert 换类型、Merge 合流、Copy 分流,而类型签名始终统一,非常适合做类型安全的流式 DAG。这也是它在 eino 分层架构中位于最底层"类型层"的原因--组件、编排、ADK 三层都依赖它。

## 12. 相关文件

- `schema/stream.go` -- 本文主角
- `schema/select.go` -- `maxSelectNum` 与 `receiveN` select 表
- `schema/stream_test.go` / `stream_copy_external_test.go` / `stream_oneof_test.go` -- 测试,可对照行为
- `compose/stream_concat.go` / `compose/stream_reader.go` -- 编排层如何使用本抽象做流式拼接
