# LLM Wiki 管理层实施计划

> **给 agentic workers：** 执行本计划时使用 `superpowers:executing-plans`，按任务逐项完成。步骤使用 checkbox 语法记录状态。

**目标：** 为 `ai-training` 创建第一版纯 Markdown 的 `llm_wiki/` 管理层，不改动现有课程内容。

**架构：** 在仓库根目录增加 `llm_wiki/`。现有课程目录作为来源资料，wiki 页面单独保存并维护主题关系、学习路径、项目入口和维护状态。第一批覆盖仓库导航、RAG、Memory、Skill Engineering 和两个 RAG 项目入口。

**技术栈：** Markdown、YAML、zsh、ripgrep、Git

---

## 文件结构

- 创建：`llm_wiki/AGENTS.md`
  - AI 助手维护 wiki 的操作规则。
- 创建：`llm_wiki/sources.yml`
  - 来源路径和对应 wiki 页面登记表。
- 创建：`llm_wiki/wiki/index.md`
  - 仓库知识查询入口。
- 创建：`llm_wiki/wiki/curriculum-map.md`
  - 跨主题课程地图。
- 创建：`llm_wiki/wiki/concepts/index.md`
  - 概念索引。
- 创建：`llm_wiki/wiki/concepts/rag.md`
- 创建：`llm_wiki/wiki/concepts/graphrag.md`
- 创建：`llm_wiki/wiki/concepts/agent-memory.md`
- 创建：`llm_wiki/wiki/concepts/skill-engineering.md`
- 创建：`llm_wiki/wiki/concepts/llm-wiki.md`
- 创建：`llm_wiki/wiki/concepts/schema-guided-ai-maintenance.md`
- 创建：`llm_wiki/wiki/topics/index.md`
  - 主题索引。
- 创建：`llm_wiki/wiki/topics/rag-and-retrieval.md`
- 创建：`llm_wiki/wiki/topics/memory-patterns.md`
- 创建：`llm_wiki/wiki/topics/skill-engineering.md`
- 创建：`llm_wiki/wiki/projects/index.md`
  - 项目索引。
- 创建：`llm_wiki/wiki/projects/local-rag-project.md`
- 创建：`llm_wiki/wiki/projects/qanything-case-study.md`
- 创建：`llm_wiki/wiki/assignments/index.md`
  - 作业索引，第一批只登记后续覆盖范围。
- 创建：`llm_wiki/wiki/maintenance/index.md`
  - 维护索引。
- 创建：`llm_wiki/wiki/maintenance/topic-inventory.md`
- 创建：`llm_wiki/wiki/maintenance/source-coverage.md`
- 创建：`llm_wiki/wiki/maintenance/wiki-lint-report.md`
- 创建：`llm_wiki/wiki/maintenance/open-questions.md`
- 创建：`llm_wiki/wiki/maintenance/change-log.md`

本实施不修改现有课程文件。

### 任务 1：创建 wiki 操作 schema

**文件：**

- 创建：`llm_wiki/AGENTS.md`
- 创建：`llm_wiki/sources.yml`

- [x] **步骤 1：创建 `llm_wiki/AGENTS.md`**

写入事实来源、编辑边界、查询、摄入、巡检和评审规则。

- [x] **步骤 2：创建 `llm_wiki/sources.yml`**

登记第一批来源：

- 根目录 `README.md`
- 根目录 `AGENTS.md`
- `04_rag_and_retrieval/`
- `10_memory_patterns_basics/`
- `18_skill_engineering/`
- `04_rag_and_retrieval/05_local_rag_project/`
- `04_rag_and_retrieval/06_qanything_case_study/`

- [x] **步骤 3：验证 schema 文件存在**

运行：

```bash
test -f llm_wiki/AGENTS.md
test -f llm_wiki/sources.yml
```

预期：两个命令退出状态都是 `0`。

### 任务 2：创建 wiki 导航页

**文件：**

- 创建：`llm_wiki/wiki/index.md`
- 创建：`llm_wiki/wiki/curriculum-map.md`
- 创建：`llm_wiki/wiki/concepts/index.md`
- 创建：`llm_wiki/wiki/topics/index.md`
- 创建：`llm_wiki/wiki/projects/index.md`
- 创建：`llm_wiki/wiki/assignments/index.md`
- 创建：`llm_wiki/wiki/maintenance/index.md`

- [x] **步骤 1：创建 wiki 总入口**

链接课程地图、概念索引、主题索引、项目索引、作业索引和维护索引。

- [x] **步骤 2：创建课程地图**

基于根目录 `README.md` 总结主要课程阶段，并突出第一批纳入管理的区域。

- [x] **步骤 3：创建分区索引页**

每个 wiki 分区都创建 `index.md`，确保所有页面都可以从 `llm_wiki/wiki/index.md` 访问。

- [x] **步骤 4：验证索引页存在**

运行：

```bash
find llm_wiki/wiki -maxdepth 2 -name 'index.md' | sort
```

预期输出包含：

```text
llm_wiki/wiki/assignments/index.md
llm_wiki/wiki/concepts/index.md
llm_wiki/wiki/index.md
llm_wiki/wiki/maintenance/index.md
llm_wiki/wiki/projects/index.md
llm_wiki/wiki/topics/index.md
```

