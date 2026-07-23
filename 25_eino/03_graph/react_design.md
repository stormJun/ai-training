# ReAct 设计深读:带环图怎么拼出来

> 源码:`/Users/songxijun/workspace/otherProject/eino/flow/agent/react/react.go`(经典版)、`/Users/songxijun/workspace/otherProject/eino/adk/react.go`(ADK 生产版)
> 配套:[react_agent.md](./react_agent.md)(用法 + 基本机制 + 示例)、[pregel.md](./pregel.md)(驱动它的 Pregel 引擎)
>
> 本文聚焦**设计内部**:ReAct 的带环图怎么拼、状态怎么累积、分支怎么决策、ADK 版多了什么。不讲用法(见 react_agent.md)。

## 0. 一句话定位

eino 的 ReAct 不是一段 `for` 循环代码,而是**"`ChatModel` 节点 + `ToolsNode` 节点 + 两个分支 + `state` 对话历史"拼出的一张 Pregel 驱动的带环图**。循环由引擎迭代,业务代码零 `for`。和我们 demo 那套 Pregel 引擎是同一个机制的真实应用--顶点换成真 LLM 和真工具、状态换成共享 `state`、分支条件换成"消息里有没有 ToolCall"。

## 1. 核心思想:ReAct = 带环图

ReAct 的 think-act 循环(模型推理 -> 有工具调用就执行 -> 回模型继续)是个环。eino 把它建成图:

```
START ──▶ chat ──分支①──▶ tools ──分支②──▶ chat   (回环)
              │                │
              └──▶ END         └──▶ direct_return ──▶ END
```

两个节点 + 两个分支构成环,迭代由 Pregel superstep 引擎跑(`AnyPredecessor` + `MaxStep` 兜底)。这正是 [pregel.md](./pregel.md) 讲的"有环图 + superstep"的真实落地。

## 2. 配置与状态

### 2.1 `AgentConfig`(`react.go:136`)

```go
type AgentConfig struct {
    ToolCallingModel    model.ToolCallingChatModel        // 带工具调用能力的模型
    ToolsConfig         compose.ToolsNodeConfig           // 工具节点配置
    MessageModifier     MessageModifier                   // 模型前改写输入(如加 system prompt)
    MessageRewriter     MessageModifier                   // 改写 state 历史(如压缩上下文)
    MaxStep             int                               // 步数上限(默认 12)
    ToolReturnDirectly  map[string]struct{}               // 这些工具的结果直接作为最终答案
    StreamToolCallChecker func(ctx, sr) (bool, error)     // 流式下判断模型输出是否含工具调用
    ...
}
```

### 2.2 `state`--循环的"记忆"(`react.go:56`)

```go
type state struct {
    Messages                 []*schema.Message  // 跨超步累积的完整对话历史
    ReturnDirectlyToolCallID string             // 命中"直接返回"的工具调用 ID
}
```

`state.Messages` 是 ReAct 的关键:每轮模型调用都看到之前所有消息(用户问题 + 模型回复 + 工具结果)。靠 `WithGenLocalState` 挂一份 per-run 状态(`react.go:329`),注册名 `_eino_react_state`(`react.go:62`)以支持检查点序列化。

## 3. 图的构建(`NewAgent`,`react.go:284`)

```go
graph := compose.NewGraph[[]*schema.Message, *schema.Message](
    compose.WithGenLocalState(func(ctx) *state { return &state{Messages: ...} }))

// ① 模型节点:StatePreHandler 在模型前把输入累积进 state.Messages
graph.AddChatModelNode("chat", chatModel, compose.WithStatePreHandler(modelPreHandle))  // :349
graph.AddEdge(compose.START, "chat")                                                    // :353

// ② 工具节点:StatePreHandler 把模型回复累积进 state,记下 ReturnDirectlyToolCallID
graph.AddToolsNode("tools", toolsNode, compose.WithStatePreHandler(toolsNodePreHandle)) // :365

// ③ 模型后分支:有 ToolCall -> tools,无 -> END
graph.AddBranch("chat", compose.NewStreamGraphBranch(modelPostBranchCondition, {tools, END})) // :378

// ④ 工具后分支:命中直接返回 -> direct_return,否则 -> chat(回环)
buildReturnDirectly(graph)                                                              // :382

// ⑤ 编译:Pregel 模式 + 步数兜底
runnable, _ := graph.Compile(ctx,
    compose.WithMaxRunSteps(config.MaxStep),
    compose.WithNodeTriggerMode(compose.AnyPredecessor),
    compose.WithGraphName(graphName))                                                   // :386
```

