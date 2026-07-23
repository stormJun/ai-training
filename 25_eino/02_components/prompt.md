# ChatTemplate 提示词模板

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/prompt/`
> 核心文件: `interface.go`、`chat_template.go`、`agentic_chat_template.go`、`option.go`
> 本文阐述 ChatTemplate 和 AgenticChatTemplate 的接口、构造、FString 语法与用法。

## 一、概述

ChatTemplate 是**提示词模板**组件，作用是把变量填充进模板，生成 `ChatModel` 需要的 `[]*schema.Message`。它是 RAG、Agent 等场景中"变量拼入 prompt"的标准抽象。

Eino 提供两种模板接口，对应两种消息类型：

| 接口 | 输出类型 | 适用场景 |
|------|----------|----------|
| `ChatTemplate` | `[]*schema.Message` | 普通对话模型，大多数场景 |
| `AgenticChatTemplate` | `[]*schema.AgenticMessage` | ADK 层智能体，携带 richer 状态 |

二者结构和使用方式完全一致，只是输出类型不同。默认实现 `DefaultChatTemplate`/`DefaultAgenticChatTemplate` 支持 FString 语法，也可自定义实现。

## 二、接口契约

### 2.1 ChatTemplate

`prompt.ChatTemplate` 接口(`interface.go:43`):
```go
type ChatTemplate interface {
	Format(ctx context.Context, vs map[string]any, opts ...Option) ([]*schema.Message, error)
}
```

- 输入 `vs map[string]any`：变量键值对，模板中 `{key}` 会被 `vs[key]` 替换
- 输出 `[]*schema.Message`：填充后的消息列表，可直接喂给 `ChatModel.Generate`
- 模板不存在的变量会返回**运行时错误**（没有默认值，必须全填）

### 2.2 AgenticChatTemplate

`prompt.AgenticChatTemplate` 接口(`interface.go:47`):
```go
type AgenticChatTemplate interface {
	Format(ctx context.Context, vs map[string]any, opts ...Option) ([]*schema.AgenticMessage, error)
}
```

专为 ADK 层智能体设计，输出 `AgenticMessage`，携带更多状态信息。用法与 `ChatTemplate` 相同。

## 三、构造:FromMessages 与语法

默认实现用 `prompt.FromMessages` 构造:
```go
// chat_template.go:42
func FromMessages(formatType schema.FormatType, templates ...schema.MessagesTemplate) *DefaultChatTemplate
```

- `formatType`: 模板语法类型，目前只有 `schema.FString`
- `templates`: 每个 `schema.MessagesTemplate` 是一条消息模板，包含角色和内容

### 3.1 FString 语法

FString 是最常用的语法，使用 `{var_name}` 表示变量占位符:

| 语法 | 说明 |
|------|------|
| `{variable_name}` | 替换为 `vs["variable_name"]` 的字符串形式 |
| `{messages}` | 通常放 `schema.MessagesPlaceholder`，表示插入消息列表 |

### 3.2 MessagesPlaceholder 占位符

在 RAG 或 Agent 场景，经常需要**插入一整段消息列表**（如历史对话、检索结果），eino 提供 `schema.MessagesPlaceholder`:

```go
// 模板中插入整个对话历史
schema.SystemMessage("你是一个助手，请根据历史对话回答问题。"),
schema.MessagesPlaceholder("history"), // {history} 会展开为多条消息
schema.UserMessage("{query}"),
```

这个占位符展开后，`history` 中的每条消息都会单独输出，保持角色信息不变。

## 四、完整示例

### 4.1 基础问答模板

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/prompt"
	"github.com/cloudwego/eino/schema"
)

func main() {
	ctx := context.Background()

	// 构造模板
	tpl := prompt.FromMessages(schema.FString,
		schema.SystemMessage("你是{role}。请简洁回答用户问题。"),
		schema.UserMessage("问题: {question}"),
	)

	// 填充变量
	messages, err := tpl.Format(ctx, map[string]any{
		"role":     "Go 语言专家",
		"question": "什么是 goroutine?",
	})
	if err != nil { panic(err) }

	// messages 就是填充好的，可以直接喂给 ChatModel
	for _, msg := range messages {
		fmt.Printf("[%s] %s\n", msg.Role, msg.Content)
	}
	// Output:
	// [system] 你是Go语言专家。请简洁回答用户问题。
	// [user] 问题: 什么是 goroutine?
}
```

### 4.2 带 MessagesPlaceholder 的 RAG 模板

```go
tpl := prompt.FromMessages(schema.FString,
	schema.SystemMessage(`你是一个知识库问答助手。请根据用户问题和检索到的上下文回答问题。

已知上下文:
{context}
`),
	schema.UserMessage("{question}"),
)

// 检索得到 documents 之后，拼入模板
messages, err := tpl.Format(ctx, map[string]any{
	"context":  retrievedDocumentsText, // 把检索结果拼成字符串填入
	"question": userQuestion,
})
```

### 4.3 带对话历史的 Agent 模板

