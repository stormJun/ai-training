---
type: "schema"
status: "active"
created: "2026-05-03"
updated: "2026-05-03"
aliases:
  - "LLM Wiki 维护规则"
  - "Wiki Schema"
tags:
  - "ai-training"
  - "llm-wiki"
  - "schema"
  - "maintenance"
sources:
  - "llm_wiki/sources.yml"
---

# LLM Wiki 维护规则

本目录是 `ai-training` 仓库的 LLM Wiki 管理层。它负责总结、链接和维护现有课程资料之间的关系，但不是代码、作业、项目配置或课程原文的事实来源。

## 事实来源

事实来源保留在 `llm_wiki/` 之外：

- 根目录 `README.md`
- 根目录 `AGENTS.md`
- 编号主题目录
- 合并后的主题父目录
- `assignments/`
- `reference_projects/`
- 各项目自己的 README 与配置文件

LLM Wiki 可以解释这些来源、建立交叉引用、记录维护状态，但不能无声地覆盖或否定来源文件。发现冲突时，应记录到 `wiki/maintenance/open-questions.md` 或 `wiki/maintenance/wiki-lint-report.md`。

## 编辑边界

默认允许：

- 创建或修改 `llm_wiki/` 下的文件
- 更新 `llm_wiki/sources.yml` 中的来源覆盖记录
- 阅读已登记来源路径后更新 wiki 页面

需要用户明确要求：

- 修改根目录 `README.md`
- 修改根目录 `AGENTS.md`
- 修改课程 README
- 修改代码、Notebook、作业、示例答案或项目配置

## 查询流程

回答仓库知识类问题时：

1. 先读 `llm_wiki/wiki/index.md`。
2. 沿链接阅读相关概念页、主题页、项目页、作业页或维护页。
3. 如果 wiki 覆盖不足，再检查 `llm_wiki/sources.yml` 中登记的来源路径。
4. 回答时给出相关来源路径。
5. 如果答案中出现可复用知识，应提出或直接应用仅限 wiki 的更新。

## 摄入流程

摄入是指把来源资料整理成 wiki 更新。

每次摄入时：

1. 在 `llm_wiki/sources.yml` 中确认来源条目。
2. 阅读来源 README 和附近高价值 Markdown 文件。
3. 优先更新现有 wiki 页面，再创建新页面。
4. 页面应作为地图和索引，不复制完整课程内容。
5. 每个涉及仓库事实的页面都要写明来源路径。
6. 在 `wiki/maintenance/source-coverage.md` 记录覆盖变化。
7. 在 `wiki/maintenance/change-log.md` 记录重要变更。

## 巡检流程

巡检是指检查 wiki 是否与仓库结构和来源内容发生漂移。

需要检查：

- 相对链接是否失效
- 页面是否缺少来源引用
- 已登记来源是否缺少 wiki 覆盖
- 页面是否没有被分区索引收录
- 概念定义是否重复或冲突
- 来源路径是否已经不存在
- 项目页是否缺少安装或运行入口

巡检结果写入 `wiki/maintenance/wiki-lint-report.md`。

## 页面标准

每个 Markdown 页面都应保持 Obsidian 友好：

- 文件顶部必须有 YAML frontmatter。
- frontmatter 至少包含 `type`、`status`、`created`、`updated`、`aliases`、`tags`。
- 涉及仓库事实的页面应在 frontmatter 的 `sources` 中列出来源路径。
- 页面正文保留普通 Markdown 链接，便于 GitHub、IDE 和终端阅读。
- 页面末尾增加 `## Obsidian 连接`，使用 Obsidian 双链连接中心页、相关主题、相关概念、相关项目或维护页。
- 每个页面至少连接到 `[[wiki/index|AI 工程化训练营 LLM Wiki]]` 或对应分区索引，避免 Graph View 中出现孤立点。

概念页应包含：

- `一句话定义`
- `为什么重要`
- `在本仓库中的位置`
- `相关主题`
- `相关项目`
- `来源引用`
- `维护备注`

主题页应包含：

- `仓库位置`
- `在课程中的角色`
- `学习者应掌握的内容`
- `前置知识`
- `后续主题`
- `关键文件与入口`
- `相关概念`
- `维护备注`

项目页应包含：

- `仓库位置`
- `项目目的`
- `架构摘要`
- `安装与运行入口`
- `相关课程主题`
- `相关概念`
- `维护备注`

## 评审策略

基于已登记来源路径的 wiki-only 变更可以直接执行。涉及来源文件的变更，除非用户明确要求，否则只作为建议列出。

第一批实现覆盖：

- 根目录导航
- `04_rag_and_retrieval/`
- `10_memory_patterns_basics/`
- `18_skill_engineering/`
- `04_rag_and_retrieval/` 下的 RAG 项目入口页

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/maintenance/index|维护索引]]
- [[wiki/concepts/schema-guided-ai-maintenance|Schema 驱动的 AI 维护]]
- [[wiki/concepts/llm-wiki|LLM Wiki]]
