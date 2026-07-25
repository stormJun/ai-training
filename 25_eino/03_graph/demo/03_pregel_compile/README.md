# 03 Pregel + Compile(声明式拓扑 + 校验 + 环检测)

> 源码:[`main.go`](./main.go)(纯标准库,不依赖 eino)
> 配套概念文档:[`../pregel.md`](../pregel.md)
> 上游:[`../02_pregel_barrier`](../02_pregel_barrier/README.md)(串行四机制 + 屏障/并行/可中断,本阶段在其上引入 Compile)
>
> 本文完整描述这份 demo 的设计:从零实现一个最小的 Pregel 执行引擎,涵盖 Pregel 四机制 + 最小 Compile 阶段 + 可中断屏障(taskManager),实现思路参考 eino(`compose/graph_run.go`、`compose/pregel.go`、`compose/graph.go`、`compose/graph_manager.go`)。

## Pregel 是什么

Pregel 是 Google 2010 年提出的大规模图计算系统(论文《Pregel: A System for Large-Scale Graph Processing》),核心是一套 **BSP(Bulk Synchronous Parallel,整体同步并行)** 执行模型。eino(及 LangGraph 等)借用的是其**执行思想**,不是真跑分布式系统。

**为什么需要它**:agent 的"模型↔工具"往复是**有环循环**,纯 DAG 跑不了;Pregel 正是为有环图设计的迭代执行模型--把循环从业务代码挪进引擎,业务代码不写 `for`,还能白拿流式、中断、检查点等能力。

四个核心机制(本 demo 逐一实现,落点见后续章节):

| 机制 | 含义 | demo 落点 |
|---|---|---|
| 顶点为中心 | 只给每个顶点写 `compute()`,引擎决定何时调谁 | `Vertex.Compute` |
| 超步 + 屏障 | 按超步推进,每步并行跑活跃顶点,步间屏障等齐 | `for step` + `taskManager.wait` |
| 消息 S->S+1 | S 步发的消息 S+1 步才收到,顶点间靠消息解耦 | `current`/`next` 邮箱交换 |
| 触发与终止 | 收到消息即激活;无在途消息即终止 | `len(current)==0` |

### 四机制图示

**图一:顶点为中心 -- 不写循环,只写每个顶点的 compute()**

```
  命令式(你写循环)                  Pregel(你写顶点,引擎写循环)
  ────────────────                  ───────────────────────────
  for !done {                       A.compute = 收到消息->算->发消息
    跑A()                            B.compute = 收到消息->算->发消息
    if ... { 跑B() }                 C.compute = 收到消息->算->发消息
    ...                             // 没有 for。何时调 A/B/C 由引擎决定
  }
```

**图二:超步时间轴(三顶点 A/B/C,消息在屏障间的"在途消息池"里传递)**

```
                A                 B                 C
                ─                 ─                 ─

 ▶ S0     ┌─────────┐
          │compute()│        idle              idle
          │ 初始消息 │
          │ 发->B,->C │
          └─────────┘
 ══════════════════ 屏障(barrier)═════════════════════════
   在途消息池:    [->B]  [->C]            ← S0 发出, S1 才送达
 ═════════════════════════════════════════════════════════
                          ▼                  ▼
 ▶ S1     idle      ┌─────────┐       ┌─────────┐
                    │compute()│       │compute()│   ◀ B、C 同时激活 = 并行
                    │ 收B消息 │       │ 收C消息 │
                    │ 发->C    │       │ halt ✓  │   ◀ C 处理完,投票停止
                    └─────────┘       └─────────┘
 ══════════════════ 屏障 ═════════════════════════════════
   在途消息池:           [->C]              ← B 发出, S2 送达
 ═════════════════════════════════════════════════════════
                                            ▼
 ▶ S2     idle       halt ✓         ┌─────────┐
                                    │compute()│   ◀ 收到B消息, 重新激活
                                    │ halt ✓  │
                                    └─────────┘
 ══════════════════ 屏障 ═════════════════════════════════
   在途消息池:    (空)
 ═════════════════════════════════════════════════════════

 ▶ S3    halt ✓     halt ✓          halt ✓      ◀ 全部 halt + 在途空
                                                       => END 计算结束
```

