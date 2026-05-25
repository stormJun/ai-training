# 服务化、部署与可观测性实践

本目录汇集了服务化、部署与可观测性相关的全部教学示例，覆盖 **LLM 服务化、LangGraph 工作流、Web 前端集成、容器化部署、Kubernetes 灰度发布、日志观测与指标监控** 等核心主题。每个子项目都配套示例脚本或配置文件，便于在课堂上拆解演示，也方便学员自行动手实验。

## 目录速览
- `00_fastapi_hello_world.py`：纯本地可运行的 FastAPI hello world 脚本，不依赖 Ollama，适合作为最小入门示例。
- `00_fastapi_hello_world_deep_dive.md`：围绕 `00` 代码讲 FastAPI / Starlette / ASGI / Uvicorn 分工与底层运行机制。
- `01_ollama_fastapi_server.py` / `01_ollama_fastapi_client.py`：基于 FastAPI 的 Ollama 代理服务与测试脚本，讲解传统 LLM 与 RESTful API 的对接与流式输出。
- `01_ollama_fastapi_intro.md`：`01` 入门教程，按“代码导读 + 跑通实战”方式拆解最小 FastAPI + Ollama 服务。
- `02_mock_llm_fastapi_server.py`：本地 mock LLM 服务，演示更接近真实 AI 接口的请求模型、响应模型、错误处理与流式输出。
- `multimodal/P16-FastAPI-Qwen-VL-server.py` / `multimodal/P16-FastAPI-Qwen-VL-client.py`：多模态模型 Qwen-VL 的部署示例，演示图文混合输入的处理流程。
- `docker/`：LangGraph + 通义千问工作流的容器化示例，包含 `docker-compose.yml`、配置管理与一键部署脚本。
- `p17_webLLM/`：进阶版 LangGraph AI 对话系统（FastAPI + Gradio + Celery + Postgres/SQLite），附详细文档与 Docker 化方案。
- `p18_k8s/`：Kubernetes 部署与灰度发布教材，包含 Deployment、Service、Canary、Istio、HPA 等范例 YAML。
- `elk/`、`p41elk.py`、`ELK_使用说明.md`：Python 日志推送到 Logstash/Elasticsearch/Kibana 的端到端实践。
- `ollama-exporter-main/`、`prometheus-config/`：Ollama Prometheus Exporter 及 Prometheus/Grafana 监控示例配置。
- `ray/`：Ray Serve 基础能力演示脚本，覆盖 HTTP、WebSocket、流式响应与异常场景处理。
- 其余文件：`elk_integration.log`（示例日志）、`workflow.py`、`构建命令.txt` 等辅助资料。

## 环境准备
### 基础依赖
- Python 3.10+（建议创建虚拟环境）
- Docker / Docker Compose
- 可选：PostgreSQL、Redis、Celery、Kubernetes CLI（kubectl、helm）、Ray
- 通义千问 `DASHSCOPE_API_KEY`、Ollama 运行环境、以及可选的 GPU 驱动（Qwen-VL 推理）

### 安装建议
```bash
# 进入项目根目录
cd 11_fastapi_serving

# 安装核心依赖（使用现有锁文件）
uv sync --locked

# 安装全部扩展依赖
uv sync --locked --all-extras

# OR 按需追加特性模块
uv sync --locked --extra webllm       # WebLLM / Celery / Gradio 场景
uv sync --locked --extra monitoring   # Prometheus / Exporter 场景
uv sync --locked --extra multimodal   # Qwen-VL 多模态推理
uv sync --locked --extra ray          # Ray Serve 教学脚本
```

> 提示：若修改了依赖或首次生成锁文件，请先执行 `uv lock`，再运行以上同步命令。

必要的环境变量可在 `.env`、`.env.example`、`.env.docker` 模板中查找，也可参考子目录内的 README。

