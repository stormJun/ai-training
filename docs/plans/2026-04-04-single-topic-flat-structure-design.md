# Single-Topic Flat Structure Design

**Date:** 2026-04-04

## Goal

Refactor the repository from broad category folders such as `01_llm_api_and_tool_calling/` into a flat, numbered, single-topic layout where each top-level directory represents exactly one knowledge theme or one runnable project workspace.

## Why Change

The current topic-based structure is better than week-based naming, but several top-level directories still bundle multiple themes together. That makes review harder, makes the learning path less precise, and creates directories whose names describe a collection of topics rather than one topic.

The new structure should:

- keep ordered numbering for learning flow
- ensure each numbered directory has one clear theme
- preserve runnable Python workspaces by moving code with its local files together
- avoid splitting package roots or breaking local imports
- keep assignments, reference projects, archive material, and shared resources outside the numbered mainline

## Design Principles

### 1. One Directory, One Topic

Each numbered top-level directory must represent a single subject, for example:

- `02_llm_api_calls`
- `02_langgraph_basics`
- `11_fastapi_serving`

Broad collection names such as `llm_api_and_tool_calling` or `workflow_orchestration` should no longer exist as primary learning directories.

### 2. Runnable Units Stay Intact

If a topic is already a standalone project or app root, it moves as a whole. This applies to folders that contain their own:

- `pyproject.toml`
- `requirements.txt`
- `README.md`
- local modules
- test files
- configuration files

We do not split package roots just to satisfy naming neatness.

### 3. Small Script Topics Become Small Workspaces

For single-file or notebook-driven topics, create a minimal topic workspace and move the related files into it. These workspaces may be lightweight, but they still need:

- a topic-specific `README.md`
- the topic scripts or notebooks
- any required prompt, config, or sample data files

### 4. Support Material Follows the Topic

Docs, PDFs, diagrams, images, and examples move with the topic they explain. Shared or non-topic-specific assets stay outside the numbered mainline.

### 5. Non-Mainline Material Stays Outside

These directories remain as supporting structures:

- `assignments/`
- `reference_projects/`
- `archive/`
- `shared_assets/`
- `runtime_artifacts/`
- `third_party_sources/`
- `docs/plans/`

## Target Numbered Mainline

The current mainline is a flat ordered set of real top-level learning directories:

- `01_langchain_basics`
- `02_langgraph_basics`
- `03_intent_recognition_agent`
- `04_rag_and_retrieval`
- `05_ontology_and_foundry`
- `06_finetuning_and_data_processing_and_routing_react_and_tools`
- `07_tooling_and_automation_workflows`
- `08_multi_agent_frameworks`
- `09_dsl`
- `10_memory_patterns_basics`
- `11_fastapi_serving`
- `12_dockerized_service_apps`
- `13_kubernetes_deployment`
- `14_observability_and_serving_runtime`
- `15_python_concurrency_and_performance`
- `16_customer_service_platform`
- `17_model_extensions`
- `18_skill_engineering`
- `19_harness_engineering`
- `20_learning_methodology`
- `21_claudecode_source_analysis`
- `22_reinforcement_learning_notes`

## Mapping Strategy

### Broad Topic Folders

Current broad folders are decomposed by topic boundaries, not by week boundaries and not by raw file order. For example:

- `01_llm_api_and_tool_calling/foundations` becomes the first eight numbered topic workspaces
- `04_workflow_orchestration/langchain_langgraph_foundations` becomes several workflow-related workspaces
- `07_agent_memory_and_advanced_capabilities/foundations` becomes memory, FAISS, graph-memory, and reliability topic workspaces

### Existing Standalone Projects

Already-standalone projects move mostly unchanged:

- `03_rag_and_retrieval/local_rag_project` -> `05_local_rag_project`
- `03_rag_and_retrieval/qanything_case_study` -> `06_qanything_case_study`
- `04_workflow_orchestration/langgraph_demo_project` -> `23_langgraph_demo_project`
- `10_capstone_customer_service/customer_service_platform` -> `16_customer_service_platform`

### Existing Partial Split Work

The current workspace already contains uncommitted structural changes related to extension topics and RPA content. The refactor should build on those changes instead of reverting them.

## Compatibility Rules

- preserve file content and local relative imports whenever possible
- keep project roots intact for apps with their own dependency files
- update root navigation and repo guidelines after moving folders
- update topic `README.md` files when paths or run commands change
- prefer moving directories over rewriting Python code unless imports or config paths break

## Verification Strategy

After the refactor:

- scan for old broad top-level paths in tracked text files
- verify root docs point to the new numbered topics
- verify that moved standalone apps still contain their local dependency and config files
- run lightweight structure checks rather than full end-to-end app suites unless a path break is suspected

## Accepted Direction

The user approved **方案 1**: keep numbering, flatten the learning path, and ensure each numbered directory is a single topic while preserving runnable Python code.
