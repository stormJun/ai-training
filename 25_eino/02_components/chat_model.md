# ChatModel 组件

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/model/`
> 核心文件:`interface.go`、`option.go`、`doc.go`。
> 本文剖析 ChatModel 的接口层次、双模式语义、工具绑定的并发模型,以及函数式选项机制。

## 一、概述

ChatModel 是 Eino 中最基础的组件,封装与大型语言模型的交互。其契约定义于 `components/model/doc.go:22`:

> 接收 `[]*schema.Message` 作为输入,返回响应消息--完整返回(`Generate`)或增量流式返回(`Stream`)。

任何与 LLM 通信的应用均经由该接口。具体实现(OpenAI、Ark、Ollama 等)位于 `eino-ext/components/model/`。

## 二、接口层次

### 2.1 泛型基接口 `BaseModel[M]`

ChatModel 的根接口采用泛型参数化设计(`interface.go:36`):

```go
type BaseModel[M messageType] interface {
    Generate(ctx context.Context, input []M, opts ...Option) (M, error)
    Stream(ctx context.Context, input []M, opts ...Option) (*schema.StreamReader[M], error)
}
```

类型参数 `M` 受密封类型约束(sealed type constraint):

```go
// interface.go:27
type messageType interface {
    *schema.Message | *schema.AgenticMessage
}
```

该 union 约束在编译期将 `M` 限定为仅两种具体类型,构成密封:框架据此在不丧失类型安全的前提下,统一处理普通消息与智能体消息。

### 2.2 类型别名特化

通过类型别名将泛型基接口特化为两种模型(`interface.go:71`、`:109`):

```go
type BaseChatModel = BaseModel[*schema.Message]        // 普通对话模型
type AgenticModel    = BaseModel[*schema.AgenticMessage] // 智能体模型
```

二者共享同一套 `Generate/Stream` 契约,仅消息载体不同。`AgenticModel` 面向 ADK 层的智能体场景(携带 richer 状态的 `AgenticMessage`)。

> **注**:`=` 表示类型别名(type alias)而非新定义类型,`BaseChatModel` 与 `BaseModel[*schema.Message]` 完全等价、可互换。

### 2.3 工具绑定扩展接口

在 `BaseChatModel` 之上,以接口嵌入(interface embedding)派生出两个工具绑定变体:

```go
// interface.go:80(已弃用)
type ChatModel interface {
    BaseChatModel
    BindTools(tools []*schema.ToolInfo) error   // 原地变更,并发不安全
}

