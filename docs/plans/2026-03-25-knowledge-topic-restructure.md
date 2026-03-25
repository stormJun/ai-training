# Knowledge Topic Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the existing `legacy week-based`-centric repository layout with a knowledge-topic-oriented structure and update key repository references in one coordinated migration.

**Architecture:** Perform the migration in three layers: create the new top-level information architecture, move existing week/homework/project directories into their new topic-based homes, then repair repository-facing documentation and path references so the new structure is navigable. Keep code content intact whenever possible and prefer directory moves over file-by-file rewrites.

**Tech Stack:** Git, zsh shell utilities, ripgrep, Markdown, Python project metadata, Jupyter notebook metadata

---

### Task 1: Create the new top-level knowledge-topic structure

**Files:**
- Create: `01_llm_api_and_tool_calling/`
- Create: `02_finetuning_and_peft/`
- Create: `03_rag_and_retrieval/`
- Create: `04_workflow_orchestration/`
- Create: `05_multi_agent_and_protocols/`
- Create: `06_dsl_and_rule_engines/`
- Create: `07_agent_memory_and_advanced_capabilities/`
- Create: `08_serving_deployment_and_observability/`
- Create: `09_python_async_and_performance/`
- Create: `10_capstone_customer_service/`
- Create: `assignments/`
- Create: `reference_projects/`
- Create: `third_party_sources/`
- Create: `shared_assets/`
- Create: `runtime_artifacts/`
- Create: `archive/`

**Step 1: Create the directory skeleton**

Run:

```bash
mkdir -p \
  01_llm_api_and_tool_calling \
  02_finetuning_and_peft \
  03_rag_and_retrieval \
  04_workflow_orchestration \
  05_multi_agent_and_protocols \
  06_dsl_and_rule_engines \
  07_agent_memory_and_advanced_capabilities \
  08_serving_deployment_and_observability \
  09_python_async_and_performance \
  10_capstone_customer_service \
  assignments \
  reference_projects \
  third_party_sources \
  shared_assets \
  runtime_artifacts \
  archive
```

**Step 2: Verify the new directory skeleton**

Run:

```bash
find . -maxdepth 1 -type d | sort
```

Expected: all new topic directories appear at repository root.

### Task 2: Move course content from week names to knowledge-topic names

**Files:**
- Move: `01_llm_api_and_tool_calling/foundations -> 01_llm_api_and_tool_calling/foundations`
- Move: `02_finetuning_and_peft/foundations -> 02_finetuning_and_peft/foundations`
- Move: `03_rag_and_retrieval/llamaindex_and_ragas -> 03_rag_and_retrieval/llamaindex_and_ragas`
- Move: `03_rag_and_retrieval/local_rag_project -> 03_rag_and_retrieval/local_rag_project`
- Move: `03_rag_and_retrieval/qanything_case_study -> 03_rag_and_retrieval/qanything_case_study`
- Move: `04_workflow_orchestration/langchain_langgraph_foundations -> 04_workflow_orchestration/langchain_langgraph_foundations`
- Move: `04_workflow_orchestration/langgraph_demo_project -> 04_workflow_orchestration/langgraph_demo_project`
- Move: `05_multi_agent_and_protocols/foundations -> 05_multi_agent_and_protocols/foundations`
- Move: `06_dsl_and_rule_engines/foundations -> 06_dsl_and_rule_engines/foundations`
- Move: `07_agent_memory_and_advanced_capabilities/foundations -> 07_agent_memory_and_advanced_capabilities/foundations`
- Move: `08_serving_deployment_and_observability/foundations -> 08_serving_deployment_and_observability/foundations`
- Move: `09_python_async_and_performance/foundations -> 09_python_async_and_performance/foundations`
- Move: `10_capstone_customer_service/customer_service_platform -> 10_capstone_customer_service/customer_service_platform`

**Step 1: Move course directories**

Use `mv` so Git tracks large renames efficiently.

**Step 2: Verify the new locations**

Run:

```bash
find 01_llm_api_and_tool_calling 02_finetuning_and_peft 03_rag_and_retrieval 04_workflow_orchestration 05_multi_agent_and_protocols 06_dsl_and_rule_engines 07_agent_memory_and_advanced_capabilities 08_serving_deployment_and_observability 09_python_async_and_performance 10_capstone_customer_service -maxdepth 2 -type d | sort
```

Expected: each former `legacy week-based` directory now lives under a topic directory.

### Task 3: Move homework, examples, shared projects, and legacy material

**Files:**
- Move: `assignments/rag_retrieval_homework`
- Move: `assignments/advanced_rag_homework`
- Move: `assignments/workflow_orchestration_homework`
- Move: `assignments/multi_agent_homework`
- Move: `homework_examples -> assignments/examples`
- Move: `projects -> reference_projects`
- Move: `archive/pre_course_utilities`
- Move: `archive/intermediate_materials`
- Keep: `scripts/`
- Keep: `logs/` unless later recategorized manually

**Step 1: Move supplemental directories**

Use `mv` for each directory.

**Step 2: Verify the supporting directories**

Run:

```bash
find assignments reference_projects archive -maxdepth 2 -type d | sort
```

Expected: homework, examples, reference projects, and archived material appear in their new homes.

### Task 4: Repair root documentation and repository guidance

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

**Step 1: Rewrite the repository overview**

Update root navigation to describe topic-based learning paths instead of week-based folders.

**Step 2: Rewrite repository guidelines**

Update `AGENTS.md` so future work references topic directories, assignments, and reference projects instead of `legacy week-based`.

**Step 3: Verify no broken top-level links remain**

Run:

```bash
rg -n "week0[0-9]|10_capstone_customer_service/customer_service_platform|archive/intermediate_materials|archive/pre_course_utilities" README.md AGENTS.md
```

Expected: no week-based root guidance remains, aside from intentional historical references if explicitly documented.

### Task 5: Repair high-value README and setup references

**Files:**
- Modify: moved course `README.md` files under the new topic directories
- Modify: selected setup scripts and metadata files containing legacy week references or path-shaped package names

**Step 1: Update course README entry points**

Fix `cd` commands and any self-referential path examples inside the moved course readmes.

**Step 2: Update important package names and setup hints**

Fix obvious `pyproject.toml` names, shell setup scripts, and kernel display names where the old week names would confuse users.

**Step 3: Preserve historical content where path replacement is risky**

Leave notebook output cells and archival research artifacts unchanged unless they affect active navigation or execution.

### Task 6: Run residue checks and sanity verification

**Files:**
- Verify: entire repository

**Step 1: Search for outdated active path references**

Run:

```bash
rg -n "cd week0[0-9]|cd 10_capstone_customer_service/customer_service_platform|week0[0-9]/README|10_capstone_customer_service/customer_service_platform/README|name = \"week0[0-9]|name = \"10_capstone_customer_service/customer_service_platform" . --glob '!**/.venv/**' --glob '!**/__pycache__/**' --glob '!**/.git/**' --glob '!**/node_modules/**'
```

Expected: only low-value historical references remain, primarily in notebook outputs or archived documents.

**Step 2: Check git rename health**

Run:

```bash
git status --short
```

Expected: a clean set of directory moves and documentation changes, without accidental edits in transient caches.

**Step 3: Commit the migration**

```bash
git add -A
git commit -m "refactor: reorganize repository by knowledge topics"
```
