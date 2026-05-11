# MASSIVE 中文数据加工方案：面向小尺寸模型 LoRA 微调

## 📋 方案概述

本文档设计一套面向**小尺寸模型（1B-7B）LoRA 微调**的数据加工方案，用于实现**意图识别 + 槽位填充联合任务**。

### 核心目标
- **任务**: 意图识别（60类）+ 槽位填充（55种槽位类型）
- **模型**: Qwen2.5-1.5B / Qwen2.5-3B / Llama-3.2-3B 等小尺寸模型
- **方法**: LoRA 参数高效微调（PEFT）
- **输出**: 结构化 JSON，便于下游任务解析

---

## 1. 数据源分析

### 1.1 输入数据
- **文件**: `09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/zh-CN.jsonl`
- **总量**: 16,520 条（train: 11,514 / dev: 2,033 / test: 2,974）
- **关键字段**:
  - `utt`: 原始用户语句
  - `intent`: 意图标签（60类）
  - `scenario`: 场景分类（18类）
  - `annot_utt`: 槽位标注，格式为 `[槽位类型 : 槽位值]`
  - `judgments`: 质量评分（intent_score, slots_score, grammar_score 等）

### 1.2 数据特点
- ✅ 18个场景，60种意图，55种槽位类型
- ✅ 每条数据经过3个标注员质量评审
- ⚠️ 长尾分布：部分意图/槽位样本较少
- ⚠️ 中英混合：如 "olly 安静"
- ⚠️ 部分样本无槽位（约15-20%）

---

## 2. 加工策略：针对小模型的优化

### 2.1 为什么需要针对小模型优化？

小尺寸模型（1B-7B）相比大模型（70B+）有以下特点：
1. **容量受限**: 难以记忆复杂的多任务指令
2. **泛化较弱**: 需要更清晰、一致的数据格式
3. **推理能力有限**: 倾向于模式匹配而非复杂推理

### 2.2 优化原则

| 原则 | 说明 | 实施方式 |
|------|------|----------|
| **格式统一** | 统一输入输出格式，减少模型学习负担 | 所有样本使用相同的 instruction 和 JSON 输出结构 |
| **简化表达** | 避免复杂的自然语言描述 | 使用结构化 JSON 而非自由文本 |
| **质量优先** | 小模型对噪声敏感，需要高质量数据 | 严格质检过滤（intent_score=1, slots_score=1, grammar≥3）|
| **适度增强** | 针对长尾类别进行数据增强 | 同义词替换、槽位值替换 |

---

## 3. 数据格式设计

我们设计**两种核心格式**，分别适用于不同的训练方式：

### 3.1 格式A：标准指令格式（推荐用于 LoRA 微调）

**适用场景**: Alpaca/Qwen/Llama 等遵循 instruction-following 范式的模型

```json
{
  "instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。",
  "input": "今天下午三点提醒我开会",
  "output": "{\"intent\": \"calendar_set\", \"slots\": [{\"type\": \"date\", \"value\": \"今天\"}, {\"type\": \"timeofday\", \"value\": \"下午\"}, {\"type\": \"time\", \"value\": \"三点\"}, {\"type\": \"event_name\", \"value\": \"开会\"}]}"
}
```

**设计要点**:
- `instruction`: 固定不变，简洁明确
- `input`: 原始用户语句（`utt`）
- `output`: **字符串化的 JSON**（小模型更容易学习字符串生成而非嵌套对象）

**输出结构说明**:
```json
{
  "intent": "意图标签（60选1）",
  "slots": [
    {"type": "槽位类型", "value": "槽位值"},
    ...
  ]
}
```
- 无槽位时: `"slots": []`

### 3.2 格式B：对话格式（可选，用于 Chat 模型）

