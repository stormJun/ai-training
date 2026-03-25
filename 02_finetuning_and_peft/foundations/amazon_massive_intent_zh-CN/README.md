# MASSIVE 中文意图数据加工说明

该目录内的所有文件都来源于 `02_finetuning_and_peft/foundations/chinese_data/zh-CN.jsonl`（MASSIVE 1.1 的 zh-CN 切分），只是根据不同训练场景做了预处理，方便直接喂给分类、指令或对话模型。原始数据的 `partition` 字段被拆分为多个文件，槽位等冗余字段被剥离或改写；若需要完整标注，请回到 `02_finetuning_and_peft/foundations/chinese_data/README.md` 与 `zh-CN.jsonl`。

## 文件与用途概览

| 文件 | 样本数 | 目的 | 主要字段/结构 |
| --- | --- | --- | --- |
| `train.jsonl` | 11,514 | 训练集（意图分类） | `id`, `label`, `text`, `label_text`, `label_text_ch` |
| `validation.jsonl` | 2,033 | 验证集（意图分类） | 同上 |
| `test.jsonl` | 2,974 | 测试集（意图分类） | 同上 |
| `train_converted.jsonl` | 11,514 | 指令微调（单轮） | `{"instruction", "input", "output"}` |
| `validation_converted.jsonl` | 2,033 | 指令微调验证 | 同上 |
| `test_converted.jsonl` | 2,974 | 指令微调测试 | 同上 |
| `train_chat.jsonl` | 11,514 | 多轮聊天 -> 输出意图标签 | `{"messages": [system, user, assistant]}` |
| `Mytrain.jsonl` | 11,514 | 多轮聊天 -> 输出自然语言动作 | `{"messages": [...]}` |
| `Template_Trainingdata.jsonl` | 10 | Few-shot 模板样例 | 多轮对话，英文示例 |
| `Testdata.xlsx` | 2,974 | 表格版测试集 | 同 `test.jsonl` 内容 |

> `train/validation/test` 的样本总数与 `chinese_data/README.md` 中统计一致；其余派生文件均与对应切分保持一一对应。

## 分类数据：`train|validation|test`.jsonl

- **格式**：每行是一个 JSON 对象，仅保留意图分类所需字段：
  ```json
  {"id":"1","label":48,"text":"星期五早上九点叫醒我","label_text":"alarm_set","label_text_ch":"报警器"}
  ```
- **label**：0–59 的整数，按 MASSIVE 官方意图顺序编码；`label_text` 是英文意图名，`label_text_ch` 为中文翻译，便于训练中映射或调试。
- **构造**：直接依据 `zh-CN.jsonl` 的 `partition` 切分；去掉槽位、场景、评审等字段，只保留文本与意图标签。

## 指令微调数据：`*_converted.jsonl`

- **格式**：每行 `{"instruction": "...", "input": "...", "output": "..."}`，其中 `instruction` 固定为“请识别以下用户语句的意图分类”，`input` 为中文原句，`output` 为“中文意图名(英文 intent)”的组合。
  ```json
  {
    "instruction": "请识别以下用户语句的意图分类",
    "input": "设个两小时后的闹钟",
    "output": "报警器(alarm_set)"
  }
  ```
- **用途**：适配 alpaca/FLAN 等指令式监督微调流程，无需额外 prompt 设计。
- **构造**：基于 `train|validation|test`.jsonl` 的字段，拼接中英文标签；不同切分之间内容与顺序一致。

## 聊天微调数据

### `train_chat.jsonl`

- 结构：每行一个三消息对话（system 描述助手角色，user 给出语句，assistant 仅返回 “意图分类: XXX”）。
- 适用：如需训练遵循 ChatML/对话模板的分类助手，可直接读取 `messages` 列表。
- 示例：
  ```json
  {
    "messages": [
      {"role": "system", "content": "你是一个意图识别助手，能够准确识别用户语句的意图。"},
      {"role": "user", "content": "请识别意图: 星期五早上九点叫醒我"},
      {"role": "assistant", "content": "意图分类: 报警器(alarm_set)"}
    ]
  }
  ```
- **用途**：训练 ChatGPT/LLaMA 等对话模型，只让模型输出标签，不生成长回复。适合把 MASSIVE 做成“问一句答标签”的工具型机器人。

### `Mytrain.jsonl`

- 结构与 `train_chat.jsonl` 相同，但 assistant 会给出完成动作的自然语言回应（例如“已为你设置星期五上午九点的闹钟”）。
- **用途**：
  - 训练能够理解意图并返回执行结果的家居语音助手（适配“执行反馈”场景）。
  - 可与工具链/函数调用结合：模型先识别 intent，再以自然语言回执告知用户执行情况。

## Few-shot 模板：`Template_Trainingdata.jsonl`

- 内容：少量英文对话模板，展示如何在单轮或多轮对话中回答用户问题。
- **用途**：
  1. 直接粘贴到 prompt 中作为 few-shot 示例，帮助“意图识别助手”模型遵循期望格式。
  2. 作为二次加工的模板，快速生成中文版 few-shot（如将用户和助手内容替换成中文句子）。
  3. 参考其对话结构，扩展更多多轮问答示例（例如用户追问、助手回访）。
- 与 MASSIVE 样本并非一一对应，只提供参考结构。

## 表格数据：`Testdata.xlsx`

- 提供与 `test.jsonl` 同步的 XLSX 版本，方便产品/标注人员在 Excel 中审查或追加注释。
- 常见用法：
  - 标注/审核同学在表格中添加批注、额外标签或数据清洗记录。
  - 结合 Excel/数据透视表快速统计各意图的样本数量和中文描述。
  - 筛选少量样本拷贝到产品文档或 PPT 中展示。

## 使用建议

1. **需要槽位/场景？** 返回 `02_finetuning_and_peft/foundations/chinese_data/zh-CN.jsonl`，自行处理所需字段。
2. **只做意图分类？** 直接使用 `train/validation/test`.jsonl`，配合 `label_text` 构建标签映射。
3. **指令/聊天模型？** 根据模型输入格式选取 `*_converted.jsonl` 或 `train_chat.jsonl/Mytrain.jsonl`，无需再写转换脚本。
4. **Few-shot prompt**：可引用 `Template_Trainingdata.jsonl` 或从 `train_chat.jsonl` 采样数条作为示例。

如需新增其他格式（例如文本+槽位 BIO 标注），推荐以 `zh-CN.jsonl` 为基准，保持与现有三个切分一致，以免样本顺序错位。
