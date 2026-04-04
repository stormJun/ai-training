# AI 工程化训练营单主题目录总览

本仓库现在按“单主题、带编号”的方式组织。每个编号目录只承载一个知识主题或一个独立项目，方便回顾、复习和按主题检索。每个编号主题目录现在也统一提供根级 `README.md` 作为入口说明。

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
  - LangGraph 入门脚本
- `07_llamaindex_basics/`
  - LlamaIndex 基础示例
- `08_intent_recognition_agent/`
  - 意图识别与多智能体示例

### 09-12 微调与数据处理

- `09_finetuning_overview/`
  - 微调概览、资料、环境锚点
- `10_massive_dataset_processing/`
  - MASSIVE 数据集处理与转换
- `11_lora_qlora_training/`
  - LoRA / QLoRA 训练与产物
- `12_local_finetuning_platform/`
  - 本地微调平台

### 13-17 RAG 与检索

- `13_llamaindex_retrieval_basics/`
  - LlamaIndex 检索基础
- `14_ragas_retrieval_evaluation/`
  - Ragas 评测与检索评估
- `15_graphrag_basics/`
  - GraphRAG 基础示例
- `16_local_rag_project/`
  - 本地 RAG 项目
- `17_qanything_case_study/`
  - QAnything 案例

### 18-26 工作流与 Agent 工程

- `18_prompt_templates/`
  - Prompt 模板与模板工程
- `19_output_parsing_and_chains/`
  - 输出解析、链路、基础 pipeline
- `20_routing_react_and_tools/`
  - Router、ReAct、工具调用
- `21_langgraph_workflows/`
  - LangGraph 工作流主线
- `22_langgraph_service_apps/`
  - LangGraph 服务化 app 示例
- `23_langgraph_demo_project/`
  - LangGraph demo 项目
- `24_code_assistant_workflow/`
  - 代码助手工作流
- `25_vllm_wrapper_demo/`
  - vLLM wrapper 示例
- `26_rpa_and_ai_workflow/`
  - RPA 与 AI 工作流集成

### 27-32 多 Agent 与协议

- `27_autogen_two_agent_chat/`
  - AutoGen 与双 Agent 对话
- `28_crewai_basics/`
  - CrewAI 基础
- `29_langgraph_multi_agent/`
  - LangGraph 多智能体
- `30_mcp_basics/`
  - MCP 基础
- `31_mcp_langgraph_integration/`
  - MCP 与 LangGraph 集成
- `32_a2a_langgraph/`
  - A2A 与 LangGraph

### 33-39 DSL 与记忆能力

- `33_dsl_design_basics/`
  - DSL 设计基础
- `34_lark_dsl_examples/`
  - Lark 与 DSL 示例
- `35_dsl_agent_and_db_gateway/`
  - DSL Agent 与数据库网关
- `36_memory_patterns_basics/`
  - 记忆模式基础
- `37_vector_and_faiss_memory/`
  - 向量记忆与 FAISS
- `38_knowledge_graph_memory/`
  - 知识图谱记忆
- `39_redis_memory_and_reliability/`
  - Redis 记忆与可靠性

### 40-46 服务化、部署与观测

- `40_fastapi_llm_serving/`
  - FastAPI LLM 服务
- `41_multimodal_fastapi_serving/`
  - 多模态 FastAPI 服务
- `42_dockerized_service_apps/`
  - Docker 化服务应用
- `43_kubernetes_deployment/`
  - Kubernetes 部署
- `44_elk_observability/`
  - ELK 观测与日志
- `45_prometheus_ollama_exporter/`
  - Prometheus 与 Ollama Exporter
- `46_ray_serve_streaming/`
  - Ray Serve 与流式服务

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

### 53-58 扩展专题

- `53_slm_optimization/`
  - 小模型优化
- `54_multimodal_clip_search/`
  - CLIP 图像搜索
- `55_reinforcement_learning/`
  - 强化学习
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
  - `09_finetuning_overview/`
  - `13_llamaindex_retrieval_basics/`
  - `18_prompt_templates/`
  - `27_autogen_two_agent_chat/`
  - `33_dsl_design_basics/`
  - `36_memory_patterns_basics/`
  - `40_fastapi_llm_serving/`
  - `47_asyncio_basics/`
- 完整项目目录例如 `16_local_rag_project/`、`17_qanything_case_study/`、`23_langgraph_demo_project/`、`52_customer_service_platform/` 仍然保留各自的项目结构和运行方式。
