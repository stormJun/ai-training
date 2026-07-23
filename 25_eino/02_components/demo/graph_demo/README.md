# Graph Demo(Branch 路由)

用 `compose.Graph` + `AddBranch` 实现条件路由:按输入内容分流到 `code_path` / `chat_path`。**纯 Lambda,零配置,无需 LLM**。

## 运行

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
go run ./graph_demo
```

预期输出:

```
"帮我写代码" -> [代码路径] 帮我写代码
"你好" -> [对话路径] 你好
```

## 核心代码

```go
graph := compose.NewGraph[string, string]()
graph.AddLambdaNode("router", compose.InvokableLambda(func(ctx, in string) (string, error) { return in, nil }))
graph.AddLambdaNode("code_path", ...)
graph.AddLambdaNode("chat_path", ...)

graph.AddEdge(compose.START, "router")
graph.AddBranch("router", compose.NewGraphBranch(
    func(ctx, in string) (string, error) {
        if strings.Contains(in, "代码") { return "code_path", nil }
        return "chat_path", nil
    },
    map[string]bool{"code_path": true, "chat_path": true},
))
graph.AddEdge("code_path", compose.END)
graph.AddEdge("chat_path", compose.END)
```

要点:`router` 原样返回输入,分支据此决定路由,**被选中路径收到同一份输入**(分支只路由不变换)。

## 相关文档

- [`../../03_graph/graph_basics.md`](../../03_graph/graph_basics.md) -- Graph DAG 编排详解