**适用场景**: Qwen-Chat、Llama-Instruct 等对话式模型

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的意图识别和槽位抽取助手。用户输入一句话，你需要识别意图并提取槽位信息，以JSON格式回复。"
    },
    {
      "role": "user",
      "content": "今天下午三点提醒我开会"
    },
    {
      "role": "assistant",
      "content": "{\"intent\": \"calendar_set\", \"slots\": [{\"type\": \"date\", \"value\": \"今天\"}, {\"type\": \"timeofday\", \"value\": \"下午\"}, {\"type\": \"time\", \"value\": \"三点\"}, {\"type\": \"event_name\", \"value\": \"开会\"}]}"
    }
  ]
}
```

**设计要点**:
- `system`: 任务描述，所有样本保持一致
- `user`: 原始语句
- `assistant`: 字符串化的 JSON 输出

---

## 4. 数据加工流程

### 4.1 数据过滤（质量保证）

```python
def filter_samples(sample):
    """质量过滤规则"""
    judgments = sample['judgments']

    # 规则1: 意图和槽位评分必须为1（完全匹配）
    intent_scores = [j['intent_score'] for j in judgments]
    slots_scores = [j['slots_score'] for j in judgments]
    if not all(s == 1 for s in intent_scores):
        return False
    if not all(s in [1, 2] for s in slots_scores):  # 2表示无槽位，也接受
        return False

    # 规则2: 语法评分≥3（足够好）
    grammar_scores = [j['grammar_score'] for j in judgments]
    if not all(s >= 3 for s in grammar_scores):
        return False

    # 规则3: 拼写评分≥2（无拼写错误）
    spelling_scores = [j['spelling_score'] for j in judgments]
    if not all(s >= 2 for s in spelling_scores):
        return False

    return True
```

**预期过滤结果**: 保留约 80-85% 的高质量数据

### 4.2 槽位解析

```python
import re
from typing import List, Tuple

def parse_slots(annot_utt: str, original_utt: str) -> List[dict]:
    """
    从标注语句中解析槽位

    Args:
        annot_utt: 如 "[date : 今天] [timeofday : 下午] [time : 三点] 提醒我 [event_name : 开会]"
        original_utt: 原始语句，用于验证

    Returns:
        [{"type": "date", "value": "今天"}, ...]
    """
    pattern = r'\[([^:]+)\s*:\s*([^\]]+)\]'
    matches = re.findall(pattern, annot_utt)

    slots = []
    for slot_type, slot_value in matches:
        slot_type = slot_type.strip()
        slot_value = slot_value.strip()

        # 验证槽位值是否在原始语句中
        if slot_value in original_utt:
            slots.append({
                "type": slot_type,
                "value": slot_value
            })
        else:
            print(f"警告: 槽位值 '{slot_value}' 未在原句 '{original_utt}' 中找到")

    return slots
```

### 4.3 数据转换

#### 格式A：标准指令格式

```python
import json

def convert_to_instruction_format(sample: dict) -> dict:
    """转换为标准指令格式"""
    # 解析槽位
    slots = parse_slots(sample['annot_utt'], sample['utt'])

    # 构造输出JSON
    output_dict = {
        "intent": sample['intent'],
        "slots": slots
    }

    # 转换为字符串（小模型友好）
    output_str = json.dumps(output_dict, ensure_ascii=False)

    return {
        "instruction": "请识别用户意图并提取槽位信息,以JSON格式输出。",
        "input": sample['utt'],
        "output": output_str,
        # 保留元信息，便于调试和分析
        "meta": {
            "id": sample['id'],
            "scenario": sample['scenario'],
            "partition": sample['partition']
        }
    }
```

#### 格式B：对话格式

```python
def convert_to_chat_format(sample: dict) -> dict:
    """转换为对话格式"""
    slots = parse_slots(sample['annot_utt'], sample['utt'])

    output_dict = {
        "intent": sample['intent'],
        "slots": slots
    }
    output_str = json.dumps(output_dict, ensure_ascii=False)

    return {
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的意图识别和槽位抽取助手。用户输入一句话，你需要识别意图并提取槽位信息，以JSON格式回复。"
            },
            {
                "role": "user",
                "content": sample['utt']
            },
            {
                "role": "assistant",
                "content": output_str
            }
        ],
        "meta": {
            "id": sample['id'],
            "scenario": sample['scenario'],
            "partition": sample['partition']
        }
    }
