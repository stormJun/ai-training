# Tool 组件

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/tool/`
> 核心文件:`interface.go`、`option.go`、`interrupt.go`、`utils/`(函数式构造)。
> 本文阐述 Tool 的接口层次、函数式构造、Option 机制与中断/恢复。

## 一、概述

Tool 组件让 ChatModel 能够**调用外部能力**(查天气、查数据库、执行代码、调 API)。其契约定义于 `components/tool/doc.go:17`:

> 定义工具接口,使语言模型可调用外部能力,并提供工具内的中断/恢复支持。

工具在 Eino 中的角色:

```
ChatModel(带 Tools)  ──生成 ToolCall──▶  ToolsNode ──执行──▶  Tool
       ▲                                                      │
       └────────────── 结果作为 tool 消息回传 ─────────────────┘
```

- **Tool** 定义"能力"的元信息与执行逻辑(本文)。
- **ToolsNode**(`compose/tool_node.go`)在编排中执行工具,把模型产出的 `ToolCall` 分发给对应 Tool,再把结果回传--属于编排层,见 `03_graph/`。
- 完整的工具调用循环(ReAct)由 ADK 的 `ChatModelAgent` 自动驱动,见 ADK 文档。

## 二、接口层次

Tool 采用**基础接口 + 扩展接口**的层次结构(`interface.go`):

```
BaseTool                  Info() *schema.ToolInfo            仅元数据,供 ChatModel 决策调用
├── InvokableTool         InvokableRun(args string) string   标准:参数为 JSON 字符串,返回字符串
├── StreamableTool        StreamableRun(...) StreamReader    流式:返回 StreamReader[string]
├── EnhancedInvokableTool InvokableRun(ToolArgument) ToolResult   多模态:返回文本/图/音频/文件
└── EnhancedStreamableTool StreamableRun(...) StreamReader<ToolResult>
```

### 2.1 `BaseTool`:元数据

```go
// interface.go:32
type BaseTool interface {
    Info(ctx context.Context) (*schema.ToolInfo, error)
}
```

`Info` 返回 `schema.ToolInfo`,含工具名、描述、参数 JSON Schema。ChatModel 据此决定**是否调用、如何调用**。仅 `BaseTool` 即足以"把工具定义传给模型";实际执行则需扩展接口。

### 2.2 `InvokableTool`:标准可调用

```go
// interface.go:42
type InvokableTool interface {
    BaseTool
    InvokableRun(ctx context.Context, argumentsInJSON string, opts ...Option) (string, error)
}
```

参数是模型产出的 **JSON 字符串**,返回**字符串**结果(作为 tool 消息回传模型)。框架在使用 `utils.InferTool` / `utils.NewTool` 构造时会自动完成 JSON 解码与编码,实现方无需手写序列化。

### 2.3 `StreamableTool`:流式可调用

```go
// interface.go:53
type StreamableTool interface {
    BaseTool
    StreamableRun(ctx context.Context, argumentsInJSON string, opts ...Option) (*schema.StreamReader[string], error)
}
```

返回 `StreamReader[string]`,逐块产出结果。适合长结果(如逐段生成报告)。调用方(ToolsNode)负责关闭 reader。

### 2.4 Enhanced 变体:多模态

`EnhancedInvokableTool` / `EnhancedStreamableTool`(`interface.go:67`、`:76`)参数为 `*schema.ToolArgument`,返回 `*schema.ToolResult`,可携带**文本、图像、音频、视频、文件**等多模态内容。当工具同时实现标准与增强接口时,ToolsNode 优先使用增强接口。

## 三、如何选择接口

| 需求 | 选择 |
|---|---|
| 绝大多数工具,返回文本 | `InvokableTool` |
| 结果需逐块产出(长文本、进度) | `StreamableTool` |
| 返回图像/音频/文件等多模态内容 | `EnhancedInvokableTool` / `EnhancedStreamableTool` |
| 仅需把工具定义传给模型,不需执行 | `BaseTool` |

## 四、创建工具:函数式构造(推荐)

`components/tool/utils` 提供构造器,免除手写 JSON 序列化样板代码。两种策略(`utils/doc.go:20`):

1. **从 struct tag 推导(推荐)**:`InferTool` / `InferStreamTool` / `InferEnhancedTool` -- 参数 JSON Schema 自动由输入结构体的字段名与 tag 生成。
2. **手动 ToolInfo**:`NewTool` / `NewStreamTool` -- 自行提供 `schema.ToolInfo`,适用于 schema 无法用 Go struct 表达或需动态构造的场景。

### 4.1 `InferTool`

```go
// utils/invokable_func.go:46
func InferTool[T, D any](toolName, toolDesc string, i InvokeFunc[T, D], opts ...Option) (tool.InvokableTool, error)

