# LangChain Basics

环境准备、LLM API 调用、Tool Calling 聊天示例、LangChain 基础示例，以及 Prompt / OutputParser / Chain 相关入门内容，统一收纳在这个目录下。

## 内容

- `environment_setup.md`
  - 环境准备说明
- `pyproject.toml` / `requirements.txt` / `uv.lock` / `uv.toml`
  - 依赖与环境管理文件
- `qwen_api_basic.py`
  - 最小 Qwen / DashScope 兼容接口调用示例
- `qwen_chat_basic.py`
  - 基础聊天示例
- `qwen_tool_calling_demo.py`
  - Tool Calling 示例
- `langchain_qwen_basic.py`
  - LangChain 最小聊天示例
- `langchain_qwen_extra.py`
  - LangChain 补充实验脚本
- `prompt_templates/`
  - 原 `18_prompt_templates`
  - 主要包含 `langchain_core.prompts`、模板工程、提示词基础
- `output_parsing_and_chains/`
  - 原 `19_output_parsing_and_chains`
  - 主要包含输出解析器、PromptTemplate、ChatPromptTemplate、Runnable / Chain 等内容
- `test_qwen_api_basic.py`
  - API 调用示例测试
- `test_qwen_chat_examples.py`
  - 聊天与 Tool Calling 示例测试
- `test_langchain_qwen_basic.py`
  - LangChain 示例测试
- `.env.example`
  - 环境变量模板

## 配置

先在当前目录创建 `.env`：

```env
DASHSCOPE_API_KEY=your_api_key_here
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

默认模型：

- `qwen_api_basic.py`: `qwen-plus`
- `qwen_chat_basic.py`: `qwen-plus`
- `qwen_tool_calling_demo.py`: `qwen-plus`
- `langchain_qwen_basic.py`: `qwen-plus`

## 运行

```bash
python3 qwen_api_basic.py
python3 qwen_chat_basic.py
python3 qwen_tool_calling_demo.py
python3 langchain_qwen_basic.py
python3 langchain_qwen_extra.py
```

子目录中的笔记、脚本和 notebook 可以分别进入对应目录查看：

```bash
cd prompt_templates
cd output_parsing_and_chains
```

## 测试

```bash
pytest -q test_qwen_api_basic.py test_qwen_chat_examples.py test_langchain_qwen_basic.py
```