把四机制对到图上:

- **① 顶点为中心**:A/B/C 三列各有自己的 `compute()` 框,互不调用(见图一)。A 不知 B 何时跑,B 不知 C 何时跑。
- **② 超步 + 屏障**:`S0`/`S1`/`S2` 是三个 superstep,`═══屏障═══` 保证本步所有激活顶点全跑完、消息全入池才进下一步。S1 里 B、C **同一行同时跑**即"每轮并行"。
- **③ 消息 S -> S+1**:关键看**在途消息池**。S0 里 A 发的 `[->B][->C]` 不立刻到达,停在屏障间的池子里,**S1 开头才送达**(两个 ▼);B 在 S1 发的 `[->C]` 同样停到 S2 才到 C。顶点间从不直接调用,消息在池子里"隔一步"才被收到。
- **④ 触发与终止**:每个 ▼ 表示"收到消息才激活"--没收到消息的列为 `idle`;C 在 S1 处理完 `halt ✓`(投票停止),S2 又收到 B 消息故**重新激活**再 halt;到 S3 池子空 + 三顶点全 `halt ✓` => END。

> 循环不是写出来的,是"顶点互相发消息 + 引擎一轮轮调度"自然转出来的。完整概念拆解见 [`../pregel.md`](../pregel.md)。

## 一、它是什么

一份约 460 行的 Go 程序,把 Pregel 的核心浓缩成一个可 `go run` 的文件。它不是一个"裁剪版 eino",而是**用最小代码把 Pregel 四机制 + Compile 阶段 + 可中断屏障(taskManager)重新实现一遍**,让人能看清每个机制落在哪一行。

跑的是一个 mini-ReAct:一个模型顶点 + 两个工具顶点(search/calc),演示**有环循环(model↔tool)、同一超步多顶点并行、自然终止**。

## 二、运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/25_eino/03_graph/demo/03_pregel_compile
go run .
```

预期输出:

```
[compile] 检测到环: [model->search->model][calc->model->calc](Pregel 允许,继续编译)

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

=== 场景二:主动取消 ===
[compile] 无环

── superstep 0 ── 活跃顶点: [slow]
  [slow] 开始计算(睡 0.5s,但响应 ctx)...
  (主动 cancel())
  [slow] 被 ctx 取消,提前返回(in-flight Compute 被打断)
Run 返回错误(被取消): context canceled
```

`go vet` 通过,`go run -race` 无数据竞争。

## 三、三层解耦(设计的骨架)

唯一耦合是 `Message`:

```
Message  ── 纯数据(无 To,路由由声明决定),无行为
Vertex   ── 纯行为(Compute),无调度、不路由
Engine   ── 纯调度 + 编译,无业务行为
```

- `Vertex` 不知道 `Engine` 存在(签名里没 step、没 engine 引用)。
- `Engine` 不碰 `Vertex` 内部(只调 `Compute`)。
- 两边只通过 `Message` 通信。

这就是"顶点为中心"在类型层面的体现:顶点和引擎之间唯一的语言是消息。

## 四、三阶段流水线:Graph -> Compile -> Compiled

```
构建期(可变)             翻译期(一次性)            运行期(不可变,可反复)
──────────────           ──────────────            ──────────────────
g := NewGraph(20)        c, err := g.Compile()     c.Run(ctx, initial)
  g.AddVertex(...)         ├─ 结构校验               └─ for step { ... route ... }
  g.AddEdge(...)           ├─ findLoops(报告)
  g.AddBranch(...)         └─ 冻结 -> *Compiled
   Graph                    Compile                   Compiled
```

对应 eino 的 `graph`(构建)-> `graph.compile`(`graph.go:674`)-> `runner`(运行)。

### 4.1 `Graph` -- 构建期:可变的声明收集器

```go
type Graph struct {
    vertices map[string]Vertex
    edges    map[string][]string  // 普通边 from -> [to]
    branches map[string]*Branch   // 分支 from -> branch
    maxSteps int
}

