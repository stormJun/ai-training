# Eino 使用文档

本目录整理 [CloudWeGo Eino](https://www.cloudwego.io/zh/docs/eino/) 框架的使用文档与学习笔记。Eino 是用 Go 编写的 LLM 应用开发框架,提供组件抽象、Graph 编排、流式传输、回调、记忆等能力。

## 源码位置

Eino 源码位于本机另一目录,便于阅读源码对照:

```
/Users/songxijun/workspace/otherProject/eino
```

## 文档结构

```
26eino/
├── README.md                  # 本文件,文档索引
├── 01_overview/               # ✅ 框架总览:定位、核心概念、模块划分
├── 02_components/             # ✅ 组件抽象:ChatModel / Tool / Retriever / Embedding 等
│   └── demo/                  #    可运行 demo(ChatModel / Tool 调用 / ReAct agent)
├── 03_graph/                 # ✅ 编排层:Chain / Graph / Workflow / ReAct agent
├── 04_streaming/              # ✅ 流式传输:StreamReader/Writer、Convert、Merge、Copy / 自动衔接
├── 05_callback/               # ✅ 回调与可观测性:固定切点 AOP、Handler 构建、注入
├── 06_memory/                 # ✅ 记忆与对话上下文管理:Backend / 裁剪策略 / 中间件
├── 07_adk/                   # ✅ ADK 智能体开发套件:Agent 接口 / ChatModelAgent / 中间件 / 预置智能体 / HITL
├── 08_examples/              # 🔧 完整可运行示例
└── source_notes/              # ✅ 源码设计分析(stream.go 设计拆解)
```

## 编写约定

- 文档用中文,代码示例用 Go。
- 涉及源码结论时,标注 `源码路径:行号`,例如 `schema/stream.go:99`,方便点击跳转。
- 示例代码需要能独立运行,给出 `go run` 命令与依赖说明。