### 消息怎么在循环中累积(关键)

靠两个 `StatePreHandler`:

- `modelPreHandle`(`react.go:333`):把输入(用户问题或工具结果)append 进 `state.Messages`,跑 `MessageRewriter`/`MessageModifier`,再把**完整历史**喂给模型。
- `toolsNodePreHandle`(`react.go:357`):把模型这条带 ToolCall 的 assistant 消息 append 进 state,并按配置设置 `ReturnDirectlyToolCallID`。

所以模型每轮看到的是不断增长的对话--靠 state 传递,不是节点间直传。

## 4. 两个分支:agent 的决策点

### 分支①(模型后,`react.go:369`):有没有 ToolCall

```go
modelPostBranchCondition := func(ctx, sr *StreamReader[*schema.Message]) (string, error) {
    if isToolCall, _ := toolCallChecker(ctx, sr); isToolCall { return "tools", nil }
    return compose.END, nil
}
```

### 分支②(工具后,`react.go:428`):有没有命中"直接返回"

```go
// state.ReturnDirectlyToolCallID 非空 -> direct_return;否则 -> chat(回环)
```

`buildReturnDirectly`(`react.go:399`)加 `direct_return` Lambda:从多条工具消息里挑出 `ReturnDirectlyToolCallID` 对应那条作为最终答案,再 `-> END`。

## 5. 关键机制

### 5.1 `StreamToolCallChecker`:流式下怎么判"有没有工具调用"

不同模型流式输出 ToolCall 的方式不同(OpenAI 先吐 ToolCall;Claude 先吐文本再吐 ToolCall)。所以分支①的条件做成**可插拔**(`react.go:179`),默认 `firstChunkStreamToolCallChecker`(`react.go:218`)只看第一个非空 chunk。文档明确警告默认实现对 Claude 不好使,需自定义 checker。

### 5.2 `toolResultCollectorMiddleware`:工具结果双路分发

`newToolResultCollectorMiddleware()`(`react.go:65`)是个 `ToolMiddleware`,prepend 进 `ToolsConfig.ToolCallMiddlewares`(`react.go:320`)。它从 ctx 读 `toolResultSenders`,把每个工具结果(工具名、callID、结果)转发给发送方。

作用:工具结果**既作为消息回流进图循环,又作为事件外发给调用方**(可观测/流式事件),两条路径解耦。四种工具形态(Invokable/Streamable/Enhanced×2)各有对应 middleware 分支。

### 5.3 `ToolReturnDirectly` / `SetReturnDirectly`:工具结果即最终答案

两种触发:

- **配置式**:`AgentConfig.ToolReturnDirectly`(`react.go:164`),`getReturnDirectlyToolCallID`(`react.go:465`)扫描模型 ToolCalls,命中则在 `toolsNodePreHandle` 记 callID。
- **运行时式**:`SetReturnDirectly(ctx)`(`react.go:254`)--工具执行体内可调,经 `compose.ProcessState` 写 state,优先级高于配置。

### 5.4 `MaxStep` 兜底

`WithMaxRunSteps(config.MaxStep)`(默认 12 = 节点数 2 + 10)。Pregel 的死循环防护--模型若一直要调工具,到上限报错。

## 6. `Agent` 接口与可组合

```go
type Agent struct {
    runnable compose.Runnable[[]*schema.Message, *schema.Message]
    graph    *compose.Graph[...]
    ...
}
```

- `Generate`/`Stream`(`react.go:480/485`)就是 `runnable.Invoke/Stream`。
- `ExportGraph`(`react.go:490`)导出图 + 编译选项,可作子图嵌入更大的图--**agent 可组合性**,是多智能体编排的基础。

## 7. ADK 版(`adk/react.go`)多了什么

`newReact`(`adk/react.go:354`)同款环,但图更丰富、面向生产:

```
START -> Init -> ChatModel ─branch─▶ {terminal, CancelCheck -> ToolNode -> AfterToolCalls
                                          -> AfterToolCallsCancelCheck ─branch─▶ {ChatModel, ToolNodeToEndConverter -> terminal}}
```

相对经典版的增强:

