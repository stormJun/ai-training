# 仓库目录总览

本仓库围绕 AI 工程实践，按「编号主线 + 合并父目录」组织代码、学习笔记与独立项目。每个编号目录对应一个主题；强相关的连续主题会合并到同一编号父目录下，减少顶层目录数量。根目录 `README.md` 作为入口，详细内容进入对应目录查看。

## 主题目录

### 基础框架与编排

- `01_langchain_basics/` — LangChain 入门脚本，覆盖 Qwen API、Chat、Function Calling、Prompt Template 等基础用法。
- `02_langgraph_basics/` — LangGraph 学习主线，包含 `01_intro/`、`02_workflows/`、`03_service_apps/`、`04_demo_project/`、`05_multi_agent/`、`06_protocols_and_integrations/`、`07_deep_dive_notes/`。

### 检索增强与知识建模

- `04_rag_and_retrieval/` — RAG 与检索主题的合并父目录，已纳入 LlamaIndex 基础与检索。
  - `01_llamaindex_basics/` — LlamaIndex 基础用法。
  - `02_llamaindex_retrieval_basics/` — 检索器与索引结构。
  - `03_ragas_retrieval_evaluation/` — 用 Ragas 评估检索质量。
  - `04_graphrag_basics/` — GraphRAG 与图增强检索。
  - `05_local_rag_project/` — 本地可运行的 RAG 端到端项目。
  - `06_qanything_case_study/` — QAnything 开源案例拆解。

### Agent 与工作流

- `03_intent_recognition_agent/` — 意图识别与多 Agent 示例。
- `06_finetuning_and_data_processing_and_routing_react_and_tools/` — Router、ReAct、工具调用，并收纳原 09-12 微调与数据处理。
  - `01_finetuning_and_data_processing/`
    - `01_finetuning_overview/` — 微调总览与依赖锚点。
    - `02_massive_dataset_processing/` — 大规模数据处理。
    - `03_lora_qlora_training/` — LoRA / QLoRA 训练。
    - `04_local_finetuning_platform/` — 本地微调平台。
- `07_tooling_and_automation_workflows/` — 工具化与自动化工作流合集。
  - `01_code_assistant_workflow/` — 代码助手工作流。
  - `03_rpa_and_ai_workflow/` — RPA + AI 工作流。
- `09_dsl/` — DSL 主题的合并父目录。
  - `01_dsl_design_basics/` — DSL 设计基础。
  - `02_lark_dsl_examples/` — Lark DSL 示例。
  - `03_dsl_agent_and_db_gateway/` — DSL Agent 与数据库网关。
  - `reference_projects/project6_1/`、`reference_projects/project6_2/` — DSL 参考项目。

### 记忆能力

- `10_memory_patterns_basics/` — Agent 记忆专题，涵盖记忆模式、向量记忆、知识图谱记忆、Redis 记忆与可靠性。

### 训练与对齐

- `22_reinforcement_learning_notes/` — 强化学习系统学习笔记，含 Q-Learning 补充资料与演示项目。

### 服务化与部署

- `11_fastapi_serving/` — FastAPI 服务主题，包含基础 LLM 服务与多模态示例。
  - `multimodal/` — 多模态服务示例。
- `12_dockerized_service_apps/` — Docker 化服务应用。
- `13_kubernetes_deployment/` — Kubernetes 部署示例。
- `14_observability_and_serving_runtime/` — 可观测性与 serving runtime 的合并父目录。
- `26_vllm/` — vLLM 包装示例。
  - `01_elk_observability/` — ELK 日志栈。
  - `02_prometheus_ollama_exporter/` — Prometheus + Ollama 指标。
  - `03_ray_serve_streaming/` — Ray Serve 流式推理。
  - `04_ttft_and_llm_serving_latency/` — TTFT 与推理延迟。

### 并发与性能

- `15_python_concurrency_and_performance/` — Python 并发与性能合集。
  - `01_asyncio_and_gil_basics/` — asyncio 与 GIL 基础。
  - `02_async_web_patterns/` — 异步 Web 模式。
  - `03_performance_benchmarking/` — 性能基准。
  - `04_async_multiprocess_hybrid/` — 异步 + 多进程混合调度。

### 综合项目与模型扩展

- `16_customer_service_platform/` — 智能客服端到端综合项目。
- `17_model_extensions/` — 模型扩展主题的合并父目录。
  - `01_slm_optimization/` — 小模型优化。
  - `02_multimodal_clip_search/` — CLIP 多模态检索。

### 工程方法论与源码研究

- `18_skill_engineering/` — Skill / Prompt 工程扩展资料。
- `19_harness_engineering/` — Harness Engineering 与上下文工程。
- `20_learning_methodology/` — 学习方法论整理。
- `21_claudecode_source_analysis/` — Claude Code 源码与实现理解（agent runtime、上下文系统、工具解析等）。

### Agent 工程案例与 CLI

- `23_agent_case_studies/` — Agent 工程实践案例文章（金融可信智能体：Agentic Engineering 的工程实践与演进）。
- `24_agent_cli/` — Agent CLI 主题：面向 Agent Skill 的 CLI/SSO 鉴权体系笔记与 agent-cli-demo 项目（`cli/`、`server/`、`scripts/`）。

## 其他目录

- `assignments/` — 主题练习与配套示例答案。
- `reference_projects/` — 独立参考项目，目录内通常按 `core/`、`agents/`、`config/`、`tools/`、`scripts/`、`app/` 划分。
- `archive/` — 历史资料与不再维护的实验内容。
- `third_party_sources/` — 第三方引入源码（如 `gemini-fullstack-langgraph-quickstart/`）。
- `llm_wiki/` — 仓库内 Obsidian 知识库（concepts / topics / projects / maintenance）。
- `scripts/` — 仓库级辅助脚本（如 `convert_ipynb_to_md_py.py`、`shared_env_check.sh`）。
- `logs/` — 本地 MCP / 工具运行日志。

## 运行与依赖

仓库不提供统一的虚拟环境——每个子项目或脚本主题各自维护依赖。请在对应子目录内按其 `pyproject.toml`、`requirements.txt` 或 `Makefile` 操作。

常见模式：

- 微调与数据处理：进入 `06_finetuning_and_data_processing_and_routing_react_and_tools/01_finetuning_and_data_processing/01_finetuning_overview/`，按其依赖锚点配置环境。
- FastAPI 服务：
  - `cd 11_fastapi_serving && uv sync --locked`
  - `cd 04_rag_and_retrieval/05_local_rag_project/local_rag_project && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- LangGraph 端到端项目：
  - `cd 02_langgraph_basics/04_demo_project/langgraph_demo_project && uv sync --locked`
- 仅脚本或 Notebook 的主题（如 DSL、记忆、并发、Multi-Agent）通常参考就近的依赖锚点：
  - `04_rag_and_retrieval/02_llamaindex_retrieval_basics/`
  - `09_dsl/01_dsl_design_basics/`
  - `10_memory_patterns_basics/`
  - `15_python_concurrency_and_performance/01_asyncio_and_gil_basics/`
- 启动应用：在子项目根目录执行 `python main.py`、`uvicorn main:app --reload` 或使用其 `Makefile`。

## 约定

- 协作、命名、提交、测试等细节统一在 [`AGENTS.md`](./AGENTS.md) 中维护。
- 涉及 API Key、Token 等敏感信息时使用 `.env` 或环境变量，仓库内不提交明文密钥。