func (g *Graph) AddVertex(v Vertex)
func (g *Graph) AddEdge(from, to string)
func (g *Graph) AddBranch(from string, b *Branch)
```

- **可变**:用户逐步声明拓扑,构建是探索性的。
- **只收集,不执行**:`Graph` **没有 `Run` 方法**,必须先 `Compile`。强制"声明归声明,执行归执行"。
- 对应 eino `graph`(`graph.go:57`):同样持 `nodes`/`edges`/`branches`,只 `AddXxx` 不能跑。

### 4.2 `Compile` -- 翻译期:一次性的桥

```go
func (g *Graph) Compile() (*Compiled, error) {
    // 1. 结构校验
    // 2. 环检测
    // 3. 冻结
}
```

"Compile" 即**编译**--借用编译器概念:不能直接跑源码(声明式拓扑),得先编译成可执行的东西(`*Compiled`)。它是构建期到运行期的一次性前置处理。**不跑图、不改图、不传数据**,只做"跑之前的准备"。

具体三步操作:

**① 结构校验**(把错误挡在运行前):遍历 `edges`/`branches`,检查每条边的源/目标、每个分支的 endNode 都是已注册顶点或 `START`/`END`,不合法就返回 error。

```go
for from, tos := range g.edges {
    if _, ok := g.vertices[from]; !ok && from != START {
        return nil, fmt.Errorf("edge source %q is not a registered vertex", from)
    }
    for _, to := range tos {
        if _, ok := g.vertices[to]; !ok && to != END {
            return nil, fmt.Errorf("edge target %q is not a registered vertex (from %q)", to, from)
        }
    }
}
// 分支同理:校验 from 与每个 endNode
```

**② 环检测**(编译期静态分析,两阶段,对应 eino `validateDAG` + `findLoops`):合并普通边 + 分支 endNodes 成后继表,然后:

- **阶段 1 Kahn 入度法**:入度 0 的节点不在环上,摘掉它并减后继入度;反复摘到摘不动,剩下入度仍 >0 的节点就是环上的(它们互相指着,入度永远降不到 0)。
- **阶段 2 路径 DFS**:从环上起点出发,后继已在当前路径上 = 环,提取环路径。

Pregel 允许环(ReAct 需要),所以**只报告不拒绝**。

```go
succ := g.successors()                       // 合并 edges + 分支 endNodes
if loops := findLoops(succ); len(loops) > 0 {
    fmt.Printf("[compile] 检测到环: %s(Pregel 允许,继续编译)\n", formatLoops(loops))
} else {
    fmt.Println("[compile] 无环")
}
```

**③ 冻结**(可变 -> 不可变):把校验过的字段打包成 `*Compiled` 返回,之后 `Run` 只读不改。

```go
return &Compiled{
    vertices: g.vertices, edges: g.edges, branches: g.branches, maxSteps: g.maxSteps,
}, nil
```

demo 调用 `Compile` 时实际发生:校验通过(demo 的边/分支目标都合法);`findLoops` 检测出 `[model->search->model]`、`[calc->model->calc]` 两个环并打印;冻结出一个 `*Compiled` 供 `Run`。

设计收益:

- **能失败**:坏拓扑(边指向不存在的顶点)在 `Compile` 就报错,不等到 `Run` 中途崩。
- **一次性工作放这儿**:环检测、校验只做一次,不每次 `Run` 重复。
- **强制前置**:必须 `Compile` 才能 `Run`(`Graph` 没有 `Run` 方法)。对应 eino 必须先 `graph.Compile()` 才能 `Invoke`。
- 环检测对应 eino 的 `validateDAG` + `findLoops`(`graph.go:1131`)--eino DAG 模式**拒绝**环,Pregel 模式不检测;demo 是 Pregel,**检测到也只报告**(演示 compile 能看穿结构)。

### 4.3 `Compiled` -- 运行期:不可变,可反复跑

```go
type Compiled struct {
    vertices map[string]Vertex
    edges    map[string][]string
    branches map[string]*Branch
    maxSteps int
}

