# Chain Demo

用 `compose.Chain` 的 fluent API 编排线性流水线:`string -> Lambda -> ChatModel -> Lambda -> string`,并演示同一 `Runnable` 的 `Invoke` 与 `Stream`。

## 运行

复用上级 `demo/.env`。在 `demo/` 目录下:

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
go run ./chain_demo
```

预期输出:

```
>> 已加载 .env
输出: Go语言（又称Golang）是谷歌于2009年开源…
=== Stream ===
Go 的并发以远轻于操作系统线程的 goroutine 为执行单元…
(共 1 个 chunk)
```

## 注意:Stream 只有 1 个 chunk

这正是 chain_basics §9 的"**InvokableLambda 流式退化**"实锤:链中 `InvokableLambda` 节点会把上游流读尽、算完再一次性发出,整链流式被压成一块。要真正逐块流式,需用 `StreamableLambda`/`TransformableLambda`。

## 相关文档

- [`../../03_graph/chain_basics.md`](../../03_graph/chain_basics.md) -- Chain 线性编排详解