## 教学模块概览
### 1. LLM 服务化与代理
- **FastAPI Hello World 入门**：`00_fastapi_hello_world.py` 提供完全本地可启动的最小服务，不依赖 Ollama，适合第一次理解 `FastAPI()`、路由、JSON 返回和 `uvicorn` 启动。
  ```bash
  uv run python 00_fastapi_hello_world.py
  ```
  如果你想深入理解这份最小代码背后的机制，继续看 [00_fastapi_hello_world_deep_dive.md](00_fastapi_hello_world_deep_dive.md)。
- **Ollama FastAPI 代理**：`01_ollama_fastapi_server.py` 将本地 Ollama 接口包装为统一 REST API，支持流式输出，搭配 `01_ollama_fastapi_client.py` 验证。
  ```bash
  uvicorn 01_ollama_fastapi_server:app --host 0.0.0.0 --port 8000
  python 01_ollama_fastapi_client.py
  ```
  建议在 hello world 跑通后，再配合阅读 [01_ollama_fastapi_intro.md](01_ollama_fastapi_intro.md)，理解服务端代理转发和流式输出是怎么加上去的。
- **本地 Mock LLM 服务**：`02_mock_llm_fastapi_server.py` 不依赖外部模型，但接口形状已经接近真实 AI 服务，适合在 hello world 之后练习请求模型、响应模型、`HTTPException` 和 `StreamingResponse`。
  ```bash
  uv run python 02_mock_llm_fastapi_server.py
  ```
- **多模态接入**：`multimodal/P16-FastAPI-Qwen-VL-server.py` 演示下载并加载 Qwen-VL-Chat，`multimodal/P16-FastAPI-Qwen-VL-client.py` 提供兼容 OpenAI Chat Completions 的请求示例。适合说明显存占用、图文混合 prompt、以及多模态推理流程。

### 2. LangGraph 工作流与 WebLLM 综合应用
- **容器化基础版**（`docker/`）：以内置的 LangGraph 工作流 `workflow.py`、FastAPI 应用 `main.py` 与配置模块 `config.py` 讲解如何包装千问模型为微服务，`docker-compose.yml` 支持一键启动。
- **数据库 + Gradio 进阶版**（`p17_webLLM/`）：在基础服务上扩展 PostgreSQL/SQLite 持久化、Celery 异步任务、Gradio 前端。参阅：
  - `README_DATABASE.md`：数据库版本说明与运行指南
  - `README-Docker.md`：Docker 化部署步骤
  - `CELERY_SETUP.md`：异步任务配置
  - `start_all.py`：一键启动 API + Gradio

### 3. DevOps 与容器编排
- **Kubernetes 实战**（`p18_k8s/`）：提供从基础 Deployment 到灰度发布（`canary-deployment.yaml`）、Istio 流量治理（`istio-gray-deployment.yaml`）、HPA（`hpa.yaml`）等完整示例，配套 `install.txt` 记录所需组件。
- **Ray Serve 入门**（`ray/`）：通过编号脚本逐步展示部署、HTTP 调用、WebSocket、流式输出、连接中断处理等能力，为 AIGC 服务的伸缩部署打基础。

### 4. 可观测性与系统监控
- **集中式日志**：参考 `ELK_使用说明.md`，使用 `elk/docker-compose.yml` 启动 ELK 栈，运行 `p41elk.py` 将 Python 日志通过自定义 TCP Handler 推送到 Logstash，并在 Kibana 中可视化。
- **指标监控**：`ollama-exporter-main/` 提供可直接运行的 FastAPI Exporter，采集 Ollama 请求量、时延、Token 指标，`prometheus-config/` 则示范 Prometheus 的抓取配置及与 Grafana 仪表盘对接。


## 参考资料
- [ELK_使用说明.md](ELK_使用说明.md)
- [p17_webLLM/README-Docker.md](p17_webLLM/README-Docker.md)
- [p17_webLLM/README_DATABASE.md](p17_webLLM/README_DATABASE.md)
- [ollama-exporter-main/README.md](ollama-exporter-main/README.md)
- [prometheus-config/prometheus.yml](prometheus-config/prometheus.yml)
- [docker/构建命令.txt](docker/构建命令.txt)
