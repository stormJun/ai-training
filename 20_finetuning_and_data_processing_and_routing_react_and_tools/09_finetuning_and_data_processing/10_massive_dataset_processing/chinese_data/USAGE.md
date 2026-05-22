# 数据处理脚本使用指南

本目录包含完整的数据处理、训练、推理、评估工具链，用于 MASSIVE 中文数据集的意图识别和槽位填充任务。

## 📋 文件说明

```
chinese_data/
├── zh-CN.jsonl              # 原始数据（16,520条）
├── README.md                # 数据集说明
├── DATA_PROCESSING.md       # 数据加工方案文档
│
├── process_massive.py       # ⭐ 数据处理脚本
├── inference.py             # ⭐ 推理脚本
├── evaluate.py              # ⭐ 评估脚本
├── USAGE.md                 # 本文档
│
├── processed_instruction/   # 输出：标准指令格式
│   ├── train.jsonl
│   ├── validation.jsonl
│   ├── test.jsonl
│   └── statistics.json
│
└── processed_chat/          # 输出：对话格式
    ├── train.jsonl
    ├── validation.jsonl
    ├── test.jsonl
    └── statistics.json
```

---

## 🚀 快速开始

### 步骤1: 安装依赖

```bash
pip install transformers datasets peft accelerate torch scikit-learn tqdm
```

### 步骤2: 数据处理

#### 生成标准指令格式（推荐）

```bash
cd 09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data

python process_massive.py \
  --input zh-CN.jsonl \
  --output processed_instruction \
  --format instruction
```

#### 生成对话格式（可选）

```bash
python process_massive.py \
  --input zh-CN.jsonl \
  --output processed_chat \
  --format chat
```

#### 同时生成两种格式

```bash
# 生成标准指令格式
python process_massive.py --format instruction --output processed_instruction

# 生成对话格式
python process_massive.py --format chat --output processed_chat
```

**输出示例**：
```
================================================================================
📦 MASSIVE 中文数据处理
================================================================================
输入文件: zh-CN.jsonl
输出目录: processed_instruction
数据格式: instruction
质量过滤: 启用
================================================================================

✅ 已生成: train.jsonl        ( 9234 条)
✅ 已生成: validation.jsonl   ( 1628 条)
✅ 已生成: test.jsonl         ( 2398 条)

================================================================================
📊 数据统计
================================================================================
总样本数:      16520
过滤样本数:     3260 (19.73%)
保留样本数:    13260 (80.27%)

数据集划分:
  训练集:       9234 条
  验证集:       1628 条
  测试集:       2398 条

标注统计:
  意图类别:       60 种
  场景类别:       18 种
  槽位类型:       55 种
```

---

### 步骤3: LoRA 微调（使用你自己的训练脚本）

使用生成的数据进行 LoRA 微调，例如：

```bash
# 使用 Qwen2.5-1.5B-Instruct 进行微调
python train_lora.py \
  --model_name Qwen/Qwen2.5-1.5B-Instruct \
  --train_file processed_instruction/train.jsonl \
  --eval_file processed_instruction/validation.jsonl \
  --output_dir ./outputs/qwen2.5-intent-slot \
  --num_epochs 3 \
  --batch_size 8 \
  --learning_rate 2e-4
```

---

### 步骤4: 模型推理

使用微调后的模型进行预测：

```bash
python inference.py \
  --base-model Qwen/Qwen2.5-1.5B-Instruct \
  --lora-path ./outputs/qwen2.5-intent-slot/checkpoint-best \
  --test-file processed_instruction/test.jsonl \
  --output predictions.jsonl \
  --batch-size 8
```

**参数说明**：
- `--base-model`: 基础模型路径（HuggingFace模型名或本地路径）
- `--lora-path`: LoRA权重路径（可选，不提供则使用基础模型）
- `--test-file`: 测试文件路径
- `--output`: 预测结果输出路径
- `--batch-size`: 批次大小（根据显存调整）
- `--temperature`: 温度参数（0表示贪心解码，推荐0.1）
- `--max-new-tokens`: 最大生成长度（默认256）

