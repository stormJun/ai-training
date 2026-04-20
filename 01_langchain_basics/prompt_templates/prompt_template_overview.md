# Prompt 模板概览

这一节主要介绍如何围绕 Prompt 模板做工程化封装。

## 自定义模板的价值

这里的重点不是只写一个字符串模板，而是把模板做成更可维护的工程组件，主要价值包括：

1. 类型安全：使用 Pydantic 做数据验证
2. 灵活配置：支持不同分析类型和输出选项
3. 配置管理：支持保存和加载模板配置
4. 扩展性：易于继承和扩展
5. 错误处理：输入校验和错误提示更清晰
6. 工程化能力：支持版本、缓存、元数据等扩展

## 目录说明

核心代码和示例已经在 `examples/` 目录里：

- `examples/custom_prompt_template_engineering.py`
  - 核心自定义模板类
- `examples/test_template.py`
  - 使用示例和测试
- `examples/ext_template.py`
  - 工程化扩展功能
- `examples/person_template_config.json`
  - 示例配置文件

## 学习顺序

建议按下面顺序看：

1. 先看 `examples/simple_demo.py`
2. 再看 `examples/custom_prompt_template_engineering.py`
3. 然后看 `examples/test_template.py`
4. 最后看 `examples/ext_template.py`

## 配套文件

- `prompt.txt`：基础模板文本示例

这一节更适合和 `langchain_core.prompts.StringPromptTemplate` 一起理解。
