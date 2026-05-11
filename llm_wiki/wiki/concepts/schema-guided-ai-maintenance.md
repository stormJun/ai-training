---
type: "concept"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "Schema 驱动的 AI 维护"
  - "Schema Guided AI Maintenance"
tags:
  - "ai-training"
  - "llm-wiki"
  - "concept"
  - "concept/schema"
sources:
  - "llm_wiki/AGENTS.md"
  - "llm_wiki/sources.yml"
---

# Schema 驱动的 AI 维护

## 一句话定义

Schema 驱动的 AI 维护，是用明确的目录结构、页面模板、来源登记和操作规则约束 AI 对知识库的维护行为。

## 为什么重要

没有 schema，LLM 容易把总结、改写、迁移和事实判断混在一起。对课程仓库来说，schema 可以让 AI 知道哪些文件能改、哪些只能引用、页面应该包含什么、冲突应该记录到哪里。

## 在本仓库中的位置

`llm_wiki/AGENTS.md` 是操作 schema，`llm_wiki/sources.yml` 是来源登记 schema，`llm_wiki/wiki/` 下的页面模板是内容 schema。

## 相关主题

- [Skill Engineering](../topics/skill-engineering.md)
- [Agent Memory](../topics/memory-patterns.md)

## 相关项目

- 暂无第一批项目页。

## 来源引用

- `llm_wiki/AGENTS.md`
- `llm_wiki/sources.yml`
- `docs/plans/2026-05-03-llm-wiki-management-design.md`
- `56_skill_engineering/README.md`

## 维护备注

当 wiki 结构变化时，应同步更新本页、`llm_wiki/AGENTS.md` 和 `llm_wiki/sources.yml`。

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[AGENTS|LLM Wiki 维护规则]]
- [[wiki/concepts/skill-engineering|Skill Engineering]]
- [[wiki/concepts/llm-wiki|LLM Wiki]]
- [[wiki/maintenance/wiki-lint-report|Wiki 巡检报告]]