func (c *Compiled) Run(ctx context.Context, initial Message) error
func (c *Compiled) route(id string, out Message) []string
```

- **不可变**:编译后拓扑不能改,防止"跑着跑着被改图"的 bug。
- **可反复 `Run`**:一次编译,多次运行。对应 eino 的 `Runnable` 可反复 `Invoke`/`Stream`。
- **`route` 是声明式路由的落点**:

```go
func (c *Compiled) route(id string, out Message) []string {
    if b, ok := c.branches[id]; ok {
        return b.Cond(out)   // 有分支:按产出值选 endNode(顶点不选)
    }
    return c.edges[id]       // 无分支:发往所有普通边后继
}
```

顶点只产值,**路由由编译进 `Compiled` 的声明决定**。这正是 eino"产值与路由分离"的体现:顶点产出 `*schema.Message`,声明的 `AddBranch` 按消息内容路由。

### 4.4 三者分开的收益

| 收益 | 体现 |
|---|---|
| 声明/执行分离 | `Graph` 可变只收集,`Compiled` 不可变才执行 |
| 校验前置 | 坏拓扑 `Compile` 报错,不进 `Run` |
| 一次性分析不重复 | 环检测、校验在 `Compile` 做,`Run` 只用结果 |
| 一次编译多次运行 | `Compiled` 可反复 `Run` |

## 五、核心类型逐一

### `Message` -- 纯数据

```go
type Message struct {
    ToolCalls []ToolCall // 模型要调的工具(模型产出时填)
    Results   []string   // 工具结果(工具产出时填)
    Answer    string     // 最终答案 / 用户问题
}
```

不带 `To`--路由由声明决定。对应 eino 里 `pregelChannel.Values` 中的一个值。

### `Vertex` -- 纯行为

```go
type Vertex interface {
    ID() string
    Compute(ctx context.Context, msgs []Message) Message
}
```

`Compute` 收到本超步投递给本顶点的全部消息,产出一个值。不写循环、不路由、不知道第几步。返回的 `Message` 没有"发给谁"的信息--那是 `route` 的事。**接 `ctx`**:顶点可 watch `ctx.Done()` 实现中途被打断(对应 eino 组件接 ctx,LLM 调用可被取消)。对应 eino `graphNode` + `composableRunnable.i`(类型擦除后的 compute())。

### `Branch` -- 声明式分支

```go
type Branch struct {
    Cond     func(Message) []string // 返回要发往的 endNode 列表(可多个 = 下一超步并行)
    EndNodes map[string]bool
}
```

`Cond` 是消息内容的纯函数,返回目标列表。返回多个 = 下一超步多顶点并行(对应 eino 的多路分支)。顶点的 `Compute` 碰不到 `Branch`--两边隔离。

## 六、五机制落点

| 机制 | demo 代码 | 对应 eino |
|---|---|---|
| ① 顶点为中心 | `Vertex.Compute` | `composableRunnable.i`(`runnable.go:46`) |
| ② 超步 + 屏障 | `for step` + `taskManager`(done 通道+计数+select) | `graph_run.go:241` + `taskManager.waitAll`(`graph_manager.go:415`) |
| ③ 消息 S->S+1 | `current`/`next` 邮箱,屏障处交换 | `pregelChannel.Values` 一步一清(`pregel.go:25`) |
| ④ 触发与终止 | `len(current)==0` + `maxSteps` | `getFromReadyChannels`(`graph_manager.go:189`)+ `maxRunSteps`(`graph.go:884`) |
| ⑤ Compile | `Graph.Compile` -> 校验 + `findLoops` + 冻结 | `graph.go:674` + `validateDAG` + `findLoops`(`graph.go:1131`) |

## 七、`Run` 循环详解:Pregel 语义的浓缩

```go
func (c *Compiled) Run(ctx context.Context, initial Message) error {
    current := map[string][]Message{}
    for _, to := range c.edges[START] {                // START 产出 initial,按声明投递
        current[to] = append(current[to], initial)
    }

    for step := 0; step < c.maxSteps; step++ {         // ② 超步计数器(只是个号)
        if len(current) == 0 { return nil }             // ④ 终止:无在途消息

        var tasks []*task
        for id, msgs := range current {                 // ④ 触发:有消息的顶点才跑
            if v, ok := c.vertices[id]; ok { tasks = append(tasks, &task{v: v, in: msgs}) }
        }
        tm := newTaskManager(len(tasks))
        tm.submit(ctx, tasks)
        if !tm.wait(ctx) { return ctx.Err() }           // ② 屏障:本步全完成才进下一步(可中断)

        next := map[string][]Message{}                  // ③ 在途消息池:S 发的,S+1 才送达
        for _, t := range tasks {                       // 串行路由(屏障后,无需锁)
            if t.err != nil { return t.err }            // 顶点 panic 等
            for _, to := range c.route(t.v.ID(), t.out) { // 声明式路由(顶点不选)
                if to == END { continue }
                next[to] = append(next[to], t.out)
            }
        }
        current = next                                  // ③ 交换:S 发的 = S+1 的接收
    }
    return nil
}
```

> 屏障用 `taskManager`(done 通道 + 计数 + `select`),非裸 `WaitGroup`:顶点 panic 被 `recover` 转成 error(不崩程序)、`ctx.Done()` 可取消/超时;路由移到 `wait` 之后串行做,**不需要 mutex**--并行只发生在 `Compute`(对应 eino:`execute` 并行 + `resolveCompletedTasks` 串行)。

三句话不变式:

1. **进入每轮**:`current` = 本超步各顶点应收到的全部消息
2. **轮内**:`next` = 本超步各顶点发出的全部消息(谁也不读它)
3. **轮末**:`current = next` = 把"发出的"变成"收到的"

第 3 句那一行 `current = next` = BSP 的"消息在 S 末投递、S+1 初送达"。整个 S->S+1 机制就是一个赋值。

`mu` 保护共享的 `next` map(多 goroutine 并发写,Go map 不并发安全);`wg` 是屏障,等本步全完成才进下一步。`Compute` 在锁外(真正并行),写 `next` 在锁内(串行收集)--"并行算 + 串行收"。

## 八、Demo:mini-ReAct

### 顶点

```go
type ModelVertex struct {
    step   int
    Answer string
}
func (m *ModelVertex) Compute(ctx context.Context, msgs []Message) Message {
    m.step++
    if m.step == 1 {
        return Message{ToolCalls: []ToolCall{   // 产出 tool calls,分支据此扇出到两个工具
            {Name: "search", Arg: "eino pregel"},
            {Name: "calc", Arg: "2+3"},
        }}
    }
    // 汇总工具结果,产出最终答案--分支据此路由到 END
    m.Answer = ...
    return Message{Answer: m.Answer}
}

