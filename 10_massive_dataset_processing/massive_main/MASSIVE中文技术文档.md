# MASSIVE 数据集中文技术文档

> 多语言自然语言理解（NLU）系统的完整训练和评估框架

## 📋 目录

1. [项目概述](#项目概述)
2. [数据集详解](#数据集详解)
3. [系统架构](#系统架构)
4. [模型详解](#模型详解)
5. [数据处理流程](#数据处理流程)
6. [训练流程](#训练流程)
7. [评估与测试](#评估与测试)
8. [配置文件详解](#配置文件详解)
9. [使用指南](#使用指南)
10. [常见问题](#常见问题)

---

## 项目概述

### 什么是 MASSIVE？

MASSIVE (Multilingual Amazon Slu resource package) 是一个大规模多语言自然语言理解数据集，包含：

- **52种语言**的超过 100 万条语句
- **60种用户意图**（如设置闹钟、查询天气、播放音乐等）
- **55种槽位类型**（如日期、时间、地点、人名等）
- **18个应用场景**（日历、天气、音乐、邮件、智能家居等）

### 项目目标

本项目提供了在 MASSIVE 数据集上训练和评估 NLU 模型的完整框架，支持：

1. **意图分类（Intent Classification）**：识别用户的意图
2. **槽位填充（Slot Filling）**：提取语句中的关键实体信息
3. **多语言学习**：支持单语言、多语言和跨语言训练
4. **多种模型架构**：XLM-RoBERTa、mT5 等预训练模型

---

## 数据集详解

### 数据格式

MASSIVE 数据集使用 JSONL 格式（每行一个 JSON 对象）。每条数据示例：

```json
{
  "id": "0",
  "locale": "zh-CN",
  "partition": "test",
  "scenario": "alarm",
  "intent": "alarm_set",
  "utt": "这周五点叫我起床",
  "annot_utt": "[date : 这周] [time : 五点] 叫我起床",
  "worker_id": "23",
  "slot_method": [
    {"slot": "time", "method": "translation"},
    {"slot": "date", "method": "translation"}
  ],
  "judgments": [
    {
      "worker_id": "33",
      "intent_score": 1,
      "slots_score": 1,
      "grammar_score": 4,
      "spelling_score": 2,
      "language_identification": "target"
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `id` | 样本唯一标识符（对应 SLURP 数据集的 ID） |
| `locale` | 语言区域代码（如 zh-CN、en-US） |
| `partition` | 数据集划分：train（训练）、dev（验证）、test（测试） |
| `scenario` | 应用场景（18种：calendar、weather、music等） |
| `intent` | 用户意图（60种：alarm_set、weather_query等） |
| `utt` | 原始用户语句 |
| `annot_utt` | 带槽位标注的语句，格式：`[槽位类型 : 槽位值]` |
| `worker_id` | 标注工人ID（每个语言独立） |
| `slot_method` | 槽位标注方法（translation、localization、unchanged） |
| `judgments` | 质量评审结果（每条数据有3个评审员） |

### 槽位标注格式

槽位标注使用方括号格式：`[槽位类型 : 槽位值]`

**示例：**
```
原始语句：今天下午三点提醒我开会
标注语句：[date : 今天] [timeofday : 下午] [time : 三点] 提醒我 [event_name : 开会]
```

在模型训练时，这会被转换为 BIO 标注格式：
- `B-slot_type`：槽位的开始
- `I-slot_type`：槽位的内部
- `O`：非槽位（Other）

### 数据统计（简体中文）

- **总样本数**：16,520 条
- **训练集**：11,514 条（69.7%）
- **验证集**：2,033 条（12.3%）
- **测试集**：2,974 条（18.0%）
- **平均语句长度**：10.5 字符

### 场景分布（Top 5）

| 场景 | 训练集 | 验证集 | 测试集 | 总计 |
|------|--------|--------|--------|------|
| calendar（日历） | 1,688 | 280 | 402 | 2,370 |
| play（播放） | 1,377 | 260 | 387 | 2,024 |
| qa（问答） | 1,183 | 214 | 288 | 1,685 |
| email（邮件） | 953 | 157 | 271 | 1,381 |
| iot（智能家居） | 769 | 118 | 220 | 1,107 |

### 意图分布（Top 10）

| 意图 | 样本数 | 描述 |
|------|--------|------|
| calendar_set | 810 | 设置日历事件 |
| play_music | 639 | 播放音乐 |
| weather_query | 573 | 查询天气 |
| calendar_query | 566 | 查询日历 |
| general_quirky | 555 | 通用闲聊 |
| qa_factoid | 544 | 事实问答 |
| news_query | 503 | 查询新闻 |
| email_query | 418 | 查询邮件 |
| email_sendemail | 354 | 发送邮件 |
| datetime_query | 350 | 查询日期时间 |

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    MASSIVE 训练系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   数据层     │ ───> │   模型层     │ ───> │  训练层  │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│        │                      │                      │        │
│        │                      │                      │        │
│   ┌────▼─────┐          ┌───▼────┐           ┌─────▼──┐   │
│   │ JSONL    │          │ XLM-R  │           │Trainer │   │
│   │ 数据集   │          │  模型  │           │  引擎  │   │
│   └──────────┘          └────────┘           └────────┘   │
│   ┌──────────┐          ┌────────┐           ┌────────┐   │
│   │HF Dataset│          │  mT5   │           │ 评估器 │   │
│   │   格式   │          │  模型  │           └────────┘   │
│   └──────────┘          └────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构

```
massive-main/
├── scripts/                    # 脚本目录
│   ├── train.py               # 训练脚本（已添加中文注释）
│   ├── test.py                # 测试脚本（已添加中文注释）
│   ├── predict.py             # 预测脚本
│   ├── run_hpo.py             # 超参数优化脚本
│   └── create_hf_dataset.py   # 数据集转换脚本（已添加中文注释）
│
├── src/massive/               # 源代码目录
│   ├── models/                # 模型定义
│   │   ├── xlmr_ic_sf.py     # XLM-R 联合模型（已添加中文注释）
│   │   └── mt5_ic_sf_encoder_only.py  # mT5 编码器模型
│   │
│   ├── utils/                 # 工具函数
│   │   ├── training_utils.py  # 训练工具函数
│   │   └── trainer.py         # 自定义训练器
│   │
│   └── loaders/               # 数据加载器
│       ├── collator_ic_sf.py  # 数据整理器（JointBERT风格）
│       └── collator_t2t_ic_sf.py  # 文本到文本数据整理器
│
├── examples/                  # 配置文件示例
│   ├── xlmr_base_20220411.yml       # XLM-R 基础配置
│   ├── mt5_base_t2t_20220411.yml    # mT5 文本到文本配置
│   └── xlmr_base_test_20220411.yml  # 测试配置示例
│
├── 1.1/data/                  # 数据目录
│   ├── zh-CN.jsonl           # 简体中文数据
│   ├── en-US.jsonl           # 美式英语数据
│   └── ...                    # 其他50种语言
│
└── README.md                  # 原始英文文档
```

---

## 模型详解

### 1. XLM-RoBERTa 联合模型

#### 模型架构

```
输入文本：今天下午三点提醒我开会
      │
      ▼
┌─────────────────────────────┐
│  Token化 & 添加特殊标记     │
│  [CLS] 今 天 下 午 三 点    │
│  提 醒 我 开 会 [SEP]       │
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│   XLM-RoBERTa 编码器        │
│   (12/24层 Transformer)      │
│   - 多头自注意力             │
│   - 前馈神经网络             │
│   - 层归一化                 │
└─────────────────────────────┘
      │
      ├─────────────┬─────────────┐
      ▼             ▼             ▼
  [CLS]表示    Token表示    [SEP]表示
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│ 意图分类头│  │ 槽位填充头│
│  (全连接) │  │  (全连接) │
└──────────┘  └──────────┘
      │             │
      ▼             ▼
  calendar_set    [date: 今天]
                  [timeofday: 下午]
                  [time: 三点]
                  [event_name: 开会]
```

#### 关键特性

1. **预训练编码器**：
   - 基于 XLM-RoBERTa Base（12层）或 Large（24层）
   - 在100种语言的海量文本上预训练
   - 使用掩码语言模型（MLM）目标

2. **意图分类头**：
   - 输入：[CLS] token 的表示（或池化后的序列表示）
   - 结构：1-2层全连接网络
   - 输出：60维向量（60种意图的 logits）
   - 激活函数：GELU
   - Dropout：0.1-0.3

3. **槽位填充头**：
   - 输入：每个 token 的隐藏状态
   - 结构：1-2层全连接网络
   - 输出：每个 token 的55维向量（55种槽位类型）
   - 使用 attention_mask 忽略 padding token

4. **联合训练**：
   ```python
   # 损失函数
   total_loss = intent_loss + slot_loss_coef * slot_loss

   # 其中：
   # - intent_loss: 交叉熵损失（60分类）
   # - slot_loss: 交叉熵损失（55分类，针对每个 token）
   # - slot_loss_coef: 槽位损失权重（通常为 1.0）
   ```

#### 模型参数

| 参数 | XLM-R Base | XLM-R Large |
|------|------------|-------------|
| 隐藏层大小 | 768 | 1024 |
| 注意力头数 | 12 | 16 |
| Transformer 层数 | 12 | 24 |
| 参数总数 | ~270M | ~550M |
| 词表大小 | 250,002 | 250,002 |

### 2. mT5 模型

#### 架构特点

mT5 (multilingual T5) 支持两种使用方式：

**方式一：编码器模式（类似 XLM-R）**
- 只使用 mT5 的编码器部分
- 添加意图和槽位分类头
- 与 XLM-R 模型结构相似

**方式二：序列到序列模式（Text-to-Text）**
- 使用完整的编码器-解码器架构
- 将 NLU 任务转换为文本生成任务
- 输入：`intent and slots: 今天下午三点提醒我开会`
- 输出：`intent: calendar_set slots: [date: 今天] [timeofday: 下午] [time: 三点] [event_name: 开会]`

#### 文本到文本格式示例

```python
# 输入格式
input_text = "intent and slots: " + utterance

# 输出格式
output_text = f"intent: {intent} slots: {annotated_utterance}"

# 具体示例
输入：intent and slots: 北京明天会下雨吗
输出：intent: weather_query slots: [place_name: 北京] [date: 明天] 会 [weather_descriptor: 下雨] 吗
```

---

## 数据处理流程

### 步骤 1: JSONL 到 HuggingFace Dataset

使用 `create_hf_dataset.py` 脚本转换数据：

```bash
python scripts/create_hf_dataset.py \
    -d /path/to/massive/data \
    -o /path/to/output/dataset_prefix
```

#### 转换过程

1. **读取 JSONL 文件**
   ```python
   with open('zh-CN.jsonl', 'r') as f:
       for line in f:
           data = json.loads(line)
   ```

2. **中文分词处理**
   ```python
   # 对于中日韩语言，进行字符级分词
   if locale in ['zh-CN', 'zh-TW', 'ja-JP']:
       tokens = list(utterance)  # 逐字符分割
   else:
       tokens = utterance.split()  # 空格分词
   ```

3. **槽位标注解析**
   ```python
   # 从 "[date : 今天] 天气" 解析为:
   tokens = ['今', '天', '天', '气']
   labels = ['date', 'date', 'Other', 'Other']
   ```

4. **创建数值标签**
   ```python
   # 意图映射
   intent_dict = {
       'alarm_set': 0,
       'calendar_set': 1,
       # ... 共60个意图
   }

   # 槽位映射
   slot_dict = {
       'Other': 0,
       'date': 1,
       'time': 2,
       # ... 共55个槽位类型
   }
   ```

5. **保存为 HuggingFace Dataset**
   ```python
   # 保存数据集
   dataset.save_to_disk('/path/to/output.train')
   dataset.save_to_disk('/path/to/output.dev')
   dataset.save_to_disk('/path/to/output.test')

   # 保存标签映射
   json.dump(intent_dict, open('/path/to/output.intents', 'w'))
   json.dump(slot_dict, open('/path/to/output.slots', 'w'))
   ```

### 步骤 2: 数据整理（Collation）

在训练时，`DataCollator` 将批次数据转换为模型输入格式：

```python
# 原始数据
{
    'utt': ['今', '天', '天', '气'],
    'intent_num': 42,
    'slots_num': [1, 1, 0, 0]
}

# 经过 tokenizer 和 collator 后：
{
    'input_ids': [0, 1234, 5678, 5678, 9012, 2],  # [CLS] + tokens + [SEP]
    'attention_mask': [1, 1, 1, 1, 1, 1],
    'intent_num': 42,
    'slots_num': [-100, 1, 1, 0, 0, -100]  # -100 表示忽略（特殊标记）
}
```

---

## 训练流程

### 配置文件

训练使用 YAML 格式的配置文件。示例配置：

```yaml
# XLM-R 基础配置示例
train_val:
  # 数据路径
  dataset_loc: /path/to/hf_dataset

  # 模型配置
  model_name: xlmr_ic_sf
  pretrained_model: xlm-roberta-base

  # 训练参数
  trainer_args:
    output_dir: /path/to/output
    num_train_epochs: 20
    per_device_train_batch_size: 32
    per_device_eval_batch_size: 32
    learning_rate: 5e-5
    warmup_ratio: 0.1
    weight_decay: 0.01
    evaluation_strategy: epoch
    save_strategy: epoch
    load_best_model_at_end: true
    metric_for_best_model: exact_match

  # 模型超参数
  model_config:
    slot_loss_coef: 1.0
    head_num_layers: 1
    head_layer_dim: 768
    head_dropout_rate: 0.1
    head_activation: gelu
    head_intent_pooling: first  # 使用 [CLS] token

  # 评估配置
  eval_metrics: all
  slot_labels_ignore: ['Other']  # 评估时忽略 'Other' 标签
```

### 执行训练

#### 单 GPU 训练

```bash
python scripts/train.py -c config/xlmr_base.yml
```

#### 多 GPU 训练（8 GPU）

```bash
# PyTorch >= 1.10
torchrun --nproc_per_node=8 scripts/train.py -c config/xlmr_base.yml

# PyTorch < 1.10
python -m torch.distributed.launch --nproc_per_node=8 scripts/train.py -c config/xlmr_base.yml
```

### 训练过程

1. **初始化阶段**
   - 加载配置文件
   - 初始化分词器（XLM-RoBERTa Tokenizer）
   - 加载数据集（train/dev）
   - 初始化模型（加载预训练权重）
   - 设置优化器（AdamW）和学习率调度器

2. **训练循环**
   ```python
   for epoch in range(num_epochs):
       for batch in train_dataloader:
           # 前向传播
           outputs = model(
               input_ids=batch['input_ids'],
               attention_mask=batch['attention_mask'],
               intent_num=batch['intent_num'],
               slots_num=batch['slots_num']
           )
           loss = outputs[0]

           # 反向传播
           loss.backward()
           optimizer.step()
           lr_scheduler.step()
           optimizer.zero_grad()

       # 每个 epoch 后评估
       eval_metrics = evaluate(model, dev_dataloader)

       # 保存最佳模型
       if eval_metrics['exact_match'] > best_metric:
           save_checkpoint(model)
   ```

3. **学习率调度**
   ```python
   # 线性预热 + 线性衰减
   total_steps = num_epochs * steps_per_epoch
   warmup_steps = warmup_ratio * total_steps

   # 学习率变化曲线
   lr = 5e-5 (最大值)
        │     ╱╲
        │    ╱  ╲___
        │   ╱       ╲___
        │  ╱            ╲___
        │ ╱                 ╲___
        └─────────────────────────> steps
          0     warmup   total
   ```

### 训练监控

训练过程中会记录以下指标：

```python
{
    'epoch': 1,
    'loss': 0.342,
    'learning_rate': 4.5e-5,
    'eval_intent_acc': 0.856,
    'eval_slot_micro_f1': 0.823,
    'eval_exact_match': 0.745,
    'eval_loss': 0.298
}
```

---

## 评估与测试

### 评估指标

#### 1. 意图准确率（Intent Accuracy）

```python
intent_accuracy = (正确预测的意图数) / (总样本数)
```

#### 2. 槽位微平均 F1（Slot Micro F1）

```python
# 计算所有槽位的精确率和召回率
precision = TP / (TP + FP)
recall = TP / (TP + FN)
f1 = 2 * precision * recall / (precision + recall)

# 其中：
# TP: 正确识别的槽位token数
# FP: 错误识别为槽位的token数
# FN: 遗漏的槽位token数
```

#### 3. 精确匹配准确率（Exact Match Accuracy）

```python
# 意图和所有槽位都完全正确才算匹配
exact_match = (完全正确的样本数) / (总样本数)
```

### 执行测试

```bash
# 单 GPU 测试
python scripts/test.py -c config/xlmr_base_test.yml

# 多 GPU 测试
torchrun --nproc_per_node=8 scripts/test.py -c config/xlmr_base_test.yml
```

### 测试配置示例

```yaml
test:
  # 数据和模型路径
  dataset_loc: /path/to/hf_dataset
  model_loc: /path/to/trained/model/checkpoint

  # 输出文件（可选，用于提交到 eval.ai）
  predictions_file: /path/to/predictions.jsonl

  # 训练器参数
  trainer_args:
    per_device_eval_batch_size: 32
    locale_eval_strategy: all only  # 必须为 'all only' 如果要保存预测

  # 评估配置
  eval_metrics: all
  slot_labels_ignore: ['Other']
```

### 输出格式

测试完成后会输出详细的评估结果：

```python
{
  # 整体指标
  "test_intent_acc": 0.8623,
  "test_slot_micro_f1": 0.8347,
  "test_exact_match": 0.7512,

  # 按语言分解
  "test_zh-CN_intent_acc": 0.8734,
  "test_zh-CN_slot_micro_f1": 0.8456,
  "test_zh-CN_exact_match": 0.7623,

  # 按场景分解
  "test_calendar_intent_acc": 0.9123,
  "test_weather_intent_acc": 0.8956,
  # ...
}
```

---

## 配置文件详解

### 完整配置文件示例

```yaml
# ==================== 训练和验证配置 ====================
train_val:
  # ---------- 数据集配置 ----------
  dataset_loc: /path/to/massive_1.0_hf_format/massive_1.0  # 数据集路径
  langs: ['zh-CN']  # 训练语言（可以是多个）

  # ---------- 模型配置 ----------
  model_name: xlmr_ic_sf  # 模型类型
  pretrained_model: xlm-roberta-base  # 预训练模型

  # 模型超参数
  model_config:
    slot_loss_coef: 1.0  # 槽位损失权重
    head_num_layers: 1  # 分类头层数
    head_layer_dim: null  # 分类头维度（null表示使用hidden_size）
    head_dropout_rate: 0.1  # Dropout率
    head_activation: gelu  # 激活函数
    head_intent_pooling: first  # 意图池化方式（first/mean/max）
    hidden_layer_for_class: last  # 使用哪一层的隐藏状态

  # ---------- Tokenizer 配置 ----------
  tokenizer:
    pretrained_model: xlm-roberta-base
    use_fast: true  # 使用快速tokenizer

  # ---------- 数据整理器配置 ----------
  collator:
    type: ic_sf  # 类型：ic_sf 或 t2t_ic_sf
    max_length: 128  # 最大序列长度
    padding: max_length  # padding策略
    slot_pad_token: -100  # 槽位padding值

  # ---------- 训练器类型 ----------
  trainer: massive  # 'massive' 或 'massive s2s'

  # ---------- 训练参数 ----------
  trainer_args:
    # 输出和日志
    output_dir: /path/to/output
    logging_dir: /path/to/logs
    logging_strategy: steps
    logging_steps: 50

    # 训练控制
    num_train_epochs: 20
    per_device_train_batch_size: 32
    per_device_eval_batch_size: 32
    gradient_accumulation_steps: 1

    # 优化器
    learning_rate: 5.0e-5
    weight_decay: 0.01
    adam_epsilon: 1.0e-8
    max_grad_norm: 1.0

    # 学习率调度
    warmup_ratio: 0.1
    lr_scheduler_type: linear

    # 评估和保存
    evaluation_strategy: epoch
    save_strategy: epoch
    save_total_limit: 3  # 最多保存3个检查点
    load_best_model_at_end: true
    metric_for_best_model: exact_match
    greater_is_better: true

    # 多语言评估策略
    locale_eval_strategy: all only  # 'each' 或 'all only'

    # 随机种子
    seed: 42
    data_seed: 42

    # 分布式训练
    local_rank: -1  # 自动设置
    ddp_find_unused_parameters: false

    # 性能优化
    fp16: false  # 混合精度训练
    dataloader_num_workers: 4
    dataloader_pin_memory: true

  # ---------- 评估配置 ----------
  eval_metrics: all  # 'all' 或 ['intent_acc', 'slot_micro_f1', 'exact_match']
  slot_labels_ignore: ['Other']  # 评估时忽略的标签

# ==================== 测试配置 ====================
test:
  dataset_loc: /path/to/massive_1.0_hf_format/massive_1.0
  model_loc: /path/to/trained/model/checkpoint-best
  predictions_file: /path/to/predictions.jsonl  # 可选

  trainer: massive

  trainer_args:
    per_device_eval_batch_size: 32
    locale_eval_strategy: all only

  eval_metrics: all
  slot_labels_ignore: ['Other']
```

### 关键参数说明

#### 1. 学习率（learning_rate）

- **推荐值**：1e-5 到 5e-5
- **说明**：预训练模型通常使用较小的学习率
- **调整建议**：
  - 如果loss不下降：增大学习率
  - 如果loss震荡：减小学习率

#### 2. 批次大小（batch_size）

- **推荐值**：16-64（取决于GPU内存）
- **说明**：有效批次大小 = batch_size × gradient_accumulation_steps × num_gpus
- **调整建议**：
  - GPU内存不足：减小batch_size，增大gradient_accumulation_steps
  - 例如：batch_size=16, grad_accum=2 等效于 batch_size=32

#### 3. 槽位损失系数（slot_loss_coef）

- **推荐值**：0.5-2.0
- **说明**：平衡意图和槽位两个任务的重要性
- **调整建议**：
  - 如果槽位F1低：增大系数（如1.5或2.0）
  - 如果意图准确率低：减小系数（如0.5或0.8）

#### 4. 预热比例（warmup_ratio）

- **推荐值**：0.06-0.1
- **说明**：训练开始时学习率逐渐增大的步数比例
- **调整建议**：
  - 数据集大：使用较小的warmup_ratio（0.06）
  - 数据集小：使用较大的warmup_ratio（0.1）

---

## 使用指南

### 快速开始

#### 步骤 1: 准备环境

```bash
# 创建conda环境
conda env create -f conda_env.yml
conda activate massive

# 或手动安装依赖
pip install torch transformers datasets ruamel.yaml
```

#### 步骤 2: 下载数据

```bash
# 下载 MASSIVE 1.1
curl https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz \
    --output amazon-massive-dataset-1.1.tar.gz

# 解压
tar -xzvf amazon-massive-dataset-1.1.tar.gz
```

#### 步骤 3: 转换数据格式

```bash
# 转换为 HuggingFace Dataset 格式
python scripts/create_hf_dataset.py \
    -d 1.1/data \
    -o massive_1.1_hf_format/massive_1.1
```

输出文件：
- `massive_1.1_hf_format/massive_1.1.train/` - 训练集
- `massive_1.1_hf_format/massive_1.1.dev/` - 验证集
- `massive_1.1_hf_format/massive_1.1.test/` - 测试集
- `massive_1.1_hf_format/massive_1.1.intents` - 意图映射
- `massive_1.1_hf_format/massive_1.1.slots` - 槽位映射

#### 步骤 4: 配置训练

创建配置文件 `my_config.yml`：

```yaml
train_val:
  dataset_loc: massive_1.1_hf_format/massive_1.1
  langs: ['zh-CN']  # 只训练中文
  model_name: xlmr_ic_sf
  pretrained_model: xlm-roberta-base

  trainer_args:
    output_dir: ./output/zh_xlmr_base
    num_train_epochs: 20
    per_device_train_batch_size: 32
    learning_rate: 5e-5
    evaluation_strategy: epoch
    save_strategy: epoch
    load_best_model_at_end: true
    metric_for_best_model: exact_match
```

#### 步骤 5: 开始训练

```bash
# 设置 PYTHONPATH
export PYTHONPATH=${PYTHONPATH}:$(pwd)/src

# 开始训练
python scripts/train.py -c my_config.yml
```

#### 步骤 6: 评估模型

创建测试配置 `my_test_config.yml`：

```yaml
test:
  dataset_loc: massive_1.1_hf_format/massive_1.1
  model_loc: ./output/zh_xlmr_base/checkpoint-best
  predictions_file: ./predictions.jsonl

  trainer_args:
    per_device_eval_batch_size: 32
    locale_eval_strategy: all only
```

运行测试：

```bash
python scripts/test.py -c my_test_config.yml
```

### 多语言训练

训练支持多种语言：

```yaml
train_val:
  langs: ['zh-CN', 'en-US', 'ja-JP']  # 同时训练中英日
```

### 跨语言迁移学习

在英语上训练，在中文上测试：

```yaml
# 训练配置
train_val:
  langs: ['en-US']
  # ... 其他配置

# 测试配置
test:
  langs: ['zh-CN']  # 在中文上测试
```

---

## 常见问题

### 1. GPU 内存不足

**问题**：训练时出现 CUDA out of memory 错误

**解决方案**：
```yaml
trainer_args:
  per_device_train_batch_size: 16  # 减小批次大小
  gradient_accumulation_steps: 2   # 增加梯度累积
  fp16: true  # 使用混合精度训练
```

### 2. 训练速度慢

**问题**：训练速度太慢

**解决方案**：
```yaml
trainer_args:
  dataloader_num_workers: 8  # 增加数据加载worker数
  fp16: true  # 使用混合精度（A100/V100 GPU）
  per_device_train_batch_size: 64  # 增大批次大小
```

或使用多 GPU：
```bash
torchrun --nproc_per_node=8 scripts/train.py -c config.yml
```

### 3. 槽位 F1 分数低

**问题**：意图准确率高，但槽位 F1 很低

**解决方案**：
```yaml
model_config:
  slot_loss_coef: 2.0  # 增加槽位损失权重

trainer_args:
  learning_rate: 3e-5  # 适当降低学习率
  num_train_epochs: 30  # 增加训练轮数
```

### 4. 过拟合

**问题**：训练集指标很高，验证集指标低

**解决方案**：
```yaml
model_config:
  head_dropout_rate: 0.3  # 增大 dropout

trainer_args:
  weight_decay: 0.01  # 增加权重衰减
  warmup_ratio: 0.1
```

或使用数据增强、添加更多训练数据。

### 5. 中文分词问题

**问题**：中文 token 数量超过最大长度

**解决方案**：
```yaml
collator:
  max_length: 256  # 增加最大长度（中文字符级分词需要更长）
```

### 6. 加载检查点失败

**问题**：`Error loading checkpoint`

**解决方案**：
1. 确认检查点路径正确
2. 确认模型配置与训练时一致
3. 使用完整路径而不是相对路径

### 7. 评估指标不一致

**问题**：验证集指标与 eval.ai 排行榜不一致

**解决方案**：

验证引擎的指标仅供参考，官方指标以 eval.ai 为准。确保：
```yaml
test:
  predictions_file: predictions.jsonl  # 必须设置
  trainer_args:
    locale_eval_strategy: all only  # 必须设置
```

然后将 `predictions.jsonl` 提交到 eval.ai。

---

## 高级话题

### 超参数优化

使用 Ray Tune 进行超参数搜索：

```yaml
# hpo_config.yml
hpo:
  backend: ray
  n_trials: 20
  direction: maximize

  hp_space:
    learning_rate: [1e-5, 5e-5]  # 搜索范围
    per_device_train_batch_size: [16, 32, 64]
    slot_loss_coef: [0.5, 1.0, 2.0]
```

运行超参数优化：
```bash
python scripts/run_hpo.py -c hpo_config.yml
```

### 模型融合

训练多个模型并融合预测：

```python
# 加载多个模型
model1 = load_model('checkpoint1')
model2 = load_model('checkpoint2')
model3 = load_model('checkpoint3')

# 融合预测（投票或平均）
intent_pred = voting([model1.intent, model2.intent, model3.intent])
slot_pred = averaging([model1.slots, model2.slots, model3.slots])
```

### 自定义模型

添加自己的模型：

```python
# src/massive/models/my_model.py
class MyCustomModel(PreTrainedModel):
    def __init__(self, config, intent_dict, slot_dict):
        super().__init__(config)
        # 自定义初始化

    def forward(self, input_ids, attention_mask, intent_num, slots_num):
        # 自定义前向传播
        return (loss, (intent_logits, slot_logits))
```

在配置中使用：
```yaml
train_val:
  model_name: my_model  # 自定义模型名
```

---

## 参考资料

### 论文引用

```bibtex
@misc{fitzgerald2022massive,
    title={MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages},
    author={Jack FitzGerald and Christopher Hench and Charith Peris and Scott Mackie and Kay Rottmann and Ana Sanchez and Aaron Nash and Liam Urbach and Vishesh Kakarala and Richa Singh and Swetha Ranganath and Laurie Crist and Misha Britan and Wouter Leeuwis and Gokhan Tur and Prem Natarajan},
    year={2022},
    eprint={2204.08582},
    archivePrefix={arXiv},
    primaryClass={cs.CL}
}
```

### 相关链接

- **MASSIVE 论文**：https://arxiv.org/abs/2204.08582
- **官方仓库**：https://github.com/alexa/massive
- **排行榜**：https://eval.ai/web/challenges/challenge-page/1697/overview
- **MMNLU-22 Workshop**：https://mmnlu-22.github.io/
- **SLURP 数据集**：https://github.com/pswietojanski/slurp

### 预训练模型

- **XLM-RoBERTa**：https://huggingface.co/xlm-roberta-base
- **mT5**：https://huggingface.co/google/mt5-base

---

## 更新日志

- **2025-12-17**：创建中文技术文档，添加代码中文注释
- **2022-11-28**：MASSIVE 1.1 发布，新增加泰罗尼亚语数据
- **2022-04-20**：MASSIVE 1.0 发布，包含51种语言

---

## 许可证

本项目使用 Apache License 2.0。详见 LICENSE.txt。

部分代码改编自 JointBERT，详见 NOTICE.md。

---

**文档维护**: 如有问题或建议，请提交 Issue 到官方仓库。
