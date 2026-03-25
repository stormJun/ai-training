# AI 工程化训练营知识点总览

本仓库按知识点而不是按周次组织，方便回顾、复习和按主题查找资料。大部分目录都是相对独立的 Python、Notebook 或项目工作区，进入对应目录后再查看各自的 `README.md`、依赖和运行方式。

## 目录导航

- `01_llm_api_and_tool_calling/`
  - 模型 API 调用、HTTP 请求、Tool Calling、LangChain/LangGraph/LlamaIndex 入门
  - 入口：[`01_llm_api_and_tool_calling/foundations/README.md`](01_llm_api_and_tool_calling/foundations/README.md)
- `02_finetuning_and_peft/`
  - LoRA / QLoRA / PEFT、本地微调平台、量化和数据处理
  - 入口：[`02_finetuning_and_peft/foundations/README.md`](02_finetuning_and_peft/foundations/README.md)
- `03_rag_and_retrieval/`
  - LlamaIndex、RAG、Ragas、Local RAG、QAnything 案例
  - 入口：
    - [`03_rag_and_retrieval/llamaindex_and_ragas/README.md`](03_rag_and_retrieval/llamaindex_and_ragas/README.md)
    - [`03_rag_and_retrieval/local_rag_project/README.md`](03_rag_and_retrieval/local_rag_project/README.md)
    - [`03_rag_and_retrieval/qanything_case_study/README_zh.md`](03_rag_and_retrieval/qanything_case_study/README_zh.md)
- `04_workflow_orchestration/`
  - LangChain、LangGraph、工作流编排、Agent 工程化和示例项目
  - 入口：
    - [`04_workflow_orchestration/langchain_langgraph_foundations/README.md`](04_workflow_orchestration/langchain_langgraph_foundations/README.md)
    - [`04_workflow_orchestration/langgraph_demo_project/README.md`](04_workflow_orchestration/langgraph_demo_project/README.md)
- `05_multi_agent_and_protocols/`
  - 多 Agent 协作、MCP、A2A、LangGraph MAS
  - 入口：[`05_multi_agent_and_protocols/foundations/README.md`](05_multi_agent_and_protocols/foundations/README.md)
- `06_dsl_and_rule_engines/`
  - DSL 设计、Lark/ANTLR、规则引擎、Text-to-SQL 中间表示
  - 入口：[`06_dsl_and_rule_engines/foundations/README.md`](06_dsl_and_rule_engines/foundations/README.md)
- `07_agent_memory_and_advanced_capabilities/`
  - Agent Memory、知识图谱记忆、RPA、小模型优化
  - 入口：[`07_agent_memory_and_advanced_capabilities/foundations/README.md`](07_agent_memory_and_advanced_capabilities/foundations/README.md)
- `08_serving_deployment_and_observability/`
  - FastAPI 服务化、Docker、Kubernetes、ELK、Prometheus、Ray
  - 入口：[`08_serving_deployment_and_observability/foundations/README.md`](08_serving_deployment_and_observability/foundations/README.md)
- `09_python_async_and_performance/`
  - `asyncio`、并发性能、异步 Web API、性能压测与分析
  - 入口：[`09_python_async_and_performance/foundations/README.md`](09_python_async_and_performance/foundations/README.md)
- `10_capstone_customer_service/`
  - 智能客服综合项目、RAG + LangGraph + Tool + 多租户 + 前后端
  - 入口：[`10_capstone_customer_service/customer_service_platform/README.md`](10_capstone_customer_service/customer_service_platform/README.md)

## 其他目录

- `assignments/`
  - 课程作业与作业参考答案
- `reference_projects/`
  - 独立参考项目和扩展项目
- `archive/`
  - 历史实验和暂不纳入主线结构的内容
- `scripts/`
  - 仓库级辅助脚本
- `docs/plans/`
  - 仓库级重构或实现计划

## 重要说明

- 不同知识点目录通常有各自独立的依赖和运行方式，不要默认共用同一个虚拟环境。
- 运行命令、环境变量和测试方式请以对应子目录的 `README.md` 或 `pyproject.toml` 为准。
- 如需快速理解仓库结构，优先从本文件和目标知识点目录下的 `README.md` 开始。
