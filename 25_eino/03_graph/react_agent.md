# ReAct Agent:让框架自动跑工具调用循环

> 源码:`/Users/songxijun/workspace/otherProject/eino/flow/agent/react/react.go`
> 可运行 demo:[`../02_components/demo/react_demo/`](../02_components/demo/react_demo/)
> 本文是"用手写 ReAct 循环换取框架自动驱动"的切入点。设计内部深读见 [`react_design.md`](./react_design.md)。

## 一、概述

`flow/agent/react` 提供一个 **ReAct agent** 抽象:把 ChatModel + 工具交给 `react.NewAgent`,框架**自动驱动**"模型推理 -> 调工具 -> 回传结果 -> 再推理"的循环,直到模型不再调用工具、给出最终回复。

类型定义(`react.go:261`):

```go
// Agent is the ReAct agent.
// ReAct will call the chat model, if the message contains tool calls, it will call the tools.
// otherwise, ReAct will continue to call the chat model until the message contains no tool calls.
type Agent struct {
    runnable compose.Runnable[[]*schema.Message, *schema.Message]
    graph    *compose.Graph[[]*schema.Message, *schema.Message]
    ...
}
```

`Agent` 内部持有一个 `compose.Graph`,本质是编排层产物。

## 二、为什么需要 agent 抽象:有环循环

工具调用智能体的核心循环是**有环**的:

```
        ┌─── 有 ToolCall ───▶ ToolsNode ───┐
        │                                     │
ChatModel ◀──────────────────────────────────┘ (回到模型，带工具结果)
        │
        └──── 无 ToolCall ────▶ END（最终回复）
```

这是循环,不是 DAG。用裸 Graph 手写需要自行处理:

1. 用 Pregel 状态累积对话历史(`state.go`)。
2. 在模型节点后接分支(`NewGraphBranch`),按 `resp.ToolCalls` 是否为空决定回 tools 还是 END。
3. 设 `MaxStep` 防止死循环。

`react.NewAgent` 把这三件事封装好,调用方无需手写。对比 [`../02_components/demo/tool_demo/`](../02_components/demo/tool_demo/) 里手写的 ~40 行循环,agent 把它压成两行。

## 三、`react.NewAgent` 与 `AgentConfig`

```go
// react.go:284
func NewAgent(ctx context.Context, config *AgentConfig) (*Agent, error)

// react.go:135
type AgentConfig struct {
    ToolCallingModel model.ToolCallingChatModel  // 推荐：支持 WithTools 的模型
    Model            model.ChatModel             // 已弃用：用 ToolCallingModel
    ToolsConfig      compose.ToolsNodeConfig     // 工具节点配置
    MessageModifier  MessageModifier             // 调用模型前改写输入（如加 system prompt）
    MessageRewriter  MessageModifier             // 改写 state 中的历史（如压缩上下文）
    MaxStep          int                          // 最大步数，默认 12（pregel: 节点数+10）
    ToolReturnDirectly map[string]struct{}        // 调用即返回的工具
    StreamToolCallChecker func(...) (bool, error) // 流式下判断是否有 tool call
    ...
}
```

最小配置只需两个字段:

```go
agent, err := react.NewAgent(ctx, &react.AgentConfig{
    ToolCallingModel: chatModel,                          // 模型
    ToolsConfig: compose.ToolsNodeConfig{
        Tools: []tool.BaseTool{weatherTool},              // 工具列表
    },
})
```

- **`ToolCallingModel`**(`react.go:139`)--类型为 `model.ToolCallingChatModel`(即具备 `WithTools` 方法的模型,见 [`../02_components/chat_model.md`](../02_components/chat_model.md) §4.2)。`ark.ChatModel` 实现了该接口(`chatmodel.go:34` 断言、`:450` 方法)。
- **`ToolsConfig.Tools`**(`tool_node.go:185`)--`[]tool.BaseTool`,工具需实现 `InvokableTool` 或 `StreamableTool`(见 [`../02_components/tool.md`](../02_components/tool.md) §2)。