```go
tpl := prompt.FromMessages(schema.FString,
	schema.SystemMessage("你是会使用工具的智能助手。"),
	schema.MessagesPlaceholder("history"), // 插入历史对话，每条消息保持角色
	schema.UserMessage("{input}"),
)

// 格式后，history 中的每条消息会展开
messages, err := tpl.Format(ctx, map[string]any{
	"history": historyMessages, // []*schema.Message 类型
	"input":   userInput,
})
```

## 五、在 Chain/Graph 中使用

在编排中，可直接用 `AppendChatTemplate`（Chain）或 `AddChatTemplateNode`（Graph）接入，无需包装 Lambda:

```go
// Chain 示例
chain := compose.NewChain[map[string]any, string]()
chain.AppendChatTemplate(tpl)        // 输入 map[string]any -> 输出 []*schema.Message
chain.AppendChatModel(chatModel)
chain.AppendLambda(func(ctx context.Context, msg *schema.Message) (string, error) {
	return msg.Content, nil
})
```

```go
// Workflow 示例
wf := compose.NewWorkflow[map[string]any, string]()
tplNode := wf.AddChatTemplateNode("prompt", tpl)
tplNode.AddInput(compose.START) // 输入就是变量 map，直接用
// ...
```

如果上游输出不是 `map[string]any`，用**字段映射**把上游输出导入模板变量:
```go
// Workflow 中，上游 query 节点输出 string，放到模板的 "query" 字段
promptNode.AddInput("query", compose.FromField("query"))
```

## 六、Option 机制

`prompt` 组件**没有预定义通用选项**，`Option` 类型仅为**自定义模板实现**提供扩展点:

```go
// 自定义模板实现添加特定选项
func WithMyCustomOption(v string) prompt.Option {
	return prompt.WrapImplSpecificOptFn(func(o *MyOptions) {
		o.Custom = v
	})
}

// 在自定义模板的 Format 方法内提取
func (t *MyCustomTemplate) Format(ctx context.Context, vs map[string]any, opts ...prompt.Option) ([]*schema.Message, error) {
	customOpts := prompt.GetImplSpecificOptions(&MyOptions{Default: "default"}, opts...)
	// ...
}
```

默认实现 `DefaultChatTemplate` 不使用任何选项，`opts` 参数直接忽略。

## 七、AgenticChatTemplate 说明

`AgenticChatTemplate` 和 `ChatTemplate` 用法完全一致，只是输出类型不同:
- 构造: `prompt.FromAgenticMessages(schema.FString, ...schema.AgenticMessagesTemplate)`
- 输出: `[]*schema.AgenticMessage`，供 ADK 层智能体使用
- 选项机制: 同样只有实现特定选项，没有通用选项

## 八、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **模板变量缺失 panic** | `vs` 中缺少模板中声明的变量 | 检查所有 `{var}` 在 `vs` 中都有键值对，拼写一致 |
| **MessagesPlaceholder 类型不对** | `vs["history"]` 不是 `[]*schema.Message` 类型 | 必须是 `[]*schema.Message` 才能正确展开多条消息 |
| **变量名拼写错误** | Go 模板是 `.Field`，FString 是 `{field}` | FString 直接写变量名，不要加 `.` |
| **多条消息合并成一条** | 把所有内容写进一条 `schema.Message`，不用 `MessagesPlaceholder` | 需要多条消息保持角色时，一定要用 `schema.MessagesPlaceholder` |
| **在 ChatModel 后接 ChatTemplate** 类型不匹配 | ChatTemplate 输入是 `map[string]any`，ChatModel 输出是 `*schema.Message` | 需要用 Lambda 或字段映射把 ChatModel 输出包装成 `map[string]any` |

## 九、设计要点小结

| 设计点 | 手段 | 收益 |
|--------|------|------|
| **双接口分离** | `ChatTemplate` → `*schema.Message`，`AgenticChatTemplate` → `*schema.AgenticMessage` | 普通对话和智能体场景各有专属接口，类型安全 |
| **多消息模板** | 构造时接受多个 `MessagesTemplate`，每个对应一条消息 | 自然表达多轮对话模板，system/user/assistant 角色分明 |
| **FString 内置** | 内置最简单的占位符替换，无需依赖第三方模板引擎 | 绝大多数场景够用，也可自定义实现 Jinja2 等其他语法 |
| **MessagesPlaceholder** | 特殊占位符展开整个消息列表 | 干净解决"插入历史对话/检索结果"这类常见场景 |
| **接口极小** | `Format` 唯一方法，无通用选项 | 自定义实现容易，符合 Eino "接口抽象不臃肿" |

ChatTemplate 是 LLM 应用的"最后一公里"——不管检索多好、模型多强，最终都需要模板把变量拼对喂给模型，Eino 的抽象简洁但覆盖绝大多数场景。

## 十、参考

- [ChatTemplate 官方文档](https://www.cloudwego.io/zh/docs/eino/core_modules/components/prompt_template_guide/)
- 组件总览:[README.md](./README.md)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/components/prompt`
