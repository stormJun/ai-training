---
type: "topic"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "Agent Memory"
  - "记忆模式"
tags:
  - "ai-training"
  - "llm-wiki"
  - "topic"
  - "topic/memory"
sources:
  - "10_memory_patterns_basics/强化学习系统学习笔记.md"
---

# Agent Memory

## 仓库位置

- `10_memory_patterns_basics/`

## 在课程中的角色

本主题负责讲解 Agent 如何保存、压缩、检索和复用上下文，是从“单次 RAG 查询”走向“长期可积累系统”的关键桥梁。

## 学习者应掌握的内容

- 短期记忆和线程级会话持久化
- 摘要记忆与上下文压缩
- 滑动窗口记忆
- 向量记忆与 FAISS
- 知识图谱记忆
- Redis 时序记忆
- 工具调用重试与降级

## 前置知识

- LLM 对话基础
- RAG 与检索基础
- Python 脚本运行和依赖管理

## 后续主题

- Skill Engineering
- 多 Agent 框架
- MCP 与 Agent 协议
- LLM Wiki 知识库维护

## 关键文件与入口

- `10_memory_patterns_basics/README.md`
- `10_memory_patterns_basics/TECH_DOC.md`
- `10_memory_patterns_basics/p04-shortMEM.py`
- `10_memory_patterns_basics/p06-summaryMEM.py`
- `10_memory_patterns_basics/p08-vectorMEM.py`
- `10_memory_patterns_basics/p09-faissMEM.py`
- `10_memory_patterns_basics/p10-KnowledgeTripleMEM.py`
- `10_memory_patterns_basics/p11-redisMEM.py`

## 相关概念

- [Agent Memory](../concepts/agent-memory.md)
- [RAG](../concepts/rag.md)
- [LLM Wiki](../concepts/llm-wiki.md)

## 维护备注

本主题中已有本地运行产物和索引目录；wiki 只引用结构和入口，不把运行产物纳入知识源。

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/curriculum-map|课程地图]]
- [[wiki/concepts/agent-memory|Agent Memory]]
- [[wiki/concepts/rag|RAG]]
- [[wiki/topics/rag-and-retrieval|RAG 与检索]]
- [[wiki/topics/skill-engineering|Skill Engineering]]
