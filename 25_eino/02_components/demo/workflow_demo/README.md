# Workflow Demo

用 `compose.Workflow` 的声明式 API 编排:以 `AddInput` 声明节点间数据流(替代 Graph 的 `AddEdge`)。

## 运行

复用上级 `demo/.env`。在 `demo/` 目录下:

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
go run ./workflow_demo
```

预期输出:

```
>> 已加载 .env
输出: Go（又称Golang）是谷歌于2009年开源的静态强类型编译型语言…
```

## 核心代码

```go
wf := compose.NewWorkflow[string, string]()

buildMsgs := wf.AddLambdaNode("build_msgs", ...)
chat := wf.AddChatModelNode("chat", chatModel)
toText := wf.AddLambdaNode("to_text", ...)

buildMsgs.AddInput(compose.START) // 首节点接收工作流输入
chat.AddInput("build_msgs")       // 声明输入来源（替代 AddEdge）
toText.AddInput("chat")
wf.AddEnd("to_text")

runnable, _ := wf.Compile(ctx)
out, _ := runnable.Invoke(ctx, "用一句话介绍 Go 语言")
```

对照 `../` 下其它 demo:`tool_demo`/`react_demo` 用 Agent,本 demo 用 Workflow 的声明式数据流,适合多输入汇聚的 DAG 场景。

## 相关文档

- [`../../03_graph/workflow.md`](../../03_graph/workflow.md) -- Workflow 声明式编排详解
