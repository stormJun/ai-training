# 02 Pregel + 屏障(并行 / 可中断)

> 源码:[`main.go`](./main.go)(纯标准库,不依赖 eino)
> 上游:[`../01_pregel_core`](../01_pregel_core/pregel_core.md)(串行四机制)
> 下游:[`../03_pregel_compile`](../03_pregel_compile/pregel_compile.md)(+ Compile / 环检测)
> 配套概念文档:[`../pregel.md`](../pregel.md)

在 01 串行版基础上引入 **taskManager 屏障**:`Compute 并行 + 步间屏障 + panic 恢复 + ctx 取消`。
拓扑仍内联(无 Graph/Compile)。对应 eino `taskManager`(`graph_manager.go:269`)+ `graph_run.go:241` 的并行 `execute`。

## 新增(相对 01)

| 机制 | 代码 | 说明 |
|---|---|---|
| 并行 Compute | `taskManager.submit` + goroutine | 活跃顶点同超步并行跑 |
| 屏障 | `taskManager.wait` | 步间等齐:本步全完成才进下一步 |
| panic 恢复 | `execute` 的 `recover` | 顶点 panic 转 error,不崩程序 |
| ctx 取消/超时 | `wait` 的 `select` + `ctx.Done()` | 可中断屏障 + in-flight Compute 被打断 |

## 运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/02_pregel_barrier
go run .
```

含两个场景:
- **场景一**:mini-ReAct(model + search + calc),并行版(search/calc 同超步并行)
- **场景二**:主动取消--slow 顶点睡 0.5s 但响应 ctx,Run 起来后 100ms `cancel()`,in-flight Compute 被打断、屏障立即返回

场景二预期:

```
=== 场景二:主动取消 ===
── superstep 0 ── 活跃顶点: [slow]
  [slow] 开始计算(睡 0.5s,但响应 ctx)...
  (主动 cancel())
  [slow] 被 ctx 取消,提前返回(in-flight Compute 被打断)
Run 返回错误(被取消): context canceled
```

## 屏障:done 通道 + 计数(单一所有者无锁)

```
worker(execute)                 Owner(Run 协程)
─────────────                   ──────────────
Compute(ctx, in)                submit: num++(串行,无并发)
  ↓ panic? -> recover 转 err    wait:  for num>0 { select {
done <- t   ───────────────────          case <-done: num--
                                          case <-ctx.Done(): drain + return false
                                        } }
```

- `num` 用「单一所有者」模型:只由 Owner 读写,worker 只发 `done` 信号 -> 裸 `int` 无需 mutex。
- worker **禁止** `num--`:多 worker 并发改 `num` 会竞争,须加锁--那是大忌。
- `done` 通道缓冲 = 任务数,worker 发送不阻塞。

## 为什么不用裸 sync.WaitGroup

比 `sync.WaitGroup` 多两件:
1. **panic 转 error**:`recover` 把顶点 panic 转成 `task.err`,不崩程序,Run 返回错误。
2. **ctx 可打断**:`select` 同时监听 `done` 与 `ctx.Done()`,取消/超时时协作式收尾(drain 剩余完成信号)再返回。

## 并行算 + 串行收

并行只发生在 `Compute`(锁外),路由移到 `wait` 之后串行做--**不需要 mutex**。
对应 eino:`execute` 并行 + `resolveCompletedTasks` 串行。

## 本阶段的边界(后续阶段补齐)

- **拓扑仍内联**:edges/branches 直接挂 Engine,无校验、无环检测。声明式拓扑 + Compile 在 **03**。
- **无 State / 无检查点 / 无中断恢复**:见 04_pregel_checkpoint_demo。
