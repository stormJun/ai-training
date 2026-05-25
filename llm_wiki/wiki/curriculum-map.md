---
type: "map"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "课程地图"
  - "训练营学习地图"
tags:
  - "ai-training"
  - "llm-wiki"
  - "map"
  - "curriculum"
sources:
  - "README.md"
---

# 课程地图

本页整理 `ai-training` 的主学习路径，并标记第一批纳入 LLM Wiki 管理的区域。

## 主要阶段

1. 基础能力：LangChain、LangGraph、LlamaIndex、工具调用、意图识别。
2. 微调与数据处理：数据集处理、LoRA/QLoRA、本地微调平台。
3. RAG 与检索：LlamaIndex 检索、Ragas 评测、GraphRAG、本地 RAG 项目、QAnything 案例。
4. 工作流与 Agent 工程：Prompt 模板、路由、ReAct、LangGraph 工作流、服务化应用、自动化工作流。
5. 多 Agent 与协议：AutoGen、CrewAI、LangGraph 多 Agent、MCP、MCP-LangGraph 集成、A2A。
6. DSL 与记忆：DSL 设计、Lark 示例、DSL Agent 网关、Agent Memory。
7. 服务化、部署与观测：FastAPI serving、多模态 serving、Docker、Kubernetes、ELK、Prometheus、Ray Serve、TTFT。
8. 异步与性能：asyncio、Future/Task/Executor/GIL、异步 Web、性能基准、协程与多进程混合。
9. 综合项目与扩展专题：智能客服平台、模型扩展、Skill Engineering、Harness Engineering、学习方法论。

## 第一批管理区域

- [RAG 与检索](topics/rag-and-retrieval.md)：覆盖 `04_rag_and_retrieval/`。
- [Agent Memory](topics/memory-patterns.md)：覆盖 `10_memory_patterns_basics/`。
- [Skill Engineering](topics/skill-engineering.md)：覆盖 `18_skill_engineering/`。

## 跨主题关系

- RAG 解决“如何从资料中找回相关信息”。
- Memory 解决“Agent 如何长期保存和复用信息”。
- Skill Engineering 解决“如何把可复用操作规范交给 AI 执行”。
- LLM Wiki 把这些思想合起来：课程目录保持为事实来源，wiki 负责长期维护结构化关系和学习路径。

## 来源引用

- `README.md`
- `04_rag_and_retrieval/README.md`
- `10_memory_patterns_basics/README.md`
- `18_skill_engineering/README.md`

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/topics/rag-and-retrieval|RAG 与检索]]
- [[wiki/topics/memory-patterns|Agent Memory]]
- [[wiki/topics/skill-engineering|Skill Engineering]]
- [[wiki/concepts/llm-wiki|LLM Wiki]]
