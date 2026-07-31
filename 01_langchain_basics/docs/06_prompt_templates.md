# Prompt 模板

本主题收纳 Prompt 模板、基础模板文件以及自定义模板工程化示例。

## 内容

- `07_prompt_template_overview.md`
  - Prompt 模板总览说明
- `08_prompt_template_text.txt`
  - 模板文本示例
- `09_prompt_template_simple_demo.py`
  - 最小自定义模板示例
- `10_prompt_template_engineering.py`
  - 工程化自定义模板示例
- `11_prompt_template_usage_demo.py`
  - 模板使用和配置管理示例
- `12_prompt_template_advanced.py`
  - 高级模板扩展示例
- `13_prompt_template_config.json`
  - 示例配置文件
- `13a_deerflow_prompt_template_design.md`
  - DeerFlow 在复杂 agent 系统里的 prompt 分层设计案例
- `13b_deerflow_prompt_layering_demo.py`
  - 纯 Python 版 DeerFlow prompt 分层最小演示

## 开始方式

- 本主题共用上一级 `01_langchain_basics/` 的 uv 环境
- 在 `01_langchain_basics/` 目录执行 `uv sync --locked`
- 优先阅读 `.md`
- 建议先看 `07_prompt_template_overview.md`，再看 `13a_deerflow_prompt_template_design.md`
- 再通过 `uv run python 09_prompt_template_simple_demo.py` 运行基础模板示例
- 如果想看复杂 agent 场景里的最小落地原型，运行 `uv run python 13b_deerflow_prompt_layering_demo.py`