调用:

```go
// react.go:480
func (r *Agent) Generate(ctx, input []*schema.Message, opts ...) (*schema.Message, error)
// react.go:485
func (r *Agent) Stream(ctx, input []*schema.Message, opts ...) (*schema.StreamReader[*schema.Message], error)
```

## 四、内部机制:Pregel 驱动的 Graph

`NewAgent` 内部构建一个 Graph,两个核心节点(`react.go:128`):

```go
const (
    nodeKeyTools = "tools"  // ToolsNode：执行工具
    nodeKeyModel = "chat"   // ChatModel：推理
)
```

执行流程(Pregel 迭代):

1. 调用 ChatModel(带工具绑定),产出含 `ToolCalls` 的消息。
2. 模型节点后接**分支条件**(`react.go:369` 的 `modelPostBranchCondition`):检查 `ToolCalls` 是否为空。
3. 非空 -> 路由到 ToolsNode,执行工具,结果作为 tool 消息累积进 state,回到步骤 1。
4. 为空 -> 路由到 END,返回最终消息。
5. `MaxStep`(默认 12,`react.go:159`)限制最大迭代轮次,防止死循环。

> 关键:**循环由 Pregel 的迭代语义驱动**,不是手写的 for 循环。state 跨轮累积对话历史(含 tool 消息),使模型每轮都能看到完整上下文。

## 五、完整示例

[`../02_components/demo/react_demo/`](../02_components/demo/react_demo/) 用真实 Ark 模型跑通:

```go
// 1. 构造 ToolCallingChatModel（ark.ChatModel 实现该接口）
chatModel, _ := buildToolCallingModel(ctx)

// 2. 创建天气工具
weatherTool, _ := utils.InferTool("get_weather", "查询指定城市的天气", getWeather)

// 3. 一行配置构建 ReAct agent
agent, err := react.NewAgent(ctx, &react.AgentConfig{
    ToolCallingModel: chatModel,
    ToolsConfig: compose.ToolsNodeConfig{
        Tools: []tool.BaseTool{weatherTool},
    },
})

// 4. 提问，agent 自动跑循环
resp, err := agent.Generate(ctx, []*schema.Message{
    schema.UserMessage("北京今天天气怎么样？请用工具查询后回答。"),
})
fmt.Println(resp.Content)
```

实测输出:

```
最终回复: 根据查询结果，北京今天的天气为晴，气温28摄氏度。
```

agent 内部自主完成:决策调 `get_weather` -> 执行 -> 回传 -> 基于结果生成最终回复。调用方看不到循环细节。

## 六、`AgentConfig` 关键字段

| 字段 | 作用 |
|---|---|
| `ToolCallingModel`(`:139`) | 推荐的模型字段,需实现 `WithTools` |
| `ToolsConfig`(`:145`) | 工具节点配置,`Tools []tool.BaseTool` |
| `MaxStep`(`:160`) | 最大迭代步数,默认 12(防止死循环) |
| `ToolReturnDirectly`(`:164`) | 指定某些工具被调用时直接返回结果,不再回模型 |
| `MessageModifier`(`:149`) | 调模型前改写输入,如注入 system prompt(注:`NewPersonaModifier` 已弃用,建议直接在输入里带 system 消息) |
| `MessageRewriter`(`:156`) | 改写 state 中的历史,如压缩超长上下文 |
| `StreamToolCallChecker`(`:179`) | 流式模式下判断 chunk 是否含 tool call。默认只查首块,**Claude 等先出文本后出 tool call 的模型需自定义** |

`ToolReturnDirectly` 的典型用途:某些工具(如"结束对话")的结果就是最终答案,无需再让模型加工。也可在工具内部调用 `react.SetReturnDirectly(ctx)`(`react.go:254`)动态触发。

## 七、与手写循环对比

