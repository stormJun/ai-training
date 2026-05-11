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
- `21_langgraph_workflows`
- `40_fastapi_llm_serving`

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

The mainline becomes a flat ordered set of single-topic directories:

- `01_environment_setup`
- `02_llm_api_calls`
- `03_http_model_requests`
- `04_tool_calling_chat`
- `05_langchain_basics`
- `06_langgraph_basics`
- `07_llamaindex_basics`
- `08_intent_recognition_agent`
- `09_finetuning_overview`
- `10_massive_dataset_processing`
- `11_lora_qlora_training`
- `12_local_finetuning_platform`
- `13_llamaindex_retrieval_basics`
- `14_ragas_retrieval_evaluation`
- `15_graphrag_basics`
- `16_local_rag_project`
- `17_qanything_case_study`
- `18_prompt_templates`
- `19_output_parsing_and_chains`
- `20_routing_react_and_tools`
- `21_langgraph_workflows`
- `22_langgraph_service_apps`
- `23_langgraph_demo_project`
- `24_code_assistant_workflow`
- `25_vllm_wrapper_demo`
- `26_rpa_and_ai_workflow`
- `27_autogen_two_agent_chat`
- `28_crewai_basics`
- `29_langgraph_multi_agent`
- `30_mcp_basics`
- `31_mcp_langgraph_integration`
- `32_a2a_langgraph`
- `33_dsl_design_basics`
- `34_lark_dsl_examples`
- `35_dsl_agent_and_db_gateway`
- `36_memory_patterns_basics`
- `40_fastapi_llm_serving`
- `41_multimodal_fastapi_serving`
- `42_dockerized_service_apps`
- `43_kubernetes_deployment`
- `44_elk_observability`
- `45_prometheus_ollama_exporter`
- `46_ray_serve_streaming`
- `47_asyncio_basics`
- `48_asyncio_primitives_and_gil`
- `49_async_web_patterns`
- `50_performance_benchmarking`
- `51_async_multiprocess_hybrid`
- `52_customer_service_platform`
- `53_slm_optimization`
- `54_multimodal_clip_search`
- `55_reinforcement_learning`
- `56_skill_engineering`
- `57_harness_engineering`
- `58_learning_methodology`

## Mapping Strategy

### Broad Topic Folders

Current broad folders are decomposed by topic boundaries, not by week boundaries and not by raw file order. For example:

- `01_llm_api_and_tool_calling/foundations` becomes the first eight numbered topic workspaces
- `04_workflow_orchestration/langchain_langgraph_foundations` becomes several workflow-related workspaces
- `07_agent_memory_and_advanced_capabilities/foundations` becomes memory, FAISS, graph-memory, and reliability topic workspaces

### Existing Standalone Projects

Already-standalone projects move mostly unchanged:

- `03_rag_and_retrieval/local_rag_project` -> `16_local_rag_project`
- `03_rag_and_retrieval/qanything_case_study` -> `17_qanything_case_study`
- `04_workflow_orchestration/langgraph_demo_project` -> `23_langgraph_demo_project`
- `10_capstone_customer_service/customer_service_platform` -> `52_customer_service_platform`

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
