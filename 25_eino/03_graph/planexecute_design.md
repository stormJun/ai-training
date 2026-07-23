# Plan-and-Execute 设计深读:规划-执行-重规划

> 源码:`/Users/songxijun/workspace/otherProject/eino/adk/prebuilt/planexecute/plan_execute.go`(880 行)
> 配套:[react_design.md](./react_design.md)(ReAct,另一种 agent 模式)、[pregel.md](./pregel.md)(底层驱动引擎)
>
> 本文聚焦**设计内部**:Plan-and-Execute 的三角色怎么分工、怎么用 ADK 多智能体原语拼出来、Plan 怎么可插拔、与 ReAct 的区别。

## 0. 一句话定位

eino 的 Plan-and-Execute 是 `adk/prebuilt` 里的一个**预置 agent**,结构是 `SequentialAgent(Planner, LoopAgent(Executor, Replanner))`:Planner 一次性出多步计划,Executor 执行第一步(自己是个带工具的 ReAct agent),Replanner 看进度决定"修订计划"或"收尾",循环到完成。它建在 ADK 多智能体组合原语上(底层仍编译成 Pregel 图),和 ReAct 是互补的两种 agent 模式。

## 1. 核心思想:先规划,再执行-重规划循环

ReAct 是"每步即时思考、无前瞻"的 reactive 模式。Plan-and-Execute 不同:

1. **Planning**:先把用户问题拆成多步结构化计划。
2. **Execution**:执行计划的第一步(可复杂,内部可多轮工具)。
3. **Replanning**:每步执行后评估进度,要么修订后续计划,要么给出最终答案。

适合步骤较明确、可拆分的长任务。循环由 `LoopAgent` 驱动,不写 `for`。

## 2. 三角色

### 2.1 Planner(规划,`NewPlanner` `:437`)

接收用户输入,产出结构化 `Plan`。`PlannerConfig`(`:260`)支持两种产 Plan 的方式:

```go
type PlannerConfig struct {
    ChatModelWithFormattedOutput model.BaseChatModel     // 结构化输出模型,直接产 Plan JSON
    ToolCallingChatModel         model.ToolCallingChatModel // 或工具调用模型
    ToolInfo                     *schema.ToolInfo        // tool-call 时的 Plan schema(默认 PlanToolInfo)
    GenInputFn                   GenPlannerModelInputFn  // 用户输入 -> planner 输入
    NewPlan                      NewPlan                 // 自定义 Plan 工厂
}
```

二选一:要么用支持结构化输出的模型直接吐 Plan,要么用工具调用模型调一个 `plan` 工具(默认 `PlanToolInfo`,`:113`)产出 Plan。

### 2.2 Executor(执行,`NewExecutor` `:510`)

执行 Plan 的**第一步**。它本身是个**完整 agent**(模型 + 工具,自带 ReAct 循环):

```go
type ExecutorConfig struct {
    Model         model.BaseChatModel   // 执行用模型(若用工具须支持 WithTools)
    ToolsConfig   adk.ToolsConfig       // 可用工具
    MaxIterations int                    // 执行器内部 ReAct 上限(默认 20,:497)
    GenInputFn    GenModelInputFn        // ExecutionContext -> 执行器输入
}
```

所以"执行一步"可能内部跑多轮工具调用(ReAct)。执行完产出 `ExecutedStep{Step, Result}`(`:504`)。

### 2.3 Replanner(重规划,`NewReplanner` `:807`)

每次执行后,看 `ExecutionContext` 评估进度。它用**两个工具**让模型决定下一步:

```go
type ReplannerConfig struct {
    ChatModel   model.ToolCallingChatModel  // 工具调用模型
    PlanTool    *schema.ToolInfo            // 调它 = 修订计划(给后续步骤)
    RespondTool *schema.ToolInfo            // 调它 = 给最终答案,收尾
    GenInputFn  GenModelInputFn
    NewPlan     NewPlan
}
```

模型调 `PlanTool` -> 产出新 Plan(继续循环);调 `RespondTool` -> 产出 `Response`(`:104`,最终答案,结束)。**用"调哪个工具"表达"继续 or 收尾"**,很巧妙。

