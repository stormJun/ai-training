---
type: "maintenance"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "开放问题"
tags:
  - "ai-training"
  - "llm-wiki"
  - "maintenance"
  - "maintenance/questions"
sources:
  - "docs/plans/2026-05-03-llm-wiki-management-design.md"
---

# 开放问题

## 当前问题

1. 是否需要把 `llm_wiki/` 入口链接加入根目录 `README.md`？
2. 是否需要为 `30_agent_protocols_and_mcp/` 增加第二批主题页？
3. 是否需要为 `52_customer_service_platform/` 建立项目级 wiki 页面？
4. 是否需要添加自动化脚本检查 wiki 内部链接？

## 当前决策

- 第一批实现只创建 `llm_wiki/` 管理层，不修改现有课程内容。
- 课程目录、README、作业和项目配置仍是事实来源。

## 来源引用

- `docs/plans/2026-05-03-llm-wiki-management-design.md`
- `llm_wiki/AGENTS.md`

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/maintenance/index|维护索引]]
- [[wiki/maintenance/source-coverage|来源覆盖]]
- [[wiki/maintenance/wiki-lint-report|Wiki 巡检报告]]
- [[wiki/concepts/llm-wiki|LLM Wiki]]
