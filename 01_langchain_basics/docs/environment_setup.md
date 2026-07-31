# Python 工程化环境准备步骤

本目录统一使用 `uv` 管理 Python 版本、虚拟环境、依赖安装和锁定版本。

## 1. 安装 uv

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后确认版本：

```bash
uv --version
```

## 2. 本目录的依赖文件

当前目录只保留 uv 相关依赖入口：

- `pyproject.toml`
  - 项目元数据和直接依赖列表
- `uv.lock`
  - uv 解析出的完整锁定依赖版本
- `uv.toml`
  - uv 配置文件，本目录用于配置清华 PyPI 镜像源

不再维护 `requirements.txt`。后续新增依赖时优先使用 `uv add`，不要手工编辑锁文件。

## 3. 初始化环境

进入当前目录：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics
```

同步锁定依赖：

```bash
uv sync --locked
```

如果修改了 `pyproject.toml` 里的依赖，需要重新解析并更新锁文件：

```bash
uv lock
uv sync
```

## 4. 常用 uv 命令

```bash
# 运行脚本
uv run python 01_qwen_api_basic.py

# 运行测试
uv run pytest -q

# 添加依赖
uv add openai

# 添加开发依赖
uv add --dev pytest

# 删除依赖
uv remove openai

# 查看依赖树
uv tree

# 同步环境
uv sync

# 严格按 uv.lock 同步
uv sync --locked
```

## 5. 使用环境变量保存 API Key

推荐在当前目录创建 `.env`：

```env
DASHSCOPE_API_KEY=your_api_key_here
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Python 代码中通过 `python-dotenv` 加载：

```python
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
```

命令行临时设置也可以：

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
export OPENAI_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

## 6. 运行示例

```bash
uv run python 01_qwen_api_basic.py
uv run python 02_qwen_chat_basic.py
uv run python 03_function_calling.py
uv run python 04_langchain_qwen_basic.py
uv run python 05_langchain_qwen_extra.py
```

## 7. 运行测试

```bash
uv run pytest -q test_01_qwen_api_basic.py test_02_qwen_chat_examples.py test_04_langchain_qwen_basic.py
```

## 8. 安全注意事项

1. 不要把真实 API Key 提交到版本控制系统。
2. 使用 `.env` 或系统环境变量保存密钥。
3. `.env.example` 只放占位符，不放真实密钥。
4. 如果 API Key 泄露，应立即轮换。