```

### 4.4 完整加工脚本

```python
import json
from pathlib import Path
from collections import defaultdict, Counter

def process_massive_data(
    input_file: str,
    output_dir: str,
    format_type: str = "instruction",  # "instruction" or "chat"
    enable_filter: bool = True
):
    """
    完整数据加工流程

    Args:
        input_file: zh-CN.jsonl 路径
        output_dir: 输出目录
        format_type: 数据格式类型
        enable_filter: 是否启用质量过滤
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 统计信息
    stats = {
        'total': 0,
        'filtered': 0,
        'train': 0,
        'dev': 0,
        'test': 0,
        'intent_dist': Counter(),
        'scenario_dist': Counter(),
        'slot_type_dist': Counter()
    }

    # 按partition分组
    data_by_partition = defaultdict(list)

    # 读取和处理数据
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total'] += 1
            sample = json.loads(line.strip())

            # 质量过滤
            if enable_filter and not filter_samples(sample):
                stats['filtered'] += 1
                continue

            # 转换格式
            if format_type == "instruction":
                converted = convert_to_instruction_format(sample)
            elif format_type == "chat":
                converted = convert_to_chat_format(sample)
            else:
                raise ValueError(f"Unknown format: {format_type}")

            # 分区存储
            partition = sample['partition']
            data_by_partition[partition].append(converted)

            # 更新统计
            stats[partition] += 1
            stats['intent_dist'][sample['intent']] += 1
            stats['scenario_dist'][sample['scenario']] += 1

            # 统计槽位类型
            slots = parse_slots(sample['annot_utt'], sample['utt'])
            for slot in slots:
                stats['slot_type_dist'][slot['type']] += 1

    # 写入文件
    partition_mapping = {'train': 'train', 'dev': 'validation', 'test': 'test'}
    for partition, samples in data_by_partition.items():
        output_file = output_path / f"{partition_mapping[partition]}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        print(f"✅ 已生成: {output_file} ({len(samples)} 条)")

    # 输出统计信息
    print("\n📊 数据统计:")
    print(f"  总样本数: {stats['total']}")
    print(f"  过滤样本数: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    print(f"  训练集: {stats['train']}")
    print(f"  验证集: {stats['dev']}")
    print(f"  测试集: {stats['test']}")

    print(f"\n  意图类别: {len(stats['intent_dist'])} 种")
    print(f"  场景类别: {len(stats['scenario_dist'])} 种")
    print(f"  槽位类型: {len(stats['slot_type_dist'])} 种")

    # 保存统计信息
    stats_file = output_path / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        # 转换Counter为dict以便JSON序列化
        stats_export = {
            **stats,
            'intent_dist': dict(stats['intent_dist']),
            'scenario_dist': dict(stats['scenario_dist']),
            'slot_type_dist': dict(stats['slot_type_dist'])
        }
        json.dump(stats_export, f, ensure_ascii=False, indent=2)
    print(f"\n📈 统计信息已保存: {stats_file}")

    return stats

# 使用示例
if __name__ == "__main__":
    process_massive_data(
        input_file="09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/zh-CN.jsonl",
        output_dir="09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/processed_instruction",
        format_type="instruction",
        enable_filter=True
    )

    process_massive_data(
        input_file="09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/zh-CN.jsonl",
        output_dir="09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/processed_chat",
        format_type="chat",
        enable_filter=True
    )
```

---

## 5. 输出文件说明

### 5.1 目录结构

```
09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/
├── zh-CN.jsonl                           # 原始数据
├── processed_instruction/                # 标准指令格式
│   ├── train.jsonl                      # 训练集 (~9,200条)
│   ├── validation.jsonl                 # 验证集 (~1,600条)
│   ├── test.jsonl                       # 测试集 (~2,400条)
│   └── statistics.json                  # 数据统计
└── processed_chat/                       # 对话格式
    ├── train.jsonl
    ├── validation.jsonl
    ├── test.jsonl
    └── statistics.json
```

### 5.2 数据样本示例

#### train.jsonl（标准指令格式）
```json
{"instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。", "input": "星期五早上九点叫醒我", "output": "{\"intent\": \"alarm_set\", \"slots\": [{\"type\": \"date\", \"value\": \"星期五\"}, {\"type\": \"time\", \"value\": \"九点\"}]}", "meta": {"id": "1", "scenario": "alarm", "partition": "train"}}
{"instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。", "input": "设个两小时后的闹钟", "output": "{\"intent\": \"alarm_set\", \"slots\": [{\"type\": \"time\", \"value\": \"两小时后\"}]}", "meta": {"id": "2", "scenario": "alarm", "partition": "train"}}
{"instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。", "input": "今天北京天气怎么样", "output": "{\"intent\": \"weather_query\", \"slots\": [{\"type\": \"date\", \"value\": \"今天\"}, {\"type\": \"place_name\", \"value\": \"北京\"}]}", "meta": {"id": "42", "scenario": "weather", "partition": "train"}}
```

---

## 6. LoRA 微调建议

### 6.1 推荐模型

| 模型 | 参数量 | 优势 | 备注 |
|------|--------|------|------|
| Qwen2.5-1.5B-Instruct | 1.5B | 中文优势明显，指令遵循能力强 | **首选** |
| Qwen2.5-3B-Instruct | 3B | 更强的理解能力 | 推荐 |
| Llama-3.2-3B-Instruct | 3B | 英文能力强，中文一般 | 可用 |
| GLM-4-9B-Chat | 9B | 综合能力强，但推理慢 | 资源充足时可选 |

### 6.2 LoRA 超参数建议

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,                      # LoRA秩，控制可训练参数量
    lora_alpha=32,             # 缩放因子，通常设为 2*r
    target_modules=[           # 目标模块（Qwen2.5）
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ],
    lora_dropout=0.05,         # Dropout率
    bias="none",               # 不训练bias
    task_type="CAUSAL_LM"      # 任务类型
)
```

### 6.3 训练超参数建议

```python
training_args = TrainingArguments(
    output_dir="./outputs/qwen2.5-1.5b-intent-slot",

    # 基础设置
    num_train_epochs=3,                    # 训练轮数，小数据集2-3轮足够
    per_device_train_batch_size=8,        # 批次大小，根据显存调整
    per_device_eval_batch_size=16,
    gradient_accumulation_steps=2,         # 梯度累积，等效batch_size=16

    # 学习率
    learning_rate=2e-4,                    # LoRA通常用较大学习率
    lr_scheduler_type="cosine",            # 余弦学习率衰减
    warmup_ratio=0.1,                      # 10%的步数用于warmup

    # 优化器
    optim="adamw_torch",
    weight_decay=0.01,

    # 评估与保存
    evaluation_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    save_total_limit=3,                    # 只保留最好的3个checkpoint
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",

    # 日志
    logging_steps=10,
    report_to="tensorboard",

    # 其他
    fp16=True,                             # 混合精度训练（A100可用bf16）
    gradient_checkpointing=True,           # 节省显存
    remove_unused_columns=False,
)
```

### 6.4 显存占用估算

| 模型 | Batch Size | LoRA Rank | 显存占用 | GPU 推荐 |
|------|------------|-----------|----------|----------|
| Qwen2.5-1.5B | 8 | 16 | ~8GB | RTX 3090 / V100 |
| Qwen2.5-3B | 4 | 16 | ~12GB | RTX 4090 / A100 |
| Qwen2.5-7B | 2 | 16 | ~18GB | A100 40GB |

> 启用 gradient_checkpointing 和 fp16 可以大幅降低显存占用

---

## 7. 评估方法

### 7.1 评估指标

**意图识别**:
- Accuracy: 准确率
- F1-Score (Macro): 宏平均F1
- F1-Score (Weighted): 加权F1

**槽位填充**:
- Exact Match (EM): 完全匹配率（所有槽位都正确）
- Slot F1: 槽位级别的F1（按槽位类型计算）
- Value F1: 槽位值的F1

**联合任务**:
- Joint Accuracy: 意图和所有槽位都正确的样本比例
- Intent Accuracy: 意图准确率
- Slot Exact Match: 槽位完全匹配率

### 7.2 评估脚本

```python
import json
from sklearn.metrics import accuracy_score, f1_score, classification_report
from collections import defaultdict

def evaluate_predictions(pred_file: str, gold_file: str):
    """
    评估预测结果

    Args:
        pred_file: 模型预测输出文件（每行一个JSON）
        gold_file: 标准答案文件
    """
    # 读取数据
    predictions = []
    with open(pred_file, 'r') as f:
        for line in f:
            predictions.append(json.loads(line.strip()))

    gold_data = []
    with open(gold_file, 'r') as f:
        for line in f:
            gold_data.append(json.loads(line.strip()))

    assert len(predictions) == len(gold_data), "预测和标准答案数量不一致"

    # 解析预测结果
    pred_intents = []
    gold_intents = []
    slot_exact_match = 0
    joint_correct = 0

    for pred, gold in zip(predictions, gold_data):
        # 解析预测输出（字符串 -> dict）
        try:
            pred_output = json.loads(pred['output'])
            gold_output = json.loads(gold['output'])
        except:
            print(f"解析失败: {pred['output']}")
            continue

        # 意图
        pred_intent = pred_output.get('intent', '')
        gold_intent = gold_output.get('intent', '')
        pred_intents.append(pred_intent)
        gold_intents.append(gold_intent)

        # 槽位
        pred_slots = set(
            (slot['type'], slot['value'])
            for slot in pred_output.get('slots', [])
        )
        gold_slots = set(
            (slot['type'], slot['value'])
            for slot in gold_output.get('slots', [])
        )

        if pred_slots == gold_slots:
            slot_exact_match += 1

        # 联合准确率
        if pred_intent == gold_intent and pred_slots == gold_slots:
            joint_correct += 1

    # 计算指标
    total = len(predictions)

    print("=" * 60)
    print("📊 评估结果")
    print("=" * 60)

    # 意图识别指标
    intent_acc = accuracy_score(gold_intents, pred_intents)
    intent_f1_macro = f1_score(gold_intents, pred_intents, average='macro')
    intent_f1_weighted = f1_score(gold_intents, pred_intents, average='weighted')

    print("\n🎯 意图识别:")
    print(f"  Accuracy: {intent_acc:.4f}")
    print(f"  F1 (Macro): {intent_f1_macro:.4f}")
    print(f"  F1 (Weighted): {intent_f1_weighted:.4f}")

    # 槽位填充指标
    slot_em = slot_exact_match / total

    print("\n🏷️  槽位填充:")
    print(f"  Exact Match: {slot_em:.4f}")

    # 联合任务指标
    joint_acc = joint_correct / total

    print("\n🔗 联合任务:")
    print(f"  Joint Accuracy: {joint_acc:.4f}")

    print("\n" + "=" * 60)

    # 详细分类报告（可选）
    print("\n📋 意图分类详细报告:")
    print(classification_report(gold_intents, pred_intents))

    return {
        'intent_accuracy': intent_acc,
        'intent_f1_macro': intent_f1_macro,
        'intent_f1_weighted': intent_f1_weighted,
        'slot_exact_match': slot_em,
        'joint_accuracy': joint_acc
    }
```

---

## 8. 数据增强策略（可选）

针对长尾意图/槽位，可以进行数据增强：

### 8.1 同义词替换

```python
# 示例：日期表达的多样性
date_synonyms = {
    "今天": ["今日", "本日"],
    "明天": ["明日", "次日"],
    "后天": ["后日"]
}

# 示例：时间表达
time_synonyms = {
    "早上": ["早晨", "上午"],
    "下午": ["午后"],
    "晚上": ["傍晚", "夜晚"]
}
```

### 8.2 槽位值替换

```python
# 替换人名、地名等
def augment_by_slot_replacement(sample, slot_value_pool):
    """
    通过替换槽位值来增强数据

    Args:
        sample: 原始样本
        slot_value_pool: 槽位值候选池

    Returns:
        新样本
    """
    # 解析槽位
    slots = parse_slots(sample['annot_utt'], sample['utt'])

    # 随机替换一个槽位值
    if not slots:
        return None

    slot_to_replace = random.choice(slots)
    slot_type = slot_to_replace['type']
    old_value = slot_to_replace['value']

    # 从候选池中随机选择新值
    if slot_type not in slot_value_pool:
        return None

    new_value = random.choice(slot_value_pool[slot_type])

    # 替换
    new_utt = sample['utt'].replace(old_value, new_value)

    # 构造新样本
    new_sample = sample.copy()
    new_sample['utt'] = new_utt
    # ... 更新 annot_utt 和 slots

    return new_sample
```

### 8.3 回译增强（Translation Augmentation）

```python
# 使用翻译模型进行回译
# 中文 -> 英文 -> 中文
# 可以引入一定的多样性，但需要人工检查质量
```

---

## 9. 常见问题与解决方案

### Q1: 小模型输出格式不稳定怎么办？

**问题**: 模型输出的 JSON 格式不完整或有语法错误

**解决方案**:
1. 在 instruction 中强调 JSON 格式：`"必须严格按照JSON格式输出"`
2. 增加格式示例（Few-shot）
3. 后处理：使用正则提取 intent 和 slots
4. 使用约束解码（如 JSON schema 约束）

### Q2: 槽位召回率低怎么办？

**问题**: 模型识别意图准确，但经常漏掉槽位

**解决方案**:
1. 检查训练数据中槽位标注是否完整
2. 增加有槽位样本的比例（过滤掉部分无槽位样本）
3. 在 instruction 中明确要求提取所有槽位
4. 使用更大的模型（如 3B -> 7B）

### Q3: 长尾意图效果差怎么办？

**问题**: 样本少的意图类别（< 100 条）识别效果差

**解决方案**:
1. 数据增强：针对长尾类别进行同义替换和槽位替换
2. 使用 Focal Loss 或类别权重平衡
3. 合并相似意图（如果业务允许）
4. Few-shot 提示：在推理时添加长尾类别的示例

### Q4: 模型训练不收敛怎么办？

**解决方案**:
1. 降低学习率：2e-4 -> 1e-4
2. 增加 warmup 比例：0.1 -> 0.2
3. 检查数据格式是否正确（特别是 JSON 字符串转义）
4. 使用梯度裁剪：`max_grad_norm=1.0`

---

## 10. 完整代码仓库结构

```
09_finetuning_and_data_processing/10_massive_dataset_processing/chinese_data/
├── zh-CN.jsonl                          # 原始数据
├── README.md                            # 数据集说明
├── DATA_PROCESSING.md                   # 本文档
├── process_massive.py                   # 数据加工脚本
├── evaluate.py                          # 评估脚本
├── augment.py                           # 数据增强脚本（可选）
├── train_lora.py                        # LoRA 微调脚本（可选）
├── processed_instruction/               # 输出：标准指令格式
│   ├── train.jsonl
│   ├── validation.jsonl
│   ├── test.jsonl
│   └── statistics.json
└── processed_chat/                      # 输出：对话格式
    ├── train.jsonl
    ├── validation.jsonl
    ├── test.jsonl
    └── statistics.json
```

---

## 11. 下一步行动

- [ ] 运行 `process_massive.py` 生成训练数据
- [ ] 检查 `statistics.json` 确认数据分布
- [ ] 准备 LoRA 微调环境（transformers, peft, accelerate）
- [ ] 选择基础模型（推荐 Qwen2.5-1.5B-Instruct）
- [ ] 开始微调训练
- [ ] 在验证集上评估，调整超参数
- [ ] 在测试集上评估最终模型

---

**最后更新**: 2025-12-17
**适用模型**: Qwen2.5 / Llama-3.2 / GLM-4 等指令微调模型
**推荐 GPU**: RTX 3090 / V100 / A100