// interface.go:99(推荐)
type ToolCallingChatModel interface {
    BaseChatModel
    WithTools(tools []*schema.ToolInfo) (ToolCallingChatModel, error) // 返回新实例,不可变
}
```

完整层次(`doc.go:34`):

```
BaseChatModel              Generate + Stream(所有实现)
├── ToolCallingChatModel   推荐;WithTools 返回新实例,并发安全
└── ChatModel              已弃用;BindTools 原地变更状态,新代码应避免
```

## 三、双模式:Generate 与 Stream

| 方法 | 语义 | 适用场景 |
|---|---|---|
| `Generate` | 阻塞至模型返回完整响应 | 结构化抽取、分类等需完整结果后方可继续的场景 |
| `Stream` | 返回 `*schema.StreamReader[M]`,逐块产出 | 聊天 UI、长文本生成等需增量转发至调用方的场景 |

`Stream` 的调用方负有**关闭 reader** 的责任,否则底层连接泄漏(`doc.go:42`、`interface.go:55`):

```go
reader, err := m.Stream(ctx, messages)
if err != nil { return err }
defer reader.Close()                    // 必须关闭
for {
    chunk, err := reader.Recv()
    if errors.Is(err, io.EOF) { break }
    if err != nil { return err }
    // 处理 chunk
}
```

此外,`schema.StreamReader` 为**单次消费**(read-once);若需多消费者,须在读取前调用 `Copy`。该抽象的底层设计见 [`../source_notes/stream_design.md`](../source_notes/stream_design.md)。

## 四、工具绑定的并发模型

工具绑定存在三种机制,其核心差异在于**可变性与并发安全性**:

### 4.1 `ChatModel.BindTools`(已弃用)

`BindTools` 原地变更接收者状态(`interface.go:80`)。当同一实例被并发使用时,一个 goroutine 的工具列表会覆盖另一个,构成数据竞争(`interface.go:75-79`)。新代码不应使用。

### 4.2 `ToolCallingChatModel.WithTools`(推荐)

`WithTools` **不变更接收者**,而是返回携带指定工具的新实例(`interface.go:99`)。由此基实例可在 goroutine 间安全共享,并派生出工具集各异的单请求变体(`interface.go:96-98`):

```go
base, _       := openai.NewChatModel(ctx, cfg)                        // 共享基实例,无工具
withSearch, _ := base.WithTools([]*schema.ToolInfo{searchTool})       // 派生:含搜索工具
withCalc, _   := base.WithTools([]*schema.ToolInfo{calcTool})         // 派生:含计算工具
```

### 4.3 `model.WithTools` 选项(调用时传递)

除实例级绑定外,工具亦可在调用时以函数式选项传入(`option.go:116`),作用于任意 `BaseModel`:

```go
resp, err := m.Generate(ctx, messages, model.WithTools([]*schema.ToolInfo{searchTool}))
```

该机制对 `AgenticModel` 尤为关键--`AgenticModel` **不暴露 `WithTools` 方法**,工具统一在请求时经 `model.WithTools` 选项传递,与 `ChatModelAgent` 的工具绑定方式一致(`interface.go:106-108`)。

### 4.4 三者对比

| 机制 | 作用对象 | 可变性 | 并发安全 | 适用 |
|---|---|---|---|---|
| `BindTools`(弃用) | 实例 | 原地变更 | ✗ | 不推荐 |
| `WithTools` 方法 | 实例 | 返回新实例(不可变) | ✓ | `ToolCallingChatModel` |
| `WithTools` 选项 | 调用 | 单次请求 | ✓ | 任意 `BaseModel`,含 `AgenticModel` |

## 五、函数式选项机制

ChatModel 的参数化通过 `...Option` 完成。其设计支持**通用选项**与**实现特定选项**在同一切片中混合传递。

### 5.1 `Option` 的双槽结构

```go
// option.go:64
type Option struct {
    apply            func(opts *Options)   // 通用选项 setter
    implSpecificOptFn any                  // 实现特定选项 setter(类型擦除)
}
```

关键不变式(`option.go:61`):**每个 `Option` 仅承载二者之一,从不同时持有**。据此,`GetCommonOptions` 与 `GetImplSpecificOptions` 可对同一 `Option` 切片进行正交划分。

### 5.2 通用选项

通用选项直接操作 `Options` 结构体(`option.go:22`),由框架预定义:

| 选项 | 字段 | 语义 |
|---|---|---|
| `WithTemperature` | `Temperature *float32` | 采样温度,控制随机性 |
| `WithTopP` | `TopP *float32` | 核采样,控制多样性 |
| `WithMaxTokens` | `MaxTokens *int` | 最大生成 token 数,触及后通常以 `length` 终止 |
| `WithModel` | `Model *string` | 模型名(覆盖构造期配置) |
| `WithStop` | `Stop []string` | 停止词 |
| `WithTools` | `Tools []*schema.ToolInfo` | 可调用工具集 |
| `WithToolChoice` | `ToolChoice *schema.ToolChoice` | 工具选择策略,可附 `allowedToolNames` 约束子集(仅 ChatModel) |
| `WithDeferredTools` | `DeferredTools []*schema.ToolInfo` | 延迟加载工具,供模型内置工具搜索按需载入 |
| `WithToolSearchTool` | `ToolSearchTool *schema.ToolInfo` | 工具搜索工具本身(不应入 `WithTools`) |
| `WithAgenticToolChoice` | `AgenticToolChoice *schema.AgenticToolChoice` | 智能体工具选择(仅 AgenticModel) |

### 5.3 实现特定选项

实现方通过 `WrapImplSpecificOptFn[T]` 将自定义 setter 包装为 `Option`(`option.go:196`):

```go
// 实现包内定义
func WithMyParam(v string) model.Option {
    return model.WrapImplSpecificOptFn(func(o *MyOptions) {
        o.MyParam = v
    })
}
```

调用方可自由混合标准选项与实现特定选项:

```go
resp, err := m.Generate(ctx, msgs,
    model.WithTemperature(0.7),
    mypkg.WithMyParam("value"),
)
```

### 5.4 选项提取

实现方在 `Generate/Stream` 内必须分别提取两类选项(`doc.go:52`):

```go
func (m *MyModel) Generate(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.Message, error) {
    common := model.GetCommonOptions(&model.Options{Temperature: &m.defaultTemp}, opts...)  // option.go:211
    myOpts := model.GetImplSpecificOptions(&MyOptions{MyParam: "default"}, opts...)          // option.go:239
    // 使用 common.Temperature、myOpts.MyParam …
}
```

`GetImplSpecificOptions[T]` 内部以类型断言 `opt.implSpecificOptFn.(func(*T))` 分派(`option.go:247`):仅当实现特定 setter 的类型与请求方 `T` 匹配时才应用。由此,同一 `Option` 切片中不同实现的特定选项互不干扰,各实现仅拾取属于自身的选项。

## 六、实现要点

实现一个 ChatModel 需遵循:

1. 满足 `BaseChatModel`(`Generate` + `Stream`)或其扩展接口(`ToolCallingChatModel`)。
2. 在 `Generate/Stream` 内调用 `GetCommonOptions` 与 `GetImplSpecificOptions` 提取选项。
3. 实现特定选项经 `WrapImplSpecificOptFn` 暴露。
4. 流式场景下若需精确控制回调触发时机,实现 `Checker.IsCallbacksEnabled` 返回 `true`,由组件自行触发回调(见 [`./README.md`](./README.md) §2.4)。
5. `Stream` 返回的 reader 由调用方关闭,实现方应确保在出错或 panic 时正确结束底层流。

## 七、完整示例

> **可运行 demo**:本目录下 [`demo/`](./demo/) 提供一个接入火山方舟 Ark 的可运行示例,演示 `Generate` / `Stream` / `WithTemperature` 的完整闭环(需在 `.env` 配置 Key,见 demo README)。本文示例为带工具绑定的进阶写法。

以下示例综合展示构造、双模式调用、并发安全工具绑定与选项传递(模型实现来自 eino-ext):

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "io"

    "github.com/cloudwego/eino/components/model"
    "github.com/cloudwego/eino/schema"
    // eino-ext 实现
    "github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
    ctx := context.Background()

    // 1. 构造(实现来自 eino-ext)
    base, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:  "gpt-4o",
        APIKey: os.Getenv("OPENAI_API_KEY"),
    })
    if err != nil { panic(err) }

    msgs := []*schema.Message{
        schema.SystemMessage("你是一名简洁的助手。"),
        schema.UserMessage("用一句话介绍 Go 语言。"),
    }

    // 2. 阻塞调用,附调用时选项
    resp, err := base.Generate(ctx, msgs, model.WithTemperature(0.7))
    if err != nil { panic(err) }
    fmt.Println(resp.Content)

    // 3. 流式调用,务必关闭 reader
    reader, err := base.Stream(ctx, msgs)
    if err != nil { panic(err) }
    defer reader.Close()
    for {
        chunk, err := reader.Recv()
        if errors.Is(err, io.EOF) { break }
        if err != nil { panic(err) }
        fmt.Print(chunk.Content)
    }

    // 4. 并发安全地派生带工具的实例(若 base 实现 ToolCallingChatModel)
    //    tcm, _ := base.(model.ToolCallingChatModel)
    //    withTools, _ := tcm.WithTools([]*schema.ToolInfo{searchTool})
    //    _ = withTools
}
```

