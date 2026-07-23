package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/cloudwego/eino/compose"
)

// 本 demo 演示 Graph + Branch：按输入内容路由到不同路径(纯 Lambda，零配置，无需 LLM)。
// 运行（在 demo/ 目录下）：go run ./graph_demo

func main() {
	ctx := context.Background()

	graph := compose.NewGraph[string, string]()

	// router 原样返回输入，分支条件据此决定路由，被选中路径收到同一份输入
	graph.AddLambdaNode("router", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
		return in, nil
	}))
	graph.AddLambdaNode("code_path", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
		return "[代码路径] " + in, nil
	}))
	graph.AddLambdaNode("chat_path", compose.InvokableLambda(func(ctx context.Context, in string) (string, error) {
		return "[对话路径] " + in, nil
	}))

	graph.AddEdge(compose.START, "router")
	graph.AddBranch("router", compose.NewGraphBranch(
		func(ctx context.Context, in string) (string, error) {
			if strings.Contains(in, "代码") {
				return "code_path", nil
			}
			return "chat_path", nil
		},
		map[string]bool{"code_path": true, "chat_path": true},
	))
	graph.AddEdge("code_path", compose.END)
	graph.AddEdge("chat_path", compose.END)

	runnable, err := graph.Compile(ctx)
	if err != nil {
		log.Fatalf("Compile 失败: %v", err)
	}

	for _, q := range []string{"帮我写代码", "你好"} {
		out, err := runnable.Invoke(ctx, q)
		if err != nil {
			log.Fatalf("Invoke 失败: %v", err)
		}
		fmt.Printf("%q -> %s\n", q, out)
	}
}