| 增强 | 位置 | 作用 |
|---|---|---|
| **泛型化** | `typedState[M]`/`typedReactConfig[M]`(`:35/:291`),M = `*schema.Message` 或 `*schema.AgenticMessage` | 一套代码支撑普通 agent 与多智能体消息;`newReact` 与 `newAgenticReact` 两个构造器 |
| **迭代预算** | ChatModel 的 StatePreHandler 里 `decrementRemainingIterations`,耗尽返 `ErrExceedMaxIterations`(`:33`) | 替代图级 MaxStep,默认 20(`:345`) |
| **取消安全点** | `CancelCheck`(`:399`)、`AfterToolCallsCancelCheck`(`:473`) | 配合 `CancelMode` 在"模型后/工具后"安全边界取消 |
| **AfterToolCalls 节点** | `:442` | 持久化工具结果到 state、对齐消息 ID、触发 after-tool-calls 钩子 |
| **afterAgentFunc** | `:488` | 可选终态节点,成功结束时运行 |
| **检查点向后兼容** | `init()`(`:77`)v0.7/v0.8 双纪元、`stateV080.GobDecode`(`:215`) | 跨版本检查点迁移 |
| **Agentic 扩展** | `ToolGenActions`/`ToolMsgIDs`/`DeferredToolInfos`/`ReturnDirectlyEvent`(`:41-56`) | 多智能体交接、延迟工具检索 |

ADK 版被 `ChatModelAgent` 包裹,再叠回调、事件、重试、failover,是面向生产的那层。

## 8. 设计哲学小结

1. **ReAct = 带环图,非循环体**。复用 Pregel 引擎,工具执行/流式/中断/检查点全白拿。
2. **状态即记忆**。`state.Messages` 累积对话,`StatePreHandler` 每轮累积并喂模型。
3. **分支是决策点**。"要不要调工具""要不要直接返回"都表达成图分支,可插拔(`StreamToolCallChecker`)。
4. **可组合**。`ExportGraph` 让 agent 当子图嵌进更大的图,是多智能体编排的基础。
5. **经典版教学、ADK 版生产**。同构,ADK 加泛型/取消安全点/迭代预算/检查点兼容/多智能体扩展。

## 9. 源码索引

| 主题 | 经典版 `flow/agent/react/react.go` | ADK 版 `adk/react.go` |
|---|---|---|
| 配置 | `AgentConfig` `:136` | `typedReactConfig` `:291` |
| 状态 | `state` `:56` | `typedState` `:35` |
| 构图 | `NewAgent` `:284` | `newReact` `:354` |
| 模型前累积 | `modelPreHandle` `:333` | `:387` |
| 工具前累积 | `toolsNodePreHandle` `:357` | `toolPreHandle` `:412` |
| 模型后分支 | `modelPostBranchCondition` `:369` | `toolCallCheck` `:496` |
| 工具后分支/直接返回 | `buildReturnDirectly` `:399` | `:520`(ToolNodeToEndConverter) |
| 流式 tool call 检测 | `StreamToolCallChecker` `:179`、`firstChunkStreamToolCallChecker` `:218` | `toolCallCheck` `:496` |
| 工具结果中间件 | `newToolResultCollectorMiddleware` `:65` | (上层事件机制) |
| 直接返回 | `SetReturnDirectly` `:254`、`getReturnDirectlyToolCallID` `:465` | `getReturnDirectlyToolCallID` `:328` |
| 步数/迭代 | `MaxStep` `:159` | `RemainingIterations` `:53`、`ErrExceedMaxIterations` `:33` |
| 取消安全点 | -- | `CancelCheck` `:399`、`AfterToolCallsCancelCheck` `:473` |
| 检查点兼容 | `schema.RegisterName[*state]` `:62` | `init()` `:77`、`stateV080` `:215` |
| 接口 | `Agent` `:273`、`Generate/Stream` `:480/485`、`ExportGraph` `:490` | (由 `ChatModelAgent` 包裹) |

## 10. 参考

- 用法与示例:[react_agent.md](./react_agent.md)
- 另一种 agent 模式:[planexecute_design.md](./planexecute_design.md)(Plan-and-Execute)
- 驱动引擎:[pregel.md](./pregel.md)、[state_pregel.md](./state_pregel.md)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/flow/agent/react`、`/Users/songxijun/workspace/otherProject/eino/adk/react.go`