## 八、常见坑与排错

- **流式 reader 未关闭 -> 连接泄漏** -- `Stream` 返回的 `*StreamReader` 必须 `defer reader.Close()`;否则底层 HTTP 连接/goroutine 泄漏。注意 `log.Fatalf` 会 `os.Exit` 跳过 `defer`,流式循环中报错应 `return err` 而非 `Fatal`。
- **`BindTools` 并发不安全(已弃用)** -- `ChatModel.BindTools` 原地变更实例状态,并发共享会数据竞争。改用 `ToolCallingChatModel.WithTools`(返回新实例,不可变)或调用时 `model.WithTools` 选项。
- **`AgenticModel` 无 `WithTools` 方法** -- `AgenticModel = BaseModel[*AgenticMessage]`,不暴露 `WithTools` 方法;工具只能在调用时用 `model.WithTools` 选项传。误调 `WithTools` 方法会编译失败。
- **多消费者读同一流 -> 数据错乱** -- `StreamReader` 单次消费(read-once),两 goroutine 同时 `Recv` 会抢块。需在读取前 `reader.Copy(n)` 扇出独立副本。
- **`Generate` ≠ `Stream` 拼接** -- 两者是独立 API 调用,各自采样,结果文本不同;不要假设 Stream 的 chunk 拼起来等于 Generate 的输出。
- **选项覆盖优先级** -- 调用时选项(如 `WithTemperature`)覆盖构造期 `ChatModelConfig` 同名字段;`GetCommonOptions` 以构造期值为 base,调用时选项覆盖之。
- **impl-specific 选项按类型分派** -- `GetImplSpecificOptions[T]` 用类型断言,仅拾取匹配 `T` 的 setter;多实现混在同一 `...Option` 中各取各的,不串。
- **Ark Agent Plan vs 普通 Ark** -- Key 与 BaseURL 不通用;Agent Plan 用 `/api/plan/v3` + 专属 Key,普通 Ark 用 `/api/v3`(见 demo README)。

## 九、小结

ChatModel 的设计体现了若干 Go 惯用模式与工程考量:

| 设计点 | 手段 | 收益 |
|---|---|---|
| 消息类型统一 | 泛型 `BaseModel[M]` + 密封约束 | 类型安全下统一普通/智能体消息 |
| 同步/流式并存 | 双方法范式 | 编排层可自动衔接流式,调用方按需选择 |
| 工具绑定安全 | 不可变 `WithTools` 返回新实例 | 实例可跨 goroutine 安全共享与派生 |
| 参数扩展性 | 双槽 `Option` + 类型断言分派 | 通用与实现特定选项统一传递、正交提取 |

下一篇 [`tool.md`](./tool.md) 将阐述 Tool 组件的接口层次与函数式构造。
