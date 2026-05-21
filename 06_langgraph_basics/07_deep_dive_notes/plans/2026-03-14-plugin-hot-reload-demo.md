# Plugin Hot Reload Demo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runnable LangGraph demo under `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/` that shows plugin reload, graph rebuild, new-request cutover, and old-graph isolation.

**Architecture:** A `PluginManager` loads plugin modules from a package with `importlib`. A `GraphManager` builds a LangGraph app from the currently loaded plugins and swaps in a new compiled graph after reload. A small FastAPI API exposes `/chat`, `/reload`, and `/health`, while tests verify reload behavior using old and new graph instances.

**Tech Stack:** Python, LangGraph, FastAPI, pytest, importlib

---

### Task 1: Scaffold project and write failing tests

**Files:**
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/pyproject.toml`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/README.md`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/tests/conftest.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/tests/test_hot_reload.py`

**Step 1: Write the failing test**

Write tests for:
- plugin discovery returns initial tools
- graph rebuild picks up plugin changes
- old graph instance still uses old plugin behavior

**Step 2: Run test to verify it fails**

Run: `cd 04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo && python3 -m pytest -q`
Expected: FAIL because package/modules do not exist

### Task 2: Add minimal plugin and graph runtime

**Files:**
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/__init__.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/models.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/plugin_manager.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/graph_manager.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/plugins/__init__.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/plugins/greeting.py`
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/plugins/invoice.py`

**Step 1: Write minimal implementation**

Implement:
- plugin registry loading module tool lists
- graph creation from loaded tools
- graph swap on reload
- direct invocation API for tests

**Step 2: Run tests to verify partial pass/fail**

Run: `cd 04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo && python3 -m pytest tests/test_hot_reload.py -q`
Expected: some tests pass, remaining fail around API layer

### Task 3: Add FastAPI and reload endpoints

**Files:**
- Create: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/api.py`

**Step 1: Write failing API assertions**

Extend tests to cover:
- `/health`
- `/reload`
- `/chat`

**Step 2: Implement minimal API**

Expose:
- `GET /health`
- `POST /chat`
- `POST /reload`

**Step 3: Run tests to verify pass**

Run: `cd 04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo && python3 -m pytest -q`
Expected: PASS

### Task 4: Document usage

**Files:**
- Modify: `04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/README.md`

**Step 1: Document run steps**

Include:
- install
- run API
- simulate plugin edit + reload
- explain old/new graph behavior

**Step 2: Verify commands manually**

Run: `python -m plugin_hot_reload_demo.api`

### Task 5: Final verification

**Files:**
- No code changes required

**Step 1: Run full verification**

Run:
- `cd 04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo && python3 -m pytest -q`
- `cd 04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo && python3 -m plugin_hot_reload_demo.api`

Expected:
- tests pass
- server starts successfully
