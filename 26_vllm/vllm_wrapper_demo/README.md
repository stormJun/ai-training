# vLLM Wrapper Demo

这是一个最小的 vLLM OpenAI 兼容接口封装演示，保留迁移前的平铺文件结构。

## 文件说明

- `custom_vllm_wrapper.py`: LangChain LLM 封装器，调用 vLLM 的 `/v1/completions` 接口。
- `vllm_config.py`: 常用生成参数预设和参数说明。
- `vllm_demo.py`: 基础调用、参数对比、流式输出和 LangChain 集成演示。
- `requirements.txt`: 运行示例所需依赖。

## 运行方式

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26vllm/vllm_wrapper_demo
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vllm_demo.py
```

默认连接 `http://localhost:8000`，默认模型名为 `Qwen/Qwen2.5-0.5B-Instruct`。可以通过环境变量覆盖：

```bash
export VLLM_BASE_URL=http://localhost:8000
export VLLM_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
python vllm_demo.py
```