**输出示例**：
```
📦 加载模型...
  基础模型: Qwen/Qwen2.5-1.5B-Instruct
  LoRA权重: ./outputs/qwen2.5-intent-slot/checkpoint-best
✅ 模型加载完成！

🚀 开始推理...
  测试文件: processed_instruction/test.jsonl
  输出文件: predictions.jsonl
  批次大小: 8
  样本总数: 2398

推理进度: 100%|████████████████████| 300/300 [02:15<00:00,  2.21it/s]

✅ 推理完成！结果已保存到: predictions.jsonl
   共预测 2398 个样本
```

---

### 步骤5: 评估结果

```bash
python evaluate.py \
  --pred predictions.jsonl
```

**输出示例**：
```
================================================================================
📊 意图识别 + 槽位填充 评估结果
================================================================================

📌 数据集信息:
  测试样本数:    2398
  解析错误数:      12 ( 0.50%)

🎯 意图识别:
  Accuracy:      0.9450 ( 94.50%)
  F1 (Macro):    0.9201
  F1 (Weighted): 0.9447

🏷️  槽位填充:
  Exact Match:   0.8567 ( 85.67%)
  Precision:     0.9123
  Recall:        0.8891
  F1:            0.9005

🔗 联合任务:
  Joint Accuracy: 0.8125 ( 81.25%)
    （意图和所有槽位都正确的样本比例）

================================================================================

📋 意图分类详细报告:
              precision    recall  f1-score   support

  alarm_set       0.96      0.95      0.96        96
calendar_query    0.94      0.96      0.95       143
...

❌ 错误分析统计:
  总错误数:        450
  意图错误:        132 ( 5.50%)
  槽位错误:        343 (14.30%)
  两者都错:         25 ( 1.04%)

💾 错误案例已保存到: predictions_errors.jsonl
   共 450 个错误案例
```

---

## 📖 详细参数说明

### process_massive.py - 数据处理

```bash
python process_massive.py [OPTIONS]

选项:
  --input FILE          输入文件路径（默认: zh-CN.jsonl）
  --output DIR          输出目录（默认: processed_instruction）
  --format TYPE         数据格式: instruction 或 chat（默认: instruction）
  --no-filter           禁用质量过滤
  --quiet               静默模式，不输出详细信息

示例:
  # 基本使用
  python process_massive.py

  # 自定义输出目录和格式
  python process_massive.py --output my_data --format chat

  # 禁用质量过滤（保留所有数据）
  python process_massive.py --no-filter
```

### inference.py - 推理

```bash
python inference.py [OPTIONS]

必需参数:
  --base-model PATH     基础模型路径
  --test-file FILE      测试文件路径
  --output FILE         输出文件路径

可选参数:
  --lora-path PATH      LoRA权重路径
  --batch-size N        批次大小（默认: 8）
  --max-new-tokens N    最大生成长度（默认: 256）
  --temperature F       温度参数（默认: 0.1）
  --format TYPE         数据格式类型（默认: instruction）
  --device DEVICE       设备类型（默认: auto）

示例:
  # 使用基础模型
  python inference.py \
    --base-model Qwen/Qwen2.5-1.5B-Instruct \
    --test-file processed_instruction/test.jsonl \
    --output predictions.jsonl

  # 使用LoRA微调模型
  python inference.py \
    --base-model Qwen/Qwen2.5-1.5B-Instruct \
    --lora-path ./outputs/checkpoint-best \
    --test-file processed_instruction/test.jsonl \
    --output predictions.jsonl
```

### evaluate.py - 评估

