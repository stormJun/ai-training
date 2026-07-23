# ReAct Agent Demo

用 `flow/agent/react` 的 ReAct agent 替代手写循环:把 ChatModel + 天气工具交给 `react.NewAgent`,框架自动跑"模型↔工具"循环。

## 运行

复用上级 `demo/.env`。在 `demo/` 目录下:

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
go run ./react_demo
```

预期输出:

```
>> 已加载 .env
最终回复: 根据查询结果，北京今天的天气为晴，气温28摄氏度。
```

## 对比 `tool_demo`

| | `tool_demo` | `react_demo`(本 demo) |
|---|---|---|
| ReAct 循环 | 手写 `for` + 检测 ToolCalls + 执行 + 回传 | `react.NewAgent` 自动 |
| 代码 | ~40 行循环 | `NewAgent` + `Generate` 两行 |

两者用相同的天气工具和 Ark 模型,对照即可看清"框架替你做了什么"。

## 核心代码

```go
agent, err := react.NewAgent(ctx, &react.AgentConfig{
    ToolCallingModel: chatModel,                       // ark.ChatModel 实现该接口
    ToolsConfig: compose.ToolsNodeConfig{
        Tools: []tool.BaseTool{weatherTool},
    },
})
resp, err := agent.Generate(ctx, []*schema.Message{
    schema.UserMessage("北京今天天气怎么样？请用工具查询后回答。"),
})
```

agent 内部构建 Pregel 驱动的 Graph(chat 节点 ↔ tools 节点),自动决策、执行、回传、再生成,直到给出最终回复。

## 相关文档

- [`../../03_graph/react_agent.md`](../../03_graph/react_agent.md) -- ReAct agent 机制详解
- [`../tool_demo/`](../tool_demo/) -- 手写循环版(对照)
