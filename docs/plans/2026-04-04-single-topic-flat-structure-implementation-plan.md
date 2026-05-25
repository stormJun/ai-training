# Single-Topic Flat Structure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the repository from broad numbered category folders into a flat numbered set of single-topic workspaces without breaking local runnable Python projects.

**Architecture:** Move existing standalone projects as intact roots, create lightweight topic workspaces for script- and notebook-based subjects, then repair repository navigation and path references. Prefer directory moves over code rewrites, and only touch Python imports or config when a move would otherwise break execution.

**Tech Stack:** Git, shell file moves, Python workspaces, Markdown docs, `rg`, `find`, `pytest` where lightweight checks exist

---

### Task 1: Capture the Approved Structure

**Files:**
- Create: `docs/plans/2026-04-04-single-topic-flat-structure-design.md`
- Create: `docs/plans/2026-04-04-single-topic-flat-structure-implementation-plan.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Step 1: Save the accepted design**

Write the approved flat single-topic structure into the design doc with explicit target directory names and migration rules.

**Step 2: Save the implementation plan**

Write this plan document with the numbered topic targets and execution order.

**Step 3: Update root navigation after the moves**

Rewrite `README.md` and `AGENTS.md` after the new structure exists so the repository docs match the new topology.

**Step 4: Verify doc references**

Run: `rg -n '01_llm_api_and_tool_calling|04_workflow_orchestration|07_agent_memory_and_advanced_capabilities' README.md AGENTS.md`

Expected: only intentional historical references remain, or no matches after the final rewrite.

### Task 2: Split the LLM and Finetuning Foundations into Topic Workspaces

**Files:**
- Move from: `01_llm_api_and_tool_calling/foundations/*`
- Move from: `02_finetuning_and_peft/foundations/*`
- Create: `01_environment_setup/README.md`
- Create: `02_llm_api_calls/README.md`
- Create: `03_http_model_requests/README.md`
- Create: `04_tool_calling_chat/README.md`
- Create: `05_langchain_basics/README.md`
- Create: `02_langgraph_basics/README.md`
- Create: `07_llamaindex_basics/README.md`
- Create: `03_intent_recognition_agent/README.md`
- Create: `01_finetuning_overview/README.md`
- Create: `02_massive_dataset_processing/README.md`
- Create: `03_lora_qlora_training/README.md`
- Create: `04_local_finetuning_platform/README.md`

**Step 1: Create new top-level topic directories**

Create the numbered topic roots for the first twelve topics.

**Step 2: Move grouped files by theme**

Move environment docs, API scripts, HTTP request examples, tool-calling chat examples, LangChain examples, LangGraph examples, LlamaIndex examples, and intent-recognition files into their dedicated roots. Move finetuning overview docs, MASSIVE dataset processing files, LoRA/QLoRA material, and the local finetuning platform into their own roots.

**Step 3: Keep runnable groups intact**

Keep `local_ft/` intact under `04_local_finetuning_platform/`, and keep dataset-processing scripts with the data files they require.

**Step 4: Add minimal topic READMEs**

Each new topic root gets a short `README.md` describing content and local run entry points.

**Step 5: Verify moved roots**

Run: `find 01_environment_setup 02_llm_api_calls 04_local_finetuning_platform -maxdepth 2 -type f | sort`

Expected: moved code and support files exist under the new single-topic roots.

### Task 3: Split RAG, Workflow, Multi-Agent, DSL, and Memory Topics

**Files:**
- Move from: `03_rag_and_retrieval/*`
- Move from: `04_workflow_orchestration/*`
- Move from: `05_multi_agent_and_protocols/foundations/*`
- Move from: `06_dsl_and_rule_engines/foundations/*`
- Move from: `07_agent_memory_and_advanced_capabilities/foundations/*`
- Create numbered topic roots `13_...` through `39_...`

**Step 1: Move intact project roots**

Move `local_rag_project`, `qanything_case_study`, `langgraph_demo_project`, `rpa_and_ai_workflow`, and memory-related standalone subprojects as whole directories into their final numbered topic roots.

**Step 2: Split script and notebook collections**

Group LlamaIndex, Ragas, GraphRAG, prompt templates, output parsing, routing, LangGraph workflows, Autogen, CrewAI, MCP, A2A, DSL basics, Lark examples, memory patterns, FAISS memory, graph memory, and Redis reliability into dedicated single-topic roots.

**Step 3: Preserve local data and helper files**

Keep DSL grammar files, generated DSL files, FAISS indexes, graph storage, prompt files, notebooks, and docs next to the scripts that use them.

**Step 4: Repair local imports or hard-coded relative paths**

If a moved topic references a former parent directory, update the path locally without changing runtime behavior.

**Step 5: Verify old broad folders are empty or removable**

Run: `find 03_rag_and_retrieval 04_workflow_orchestration 05_multi_agent_and_protocols 06_dsl_and_rule_engines 07_agent_memory_and_advanced_capabilities -mindepth 1 -maxdepth 2`

Expected: only intentionally retained support material remains, or the old broad roots are ready for removal.

### Task 4: Split Serving, Concurrency, Capstone, and Extension Topics

**Files:**
- Move from: `08_serving_deployment_and_observability/foundations/*`
- Move from: `09_python_async_and_performance/foundations/*`
- Move from: `10_capstone_customer_service/customer_service_platform`
- Move from: `11_extension_topics/*`
- Create numbered topic roots `40_...` through `58_...`

**Step 1: Move serving and deployment topic roots**

Split FastAPI serving, multimodal serving, Dockerized workflow app, Kubernetes deployment, ELK, Prometheus exporter, and Ray demos into dedicated numbered roots.

**Step 2: Move concurrency topics**

Split asyncio basics, task/future/executor topics, I/O concurrency patterns, benchmarking/profiling material, and hybrid multiprocess-async examples into dedicated roots.

**Step 3: Move capstone**

Move `10_capstone_customer_service/customer_service_platform` intact to `16_customer_service_platform/`.

**Step 4: Flatten extension topics**

Move SLM optimization, CLIP search, reinforcement learning, skill engineering, harness engineering, and learning methodology from `11_extension_topics/` into their own numbered top-level roots.

**Step 5: Verify top-level numbered set**

Run: `find . -maxdepth 1 -type d | sort`

Expected: the main learning path is represented by single-topic numbered roots rather than broad category roots.

### Task 5: Repair Repository References and Run Structural Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: topic `README.md` files whose paths changed
- Modify: any `pyproject.toml`, script, or markdown file with broken moved paths

**Step 1: Rewrite root documentation**

Update `README.md` and `AGENTS.md` to describe the new flat single-topic layout and example commands.

**Step 2: Search for stale paths**

Run:

```bash
rg -n '01_llm_api_and_tool_calling|02_finetuning_and_peft|03_rag_and_retrieval|04_workflow_orchestration|05_multi_agent_and_protocols|06_dsl_and_rule_engines|07_agent_memory_and_advanced_capabilities|08_serving_deployment_and_observability|09_python_async_and_performance|10_capstone_customer_service|11_extension_topics' . --glob '!**/.git/**' --glob '!**/.venv/**'
```

Expected: only historical notes, archived material, or intentional references remain.

**Step 3: Run focused structure checks**

Run:

```bash
git status --short
find . -maxdepth 1 -type d | sort
```

Expected: the workspace reflects the intended move set and no surprise top-level category folders remain.

**Step 4: Summarize remaining manual risks**

Record any directories that still need functional test runs because they are too large or too environment-dependent for a lightweight verification pass.
