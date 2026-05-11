---
type: "maintenance"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "变更记录"
tags:
  - "ai-training"
  - "llm-wiki"
  - "maintenance"
  - "maintenance/changelog"
sources:
  - "llm_wiki/sources.yml"
---

# 变更记录

## 2026-05-03

- 创建 `llm_wiki/` 管理层骨架。
- 创建 `llm_wiki/AGENTS.md`，定义 wiki 维护边界和操作流程。
- 创建 `llm_wiki/sources.yml`，登记第一批来源路径。
- 创建 wiki 入口页、课程地图、概念索引、主题索引、项目索引、作业索引和维护索引。
- 创建第一批概念页：RAG、GraphRAG、Agent Memory、Skill Engineering、LLM Wiki、Schema 驱动的 AI 维护。
- 创建第一批主题页：RAG 与检索、Agent Memory、Skill Engineering。
- 创建第一批项目页：本地 RAG 项目、QAnything 案例。
- 创建维护页：主题清单、来源覆盖、Wiki 巡检报告、开放问题、变更记录。
- 将第一批 wiki 页面和两份计划文档统一为中文。
- 完成静态验证：文件存在性、来源路径、未完成标记和变更范围。
- 完成 Obsidian 化：为 Markdown 页面补充 YAML frontmatter、aliases、tags、sources 和 Obsidian 双链连接。
- 更新 `llm_wiki/AGENTS.md`，加入 Obsidian 页面标准。

## 来源引用

- `llm_wiki/sources.yml`
- `docs/plans/2026-05-03-llm-wiki-management-implementation-plan.md`

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/maintenance/index|维护索引]]
- [[wiki/maintenance/source-coverage|来源覆盖]]
- [[wiki/maintenance/wiki-lint-report|Wiki 巡检报告]]
- [[wiki/concepts/llm-wiki|LLM Wiki]]
