---
type: "concept"
status: "active"
created: "2026-05-03"
updated: "2026-06-12"
aliases:
  - "Agent Memory"
  - "智能体记忆"
tags:
  - "ai-training"
  - "llm-wiki"
  - "concept"
  - "concept/memory"
sources:
  - "10_memory_patterns_basics/"
---

# Agent Memory

## 一句话定义

Agent Memory 是让智能体在一次或多次交互中保存、检索、压缩和复用信息的能力集合。

## 为什么重要

如果 RAG 解决的是“从外部资料找信息”，Memory 解决的是“系统如何长期积累自己的交互和状态”。LLM Wiki 管理层更接近长期记忆：它把资料持续整理成结构化页面，让知识产生复利。

## 在本仓库中的位置

相关内容集中在 `10_memory_patterns_basics/`，包括短期记忆、摘要记忆、滑动窗口、向量记忆、FAISS、知识图谱记忆、Redis 时序记忆，以及工具调用重试与降级。

## 相关主题

- [Agent Memory](../topics/memory-patterns.md)
- [RAG 与检索](../topics/rag-and-retrieval.md)
- [Skill Engineering](../topics/skill-engineering.md)

## 相关项目

- 暂无第一批项目页；后续可为 FAISS 记忆、知识图谱记忆或 Redis 记忆示例补项目页。

## 来源引用

- `10_memory_patterns_basics/`
- `10_memory_patterns_basics/TECH_DOC.md`
- `10_memory_patterns_basics/LLM-Memory核心观点-Anthropic与OpenAI.md`

## 维护备注

本页应维护 Memory 与 RAG、LLM Wiki、Agent 工程之间的关系，而不是逐个复写脚本说明。

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/topics/memory-patterns|Agent Memory]]
- [[wiki/concepts/rag|RAG]]
- [[wiki/concepts/skill-engineering|Skill Engineering]]
