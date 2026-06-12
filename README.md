# AI 工程化训练营目录总览

本仓库现在按“编号主线 + 少量合并父目录”的方式组织。大多数编号目录承载一个知识主题或一个独立项目；对强相关的连续主题，会放进同一个编号父目录下，减少顶层目录数量。仓库只保留根目录 `README.md` 作为总览入口，具体内容直接进入对应目录查看代码、Notebook、讲义或配置文件。

## 主线目录

### 01-03 基础能力

- `01_langchain_basics/`
  - LangChain 入门脚本
- `02_langgraph_basics/`
  - LangGraph 学习主线，包含 `01_intro/`、`02_workflows/`、`03_service_apps/`、`04_demo_project/`、`05_multi_agent/`、`06_protocols_and_integrations/`、`07_deep_dive_notes/`
- `03_intent_recognition_agent/`
  - 意图识别与多智能体示例

### 04-05 检索与知识建模

- `04_rag_and_retrieval/`
  - 合并后的父目录，收纳 RAG 与检索相关主题，并补充纳入 `01_llamaindex_basics/`
  - 子目录：`01_llamaindex_basics/`、`02_llamaindex_retrieval_basics/`、`03_ragas_retrieval_evaluation/`、`04_graphrag_basics/`、`05_local_rag_project/`、`06_qanything_case_study/`
- `05_ontology_and_foundry/`
  - 本体、知识建模与 Foundry 相关内容

### 06-08 工作流与 Agent 工程

- `06_finetuning_and_data_processing_and_routing_react_and_tools/`
  - 当前收纳 Router、ReAct、工具调用，以及迁入的 `09-12` 微调与数据处理内容
  - 子目录：`09_finetuning_and_data_processing/`
- `06_finetuning_and_data_processing_and_routing_react_and_tools/01_finetuning_and_data_processing/`
  - 保留原 09-12 微调与数据处理父目录结构
  - 子目录：`01_finetuning_overview/`、`02_massive_dataset_processing/`、`03_lora_qlora_training/`、`04_local_finetuning_platform/`
- `07_tooling_and_automation_workflows/`
  - 合并后的父目录，收纳 24-26 三个相近主题
  - 子目录：`01_code_assistant_workflow/`、`02_vllm_wrapper_demo/`、`03_rpa_and_ai_workflow/`

### 09-10 DSL 与记忆能力

- `09_dsl/`
  - 合并后的 DSL 父目录，收纳 DSL 基础、Lark DSL 示例、DSL Agent/数据库网关，以及两套 DSL reference project
  - 子目录：`01_dsl_design_basics/`、`02_lark_dsl_examples/`、`03_dsl_agent_and_db_gateway/`、`reference_projects/project6_1/`、`reference_projects/project6_2/`
- `10_memory_patterns_basics/`
  - 合并后的 Agent Memory 专题，包含记忆模式、向量记忆、知识图谱记忆、Redis 记忆与可靠性

### 11-14 服务化、部署与观测

- `11_fastapi_serving/`
  - FastAPI 服务主题，包含基础 LLM 服务和 `multimodal/` 多模态示例
  - 子目录：`multimodal/`
- `12_dockerized_service_apps/`
  - Docker 化服务应用
- `13_kubernetes_deployment/`
  - Kubernetes 部署
- `14_observability_and_serving_runtime/`
  - 合并后的父目录，收纳 44-46 与 59 这组可观测性和 serving runtime 主题
  - 子目录：`01_elk_observability/`、`02_prometheus_ollama_exporter/`、`03_ray_serve_streaming/`、`04_ttft_and_llm_serving_latency/`

### 15-16 并发性能与综合项目

- `15_python_concurrency_and_performance/`
  - 合并后的并发与性能父目录，收纳 asyncio/GIL、异步 Web、性能分析与异步+多进程混合调度
  - 子目录：`01_asyncio_and_gil_basics/`、`02_async_web_patterns/`、`03_performance_benchmarking/`、`04_async_multiprocess_hybrid/`
- `16_customer_service_platform/`
  - 智能客服综合项目

### 17-22 扩展专题

- `17_model_extensions/`
  - 合并后的父目录，当前收纳小模型优化与多模态检索两个模型扩展主题
  - 子目录：`01_slm_optimization/`、`02_multimodal_clip_search/`
- `18_skill_engineering/`
  - Skill / Prompt 工程扩展资料
- `19_harness_engineering/`
  - Harness Engineering 与上下文工程
- `20_learning_methodology/`
  - 学习方法论
- `21_claudecode_source_analysis/`
  - Claude Code / Codex 源码分析与实现理解
- `22_reinforcement_learning_notes/`
  - 强化学习系统学习笔记，包含并入的 Q-Learning 补充资料与演示项目

## 其他目录

- `assignments/`
  - 课程作业与示例答案
- `reference_projects/`
  - 独立参考项目
- `archive/`
  - 历史资料与非主线内容
- `third_party_sources/`
  - 第三方引入源码
- `shared_assets/`
  - 共享资料、遗留概览与辅助笔记
- `runtime_artifacts/`
  - 运行产物与本地环境迁移残留
- `docs/plans/`
  - 设计文档与重构计划

## 运行说明

- 并不是每个单主题目录都自带完整依赖文件。
- 以下目录保留了原来大模块里的依赖锚点，脚本型主题通常可以参考它们的环境配置：
  - `04_rag_and_retrieval/02_llamaindex_retrieval_basics/`
  - `06_finetuning_and_data_processing_and_routing_react_and_tools/01_finetuning_and_data_processing/01_finetuning_overview/`
  - `08_multi_agent_frameworks/01_autogen_two_agent_chat/`
  - `09_dsl/01_dsl_design_basics/`
  - `10_memory_patterns_basics/`
  - `11_fastapi_serving/`
  - `15_python_concurrency_and_performance/01_asyncio_and_gil_basics/`
- 完整项目目录例如 `04_rag_and_retrieval/05_local_rag_project/`、`04_rag_and_retrieval/06_qanything_case_study/`、`02_langgraph_basics/23_langgraph_demo_project/`、`16_customer_service_platform/` 仍然保留各自的项目结构和运行方式。
