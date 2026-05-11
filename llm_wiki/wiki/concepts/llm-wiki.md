---
type: "concept"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "LLM Wiki"
  - "第二大脑知识库"
tags:
  - "ai-training"
  - "llm-wiki"
  - "concept"
  - "concept/llm-wiki"
sources:
  - "docs/plans/2026-05-03-llm-wiki-management-design.md"
---

# LLM Wiki

## 一句话定义

LLM Wiki 是让 LLM 持续把原始资料整理成结构化、互相链接、可维护 Markdown wiki 的知识管理模式。

## 为什么重要

传统 RAG 每次回答时临时检索片段，知识不会自然累积。LLM Wiki 强调把资料逐步编译成长期可维护的知识层，让后续查询、学习路径、冲突检查和结构维护都能基于 wiki 继续演进。

## 在本仓库中的位置

本仓库通过 `llm_wiki/` 落地 LLM Wiki 管理层。现有课程目录是事实来源；`llm_wiki/wiki/` 负责维护跨主题地图、项目入口、概念关系和维护状态。

## 相关主题

- [RAG 与检索](../topics/rag-and-retrieval.md)
- [Agent Memory](../topics/memory-patterns.md)
- [Skill Engineering](../topics/skill-engineering.md)

## 相关项目

- [本地 RAG 项目](../projects/local-rag-project.md)
- [QAnything 案例](../projects/qanything-case-study.md)

## 来源引用

- `docs/plans/2026-05-03-llm-wiki-management-design.md`
- `llm_wiki/AGENTS.md`
- `llm_wiki/sources.yml`
- Andrej Karpathy LLM Wiki gist: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`

## 维护备注

本页是 LLM Wiki 方法论在本仓库中的解释入口。具体操作规则以 `llm_wiki/AGENTS.md` 为准。

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/concepts/rag|RAG]]
- [[wiki/concepts/agent-memory|Agent Memory]]
- [[wiki/concepts/skill-engineering|Skill Engineering]]
- [[wiki/concepts/schema-guided-ai-maintenance|Schema 驱动的 AI 维护]]