type ToolVertex struct{ id, name string }
func (t *ToolVertex) Compute(ctx context.Context, msgs []Message) Message {
    // 收到模型消息(含全部 tool calls),只执行属于自己的那个
    for _, tc := range m.ToolCalls {
        if tc.Name == t.name { ... 执行 ... }
    }
    return Message{Results: results}
}

// SlowVertex 演示"主动取消":Compute 用 select 监听 ctx.Done(),取消时提前返回(in-flight 被打断)。
type SlowVertex struct{}
func (s *SlowVertex) Compute(ctx context.Context, msgs []Message) Message {
    select {
    case <-time.After(500 * time.Millisecond): return Message{}   // 正常完成
    case <-ctx.Done():                         return Message{}   // 取消时 in-flight 被打断
    }
}
```

### 声明式拓扑 + 运行

```go
g := NewGraph(20)
g.AddVertex(model)
g.AddVertex(&ToolVertex{id: "search", name: "search"})
g.AddVertex(&ToolVertex{id: "calc", name: "calc"})

g.AddEdge(START, "model")      // 用户问题 -> model
g.AddEdge("search", "model")
g.AddEdge("calc", "model")
g.AddBranch("model", &Branch{
    Cond: func(msg Message) []string {
        if len(msg.ToolCalls) > 0 { return []string{"search", "calc"} } // 有 tool call -> 两工具并行
        return []string{END}                                            // 否则 -> 结束
    },
    EndNodes: map[string]bool{"search": true, "calc": true, END: true},
})