## 3. 拓扑:Sequential(Planner -> Loop[Executor, Replanner])

`New`(`:862`)把三角色拼起来:

```go
func New(ctx, cfg *Config) (adk.ResumableAgent, error) {
    loop, _ := adk.NewLoopAgent(ctx, &adk.LoopAgentConfig{
        Name:          "execute_replan",
        SubAgents:     []adk.Agent{cfg.Executor, cfg.Replanner},  // 执行 -> 重规划,循环
        MaxIterations: maxIterations,                              // 默认 10
    })
    return adk.NewSequentialAgent(ctx, &adk.SequentialAgentConfig{
        Name:      "plan_execute_replan",
        SubAgents: []adk.Agent{cfg.Planner, loop},                 // 先规划,再进入 execute-replan 循环
    })
}
```

```
Planner ──▶ ┌─ Executor ──▶ Replanner ─┐  (Loop, 最多 MaxIterations 轮)
            └──────────────────────────┘
```

- **SequentialAgent**:Planner 跑一次,然后进 Loop。
- **LoopAgent**:Executor -> Replanner 重复,直到 Replanner 调 RespondTool(收尾)或撞 `MaxIterations`。

`Config`(`:838`):

```go
type Config struct {
    Planner       adk.Agent  // 用 NewPlanner 创建
    Executor      adk.Agent  // 用 NewExecutor 创建
    Replanner     adk.Agent  // 用 NewReplanner 创建
    MaxIterations int         // execute-replan 循环上限(默认 10,:853)
}
```

## 4. Plan 与 Response:可序列化、可插拔

### `Plan` 接口(`:45`)

```go
type Plan interface {
    FirstStep() string        // 取第一步去执行
    json.Marshaler            // 可序列化(能塞进 prompt)
    json.Unmarshaler          // 可从模型结构化输出/tool call 反序列化
}
```

默认实现 `defaultPlan{Steps []string}`(`:77`)--有序步骤列表。`NewPlan`(`:58`)是工厂函数类型,可插自定义 Plan(只要能 JSON 序列化)。

### `Response`(`:104`)

```go
type Response struct {
    Response string `json:"response"`  // 最终答案
}
```

Replanner 调 `RespondTool` 时产出,作为整个 agent 的最终输出。

## 5. ExecutionContext:跨角色状态

```go
type ExecutionContext struct {
    UserInput     []adk.Message    // 用户原始问题
    Plan          Plan             // 当前计划
    ExecutedSteps []ExecutedStep   // 已执行步骤 + 结果
}
```

`GenModelInputFn`(`:482`)/`GenPlannerModelInputFn`(`:285`)负责把 `ExecutionContext` 拼成各角色的模型输入消息(可自定义,有默认实现)。Executor 据当前 Plan 的第一步执行;Replanner 看 Plan + 已执行步骤决定继续或收尾。状态在角色间靠这个结构流转。

## 6. 关键设计点

1. **建在 ADK 多智能体原语上,不手写图**。用 `SequentialAgent` + `LoopAgent` 组合,三角色都是 `adk.Agent`。底层这些 agent 仍编译成 `compose.Graph`(Pregel 驱动),但 Plan-and-Execute 这一层是更高抽象--组合现成 agent。

2. **Executor 自己是 agent**。执行一步不是单次工具调用,而是带工具的 ReAct 子循环(`MaxIterations` 默认 20)。每步执行本身可以很复杂。

3. **Replanner 双工具决策**。用 `PlanTool`(继续)/`RespondTool`(收尾)两个工具,让模型用"调哪个工具"表达决策--比解析自由文本判断"是否完成"更可靠。

4. **Plan 可插拔**。`Plan` 接口 + JSON + `NewPlan` 工厂,默认 `defaultPlan{Steps []string}`,可换自定义结构(只要模型能产出对应 JSON)。

5. **Planner 双模式产 Plan**。结构化输出模型 OR 工具调用模型,二选一,适配不同模型能力。

