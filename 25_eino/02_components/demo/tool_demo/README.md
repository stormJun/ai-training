# Tool 调用 Demo(完整版)

用真实 Ark 模型演示**完整的工具调用闭环**:定义天气工具 -> 绑定给模型 -> 模型自主决定调用 -> 执行 -> 结果回传 -> 模型基于结果生成最终回复。

## 运行

复用上级 `demo/.env` 配置(已含 Agent Plan Key)。在 `demo/` 目录下:

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
go run ./tool_demo
```

预期输出:

```
>> 已加载 .env

----- 第 1 轮 -----
调用工具 get_weather，参数 {"city": "Beijing"}
工具结果: {"city":"Beijing","temperature":28,"weather":"晴"}

----- 第 2 轮 -----
模型最终回复: 北京今天的天气为晴，气温28℃。
```

## 它演示了什么

1. **工具创建** -- `utils.InferTool` 从 Go 函数 + struct tag 生成 `InvokableTool`,自动 JSON 编解码。
2. **工具绑定** -- `model.WithTools([]*schema.ToolInfo{toolInfo})` 作为调用时选项传给 `Generate`。
3. **ReAct 循环** -- 手写"模型决策 -> 执行 -> 回传 -> 再生成"四步循环,直到模型不再调用工具、给出最终回复:
   - `resp.ToolCalls` 非空 -> 模型要调工具
   - `weatherTool.InvokableRun(ctx, tc.Function.Arguments)` 执行工具
   - `schema.ToolMessage(result, tc.ID)` 把结果作为 tool 消息回传(用 `ToolCallID` 关联)
   - 把 assistant 的 ToolCall 消息和 tool 结果消息都 append 进对话,再次 `Generate`

## 为什么手写循环

为了讲清工具调用的**机制**。生产中这个循环由:
- **ToolsNode**(`compose/tool_node.go`)在编排图中执行工具,或
- **ADK 的 `ChatModelAgent`** 自动驱动完整 ReAct

无需手写。本 demo 等价于把 ToolsNode/Agent 的内部逻辑展开,便于理解。详见 `03_graph/` 与 ADK 文档。

## 文件

| 文件 | 职责 |
|---|---|
| `main.go` | 天气工具定义 + ChatModel 构造 + 手动 ReAct 循环 |

依赖复用上级 `demo/go.mod`(eino + ark + godotenv),`.env` 共用。

## 相关文档

- [`../tool.md`](../tool.md) 等价于 [`../../tool.md`](../../tool.md) -- Tool 组件详解
- [`../../chat_model.md`](../../chat_model.md) -- ChatModel(工具绑定、ToolCallingChatModel)