// invokable_func.go:33
type InvokeFunc[T, D any] func(ctx context.Context, input T) (output D, err error)
```

`InferTool` 做三件事:
1. 反射类型 `T` 的字段与 tag,生成参数 JSON Schema,组装成 `schema.ToolInfo`(`goStruct2ToolInfo`,`invokable_func.go:108`)。
2. 返回的 `InvokableTool` 在 `InvokableRun` 时**自动把模型给的 JSON 参数解码成 `T`**,调用 `fn`(`invokable_func.go:174-215`)。
3. 把 `fn` 的返回值 `D` **JSON 编码成字符串**回传。

实现方只需写"输入 struct + 业务函数",序列化由框架代办。

### 4.2 struct tag 约定

`InferTool` 依据输入结构体的 tag 生成参数 schema(`utils/doc.go:36`):

```go
type Input struct {
    Query    string `json:"query"          jsonschema:"required"  jsonschema_description:"搜索关键词"`
    MaxItems int    `json:"max_items"                              jsonschema_description:"最大返回条数"`
}
```

规则:
- `json:"name"` -- 控制参数名(模型可见),如 `max_items`。
- `jsonschema:"required"` -- 标记必填参数。
- `jsonschema_description:"..."` -- 字段描述,**用独立 tag**,不要塞进 `jsonschema` tag(逗号解析会出错)。

### 4.3 手动 ToolInfo:`NewTool`

当 schema 无法用 struct 表达(动态参数、复杂嵌套)时,用 `NewTool` 自行提供 `schema.ToolInfo`:

```go
// invokable_func.go:143
func NewTool[T, D any](desc *schema.ToolInfo, i InvokeFunc[T, D], opts ...Option) tool.InvokableTool
```

注意:`desc.ParamsOneOf` 与 `T` 的字段一致性由调用方保证,**无编译期检查**(`invokable_func.go:141` 注释)。

### 4.4 Optionable 变体

`InferOptionableTool`(`invokable_func.go:57`)的函数额外接收 `...tool.Option`--即 ToolsNode 在调用时传入的调用时选项(见下节)。需要按请求定制行为的工具用此变体。

## 五、Option 机制

Tool 有**两套 Option**,作用阶段不同,需区分:

### 5.1 `tool.Option`:调用时选项

定义于 `components/tool/option.go:22`,结构同 `model.Option`--内含 `implSpecificOptFn any`,通过类型断言分派:

```go
// option.go:22
type Option struct {
    implSpecificOptFn any
}
```

- **`WrapImplSpecificOptFn[T]`**(`option.go:44`)--实现方把自定义 setter 包装成 `Option`。
- **`GetImplSpecificOptions[T]`**(`option.go:62`)--实现方在 `InvokableRun` 内提取,`base` 提供默认值。

```go
// 实现包内
type customOptions struct{ conf string }

func WithConf(conf string) tool.Option {
    return tool.WrapImplSpecificOptFn(func(o *customOptions) { o.conf = conf })
}

