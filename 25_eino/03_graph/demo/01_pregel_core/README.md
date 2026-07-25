# 01 Pregel 最小内核(串行版)

> 源码:[`main.go`](./main.go)(纯标准库,不依赖 eino)
> 配套概念文档:[`../pregel.md`](../pregel.md)
> 下游:[`../02_pregel_barrier`](../02_pregel_barrier/README.md)(+ 屏障 / 并行 / 可中断)

Pregel 四机制的**最小可运行实现**:`顶点为中心 + 超步循环 + 消息 S->S+1 + 触发与终止`。
Compute **串行**、拓扑**内联**(无 Graph/Compile),无屏障、无并行--先把"Pregel 怎么转起来"讲清楚。

## 它是什么

~210 行,一个 mini-ReAct(model + search + calc)跑出"模型↔工具"有环循环,
**不写 `for`**,靠顶点互发消息 + 引擎一轮轮调度自然转出来。

## 运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/01_pregel_core
go run .
```

预期输出:

```
── superstep 0 ── 活跃顶点: [model]
  [model] 第 1 次激活,收到 1 条消息
  [model] 产出 ToolCalls=[search, calc]

── superstep 1 ── 活跃顶点: [calc search]
  [calc] 执行 2+3 -> calc(2+3)
  [search] 执行 eino pregel -> search(eino pregel)

── superstep 2 ── 活跃顶点: [model]
  [model] 第 2 次激活,收到 2 条消息
  [model] 产出最终答案 "done with 2 results: [...]",路由到 END
  [model] -> END(终端)
无在途消息,计算结束

最终答案: done with 2 results: [calc(2+3) search(eino pregel)]
```

## 三层解耦(设计的骨架)

唯一耦合是 `Message`:

```
Message  ── 纯数据(无 To,路由由声明决定),无行为
Vertex   ── 纯行为(Compute),无调度、不路由
Engine   ── 纯调度,无业务行为
```

- `Vertex` 不知道 `Engine` 存在(签名里没 step、没 engine 引用)。
- `Engine` 不碰 `Vertex` 内部(只调 `Compute`)。
- 两边只通过 `Message` 通信。

## 四机制落点

| 机制 | demo 代码 | 说明 |
|---|---|---|
| ① 顶点为中心 | `Vertex.Compute` | 只写 Compute,不写循环、不路由 |
| ② 超步 | `for step` | 本阶段串行,无屏障(屏障见 02) |
| ③ 消息 S->S+1 | `current`/`next` 邮箱 + `current=next` 交换 | S 步发的进 next,S+1 步才收到 |
| ④ 触发与终止 | `len(current)==0` | 有消息才激活;邮箱空即止 |

## Run 循环:Pregel 语义的浓缩

```go
for step := 0; step < maxSteps; step++ {
    if len(current) == 0 { return nil }      // ④ 终止
    next := map[string][]Message{}
    for id, msgs := range current {          // ④ 触发:有消息的顶点才跑(串行)
        out := v.Compute(ctx, msgs)          // ① 顶点为中心
        for _, to := range route(v.ID(), out) {
            next[to] = append(next[to], out) // ③ 进 next,本步不读
        }
    }
    current = next                           // ③ 交换:S 发的 = S+1 收的
}
```

三句话不变式:
1. **进入每轮**:`current` = 本超步各顶点应收到的全部消息
2. **轮内**:`next` = 本超步各顶点发出的全部消息(谁也不读它)
3. **轮末**:`current = next` = 把"发出的"变成"收到的"

第 3 句那一行 `current = next` = BSP 的"消息在 S 末投递、S+1 初送达"。整个 S->S+1 机制就是一个赋值。

## 本阶段的边界(后续阶段补齐)

- **串行**:`Compute` 逐个调用,无并行。并行 + 屏障在 **02**。
- **无屏障**:没有步间同步点。可中断屏障(done 通道 + ctx)在 **02**。
- **拓扑内联**:edges/branches 直接挂 Engine,无校验、无环检测。声明式拓扑 + Compile 在 **03**。
- **无取消场景**:ctx 透传但本阶段不演示。取消见 **02**。