6. **返回 `adk.ResumableAgent`**。整个 plan-execute-replan **可中断恢复**(配合 HITL/检查点)--ADK 层的能力,执行到一半能暂停等人审批再续。

7. **两层 MaxIterations**:`Config.MaxIterations`(execute-replan 循环,默认 10)+ `ExecutorConfig.MaxIterations`(执行器内部 ReAct,默认 20)。

## 7. 与 ReAct 对比

| | ReAct | Plan-and-Execute |
|---|---|---|
| 规划 | 每步即时思考,无前瞻 | 先一次性规划多步 |
| 执行 | 一步一思考,reactive | 按计划执行,每步后重规划 |
| 适合 | 探索性、步骤不确定 | 步骤较明确、可拆分的长任务 |
| 拓扑 | ChatModel+Tools 两节点带环图 | SequentialAgent + LoopAgent 组合三 agent |
| 决策点 | 分支"有无 ToolCall" | Replanner 双工具"继续 or 收尾" |
| eino 位置 | `flow/agent/react`、`adk/react` | `adk/prebuilt/planexecute` |
| 文档 | [react_design.md](./react_design.md) | 本文 |

## 8. 与 LangChain Plan-and-Execute 对比

同源模式(Planner -> Executor -> Replanner 循环),差异在实现层:

- **LangChain**:LangGraph 图(planner/executor/replanner 节点 + 边)。
- **eino**:ADK 多智能体组合(`SequentialAgent`+`LoopAgent`),底层仍编译成 Pregel 图。更高一层抽象,三角色都是 `adk.Agent`,可独立替换/嵌套。
- **Plan 结构**:eino 用 `Plan` 接口(JSON 序列化,可插拔);LangChain 常用 Pydantic schema。
- **Executor**:eino 的执行器是完整 agent(带工具 ReACT);LangChain 的执行器常是单 agent/tool。
- **Replanner 决策**:eino 用双工具(PlanTool/RespondTool);LangChain 常解析结构化输出判断 action 类型。

## 9. 设计哲学小结

1. **模式即组合**。Plan-and-Execute 不是新引擎,而是用 `Sequential`+`Loop` 两个原语组合三角色--复用 ADK 的多智能体编排,不重复造调度。
2. **职责分离**。规划(Planner)、执行(Executor)、评估重规划(Replanner)三个 agent 各司其职,可独立替换/定制。
3. **结构化通信**。角色间靠 `Plan`(JSON)和 `ExecutionContext` 传状态,不靠自由文本;Replanner 用双工具做决策,可靠可解析。
4. **可插拔**。`Plan` 接口、`NewPlan` 工厂、`GenInputFn` 都可定制,适配不同模型和业务。
5. **底层仍 Pregel**。ADK agent 编译成 `compose.Graph`,所以 Plan-and-Execute 也白拿流式、中断、检查点、回调--和 ReAct 同一套底层红利。

## 10. 源码索引

| 主题 | 位置(`plan_execute.go`) |
|---|---|
| Plan 接口 | `:45` |
| defaultPlan(默认实现) | `:77` |
| Response(最终答案) | `:104` |
| PlanToolInfo(plan 工具 schema) | `:113` |
| PlannerConfig / NewPlanner | `:260` / `:437` |
| GenPlannerModelInputFn | `:285` |
| ExecutionContext(跨角色状态) | `:475` |
| GenModelInputFn | `:482` |
| ExecutorConfig / ExecutedStep / NewExecutor | `:485` / `:504` / `:510` |
| ReplannerConfig / NewReplanner | `:595` / `:807` |
| Config / New(顶层拼装) | `:838` / `:862` |
| MaxIterations(循环/执行器) | `:853`(默认 10)/ `:497`(默认 20) |

## 11. 参考

- 配套 agent 模式:[react_design.md](./react_design.md)
- 底层引擎:[pregel.md](./pregel.md)、[state_pregel.md](./state_pregel.md)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/adk/prebuilt/planexecute`
- eino-ext 结构化输出示例:https://github.com/cloudwego/eino-ext/blob/main/components/model/openai/examples/structured/structured.go