// InvokableRun 内
func (t *MyTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    o := tool.GetImplSpecificOptions(&customOptions{conf: "default"}, opts...)
    // 用 o.conf ...
}
```

调用方(ToolsNode)可在执行工具时传 `WithConf(...)`,实现按请求定制。该机制与 `model.Option` 完全同构(类型擦除 + 类型断言分派)。

### 5.2 `utils.Option`:构造时选项

定义于 `utils/create_options.go:39`,用于 `InferTool` / `NewTool` 的**构造阶段**,定制序列化与 schema 生成:

| 选项 | 作用 |
|---|---|
| `WithUnmarshalArguments`(`create_options.go:43`) | 自定义参数解码(替代默认 JSON 解码) |
| `WithMarshalOutput`(`:51`) | 自定义输出编码 |
| `WithSchemaModifier`(`:67`) | 自定义 struct tag -> JSON Schema 的映射 |

> 区分:`tool.Option` 是**运行时**传给 `InvokableRun` 的;`utils.Option` 是**构造时**传给 `InferTool` 的。两者类型不同,不可混用。

## 六、中断与恢复(Interrupt / Resume)

工具可**暂停执行、等待外部输入**(如人工确认),并从检查点恢复(`interrupt.go`)。这是人机交互(HITL)在工具层的支持。

核心 API:

| 函数 | 作用 |
|---|---|
| `Interrupt(ctx, info)`(`interrupt.go:44`) | 暂停,`info` 为面向用户的原因(如"需确认");返回值须从 `InvokableRun` 返回 |
| `StatefulInterrupt(ctx, info, state)`(`:71`) | 暂停并保存内部状态(state 须可 gob 序列化),恢复时还原 |
| `CompositeInterrupt(...)`(`:79`) | 聚合子组件(图、其他工具)的中断 |
| `GetInterruptState[T](ctx)` | 查询是否曾被中断,取回保存的状态 |
| `GetResumeContext(ctx)` | 取恢复时携带的数据 |

典型模式(`interrupt.go:62` 示例):

```go
func (t *MyTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    wasInterrupted, hasState, state := tool.GetInterruptState[MyState](ctx)
    if !wasInterrupted {
        // 首次执行:暂停并保存状态
        return "", tool.StatefulInterrupt(ctx, "processing", MyState{Step: 1})
    }
    // 恢复执行:从 state 继续
    return continueFrom(state), nil
}
```

> 完整的中断/恢复机制(检查点持久化、路由)由编排层 `compose/interrupt.go` + `compose/resume.go` + `compose/checkpoint.go` 支持,详见 `03_graph/`。框架负责状态持久化与恢复路由,工具只需在合适时机 `Interrupt`。

## 七、与 ToolsNode 的关系

Tool 本身只定义"能力";在编排中**执行**工具的是 **ToolsNode**(`compose/tool_node.go`):

1. ChatModel 绑定工具(经 `WithTools` 或 `ToolCallingChatModel.WithTools`)。
2. 模型生成含 `ToolCall` 的消息。
3. ToolsNode 接收 `ToolCall`,按名字找到 Tool,调 `InvokableRun`/`StreamableRun`。
4. 结果作为 `tool` 角色消息回传,模型继续推理。

这套循环(ReAct)在 ADK 的 `ChatModelAgent` 中自动驱动,用户无需手写。详见 `03_graph/` 与 ADK 文档。

## 八、完整示例

> **可运行 demo**:[`demo/tool_demo/`](./demo/tool_demo/) 用真实 Ark 模型演示**完整工具调用闭环**--模型自主决策调天气工具、执行、结果回传、再生成(手动 ReAct 循环)。本节为工具创建与单次执行的最小示例。

定义一个天气工具,演示 struct tag、`InferTool`、`Info`、`InvokableRun` 的自动编解码:

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/tool/utils"
)

// WeatherInput 是工具输入。tag 会被 InferTool 反射成参数 JSON Schema。
type WeatherInput struct {
	City string `json:"city" jsonschema:"required" jsonschema_description:"城市名，如 Beijing"`
	Day  string `json:"day" jsonschema_description:"日期，如 2026-07-21；留空表示今天"`
}

// WeatherOutput 是工具输出。
type WeatherOutput struct {
	City        string `json:"city"`
	Temperature int    `json:"temperature"`
	Weather     string `json:"weather"`
}

// getWeather 是工具逻辑。InferTool 自动把模型给的 JSON 解码成 WeatherInput，
// 再把 WeatherOutput 编码成 JSON 字符串返回给模型。
func getWeather(ctx context.Context, in WeatherInput) (WeatherOutput, error) {
	// 真实场景调天气 API；此处用假数据
	return WeatherOutput{City: in.City, Temperature: 28, Weather: "晴"}, nil
}

func main() {
	ctx := context.Background()

	// 从 Go 函数 + struct tag 推导出 InvokableTool（推荐）。
	weatherTool, err := utils.InferTool(
		"get_weather",        // 工具名（模型据此调用）
		"查询指定城市的天气",    // 描述（模型据此判断何时用）
		getWeather,           // 工具函数
	)
	if err != nil {
		panic(err)
	}

	// Info 返回元数据（名称、描述、参数 schema），用于绑定给 ChatModel。
	info, _ := weatherTool.Info(ctx)
	fmt.Printf("工具名: %s\n描述: %s\n", info.Name, info.Desc)

	// 模拟模型调用工具时传入的 JSON 参数。
	// InvokableRun 自动: JSON -> WeatherInput -> 调函数 -> WeatherOutput -> JSON。
	result, err := weatherTool.InvokableRun(ctx, `{"city":"Beijing","day":""}`)
	if err != nil {
		panic(err)
	}
	fmt.Printf("执行结果: %s\n", result)
	// 执行结果: {"city":"Beijing","temperature":28,"weather":"晴"}
}
```

