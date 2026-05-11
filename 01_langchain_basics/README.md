# LangChain Basics

环境准备、LLM API 调用、Tool Calling 聊天示例、LangChain 基础示例，以及 Prompt / OutputParser / Chain 相关入门内容，统一收纳在这个目录下。

## 内容

- `environment_setup.md`
  - 环境准备说明
- `pyproject.toml` / `uv.lock` / `uv.toml`
  - uv 依赖与环境管理文件
- `01_qwen_api_basic.py` - `05_langchain_qwen_extra.py`
  - Qwen / DashScope API、Tool Calling、LangChain 基础调用示例
- `06_prompt_templates.md` - `13_prompt_template_config.json`
  - Prompt 模板、模板工程化、自定义模板和示例配置
- `14_output_parsing_and_chains.md` - `18_chain_and_runnable_guide.py`
  - 输出解析器、基础 Chain、Runnable 和 LCEL 示例
- `19_dashscope_demo_simple.py` - `21_dashscope_intent_config.json`
  - DashScope 意图识别流水线示例和配置
- `01_qwen_api_basic.py`
  - 最小 Qwen / DashScope 兼容接口调用示例
- `02_qwen_chat_basic.py`
  - 基础聊天示例
- `03_qwen_tool_calling_demo.py`
  - Tool Calling 示例
- `04_langchain_qwen_basic.py`
  - LangChain 最小聊天示例
- `05_langchain_qwen_extra.py`
  - LangChain 补充实验脚本
- `test_01_qwen_api_basic.py`
  - API 调用示例测试
- `test_02_qwen_chat_examples.py`
  - 聊天与 Tool Calling 示例测试
- `test_04_langchain_qwen_basic.py`
  - LangChain 示例测试
- `.env.example`
  - 环境变量模板

## 配置

先同步依赖：

```bash
uv sync --locked
```

先在当前目录创建 `.env`：

```env
DASHSCOPE_API_KEY=your_api_key_here
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

默认模型：

- `01_qwen_api_basic.py`: `qwen-plus`
- `02_qwen_chat_basic.py`: `qwen-plus`
- `03_qwen_tool_calling_demo.py`: `qwen-plus`
- `04_langchain_qwen_basic.py`: `qwen-plus`

## 运行

```bash
uv run python 01_qwen_api_basic.py
uv run python 02_qwen_chat_basic.py
uv run python 03_qwen_function_tool_calling_demo.py
uv run python 04_langchain_qwen_basic.py
uv run python 05_langchain_qwen_extra.py
uv run python 09_prompt_template_simple_demo.py
uv run python 15_first_chat_chain.py
uv run python 18_chain_and_runnable_guide.py
uv run python 19_dashscope_demo_simple.py
```

## 测试

```bash
uv run pytest -q test_01_qwen_api_basic.py test_02_qwen_chat_examples.py test_04_langchain_qwen_basic.py
```
