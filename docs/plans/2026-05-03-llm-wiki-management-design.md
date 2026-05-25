# LLM Wiki 管理层设计

**日期：** 2026-05-03

## 目标

为 `ai-training` 仓库增加一层 LLM Wiki 管理面，同时不改动现有课程内容。

现有仓库已经包含事实来源：编号主题目录、合并后的主题父目录、作业、参考项目、共享资料和运行产物。LLM Wiki 不替代这些目录，而是在它们之上维护一层面向人和 AI 助手的知识地图，用来解释主题关系、学习路径、项目入口和维护状态。

## 来源模式

本设计借鉴 Andrej Karpathy 的 LLM Wiki 思路：

- raw sources：原始资料，只读，作为事实来源
- wiki：LLM 生成和维护的结构化 Markdown 页面
- schema：告诉 LLM 如何摄入、查询和巡检 wiki 的规则

参考：<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>

在本仓库中，现有课程目录就是 raw sources；`llm_wiki/` 是把这些资料编译成长期可维护知识地图的管理层。

## 非目标

- 本阶段不移动、重命名或改写现有课程目录。
- 不把课程讲义全文复制进 wiki。
- 第一版不引入向量数据库、Web UI 或后台服务。
- 不把 wiki 变成代码、作业答案或项目配置的事实来源。
- 不允许 LLM 生成的总结在未评审时覆盖来源文件。

## 目录结构

在仓库根目录新增：

```text
llm_wiki/
  AGENTS.md
  sources.yml
  wiki/
    index.md
    curriculum-map.md
    concepts/
    topics/
    projects/
    assignments/
    maintenance/
```

## 核心文件职责

### `llm_wiki/AGENTS.md`

作为 LLM Wiki 的 schema 和操作手册，定义：

- 事实来源规则
- 摄入、查询、巡检流程
- 页面模板
- 来源引用要求
- 哪些文件可以由 AI 直接改
- 哪些文件只能提出修改建议

### `llm_wiki/sources.yml`

登记纳入 wiki 管理的来源路径。

第一批来源包括：

- `README.md`
- `AGENTS.md`
- `04_rag_and_retrieval/`
- `10_memory_patterns_basics/`
- `18_skill_engineering/`
- `04_rag_and_retrieval/05_local_rag_project/`
- `04_rag_and_retrieval/06_qanything_case_study/`

### `llm_wiki/wiki/index.md`

AI 助手回答仓库知识问题前应先读的入口页。它链接课程地图、概念索引、主题索引、项目索引、作业索引和维护索引。

### `llm_wiki/wiki/curriculum-map.md`

维护训练营的学习地图，说明主要阶段、主题依赖、项目入口和第一批纳入管理的区域。

## 页面类型

### 概念页

路径：`llm_wiki/wiki/concepts/*.md`

用于维护跨多个目录反复出现的概念。

模板：

```md
# 概念名

## 一句话定义
## 为什么重要
## 在本仓库中的位置
## 相关主题
## 相关项目
## 来源引用
## 维护备注
```

第一批概念页：

- `wiki/concepts/rag.md`
- `wiki/concepts/graphrag.md`
- `wiki/concepts/agent-memory.md`
- `wiki/concepts/skill-engineering.md`
- `wiki/concepts/llm-wiki.md`
- `wiki/concepts/schema-guided-ai-maintenance.md`

### 主题页

路径：`llm_wiki/wiki/topics/*.md`

用于把课程目录映射到训练营中的学习角色。

模板：

```md
# 主题名

## 仓库位置
## 在课程中的角色
## 学习者应掌握的内容
## 前置知识
## 后续主题
## 关键文件与入口
## 相关概念
## 维护备注
```

第一批主题页：

- `wiki/topics/rag-and-retrieval.md`
- `wiki/topics/memory-patterns.md`
- `wiki/topics/skill-engineering.md`

### 项目页

路径：`llm_wiki/wiki/projects/*.md`

用于总结可运行项目和项目型案例。

模板：

```md
# 项目名

## 仓库位置
## 项目目的
## 架构摘要
## 安装与运行入口
## 相关课程主题
## 相关概念
## 维护备注
```

第一批项目页：

- `wiki/projects/local-rag-project.md`
- `wiki/projects/qanything-case-study.md`

### 作业页