| | `tool_demo`(手写) | `react_demo`(agent) |
|---|---|---|
| 循环 | 自己写 `for` + 检测 `ToolCalls` + 执行 + 回传 | 框架自动(Pregel) |
| 状态管理 | 自己 append `msgs` | state 自动累积 |
| 步数限制 | 自己设 `maxRounds` | `MaxStep`(默认 12) |
| 工具绑定 | 每轮 `model.WithTools` | `WithTools` 一次(模型节点固定) |
| 代码量 | ~40 行循环 | `NewAgent` + `Generate` 两行 |
| 适用 | 讲清机制 | 生产 |

手写版的价值在于**看清机制**;agent 版的价值在于**生产可用**。两者对照阅读,能理解 ToolsNode/Agent 内部到底做了什么。

## 八、与 ADK ChatModelAgent 的关系

`flow/agent/react` 是编排/flow 层的 ReAct agent,直接基于 compose.Graph + Pregel,贴近机制。

ADK 层的 `adk.ChatModelAgent`(`adk/chatmodel.go`)是更高层封装,额外提供:

- 中间件链(`adk/middlewares/`):文件系统、技能、摘要、工具搜索等
- 人机交互(HITL)
- 统一回调
- 容错重试(`failover_chatmodel.go`、`retry_chatmodel.go`)

二者内部都驱动 ReAct 循环。生产中通常直接用 ADK 的 `ChatModelAgent`(官方快速入门即用),需要贴近机制或轻量场景时用 `flow/agent/react`。详见 ADK 文档。

## 九、常见坑与排错

- **Claude 类模型 `StreamToolCallChecker` 失效** -- 默认 checker 只查首块是否含 tool call;Claude 等先出文本后出 tool call 的模型会漏判,导致流式下不调工具。需自定义 `StreamToolCallChecker`(见 `react.go:166`)。
- **`MaxStep` 超限** -- 模型反复调工具不收敛会触发 `ErrExceedMaxSteps`(默认 12);调大 `MaxStep`,或用 `ToolReturnDirectly` 让特定工具直接返回。
- **误用弃用的 `Model` 字段** -- `AgentConfig.Model`(`model.ChatModel`,已弃用)用 `BindTools`(并发不安全);新代码用 `ToolCallingModel`(`model.ToolCallingChatModel`,`WithTools` 不可变)。ark.ChatModel 实现了该接口。
- **流式 `agent.Stream` 的 tool call 检测** -- 流式下 agent 用 `StreamToolCallChecker` 判断是否继续;模型若不先出 tool call,需配自定义 checker,否则可能提前结束或死循环。
- **`ToolReturnDirectly` 与 `SetReturnDirectly` 优先级** -- 工具内 `react.SetReturnDirectly(ctx)` 优先级高于 `AgentConfig.ToolReturnDirectly`;同一步多个工具调用只最后一个生效。
- **工具未实现 `InvokableTool`** -- `ToolsConfig.Tools` 要 `[]tool.BaseTool` 但执行需 `InvokableTool`/`StreamableTool`;只实现 `BaseTool` 会在执行时报错。

## 十、小结

| 关注点 | 解法 |
|---|---|
| 有环 ReAct 循环 | `react.NewAgent` 封装,内部 Pregel 驱动 |
| 模型 + 工具装配 | `AgentConfig.ToolCallingModel` + `ToolsConfig.Tools` |
| 防死循环 | `MaxStep`(默认 12) |
| 提前返回 | `ToolReturnDirectly` / `SetReturnDirectly` |
| 流式 tool call 检测 | `StreamToolCallChecker`(注意 Claude 类模型) |

ReAct agent 是编排层"把组件组装成智能体"的最小可用形态:ChatModel(推理)+ Tool(行动)+ Pregel(循环),由框架自动驱动。它把 `02_components` 的两个基础组件真正串成了一个会自主使用工具的智能体。

## 十一、参考

- [ReAct agent 手册](https://www.cloudwego.io/zh/docs/eino/core_modules/flow_integration_components/react_agent_manual/)
- [Graph or Agent - when to use which](https://www.cloudwego.io/zh/docs/eino/overview/graph_or_agent/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/flow/agent/react/react.go`
