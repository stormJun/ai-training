# 快速参考指南 🚀

## 已生成的文件

```
chinese_data/
│
├── 📄 脚本文件
│   ├── process_massive.py     # 数据处理脚本
│   ├── inference.py           # 推理脚本
│   ├── evaluate.py            # 评估脚本
│
├── 📖 文档文件
│   ├── README.md              # 数据集说明
│   ├── DATA_PROCESSING.md     # 详细的数据加工方案
│   ├── USAGE.md               # 完整使用指南
│   └── QUICK_START.md         # 本文档
│
├── 📦 处理后的数据（已生成）
│   ├── processed_instruction/  # 标准指令格式（推荐）
│   │   ├── train.jsonl        (9,075条)
│   │   ├── validation.jsonl   (1,598条)
│   │   ├── test.jsonl         (2,364条)
│   │   └── statistics.json
│   │
│   └── processed_chat/         # 对话格式
│       ├── train.jsonl        (9,075条)
│       ├── validation.jsonl   (1,598条)
│       ├── test.jsonl         (2,364条)
│       └── statistics.json
│
└── 📁 原始数据
    └── zh-CN.jsonl            # 原始 MASSIVE 数据
```

---

## 一分钟上手 ⚡

### 1. 数据已经处理完成！

两种格式的数据已经生成在：
- `processed_instruction/` - 标准指令格式（推荐用于 LoRA 微调）
- `processed_chat/` - 对话格式（可选）

### 2. 查看数据样本

```bash
# 标准指令格式
head -1 processed_instruction/train.jsonl | python3 -m json.tool

# 对话格式
head -1 processed_chat/train.jsonl | python3 -m json.tool
```

### 3. 开始训练

使用你自己的训练脚本，或参考 `DATA_PROCESSING.md` 中的 LoRA 微调建议：

```python
# 推荐配置
模型: Qwen2.5-1.5B-Instruct
训练数据: processed_instruction/train.jsonl
验证数据: processed_instruction/validation.jsonl
Epochs: 3
Batch Size: 8
Learning Rate: 2e-4
LoRA Rank: 16
```

### 4. 推理测试

```bash
python3 inference.py \
  --base-model Qwen/Qwen2.5-1.5B-Instruct \
  --lora-path ./outputs/checkpoint-best \
  --test-file processed_instruction/test.jsonl \
  --output predictions.jsonl
```

### 5. 评估结果

```bash
python3 evaluate.py --pred predictions.jsonl
```

---

## 常用命令 📝

### 重新处理数据

```bash
# 标准指令格式
python3 process_massive.py --format instruction --output processed_instruction

# 对话格式
python3 process_massive.py --format chat --output processed_chat

# 不过滤低质量数据
python3 process_massive.py --no-filter
```

### 查看统计信息

```bash
python3 -m json.tool processed_instruction/statistics.json
```

### 查看帮助

```bash
python3 process_massive.py --help
python3 inference.py --help
python3 evaluate.py --help
```

---

## 数据格式示例 📊

### 标准指令格式
```json
{
  "instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。",
  "input": "星期五早上九点叫醒我",
  "output": "{\"intent\": \"alarm_set\", \"slots\": [{\"type\": \"date\", \"value\": \"星期五\"}, {\"type\": \"time\", \"value\": \"九点\"}]}"
}
```

### 对话格式
```json
{
  "messages": [
    {"role": "system", "content": "你是一个专业的意图识别和槽位抽取助手..."},
    {"role": "user", "content": "星期五早上九点叫醒我"},
    {"role": "assistant", "content": "{\"intent\": \"alarm_set\", \"slots\": [...]}"}
  ]
}
```

---

## 数据统计 📈

- **总样本**: 16,521 条
- **过滤后**: 13,037 条（保留 78.91%）
- **训练集**: 9,075 条
- **验证集**: 1,598 条
- **测试集**: 2,364 条

**标注覆盖**:
- 意图类别: 60 种
- 场景类别: 18 种
- 槽位类型: 55 种
- 有槽位样本: 67.83%
- 无槽位样本: 32.17%

---

## 推荐工作流 🔄

```
1️⃣ 数据已处理 ✅
   ↓
2️⃣ LoRA 微调
   使用: processed_instruction/train.jsonl
   验证: processed_instruction/validation.jsonl
   ↓
3️⃣ 模型推理
   测试: processed_instruction/test.jsonl
   输出: predictions.jsonl
   ↓
4️⃣ 评估结果
   分析: predictions.jsonl
   错误: predictions_errors.jsonl
   ↓
5️⃣ 调优迭代
```

---

## 关键指标 🎯

评估时会输出以下指标：

- **意图识别**:
  - Accuracy (准确率)
  - F1 (Macro)
  - F1 (Weighted)

- **槽位填充**:
  - Exact Match (完全匹配率)
  - Precision (精确率)
  - Recall (召回率)
  - F1

- **联合任务**:
  - Joint Accuracy (联合准确率)

---

## 需要帮助？ 💬

1. **详细文档**: 查看 `USAGE.md`
2. **数据方案**: 查看 `DATA_PROCESSING.md`
3. **脚本帮助**: 运行 `python3 xxx.py --help`

---

**最后更新**: 2025-12-17
**数据版本**: MASSIVE 1.1
**处理状态**: ✅ 已完成
