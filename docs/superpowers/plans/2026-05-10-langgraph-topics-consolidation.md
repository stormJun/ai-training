# LangGraph Topics Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the advanced LangGraph topic directories into `02_langgraph_basics/` and repair repository-level navigation so `02_langgraph_basics/` becomes the unified entrypoint.

**Architecture:** This is a filesystem-first reorganization. Move the three target directories intact, then update the small set of active README files that present repository structure. Verification is based on path existence and targeted reference searches rather than application tests.

**Tech Stack:** git, shell utilities (`mv`, `test`, `find`, `rg`), Markdown documentation

---

### Task 1: Move the three LangGraph topic directories

**Files:**
- Create: `02_langgraph_basics/21_langgraph_workflows/`
- Create: `02_langgraph_basics/31_mcp_langgraph_integration/`
- Create: `02_langgraph_basics/32_a2a_langgraph/`
- Remove: `21_langgraph_workflows/`
- Remove: `30_agent_protocols_and_mcp/31_mcp_langgraph_integration/`
- Remove: `30_agent_protocols_and_mcp/32_a2a_langgraph/`

- [ ] **Step 1: Verify the source and destination paths before moving**

```bash
test -d 02_langgraph_basics
test -d 21_langgraph_workflows
test -d 30_agent_protocols_and_mcp/31_mcp_langgraph_integration
test -d 30_agent_protocols_and_mcp/32_a2a_langgraph
test ! -e 02_langgraph_basics/21_langgraph_workflows
test ! -e 02_langgraph_basics/31_mcp_langgraph_integration
test ! -e 02_langgraph_basics/32_a2a_langgraph
```

Expected: no output and exit code `0`.

- [ ] **Step 2: Move `21_langgraph_workflows` into `02_langgraph_basics/`**

```bash
mv 21_langgraph_workflows 02_langgraph_basics/
```

- [ ] **Step 3: Move `31_mcp_langgraph_integration` into `02_langgraph_basics/`**

```bash
mv 30_agent_protocols_and_mcp/31_mcp_langgraph_integration 02_langgraph_basics/
```

- [ ] **Step 4: Move `32_a2a_langgraph` into `02_langgraph_basics/`**

```bash
mv 30_agent_protocols_and_mcp/32_a2a_langgraph 02_langgraph_basics/
```

- [ ] **Step 5: Verify the new directory layout**

```bash
find 02_langgraph_basics -maxdepth 1 -type d | sort
```

Expected output contains:
- `02_langgraph_basics`
- `02_langgraph_basics/21_langgraph_workflows`
- `02_langgraph_basics/31_mcp_langgraph_integration`
- `02_langgraph_basics/32_a2a_langgraph`

- [ ] **Step 6: Commit the directory move**

```bash
git add 02_langgraph_basics 21_langgraph_workflows 30_agent_protocols_and_mcp
git commit -m "refactor: consolidate langgraph topics under basics"
```

### Task 2: Update repository navigation readmes

**Files:**
- Modify: `02_langgraph_basics/README.md`
- Modify: `README.md`
- Modify: `30_agent_protocols_and_mcp/README.md`

- [ ] **Step 1: Rewrite `02_langgraph_basics/README.md` as the unified LangGraph entrypoint**

Replace its contents with:

```md
# LangGraph 学习路径

本主题统一收纳 LangGraph 的基础示例、进阶工作流，以及与 MCP / A2A 结合的扩展示例。

## 内容

- `05-2langgraph.py`
  - LangGraph 最小入门示例
- `21_langgraph_workflows/`
  - LangGraph 工作流、RAG、记忆、HITL、Studio、源码理解
- `31_mcp_langgraph_integration/`
  - MCP 与 LangGraph 集成
- `32_a2a_langgraph/`
  - A2A 与 LangGraph 结合

## 建议学习顺序

1. 先看 `05-2langgraph.py`
2. 再看 `21_langgraph_workflows/`
3. 然后看 `31_mcp_langgraph_integration/`
4. 最后看 `32_a2a_langgraph/`

## 开始方式

- 基础示例可直接在本目录运行
- 进阶工作流请先阅读 `21_langgraph_workflows/README.md`
- 集成专题请分别阅读对应子目录 README
```

- [ ] **Step 2: Update the root `README.md` LangGraph entries to the new paths**

Change the LangGraph section so:
- the top-level entry for `21_langgraph_workflows/` becomes `02_langgraph_basics/`
- the protocol section no longer lists `31_mcp_langgraph_integration/` and `32_a2a_langgraph/` as children
- the `02_langgraph_basics/` description mentions the embedded `21_langgraph_workflows/`, `31_mcp_langgraph_integration/`, and `32_a2a_langgraph/`

- [ ] **Step 3: Update `30_agent_protocols_and_mcp/README.md` to remove the moved child topics**

Rewrite the file so it describes only the topics that remain in place and adds a note that LangGraph-related integration topics were moved to `../02_langgraph_basics/`.

- [ ] **Step 4: Review the modified markdown for stale navigation paths**

```bash
rg -n '21_langgraph_workflows/|31_mcp_langgraph_integration/|32_a2a_langgraph/' 强化学习系统学习笔记.md 02_langgraph_basics/强化学习系统学习笔记.md 30_agent_protocols_and_mcp/强化学习系统学习笔记.md
```

Expected: any remaining matches should reflect the new nested locations or an explicit migration note.

- [ ] **Step 5: Commit the README updates**

```bash
git add 强化学习系统学习笔记.md 02_langgraph_basics/强化学习系统学习笔记.md 30_agent_protocols_and_mcp/强化学习系统学习笔记.md
git commit -m "docs: update langgraph topic navigation"
```

### Task 3: Run repository-structure verification

**Files:**
- Verify: `02_langgraph_basics/`
- Verify: `README.md`
- Verify: `30_agent_protocols_and_mcp/README.md`

- [ ] **Step 1: Confirm the old source directories are gone**

```bash
test ! -e 21_langgraph_workflows
test ! -e 30_agent_protocols_and_mcp/31_mcp_langgraph_integration
test ! -e 30_agent_protocols_and_mcp/32_a2a_langgraph
```

Expected: no output and exit code `0`.

- [ ] **Step 2: Confirm the new paths exist**

```bash
test -d 02_langgraph_basics/21_langgraph_workflows
test -d 02_langgraph_basics/31_mcp_langgraph_integration
test -d 02_langgraph_basics/32_a2a_langgraph
```

Expected: no output and exit code `0`.

- [ ] **Step 3: Search active repository docs for stale top-level references**

```bash
rg -n '(^|[^/])21_langgraph_workflows/|30_agent_protocols_and_mcp/31_mcp_langgraph_integration|30_agent_protocols_and_mcp/32_a2a_langgraph' . \
  --glob '!**/.venv/**' \
  --glob '!runtime_artifacts/**' \
  --glob '!docs/plans/**' \
  --glob '!docs/superpowers/**' \
  --glob '!**/*.ipynb'
```

Expected: only intentionally retained historical references or notes remain.

- [ ] **Step 4: Inspect the final git status**

```bash
git status --short
```

Expected: only the intended LangGraph directory moves and README updates are present, plus any unrelated pre-existing user changes.

- [ ] **Step 5: Commit the verification state if additional doc adjustments were needed**

```bash
git add -A
git commit -m "chore: finalize langgraph topic consolidation"
```

If no extra adjustments were needed after verification, skip this commit.