路径：`llm_wiki/wiki/assignments/*.md`

用于后续把作业与主题、概念和项目建立关系。第一批只创建索引，不展开每个作业。

### 维护页

路径：`llm_wiki/wiki/maintenance/*.md`

用于记录仓库级管理状态。

第一批维护页：

- `wiki/maintenance/topic-inventory.md`
- `wiki/maintenance/source-coverage.md`
- `wiki/maintenance/wiki-lint-report.md`
- `wiki/maintenance/open-questions.md`
- `wiki/maintenance/change-log.md`

## 操作规则

### 事实来源

现有仓库内容仍是事实来源：

- 编号主题目录
- 合并后的主题父目录
- 作业目录
- 参考项目
- 根目录 `README.md`
- 根目录 `AGENTS.md`

LLM Wiki 可以总结并链接这些文件，但不能无声地与它们冲突。发现冲突时，应写入 `wiki/maintenance/open-questions.md` 或 `wiki/maintenance/wiki-lint-report.md`。

### 摄入

摄入是指读取来源目录或文件，并更新 wiki 页面。

允许输出：

- 创建或更新概念页
- 创建或更新主题页
- 创建或更新项目页
- 更新 `curriculum-map.md`
- 更新维护页
- 提出来源 README 的修改建议，但不自动修改

每次摄入应记录：

- 来源路径
- 日期
- 影响的 wiki 页面
- 未解决问题

### 查询

查询是指优先通过 wiki 回答仓库知识问题。

推荐顺序：

1. 阅读 `llm_wiki/wiki/index.md`。
2. 沿相关 wiki 链接查找。
3. 如果 wiki 覆盖不足，检查 `sources.yml` 登记的来源路径。
4. 回答时同时给出综合结论和来源路径。
5. 如果答案中出现可复用知识，提出沉淀回 wiki 的建议。

### 巡检

巡检是指定期检查 wiki 的结构漂移和语义漂移。

检查项：

- 本地链接是否失效
- wiki 页面是否缺少来源引用
- 已登记来源是否缺少 wiki 覆盖
- 页面是否没有被索引页收录
- 概念定义是否重复
- wiki 页面是否与来源 README 冲突
- 目录迁移后是否存在过期路径
- 项目页是否缺少安装或运行入口

巡检结果写入 `wiki/maintenance/wiki-lint-report.md`。

## 第一批范围

第一批只覆盖小而有代表性的区域：

1. `04_rag_and_retrieval/`
2. `10_memory_patterns_basics/`
3. `18_skill_engineering/`
4. 根目录 `README.md`
5. 根目录 `AGENTS.md`

这组范围可以同时覆盖：

- 传统 RAG
- 长期记忆
- schema 驱动的 AI 行为
- 仓库导航
- 贡献和维护规则

## 人工评审策略

LLM Wiki 生成文件可以直接修改。现有课程内容需要单独评审。

默认策略：

- wiki-only 变更可以直接执行
- 来源 README 变更只列建议，除非用户明确要求
- 代码变更不属于 wiki 维护范围
- 作业示例答案不改，除非修复明确 bug

## 演进路径

### 阶段 1：Markdown 管理层

创建 `llm_wiki/` 结构并维护第一批页面。

### 阶段 2：轻量工具

增加不依赖 LLM 的确定性脚本：

- `llm_wiki/tools/validate_links.py`
- `llm_wiki/tools/source_coverage.py`
- `llm_wiki/tools/wiki_inventory.py`

### 阶段 3：AI 辅助摄入

让 AI 按 `llm_wiki/AGENTS.md` 对变更后的主题目录生成 wiki patch。

### 阶段 4：查询和维护集成

后续可接入命令行或 MCP 工具，让 AI 助手稳定查询 wiki、检查覆盖范围并更新维护报告。

## 验收标准

设计可进入实现的标准：

- `llm_wiki/` 有清晰结构和边界
- 第一批页面命名和范围明确
- wiki 不复制来源目录
- 摄入、查询、巡检规则明确
- 事实来源规则能保护现有课程内容
- 后续自动化可以在不改变概念模型的基础上增加

## 已确认方向

用 LLM Wiki 管理 `ai-training`。现有课程目录继续作为事实来源，新增 wiki 负责维护跨主题知识、学习路径和维护状态。