要点:
- **零序列化代码**--`InferTool` 自动完成 JSON 编解码。
- **类型安全**--输入输出均为强类型 `WeatherInput`/`WeatherOutput`。
- `InvokableRun` 的第二参就是模型实际会产出的 JSON 参数串;ToolsNode 在编排中做的事与此处直接调用一致。

## 九、常见坑与排错

- **`InferTool` schema 推导失败** -- 输入类型 `T` 必须是具名 struct(字段带 `json` tag);用 `map[string]any`、`any`、非 struct 类型无法反射出 JSON Schema。动态 schema 改用 `NewTool` 手传 `*schema.ToolInfo`。
- **`jsonschema_description` 误写进 `jsonschema` tag** -- 字段描述必须用**独立** `jsonschema_description:"..."` tag;塞进 `jsonschema:"...,description=..."` 会因逗号解析出错(`utils/doc.go:44`)。
- **必填参数漏标** -- 未加 `jsonschema:"required"` 的字段,模型可能不传或传 null;关键参数务必标 required。
- **`ToolCallID` 关联错误** -- 工具结果消息必须用 `schema.ToolMessage(result, tc.ID)` 带 `ToolCallID`,与模型产出的 `ToolCall.ID` 对应;ID 不匹配模型无法关联结果,会报错或忽略。
- **`InvokableRun` 参数是 JSON 字符串,非结构体** -- 模型产出的是 JSON 字符串;`InferTool` 自动解码成 `T`,但若自行实现 `InvokableRun` 需手动 `json.Unmarshal`。
- **工具未实现 `InvokableTool`/`StreamableTool`** -- 仅 `BaseTool`(只有 `Info`)不足以执行;`ToolsNodeConfig.Tools` 要求实现 `InvokableTool` 或 `StreamableTool`(`tool_node.go:185` 注释),否则执行时报错。
- **Enhanced 与标准接口同实现时** -- ToolsNode 优先 Enhanced;若只想用标准接口,不要同时实现 Enhanced,否则结果类型(`*ToolResult` vs string)与预期不符。
- **Optionable 工具的 `opts` 来源** -- `InferOptionableTool` 的函数收到的 `opts` 是 ToolsNode 调用时透传的 `tool.Option`(如 `WithToolOption`),不是构造时选项;混淆会导致选项不生效。

## 十、小结

| 设计点 | 手段 | 收益 |
|---|---|---|
| 声明与执行解耦 | `BaseTool`(元数据)+ 扩展接口(执行) | 可仅传定义给模型,执行按需 |
| 函数式构造 | `InferTool` 反射 struct tag 生成 schema | 零样板、类型安全、自动编解码 |
| 动态 schema | `NewTool` 接受显式 `ToolInfo` | 支持无法用 struct 表达的参数 |
| 两阶段 Option | `tool.Option`(运行时)+ `utils.Option`(构造时) | 调用时定制与构造时定制分离 |
| 人机交互 | `Interrupt` / `StatefulInterrupt` + 检查点 | 工具可暂停等待人工输入并恢复 |

Tool 与 ChatModel 是构成智能体的两大基础组件:ChatModel 负责"推理",Tool 负责"行动"。二者经 ToolsNode 串联、由 ADK 驱动,即形成完整的工具调用智能体。

## 十一、参考

- [ToolsNode 指南](https://www.cloudwego.io/zh/docs/eino/core_modules/components/tools_node_guide/)
- [如何创建 Tool](https://www.cloudwego.io/zh/docs/eino/core_modules/components/tools_node_guide/how_to_create_a_tool/)
- 本机源码:`/Users/songxijun/workspace/otherProject/eino/components/tool`
