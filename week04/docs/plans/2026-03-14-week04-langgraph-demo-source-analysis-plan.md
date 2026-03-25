# Week04 LangGraph Demo Source Analysis Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an advanced source-analysis document for `week04-langgraph-demo` under `week04/docs` that explains architecture, state flow, execution paths, and extension points.

**Architecture:** The work is documentation-only. It relies on reading the existing demo source, extracting the real execution path across host and subagents, and writing a project-oriented guide that links concepts back to exact source files. Verification focuses on file existence, markdown readability, and accuracy against current source files.

**Tech Stack:** Markdown, Mermaid, Python project source under `week04-langgraph-demo`

---

### Task 1: Gather the exact source context

**Files:**
- Read: `week04-langgraph-demo/README.md`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/host_agent.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/stock_agent.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/analysis_agent.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/models.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/store.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/apps/stock_service.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/apps/analysis_service.py`
- Read: `week04-langgraph-demo/src/week04_langgraph_demo/run_all.py`
- Read: `week04-langgraph-demo/tests/test_demo.py`

**Step 1: Read the host and subagent source files**

Run: `sed -n '1,240p' week04-langgraph-demo/src/week04_langgraph_demo/host_agent.py`

Expected: The file shows `route_query`, `dispatch_local`, `dispatch_remote`, `pick_dispatch`, and `synthesize`.

**Step 2: Read shared infrastructure and service entrypoints**

Run: `sed -n '1,240p' week04-langgraph-demo/src/week04_langgraph_demo/store.py`

Expected: The file shows a cached static repository and query helpers used by the subagents.

**Step 3: Read the demo runner and tests**

Run: `sed -n '1,260p' week04-langgraph-demo/src/week04_langgraph_demo/run_all.py`

Expected: The file shows uvicorn startup, health checks, and a final `run_host_agent(..., mode="remote")` invocation.

### Task 2: Write and save the design record

**Files:**
- Create: `week04/docs/plans/2026-03-14-week04-langgraph-demo-source-analysis-design.md`

**Step 1: Summarize the approved documentation design**

Include: target reader, boundaries, chapter structure, and acceptance criteria.

**Step 2: Save the design file**

Run: `test -f week04/docs/plans/2026-03-14-week04-langgraph-demo-source-analysis-design.md`

Expected: Exit code 0.

### Task 3: Draft the source-analysis document

**Files:**
- Create: `week04/docs/week04-langgraph-demo源码解析.md`

**Step 1: Write the architecture overview**

Include:
- the demo's problem framing
- a Mermaid architecture graph
- host/subagent responsibility boundaries

**Step 2: Write the execution-flow sections**

Include:
- `HostState`, `StockAgentState`, `AnalysisState`
- the single-stock path
- the multi-stock analysis path
- `direct` and `remote` path comparison

**Step 3: Write the infrastructure and extension sections**

Include:
- `store.py`, `models.py`, `apps/*.py`, `run_all.py`, and tests
- simplified assumptions in the demo
- concrete upgrade directions toward a fuller multi-agent system

### Task 4: Verify the document against the current source

**Files:**
- Verify: `week04/docs/week04-langgraph-demo源码解析.md`

**Step 1: Check markdown headings and key terms**

Run: `rg -n "HostAgent|StockAgent|AnalysisAgent|direct|remote|store.py|run_all.py" week04/docs/week04-langgraph-demo源码解析.md`

Expected: The document contains all core sections and terms.

**Step 2: Review the rendered structure in plain text**

Run: `sed -n '1,260p' week04/docs/week04-langgraph-demo源码解析.md`

Expected: The article reads coherently and follows the approved outline.

### Task 5: Optional git integration

**Files:**
- Stage: `week04/docs/plans/2026-03-14-week04-langgraph-demo-source-analysis-design.md`
- Stage: `week04/docs/plans/2026-03-14-week04-langgraph-demo-source-analysis-plan.md`
- Stage: `week04/docs/week04-langgraph-demo源码解析.md`

**Step 1: Review git status**

Run: `git status --short week04/docs`

Expected: Only the intended documentation files appear as new or modified entries.

**Step 2: Commit if explicitly requested**

Run: `git add week04/docs && git commit -m "docs: add week04 langgraph demo source analysis"`

Expected: A focused documentation commit is created.