```bash
python evaluate.py [OPTIONS]

必需参数:
  --pred FILE           预测结果文件路径

可选参数:
  --error-file FILE     错误案例保存路径
  --no-detail           不显示详细报告
  --no-save-errors      不保存错误案例
  --output FILE         评估结果保存路径（JSON格式）

示例:
  # 基本评估
  python evaluate.py --pred predictions.jsonl

  # 保存详细评估结果
  python evaluate.py \
    --pred predictions.jsonl \
    --output evaluation_results.json \
    --error-file errors.jsonl

  # 简化输出
  python evaluate.py --pred predictions.jsonl --no-detail
```

---

## 📊 数据格式说明

### 标准指令格式 (instruction)

```json
{
  "instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。",
  "input": "星期五早上九点叫醒我",
  "output": "{\"intent\": \"alarm_set\", \"slots\": [{\"type\": \"date\", \"value\": \"星期五\"}, {\"type\": \"time\", \"value\": \"九点\"}]}",
  "meta": {
    "id": "1",
    "scenario": "alarm",
    "partition": "train"
  }
}
```

### 对话格式 (chat)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的意图识别和槽位抽取助手。用户输入一句话，你需要识别意图并提取槽位信息，以JSON格式回复。"
    },
    {
      "role": "user",
      "content": "星期五早上九点叫醒我"
    },
    {
      "role": "assistant",
      "content": "{\"intent\": \"alarm_set\", \"slots\": [{\"type\": \"date\", \"value\": \"星期五\"}, {\"type\": \"time\", \"value\": \"九点\"}]}"
    }
  ],
  "meta": {
    "id": "1",
    "scenario": "alarm",
    "partition": "train"
  }
}
```

---

## 💡 常见问题

### Q1: 如何查看数据统计信息？

```bash
# 方法1: 查看 statistics.json
cat processed_instruction/statistics.json

# 方法2: 重新运行处理脚本（会显示统计）
python process_massive.py --output processed_instruction
```

### Q2: 如何调整质量过滤标准？

编辑 `process_massive.py` 中的 `filter_samples()` 函数，修改过滤规则。

### Q3: 推理时显存不足怎么办？

```bash
# 减小批次大小
python inference.py --batch-size 4 ...

# 或使用 CPU（很慢）
python inference.py --device cpu ...
```

### Q4: 如何只评估意图识别，不评估槽位？

评估脚本会同时输出意图和槽位的指标，你可以只关注意图部分的结果。

### Q5: 如何查看具体的错误案例？

```bash
# 评估时会自动生成 predictions_errors.jsonl
python evaluate.py --pred predictions.jsonl

# 查看错误案例
head -10 predictions_errors.jsonl | python -m json.tool
```

---

## 🔧 完整工作流示例

```bash
# 1. 数据处理（生成两种格式）
python process_massive.py --format instruction --output processed_instruction
python process_massive.py --format chat --output processed_chat

# 2. LoRA 微调（使用你的训练脚本）
# python train_lora.py ...

# 3. 推理（标准指令格式）
python inference.py \
  --base-model Qwen/Qwen2.5-1.5B-Instruct \
  --lora-path ./outputs/checkpoint-best \
  --test-file processed_instruction/test.jsonl \
  --output predictions.jsonl \
  --batch-size 8

# 4. 评估
python evaluate.py \
  --pred predictions.jsonl \
  --output evaluation_results.json

# 5. 查看错误案例
head -20 predictions_errors.jsonl | python -m json.tool
```

---

## 📚 相关文档

- **数据集说明**: `README.md`
- **数据加工方案**: `DATA_PROCESSING.md`
- **MASSIVE 论文**: https://arxiv.org/abs/2204.08582
- **官方仓库**: https://github.com/alexa/massive

---

## 📧 技术支持

如有问题，请查看：
1. `DATA_PROCESSING.md` - 详细的数据加工方案和 LoRA 微调建议
2. 脚本内的帮助信息（`python xxx.py --help`）
3. 错误案例文件（`*_errors.jsonl`）

---

**最后更新**: 2025-12-17