c, _ := g.Compile()
c.Run(context.Background(), Message{Answer: "user question"})
```

### 执行轨迹

| 进入时 `current` | step | 谁活跃 | 产出 | 算出的 `next` |
|---|---|---|---|---|
| `{model:[用户问题]}` | 0 | model | ToolCalls=[search,calc] | `{search:[...], calc:[...]}` |
| `{search:[...], calc:[...]}` | 1 | search, calc(并行) | Results | `{model:[结果1,结果2]}` |
| `{model:[2条结果]}` | 2 | model | Answer | `{}`(路由到 END,沉淀) |
| `{}` | 3 | (空) | - | 终止 |

环 `model↔calc`(及 `model↔search`)在 `Compile` 期被检测到并报告;运行期由"分支扇出 + 工具回边"自然形成循环,代码里没有 `for`。

## 九、与 eino 的对应

| demo | eino | 说明 |
|---|---|---|
| `Graph`(edges/branches/vertices) | `graph`(`graph.go:57`) | 构建期声明式拓扑 |
| `Graph.Compile` -> `*Compiled` | `graph.compile` -> `*runner`(`graph.go:674`) | 翻译 + 校验 + 冻结 |
| `Compiled.edges`/`branches` | `chanSubscribeTo` + 前驱表(`graph.go:730/759`) | 运行期路由结构 |
| `findLoops`(报告) | `validateDAG` + `findLoops`(`graph.go:1131`) | 环检测(eino DAG 模式拒绝,Pregel 不检测) |
| `Branch.Cond` | `GraphBranch` condition(`branch.go`) | 声明式分支 |
| `route` | `calculateBranch` + `writeTo`/`writeToBranches`(`graph_run.go:866/828`) | 声明式路由 |
| `for step` + `taskManager` | `graph_run.go:241` + `taskManager`(`graph_manager.go:269`) | 超步 + 屏障(可中断) |
| `current`/`next` 交换 | `pregelChannel.Values` 一步一清(`pregel.go:25`) | 消息 S->S+1 |

## 十、诚实声明:demo 的边界

demo 是骨架,不是残缺的 eino。以下是**刻意省略**的生产特性(都不影响 Pregel 与 Compile 机制的演示):

- **单通道**:只有"值袋子"邮箱,无 eino 的 `dagChannel`(依赖追踪,DAG 模式用)。
- **无 State**:顶点私有状态在结构体里;eino 有跨顶点共享 State(`WithGenLocalState`)。
- **无 HITL 中断/恢复、无检查点、无回调、无流式**。(屏障已支持 `context` 取消/超时 + panic 恢复;**ctx 透传进 `Compute`,顶点 watch `ctx.Done()` 即可被中途打断 in-flight 计算**--见场景二。但 eino 的 `interruptBeforeNodes` 等人机交互暂停 + 检查点恢复仍没有。)
- **`maxSteps` 固定 int**:eino 默认 `节点数+10` + 运行期可覆盖。
- **环检测只报告不拒绝**:Pregel 允许环(ReAct 需要)。
- **Compile 翻译较轻**:demo 的 `Compiled` 字段与 `Graph` 几乎相同,`Compile` 主要是校验 + 冻结;eino 的 compile 会把 `edges` 深度转成 `chanSubscribeTo` + 前驱表 + 通道构造器(需双通道、类型擦除等更多机制)。

### 这些特性本该挂在哪(扩展点)

| 砍掉的 eino 能力 | 它本该挂在 demo 的哪里 |
|---|---|
| 中断/恢复 | `tm.wait` 之后、`current=next` 之前(eino 的 interruptBefore/After 插在屏障与下一步之间) |
| 检查点 | 每个超步的 `current` 快照即可持久化 |
| 共享 State | `Compiled` 持一份 + `Compute` 签名透传 |
| DAG 通道 | 第二种 channel 实现 |
| 动态 maxSteps | `NewGraph(20)` 换成按 `len(vertices)+10` 算 + 运行期覆盖 |

## 十一、一句话

这份 demo = **三层解耦(Message 数据 / Vertex 行为 / Engine 调度)+ 三阶段流水线(Graph 构建 -> Compile 翻译 -> Compiled 运行)+ 两个邮箱(current 收 / next 发)+ 一个交换(`current=next`)+ 一个屏障(`taskManager.wait`)**。Pregel 四机制 + Compile 全部从这些要素里长出来。最该盯的一行是 `current = next`--它一行承载了"消息 S->S+1",屏障在前、新超步在后,整个 BSP 节奏压在这一行两侧。
