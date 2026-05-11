# vLLM 封装与演示模块说明

## 目录定位
`25_vllm_wrapper_demo/vllm_wrapper_demo` 是 21_langgraph_workflows 中用于演示 vLLM 接入与参数工程化管理的模块。

该目录的目标是：
- 提供一个可复用的 vLLM LangChain 封装器
- 演示不同采样参数对输出质量的影响
- 提供可复用的参数预设和校验逻辑

## 文件结构
- `custom_vllm_wrapper.py`：自定义 `CustomVLLMWrapper`，兼容 OpenAI `/v1/completions`，支持同步、伪异步、流式、重试与参数校验。
- `vllm_demo.py`：演示脚本，覆盖基础调用、参数对比、高级参数、流式输出、LangChain 链式集成、参数校验。
- `vllm_config.py`：参数预设与说明（如 conservative、balanced、creative、beam_search）以及配置校验工具。
- `requirements.txt`：该模块的依赖建议。

## 核心能力
1. 参数治理
- 使用 Pydantic 字段约束与自定义校验器控制 `temperature/top_p/top_k/max_tokens` 等关键参数边界。
- 支持核心参数与高级参数（如 `repetition_penalty`、`presence_penalty`、`use_beam_search`、`best_of`）。

2. 服务调用与可靠性
- 通过 `base_url + /v1/completions` 访问 vLLM 服务。
- 内置 `max_retries` + 指数退避重试，降低瞬时网络波动影响。
- 可按需设置 `Authorization: Bearer <api_key>`。

3. 流式输出
- 支持 SSE 风格流式解析：解析 `data:` 行并识别 `[DONE]` 结束标识。

4. 生态集成
- 可直接作为 LangChain 的 LLM 组件接入 `PromptTemplate | llm | StrOutputParser` 链路。

## 运行方式
在 `21_langgraph_workflows` 目录下建议使用项目虚拟环境：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/21_langgraph_workflows
python -m venv .venv
source .venv/bin/activate
pip install -r vllm_wrapper_demo/requirements.txt
python vllm_wrapper_demo/vllm_demo.py
```

说明：
- 若未启动本地 vLLM 服务（默认 `http://localhost:8000`），演示脚本会在部分场景给出模拟输出。
- 真正联调前请先确保后端服务可达并模型已加载。

## 常见配置建议
- 代码生成/技术问答：`temperature=0.1~0.4`, `top_p=0.7~0.9`
- 通用对话：`temperature=0.6~0.9`, `top_p=0.9`
- 创意任务：`temperature=1.0~1.3`, `top_p=0.95`
- 需要更稳定质量时可尝试 `use_beam_search=True` 与合适的 `best_of`

## 重命名说明
原目录名：`21_langgraph_workflows/p12`
新目录名：`25_vllm_wrapper_demo/vllm_wrapper_demo`

重命名原因：目录语义更清晰，能直接体现“vLLM 封装 + 演示”的用途。
