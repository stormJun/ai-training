# MASSIVE 中文意图分类模型微调指南

## 📋 目录

- [数据集介绍](#数据集介绍)
- [数据准备](#数据准备)
- [微调流程](#微调流程)
- [模型评估](#模型评估)
- [部署使用](#部署使用)

---

## 🎯 数据集介绍

### MASSIVE 数据集概述

**MASSIVE (Multilingual Amazon SLU resource package)** 是一个大规模多语言意图分类数据集，包含：

- **语言**: 51 种语言（本项目使用中文版本）
- **规模**: 约 19,521 条中文语句
- **意图类别**: 60 种意图（如闹钟设置、音量控制、日历查询等）
- **应用场景**: 智能助手、语音交互系统

### 数据集文件说明

```
amazon_massive_intent_zh-CN/
├── train.jsonl           # 训练集 (约 11,514 条)
├── validation.jsonl      # 验证集 (约 2,033 条)
├── test.jsonl           # 测试集 (约 2,974 条)
├── Mytrain.jsonl        # 自定义训练集
└── Template_Trainingdata.jsonl  # 格式模板
```

### 原始数据格式

```json
{
  "id": "1",
  "label": 48,
  "text": "星期五早上九点叫醒我",
  "label_text": "alarm_set",
  "label_text_ch": "报警器"
}
```

**字段说明**:
- `id`: 数据唯一标识
- `label`: 意图类别 ID (0-59)
- `text`: 用户输入的原始语句
- `label_text`: 英文意图标签
- `label_text_ch`: 中文意图标签

---

## 🔧 数据准备

### 步骤 1: 数据格式转换

02_finetuning_and_peft/foundations 微调平台需要以下格式：

**方案 A: 指令格式** (推荐用于指令微调)
```json
{
  "instruction": "请识别以下用户语句的意图分类",
  "input": "星期五早上九点叫醒我",
  "output": "报警器(alarm_set)"
}
```

**方案 B: 对话格式** (推荐用于聊天模型)
```json
{
  "messages": [
    {"role": "system", "content": "你是一个意图识别助手"},
    {"role": "user", "content": "请识别意图: 星期五早上九点叫醒我"},
    {"role": "assistant", "content": "意图分类: 报警器(alarm_set)"}
  ]
}
```

### 步骤 2: 使用转换脚本

我们提供了自动转换脚本：

```bash
cd 02_finetuning_and_peft/foundations

# 转换训练集（指令格式）
python convert_massive_to_training_format.py \
  --input amazon_massive_intent_zh-CN/train.jsonl \
  --output amazon_massive_intent_zh-CN/train_converted.jsonl \
  --format instruction \
  --preview

# 转换验证集
python convert_massive_to_training_format.py \
  --input amazon_massive_intent_zh-CN/validation.jsonl \
  --output amazon_massive_intent_zh-CN/validation_converted.jsonl \
  --format instruction

# 转换测试集
python convert_massive_to_training_format.py \
  --input amazon_massive_intent_zh-CN/test.jsonl \
  --output amazon_massive_intent_zh-CN/test_converted.jsonl \
  --format instruction
```

### 步骤 3: 验证转换结果

```bash
# 查看前 3 条数据
head -n 3 amazon_massive_intent_zh-CN/train_converted.jsonl | python -m json.tool
```

---

## 🚀 微调流程

### 方式 1: 使用 Web 界面（推荐新手）

#### 1️⃣ 启动微调平台

```bash
cd 02_finetuning_and_peft/foundations
python -m local_ft.server
```

访问: http://localhost:7866

#### 2️⃣ 上传数据集

1. 进入 **数据上传** 页面
2. 选择转换后的 `train_converted.jsonl` 文件
3. 输入数据集名称: `massive_zh_intent`
4. 点击 **上传数据集**

#### 3️⃣ 配置微调参数

进入 **模型微调** 页面，配置：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| **基础模型** | `Qwen/Qwen2.5-1.5B-Instruct` | 轻量级中文模型 |
| **训练类型** | `lora` | LoRA 参数高效微调 |
| **数据集** | `custom:massive_zh_intent` | 选择上传的数据集 |
| **训练轮数** | `3` | 通常 2-3 轮即可 |
| **学习率** | `1e-4` | 稳定的学习率 |
| **批次大小** | `8` | 根据显存调整 |
| **LoRA Rank** | `8` | 平衡效果和速度 |
| **LoRA Alpha** | `16` | 通常为 rank 的 2 倍 |

#### 4️⃣ 启动训练

点击 **开始训练**，实时监控：
- 训练 Loss 曲线
- 日志输出
- GPU 使用率

#### 5️⃣ 权重合并

训练完成后：
1. 进入 **权重合并** 页面
2. 选择 checkpoint（如 `output/v0-20241216-120000/checkpoint-500`）
3. 点击 **开始合并**

---

### 方式 2: 使用命令行（推荐高级用户）

#### 直接使用 swift 命令

```bash
swift sft \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --train_type lora \
  --dataset custom:massive_zh_intent \
  --num_train_epochs 3 \
  --per_device_train_batch_size 8 \
  --learning_rate 1e-4 \
  --lora_rank 8 \
  --lora_alpha 16 \
  --target_modules q_proj k_proj v_proj o_proj \
  --gradient_accumulation_steps 4 \
  --eval_steps 100 \
  --save_steps 500 \
  --logging_steps 10 \
  --output_dir output/massive_zh_v1
```

#### 参数说明

**基础参数**:
- `--model`: 基础模型路径
- `--train_type`: 微调类型（lora/full）
- `--dataset`: 数据集名称

**训练参数**:
- `--num_train_epochs`: 训练轮数
- `--per_device_train_batch_size`: 每张卡的批次大小
- `--learning_rate`: 学习率
- `--gradient_accumulation_steps`: 梯度累积步数

**LoRA 参数**:
- `--lora_rank`: LoRA 秩（控制参数量）
- `--lora_alpha`: LoRA 缩放因子
- `--target_modules`: 应用 LoRA 的模块

**保存参数**:
- `--eval_steps`: 每 N 步评估一次
- `--save_steps`: 每 N 步保存一次
- `--output_dir`: 输出目录

---

## 📊 模型评估

### 评估脚本

创建评估脚本 `evaluate_model.py`:

```python
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

# 加载模型
model_path = "output/massive_zh_v1/checkpoint-1500"
model = AutoModelForCausalLM.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 加载测试集
test_data = []
with open("amazon_massive_intent_zh-CN/test_converted.jsonl") as f:
    for line in f:
        test_data.append(json.loads(line))

# 评估
correct = 0
total = len(test_data)

for item in tqdm(test_data):
    # 构建输入
    prompt = f"{item['instruction']}\n{item['input']}"

    # 推理
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=100)
    prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 判断正确性
    if item['output'] in prediction:
        correct += 1

# 计算准确率
accuracy = correct / total * 100
print(f"准确率: {accuracy:.2f}%")
```

运行评估:
```bash
python evaluate_model.py
```

---

## 🎯 模型使用

### 推理示例

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载模型
model_path = "output/massive_zh_v1_merged"
model = AutoModelForCausalLM.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 推理函数
def classify_intent(text):
    prompt = f"请识别以下用户语句的意图分类\n{text}"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=100)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return result

# 测试
test_cases = [
    "明天早上七点叫我起床",
    "把音量调大一点",
    "今天天气怎么样",
    "播放周杰伦的歌"
]

for text in test_cases:
    intent = classify_intent(text)
    print(f"输入: {text}")
    print(f"意图: {intent}\n")
```

### API 服务部署

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 加载模型（启动时）
model = AutoModelForCausalLM.from_pretrained("output/massive_zh_v1_merged")
tokenizer = AutoTokenizer.from_pretrained("output/massive_zh_v1_merged")

class IntentRequest(BaseModel):
    text: str

@app.post("/classify")
def classify_intent(request: IntentRequest):
    prompt = f"请识别以下用户语句的意图分类\n{request.text}"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=100)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return {"intent": result}

# 启动: uvicorn api:app --host 0.0.0.0 --port 8000
```

---

## 💡 进阶技巧

### 1. 数据增强

```python
# 对每条数据进行改写扩充
def augment_data(original_data):
    augmented = []

    templates = [
        "请识别以下用户语句的意图分类",
        "判断这句话的意图类别",
        "分析用户意图",
        "识别语句意图"
    ]

    for item in original_data:
        for template in templates:
            augmented.append({
                "instruction": template,
                "input": item["input"],
                "output": item["output"]
            })

    return augmented
```

### 2. 多意图训练

如果你有多个意图分类数据集，可以合并训练：

```bash
# 合并数据集
cat dataset1.jsonl dataset2.jsonl massive_converted.jsonl > combined.jsonl

# 训练
swift sft --dataset custom:combined ...
```

### 3. Few-shot 学习

在 prompt 中添加示例：

```python
few_shot_prompt = """
示例：
输入: 明天八点叫醒我
输出: 报警器(alarm_set)

输入: 把音量调小
输出: 音量控制(audio_volume_down)

请识别以下语句的意图:
输入: {user_input}
输出:
"""
```

---

## 🐛 常见问题

### Q1: 训练时显存不足

**解决方案**:
```bash
# 减小 batch_size
--per_device_train_batch_size 4

# 增加梯度累积
--gradient_accumulation_steps 8

# 使用更小的模型
--model Qwen/Qwen2.5-0.5B-Instruct
```

### Q2: 训练 Loss 不下降

**检查清单**:
- ✅ 学习率是否合适（尝试 1e-5 到 1e-4）
- ✅ 数据格式是否正确
- ✅ 是否有足够的训练数据
- ✅ 是否需要更多训练轮数

### Q3: 推理结果不理想

**优化方向**:
- 增加训练数据量
- 调整 prompt 格式
- 尝试更大的模型
- 增加 LoRA rank

---

## 📈 性能指标

基于 Qwen2.5-1.5B-Instruct + MASSIVE 中文数据集:

| 配置 | 训练时间 | 准确率 | 显存占用 |
|------|---------|--------|----------|
| **LoRA (rank=8)** | ~1小时 | 85-90% | 6GB |
| **LoRA (rank=16)** | ~1.5小时 | 88-92% | 8GB |
| **Full Fine-tune** | ~3小时 | 90-95% | 16GB |

*以上数据基于 RTX 3090 (24GB)*

---

## 🔗 相关资源

- [ms-swift 文档](https://github.com/modelscope/swift)
- [MASSIVE 数据集论文](https://arxiv.org/abs/2204.08582)
- [Qwen2.5 模型](https://huggingface.co/Qwen)

---

**最后更新**: 2024-12-16
**维护者**: AI Engineering Training Team
