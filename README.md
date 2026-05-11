# AI 工程化训练营目录总览

本仓库现在按“编号主线 + 少量合并父目录”的方式组织。大多数编号目录承载一个知识主题或一个独立项目；对强相关的连续主题，会放进同一个编号父目录下，减少顶层目录数量。各主题目录仍尽量提供根级 `README.md` 作为入口说明。

## 主线目录

### 01-08 基础能力

- `01_environment_setup/`
  - 环境准备、依赖说明、基础入口说明
- `02_llm_api_calls/`
  - 大模型 API 调用示例
- `03_http_model_requests/`
  - 通过 HTTP 直接请求模型服务
- `04_tool_calling_chat/`
  - Tool Calling 与基础聊天示例
- `05_langchain_basics/`
  - LangChain 入门脚本
- `06_langgraph_basics/`
  - LangGraph 学习主线，包含基础示例、`21_langgraph_workflows/`、`22_langgraph_service_apps/`、`23_langgraph_demo_project/`、`29_langgraph_multi_agent/`、`31_mcp_langgraph_integration/`、`32_a2a_langgraph/`
- `08_intent_recognition_agent/`
  - 意图识别与多智能体示例

### 09-12 微调与数据处理

- `09_finetuning_and_data_processing/`
  - 合并后的父目录，收纳 09-12 四个相近主题
  - 子目录：`09_finetuning_overview/`、`10_massive_dataset_processing/`、`11_lora_qlora_training/`、`12_local_finetuning_platform/`

### 13-17 RAG 与检索

- `13_rag_and_retrieval/`
  - 合并后的父目录，收纳 RAG 与检索相关主题，并补充纳入 `12_llamaindex_basics/`
  - 子目录：`12_llamaindex_basics/`、`13_llamaindex_retrieval_basics/`、`14_ragas_retrieval_evaluation/`、`15_graphrag_basics/`、`16_local_rag_project/`、`17_qanything_case_study/`

### 18-26 工作流与 Agent 工程

- `18_prompt_templates/`
  - Prompt 模板与模板工程
- `19_output_parsing_and_chains/`
  - 输出解析、链路、基础 pipeline
- `20_routing_react_and_tools/`
  - Router、ReAct、工具调用
- `24_tooling_and_automation_workflows/`
  - 合并后的父目录，收纳 24-26 三个相近主题
  - 子目录：`24_code_assistant_workflow/`、`25_vllm_wrapper_demo/`、`26_rpa_and_ai_workflow/`

### 27-32 多 Agent 与协议

- `27_multi_agent_frameworks/`
  - 多 Agent 框架父目录
  - 子目录：`27_autogen_two_agent_chat/`、`28_crewai_basics/`
- `30_agent_protocols_and_mcp/`
  - 协议与 MCP 基础主题父目录
  - 子目录：`30_mcp_basics/`

### 33-36 DSL 与记忆能力

- `33_dsl_design_basics/`
  - DSL 设计基础
- `34_lark_dsl_examples/`
  - Lark 与 DSL 示例
- `35_dsl_agent_and_db_gateway/`
  - DSL Agent 与数据库网关
- `36_memory_patterns_basics/`
  - 合并后的 Agent Memory 专题，包含记忆模式、向量记忆、知识图谱记忆、Redis 记忆与可靠性

### 40-46 服务化、部署与观测

- `40_fastapi_llm_serving/`
  - FastAPI LLM 服务
- `41_multimodal_fastapi_serving/`
  - 多模态 FastAPI 服务
- `42_dockerized_service_apps/`
  - Docker 化服务应用
- `43_kubernetes_deployment/`
  - Kubernetes 部署
- `44_observability_and_serving_runtime/`
  - 合并后的父目录，收纳 44-46 与 59 这组可观测性和 serving runtime 主题
  - 子目录：`44_elk_observability/`、`45_prometheus_ollama_exporter/`、`46_ray_serve_streaming/`、`59_ttft_and_llm_serving_latency/`

### 47-52 并发性能与综合项目

- `47_asyncio_basics/`
  - asyncio 基础
- `48_asyncio_primitives_and_gil/`
  - Future、Task、Executor、GIL
- `49_async_web_patterns/`
  - 异步 Web 与 I/O 模式
- `50_performance_benchmarking/`
  - 性能分析与压测
- `51_async_multiprocess_hybrid/`
  - 协程与多进程混合
- `52_customer_service_platform/`
  - 智能客服综合项目

### 53-59 扩展专题

- `53_model_extensions/`
  - 合并后的父目录，收纳 53-55 三个模型扩展主题
  - 子目录：`53_slm_optimization/`、`54_multimodal_clip_search/`、`55_reinforcement_learning/`
- `56_skill_engineering/`
  - Skill / Prompt 工程扩展资料
- `57_harness_engineering/`
  - Harness Engineering 与上下文工程
- `58_learning_methodology/`
  - 学习方法论

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
  - `01_environment_setup/`
  - `09_finetuning_and_data_processing/09_finetuning_overview/`
  - `13_rag_and_retrieval/13_llamaindex_retrieval_basics/`
  - `18_prompt_templates/`
  - `27_multi_agent_frameworks/27_autogen_two_agent_chat/`
  - `33_dsl_design_basics/`
  - `36_memory_patterns_basics/`
  - `40_fastapi_llm_serving/`
  - `47_asyncio_basics/`
- 完整项目目录例如 `13_rag_and_retrieval/16_local_rag_project/`、`13_rag_and_retrieval/17_qanything_case_study/`、`06_langgraph_basics/23_langgraph_demo_project/`、`52_customer_service_platform/` 仍然保留各自的项目结构和运行方式。