### 任务 3：创建第一批主题页和概念页

**文件：**

- 创建：`llm_wiki/wiki/concepts/rag.md`
- 创建：`llm_wiki/wiki/concepts/graphrag.md`
- 创建：`llm_wiki/wiki/concepts/agent-memory.md`
- 创建：`llm_wiki/wiki/concepts/skill-engineering.md`
- 创建：`llm_wiki/wiki/concepts/llm-wiki.md`
- 创建：`llm_wiki/wiki/concepts/schema-guided-ai-maintenance.md`
- 创建：`llm_wiki/wiki/topics/rag-and-retrieval.md`
- 创建：`llm_wiki/wiki/topics/memory-patterns.md`
- 创建：`llm_wiki/wiki/topics/skill-engineering.md`

- [x] **步骤 1：创建概念页**

每个概念页包含：

- `一句话定义`
- `为什么重要`
- `在本仓库中的位置`
- `相关主题`
- `相关项目`
- `来源引用`
- `维护备注`

- [x] **步骤 2：创建主题页**

每个主题页包含：

- `仓库位置`
- `在课程中的角色`
- `学习者应掌握的内容`
- `前置知识`
- `后续主题`
- `关键文件与入口`
- `相关概念`
- `维护备注`

- [x] **步骤 3：验证第一批主题页和概念页存在**

运行：

```bash
for path in \
  llm_wiki/wiki/concepts/rag.md \
  llm_wiki/wiki/concepts/graphrag.md \
  llm_wiki/wiki/concepts/agent-memory.md \
  llm_wiki/wiki/concepts/skill-engineering.md \
  llm_wiki/wiki/concepts/llm-wiki.md \
  llm_wiki/wiki/concepts/schema-guided-ai-maintenance.md \
  llm_wiki/wiki/topics/rag-and-retrieval.md \
  llm_wiki/wiki/topics/memory-patterns.md \
  llm_wiki/wiki/topics/skill-engineering.md
do
  test -f "$path" || exit 1
done
```

预期：命令退出状态为 `0`。

### 任务 4：创建项目页和维护页

**文件：**

- 创建：`llm_wiki/wiki/projects/local-rag-project.md`
- 创建：`llm_wiki/wiki/projects/qanything-case-study.md`
- 创建：`llm_wiki/wiki/maintenance/topic-inventory.md`
- 创建：`llm_wiki/wiki/maintenance/source-coverage.md`
- 创建：`llm_wiki/wiki/maintenance/wiki-lint-report.md`
- 创建：`llm_wiki/wiki/maintenance/open-questions.md`
- 创建：`llm_wiki/wiki/maintenance/change-log.md`

- [x] **步骤 1：创建第一批项目页**

为 `04_rag_and_retrieval/` 下两个 RAG 项目型入口创建项目页。

- [x] **步骤 2：创建维护页**

记录第一批来源覆盖、初始巡检状态、开放问题和变更记录。

- [x] **步骤 3：验证维护页存在**

运行：

```bash
for path in \
  llm_wiki/wiki/maintenance/topic-inventory.md \
  llm_wiki/wiki/maintenance/source-coverage.md \
  llm_wiki/wiki/maintenance/wiki-lint-report.md \
  llm_wiki/wiki/maintenance/open-questions.md \
  llm_wiki/wiki/maintenance/change-log.md
do
  test -f "$path" || exit 1
done
```

预期：命令退出状态为 `0`。

### 任务 5：静态验证

**文件：**

- 验证：`llm_wiki/**`
- 验证：`docs/plans/2026-05-03-llm-wiki-management-design.md`
- 验证：`docs/plans/2026-05-03-llm-wiki-management-implementation-plan.md`

- [x] **步骤 1：搜索未完成标记**

运行：

```bash
rg -n -e 'TB''D' -e 'TO''DO' -e 'FIX''ME' -e '待''定' -e '占''位' -e 'place''holder' \
  llm_wiki \
  docs/plans/2026-05-03-llm-wiki-management-design.md \
  docs/plans/2026-05-03-llm-wiki-management-implementation-plan.md
```

预期：无匹配。

- [x] **步骤 2：列出创建的文件**

运行：

```bash
find llm_wiki -type f | sort
```

预期：输出包含本计划“文件结构”中列出的所有文件。

- [x] **步骤 3：验证 `sources.yml` 登记的来源路径存在**

运行：

```bash
for path in \
  README.md \
  AGENTS.md \
  04_rag_and_retrieval \
  10_memory_patterns_basics \
  18_skill_engineering \
  04_rag_and_retrieval/05_local_rag_project \
  04_rag_and_retrieval/06_qanything_case_study
do
  test -e "$path" || exit 1
done
```

预期：命令退出状态为 `0`。

- [x] **步骤 4：确认本实施没有改动课程内容**

运行：

```bash
git status --short llm_wiki docs/plans/2026-05-03-llm-wiki-management-design.md docs/plans/2026-05-03-llm-wiki-management-implementation-plan.md
```

预期：只显示本次新增的 `llm_wiki/` 文件和两份 plan/design 文档。
