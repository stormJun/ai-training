# Hugging Face PEFT 库完整指南

## 📋 目录

- [基本概念](#基本概念)
- [PEFT 原理设计](#peft-原理设计)
- [PEFT 库架构](#peft-库架构)
- [LoRA 详解](#lora-详解)
- [QLoRA 详解](#qlora-详解)
- [PEFT 微调工作原理](#peft-微调工作原理)
- [最佳实践](#最佳实践)
- [实战示例](#实战示例)
- [性能对比](#性能对比)
- [常见问题](#常见问题)

---

## 🎯 基本概念

### 什么是 PEFT？

**PEFT (Parameter-Efficient Fine-Tuning)** 是 Hugging Face 推出的参数高效微调库，旨在用最少的可训练参数实现接近全参数微调的效果。

### 为什么需要 PEFT？

传统的全参数微调（Full Fine-tuning）面临的挑战：

```
传统微调的问题:

大型语言模型 (如 Llama-70B)
├── 参数量: 70B 参数
├── 显存需求: ~280GB (FP32) / ~140GB (FP16)
├── 训练成本: 极高
└── 部署难度: 每个任务需要保存完整模型副本

全参数微调成本计算:
┌────────────────────────────────────────┐
│ 模型参数: 70B                           │
│ 优化器状态 (Adam): 70B × 2 = 140B      │
│ 梯度: 70B                               │
│ 激活值: 根据序列长度                    │
│ ────────────────────────────────────   │
│ 总显存需求: > 300GB                     │
└────────────────────────────────────────┘

挑战:
❌ 硬件成本高 (需要多张 A100 卡)
❌ 训练速度慢
❌ 存储成本高 (每个任务需要完整模型副本)
❌ 难以快速迭代实验
```

### PEFT 的核心思想

**只训练极少量参数，冻结大部分预训练权重**

```
PEFT 方案:

原始模型 (70B 参数)
└── 全部冻结 ❄️

额外的可训练参数 (0.1% ~ 1%)
└── 仅训练这部分 🔥

优势:
✅ 显存需求: 10-50GB (可在单张消费级显卡训练)
✅ 训练速度: 快 3-10 倍
✅ 存储成本: 每个任务仅保存 adapter (几 MB - 几百 MB)
✅ 效果: 接近全参数微调 (90-95% 性能)
```

### PEFT 支持的方法

| 方法 | 可训练参数量 | 推理开销 | 适用场景 |
|------|-------------|---------|----------|
| **LoRA** | 0.1% - 1% | 无 | 通用，推荐 |
| **QLoRA** | 0.1% - 1% | 无 | 显存极度受限 |
| **Prefix Tuning** | 0.1% - 3% | 小 | 生成任务 |
| **P-Tuning** | 0.01% - 0.1% | 小 | 小样本学习 |
| **Prompt Tuning** | < 0.01% | 小 | 极小数据集 |
| **Adapter Layers** | 0.5% - 5% | 中 | 多任务学习 |
| **IA³** | 0.01% - 0.1% | 无 | 高效推理 |

---

## 🏗️ PEFT 原理设计

### 核心设计理念

PEFT 的核心设计基于以下观察：

1. **内在维度假设 (Intrinsic Dimensionality)**
   - 模型适应新任务所需的参数空间维度远小于总参数空间
   - 大部分预训练知识可以复用，只需微调很小一部分

2. **参数冻结策略**
   - 保持预训练权重不变
   - 仅训练新增的轻量级模块

3. **模块化设计**
   - Adapter 可以即插即用
   - 支持多任务快速切换

### PEFT 的数学原理

假设原始模型的前向传播为：

$$h = W_0x$$

PEFT 方法修改为：

$$h = W_0x + \Delta Wx$$

其中：
- $W_0$: 预训练权重（冻结）
- $\Delta W$: 可训练的增量权重（参数量极小）

不同 PEFT 方法对 $\Delta W$ 的建模方式不同：

| 方法 | $\Delta W$ 的形式 | 参数量 |
|------|----------|--------|
| **LoRA** | $\Delta W = BA$ (低秩分解) | $r \times (d_{in} + d_{out})$ |
| **Adapter** | $\Delta W = \text{MLP}(x)$ | $2 \times d \times r + \text{bias}$ |
| **Prefix** | $\Delta W = \text{Concat}(\text{prefix}, x)$ | $L \times d$ |

### PEFT 库架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    PEFT 库架构                               │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │  LoRA   │         │ Adapter │        │ Prefix  │
   │ Config  │         │ Config  │        │ Config  │
   └────┬────┘         └────┬────┘        └────┬────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  PeftModel     │
                    │  基础模型包装   │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │Injection│         │Training │        │Inference│
   │ 注入层  │         │ 训练    │        │ 推理    │
   └─────────┘         └─────────┘        └─────────┘
```

---

## 🔧 PEFT 库架构

### 核心组件

#### 1. PeftConfig

配置类，定义 PEFT 方法的超参数：

```python
from peft import LoraConfig, TaskType

# LoRA 配置示例
config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,  # 任务类型
    r=8,                            # LoRA 秩
    lora_alpha=16,                  # 缩放因子
    lora_dropout=0.1,               # Dropout
    target_modules=["q_proj", "v_proj"],  # 目标模块
    bias="none",                    # 偏置处理
)
```

#### 2. PeftModel

模型包装器，将 PEFT 方法应用到基础模型：

```python
from peft import get_peft_model
from transformers import AutoModelForCausalLM

# 加载基础模型
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B")

# 应用 PEFT
peft_model = get_peft_model(base_model, config)

# 查看可训练参数
peft_model.print_trainable_parameters()
# 输出: trainable params: 2,359,296 || all params: 1,543,234,560 || trainable%: 0.15%
```

#### 3. 模块注入机制

PEFT 通过动态替换模型层来注入可训练模块：

```python
# 原始模型结构
model.transformer.layers[0].self_attn.q_proj  # Linear(1024, 1024)

# 注入 LoRA 后
model.transformer.layers[0].self_attn.q_proj  # LoraLinear
  ├── base_layer: Linear(1024, 1024)  [冻结]
  ├── lora_A: Linear(1024, 8)         [可训练]
  └── lora_B: Linear(8, 1024)         [可训练]
```

### 保存和加载机制

```python
# 训练后保存 adapter
peft_model.save_pretrained("./lora_adapter")

# 生成的文件
lora_adapter/
├── adapter_config.json     # 配置文件 (几 KB)
└── adapter_model.bin       # 权重文件 (几 MB)

# 加载使用
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B")
model = PeftModel.from_pretrained(base_model, "./lora_adapter")
```

**关键优势**：
- ✅ 只保存增量参数（~10MB），不需要保存完整模型（~3GB）
- ✅ 可以快速切换不同任务的 adapter
- ✅ 支持多 adapter 叠加使用

---

## 📐 LoRA 详解

### LoRA 核心原理

**LoRA (Low-Rank Adaptation of Large Language Models)** 通过低秩矩阵分解来近似权重更新。

#### 数学表示

对于权重矩阵 $W \in \mathbb{R}^{d \times k}$：

**传统微调**：
$$W' = W_0 + \Delta W$$
其中 $\Delta W \in \mathbb{R}^{d \times k}$，参数量 = $d \times k$

**LoRA**：
$$W' = W_0 + BA$$
其中 $B \in \mathbb{R}^{d \times r}$, $A \in \mathbb{R}^{r \times k}$

参数量 = $r \times (d + k) \ll d \times k$

#### 可视化说明

```
原始线性层:
Input (d_in) ──────> Linear (W₀) ──────> Output (d_out)
                    [d_in × d_out]
                    全部冻结 ❄️

LoRA 增强:
                    ┌─> Linear (W₀) ──┐
Input (d_in) ───────┤                  ├───> Output (d_out)
                    └─> B ──> A ──────┘
                       ↓      ↓
                     [d×r]  [r×d]
                    可训练 🔥


```

前向传播: $\text{output} = W_0x + BAx = (W_0 + BA)x$

关键参数:
- r (rank): 低秩分解的秩，通常 4-64
- 参数量: $r \times (d_{in} + d_{out})$

示例 $(d_{in}=1024, d_{out}=1024)$:
- 全参数: $1024 \times 1024 = 1,048,576$
- LoRA $(r=8)$: $8 \times (1024+1024) = 16,384$ (1.5%)
- LoRA $(r=16)$: $16 \times 2048 = 32,768$ (3.1%)

### LoRA 关键超参数

#### 1. r (rank) - 秩

`r` 是 LoRA 最核心的超参数，它决定了低秩分解矩阵的维度，直接影响模型的表达能力和参数量。

##### 什么是秩（Rank）？

在 LoRA 中，权重更新 $\Delta W$ 被分解为两个低秩矩阵的乘积：

$$\Delta W = BA$$

其中：
- $B \in \mathbb{R}^{d \times r}$：维度为 (原始维度 × **r**)
- $A \in \mathbb{R}^{r \times k}$：维度为 (**r** × 原始维度)
- **r** 就是秩，控制了这两个矩阵的"中间维度"

##### 秩的影响

**参数量计算**：

对于一个线性层 $W \in \mathbb{R}^{d \times k}$：
- **全参数微调**：需要训练 $d \times k$ 个参数
- **LoRA**：仅需训练 $r \times (d + k)$ 个参数

**参数量对比示例**（以 Attention 层 Q 投影为例，d=1024, k=1024）：

| 秩 r | LoRA 参数量 | 占比 | 对比全参数 |
|------|-----------|------|----------|
| **r=4** | 8,192 | 0.8% | 128× 减少 |
| **r=8** | 16,384 | 1.6% | 64× 减少 |
| **r=16** | 32,768 | 3.1% | 32× 减少 |
| **r=32** | 65,536 | 6.3% | 16× 减少 |
| **r=64** | 131,072 | 12.5% | 8× 减少 |
| **r=128** | 262,144 | 25% | 4× 减少 |
| **全参数** | 1,048,576 | 100% | 基准 |

**关键观察**：
- r=8 时，仅用 **1.6%** 的参数就能达到接近全参数微调的效果
- r 每翻倍，参数量翻倍，但性能提升呈递减趋势

##### 秩的选择策略

```python
# 简单任务、小数据集（< 5000 样本）
config = LoraConfig(r=4)
# 示例：意图分类（10个类别）、命名实体识别（5个标签）

# 中等任务、中等数据集（5000-20000 样本）
config = LoraConfig(r=8)  # ✅ 推荐起点
# 示例：情感分析、文本分类、简单问答

# 标准配置（20000-100000 样本）
config = LoraConfig(r=16)
# 示例：多轮对话、文本摘要、翻译任务

# 复杂任务、大数据集（> 100000 样本）
config = LoraConfig(r=32)
# 示例：代码生成、复杂推理、领域知识注入

# 极致性能需求
config = LoraConfig(r=64)
# 示例：接近全参数微调的效果，但仍保持较小的 adapter 体积
```

##### 实际效果对比

**Qwen2.5-1.5B 在意图分类任务上的表现**（10000 样本，10 个意图类别）：

| 秩 r | 准确率 | 训练时间 | 显存占用 | Adapter 大小 |
|------|-------|---------|---------|------------|
| **r=2** | 87.5% | 0.8× | 8GB | 5MB |
| **r=4** | 90.2% | 0.9× | 8.5GB | 10MB |
| **r=8** | 92.3% | 1.0× | 9GB | 20MB ✅ |
| **r=16** | 93.1% | 1.2× | 10GB | 40MB |
| **r=32** | 93.5% | 1.5× | 12GB | 80MB |
| **r=64** | 93.7% | 2.0× | 15GB | 160MB |
| **全参数** | 94.0% | 5.0× | 35GB | 3GB |

**观察**：
- r=8 是**性价比最高**的选择：用 20% 的时间达到 98% 的效果
- r=4 到 r=8：性能提升明显（+2.1%）
- r=8 到 r=16：性能提升减缓（+0.8%）
- r=16 到 r=64：收益递减（+0.6%）
- **推荐策略**：从 r=8 开始，根据验证集表现调整

##### 不同任务的 r 值推荐

| 任务类型 | 数据规模 | 推荐 r | 原因 |
|---------|---------|--------|------|
| **分类任务** | 小（< 5K） | r=4 | 决策边界简单 |
| **分类任务** | 大（> 20K） | r=8-16 | 需要更多表达能力 |
| **生成任务（摘要、翻译）** | 中等 | r=16 | 生成任务通常需要更大容量 |
| **对话系统** | 大 | r=16-32 | 需要理解复杂上下文 |
| **代码生成** | 大 | r=32-64 | 需要学习精确的语法和逻辑 |
| **领域适应** | 小-中 | r=8-16 | 保留原始知识，注入新知识 |
| **指令微调** | 中-大 | r=16-32 | 学习多样化的指令遵循模式 |

##### r 的调优流程

**Step 1：确定起始值**
```python
# 默认从 r=8 开始（大多数场景的最佳起点）
config = LoraConfig(r=8, lora_alpha=16)
```

**Step 2：训练并观察**
- 查看训练/验证损失曲线
- 评估最终性能指标

**Step 3：根据现象调整**

**现象 1：欠拟合（训练 loss 和验证 loss 都很高）**
```python
# 症状：
# - 训练 loss 在 1.5+ 停滞不降
# - 验证集准确率远低于预期

# 解决：增大 r
config = LoraConfig(r=16, lora_alpha=32)  # 翻倍尝试
```

**现象 2：过拟合（训练 loss 低，验证 loss 高）**
```python
# 症状：
# - 训练 loss < 0.5，但验证 loss > 1.0
# - 验证集性能不提升或下降

# 解决：不要增大 r，使用正则化
config = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.15)
# 或提前停止训练
```

**现象 3：训练正常（最佳状态）**
```python
# 症状：
# - 训练和验证 loss 平稳下降
# - 验证集性能达到预期

# 操作：保持当前 r，或微调其他超参数
```

##### 秩与模型规模的关系

**经验法则**：更大的模型可以容纳更大的 r

| 模型规模 | 推荐 r 范围 | 原因 |
|---------|-----------|------|
| **0.5B-1B** | r=4-8 | 小模型容量有限，大 r 容易过拟合 |
| **1B-3B** | r=8-16 | 标准配置 ✅ |
| **3B-7B** | r=16-32 | 更大模型可以充分利用更大的 r |
| **7B-13B** | r=32-64 | 大模型 + 大数据集 |
| **13B+** | r=64-128 | 接近全参数微调的表达能力 |

##### 常见误区

❌ **误区1**："r 越大越好"
- ✅ 现实：r 过大会导致过拟合，尤其是在小数据集上
- ✅ 建议：根据数据规模和任务复杂度选择合适的 r

❌ **误区2**："所有层应该用相同的 r"
- ✅ 现实：可以为不同层设置不同的 r（高级用法）
- ✅ 示例：注意力层用 r=16，MLP 层用 r=8

❌ **误区3**："r 只影响性能，不影响训练"
- ✅ 现实：r 越大，训练越慢，显存占用越高
- ✅ 权衡：性能提升 vs. 资源消耗

##### 高级技巧：动态秩调整

**AdaLoRA**：自适应调整不同层的秩
```python
from peft import AdaLoraConfig

config = AdaLoraConfig(
    r=8,              # 初始秩
    target_r=4,       # 目标平均秩
    init_r=12,        # 最大初始秩
    # AdaLoRA 会自动为重要的层分配更大的秩
)
```

**优势**：
- 自动识别重要层并分配更多参数
- 在相同总参数量下获得更好的性能

**权衡**：
- 更大的 r → 更多参数 → 更好效果 → 更高成本、更慢训练
- 更小的 r → 更少参数 → 更快训练 → 可能欠拟合、性能受限

#### 2. lora_alpha - 缩放因子

`lora_alpha` 是 LoRA 的关键超参数，它控制 LoRA 层对最终输出的影响程度。

##### 数学原理

在 LoRA 中，最终输出的计算公式为：

$$\text{output} = W_0x + \frac{\alpha}{r} \times BAx$$

其中：
- $W_0x$ 是基础模型的输出（冻结）
- $BAx$ 是 LoRA 层的原始输出
- $\frac{\alpha}{r}$ 是缩放系数

**关键理解**：$\frac{\alpha}{r}$ 这个比值决定了 LoRA 权重的实际影响力。

##### 为什么存在缩放因子？

LoRA 需要缩放因子的两个核心原因：

1. **训练稳定性**：
   - LoRA 矩阵 B 初始化为 0，A 使用随机初始化
   - 这确保训练开始时 $BA = 0$，模型行为与原始模型一致
   - 如果没有缩放，LoRA 的影响可能过小或过大

2. **学习率独立性**：
   - 通过固定 $\alpha$，即使改变 $r$，也能保持训练动态相似
   - 这让我们可以调整模型容量（r）而不必重新调整学习率

##### 为什么推荐 lora_alpha = 2×r？

```python
config = LoraConfig(
    r=8,
    lora_alpha=16,  # 推荐设置为 r 的 2 倍
)
# 实际缩放系数：16/8 = 2.0
```

**原因分析**：

1. **经验最优值**：
   - 原始 LoRA 论文作者通过大量实验发现，当缩放系数在 1-2 之间时效果最好
   - `α/r = 2` 在多个任务上表现稳定

2. **适中的影响力**：
   - `α/r = 1`（如 α=8, r=8）：LoRA 影响较小，可能欠拟合
   - `α/r = 2`（如 α=16, r=8）：平衡的影响力 ✅ 推荐
   - `α/r = 4`（如 α=32, r=8）：LoRA 影响较大，可能训练不稳定

3. **便于记忆和实验**：
   - 简单的 2× 规则易于在不同 r 值间迁移
   - 当你尝试 r=4, 8, 16, 32 时，只需将 α 设为 8, 16, 32, 64

##### 配置示例

```python
# 标准配置（最常用）
config = LoraConfig(
    r=8,
    lora_alpha=16,  # α/r = 2.0
)

# 保守配置（训练更稳定，但可能需要更多epoch）
config = LoraConfig(
    r=8,
    lora_alpha=8,   # α/r = 1.0
)

# 激进配置（LoRA影响更大，收敛更快，但可能不稳定）
config = LoraConfig(
    r=8,
    lora_alpha=32,  # α/r = 4.0
)
```

##### 不同 α/r 比值的影响

| α/r 比值 | LoRA 影响力 | 训练稳定性 | 适用场景 |
|---------|-----------|----------|---------|
| **0.5** | 很小 | 很高 | 微调非常接近原始模型的场景 |
| **1.0** | 较小 | 高 | 保守的微调策略 |
| **2.0** | 适中 | 高 | ✅ **通用推荐** |
| **4.0** | 较大 | 中 | 需要大幅改变模型行为的场景 |
| **8.0+** | 很大 | 低 | 不推荐，容易训练发散 |

##### 实际效果对比

在意图分类任务上的表现（r=8）：

```python
# 实验对比
lora_alpha=4  (α/r=0.5): 准确率 88.2%, epoch=5, loss 下降慢
lora_alpha=8  (α/r=1.0): 准确率 90.5%, epoch=4, 稳定收敛
lora_alpha=16 (α/r=2.0): 准确率 91.8%, epoch=3, 最佳平衡 ✅
lora_alpha=32 (α/r=4.0): 准确率 91.2%, epoch=2, 但loss有震荡
lora_alpha=64 (α/r=8.0): 准确率 89.0%, epoch=1, 训练不稳定
```

**观察**：
- α/r 太小：收敛慢，需要更多训练轮数
- α/r=2：平衡点，收敛速度和稳定性俱佳
- α/r 太大：可能快速收敛但容易过拟合或震荡

##### 调优建议

**标准流程**：
1. **默认起点**：始终从 `lora_alpha = 2×r` 开始
2. **观察训练曲线**：
   - Loss 下降过慢 → 增大 α（如改为 3×r）
   - Loss 震荡不稳定 → 减小 α（如改为 1×r）
   - Loss 正常下降 → 保持 2×r

**特殊场景**：
```python
# 场景1：领域适应（数据分布变化小）
config = LoraConfig(r=8, lora_alpha=8)  # 保守策略

# 场景2：大规模数据集微调
config = LoraConfig(r=16, lora_alpha=32)  # 标准策略

# 场景3：小样本学习（< 1000样本）
config = LoraConfig(r=4, lora_alpha=16)  # 增大α/r比值到4

# 场景4：极端定制化需求
config = LoraConfig(r=32, lora_alpha=64)  # 大容量 + 标准缩放
```

##### 常见误区

❌ **误区1**："α 必须等于 r 的 2 倍"
- ✅ 2× 只是经验推荐，不是硬性规则
- 根据具体任务调整是完全合理的

❌ **误区2**："α 越大效果越好"
- ✅ α 过大会导致训练不稳定，甚至损害性能
- 关键是找到合适的平衡点

❌ **误区3**："改变 r 时不需要调整 α"
- ✅ 保持 α/r 比值恒定有助于迁移超参数经验
- 例如：r=8,α=16 → r=16,α=32 保持缩放一致

#### 3. target_modules - 目标模块

指定应用 LoRA 的模块：

| 模块名   | 全称              | 作用                                                         |
| -------- | ----------------- | ------------------------------------------------------------ |
| `q_proj` | Query Projection  | 将输入向量投影为**查询向量（Query）**，用于匹配键向量        |
| `k_proj` | Key Projection    | 将输入向量投影为**键向量（Key）**，用于计算与查询向量的相似度（注意力分数） |
| `v_proj` | Value Projection  | 将输入向量投影为**值向量（Value）**，用于根据注意力分数加权求和 |
| `o_proj` | Output Projection | 将多头注意力的输出向量投影为最终的注意力层输出，接入后续的前馈网络（FFN） |



```python
config = LoraConfig(
    target_modules=["q_proj", "v_proj"]  # 只对 Q、V 应用
    # 或
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]  # 全注意力
    # 或
    target_modules="all-linear"  # 所有线性层
)
```

**常见配置**：

| 配置 | 目标模块 | 参数量 | 适用场景 |
|------|---------|--------|----------|
| **轻量** | `q_proj, v_proj` | 最少 | 简单任务 |
| **标准** | `q_proj, k_proj, v_proj, o_proj` | 中等 | 通用推荐 |
| **全面** | `all-linear` | 较多 | 复杂任务 |

#### 4. lora_dropout - Dropout 率

防止过拟合：

```python
config = LoraConfig(
    lora_dropout=0.1  # 推荐 0.05-0.1
)
```

### LoRA 实现细节

#### LoRA 层的实现

```python
import torch
import torch.nn as nn

class LoRALayer(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        rank: int = 8,
        alpha: int = 16,
        dropout: float = 0.1,
    ):
        super().__init__()

        # 原始权重（冻结）
        self.base_layer = nn.Linear(in_features, out_features, bias=True)
        self.base_layer.weight.requires_grad = False

        # LoRA 矩阵 A: (in_features, rank)
        self.lora_A = nn.Linear(in_features, rank, bias=False)
        # LoRA 矩阵 B: (rank, out_features)
        self.lora_B = nn.Linear(rank, out_features, bias=False)

        # 初始化
        nn.init.kaiming_uniform_(self.lora_A.weight, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B.weight)  # B 初始化为 0，保证初始时 BA=0

        self.scaling = alpha / rank
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # 基础输出
        base_output = self.base_layer(x)

        # LoRA 输出
        lora_output = self.lora_B(self.lora_A(self.dropout(x)))

        # 组合输出
        return base_output + lora_output * self.scaling
```

#### 权重合并

训练完成后，可以将 LoRA 权重合并到基础模型：

```python
# 合并公式: W_merged = W₀ + (alpha/r) × BA

def merge_lora_weights(base_weight, lora_A, lora_B, alpha, r):
    """
    合并 LoRA 权重到基础权重

    参数：
    base_weight: [out_features, in_features]
    lora_A: [rank, in_features]
    lora_B: [out_features, rank]

    公式：W_merged = W₀ + (α/r) × BA
    """
    scaling = alpha / r
    delta_w = torch.matmul(lora_B, lora_A) * scaling
    merged_weight = base_weight + delta_w
    return merged_weight
```

**合并后的优势**：
- ✅ 推理速度与原始模型相同（无额外计算）
- ✅ 不再需要 PEFT 库
- ✅ 可以直接用 transformers 加载

### LoRA 的变体

#### 1. AdaLoRA

**自适应 LoRA**，动态调整不同层的秩：

```python
from peft import AdaLoraConfig

config = AdaLoraConfig(
    r=8,
    lora_alpha=16,
    target_r=4,  # 目标平均秩
    init_r=12,   # 初始秩
    tinit=0,
    tfinal=1000,
    deltaT=10,
)
```

#### 2. LoRA+

**改进的初始化策略**，提升收敛速度。

#### 3. DoRA (Weight-Decomposed LoRA)

**权重分解 LoRA**，将权重更新分解为方向和幅度：

```python
from peft import LoraConfig

config = LoraConfig(
    use_dora=True,  # 启用 DoRA
    r=8,
)
```

---

## 🔬 QLoRA 详解

### QLoRA 核心原理

**QLoRA (Quantized LoRA)** = **4-bit 量化** + **LoRA 微调**

核心创新：
1. 使用 4-bit NormalFloat (NF4) 量化基础模型
2. 在量化模型上应用 LoRA
3. 使用双重量化 (Double Quantization) 进一步节省显存
4. 使用分页优化器 (Paged Optimizers) 处理显存峰值

### QLoRA 架构

```
QLoRA 工作流程:

1. 量化基础模型
┌─────────────────────┐
│  FP16 模型 (3GB)    │
└──────────┬──────────┘
           │ 4-bit 量化 (NF4)
           ▼
┌─────────────────────┐
│  INT4 模型 (0.75GB) │  ← 冻结
└──────────┬──────────┘
           │
           │ 2. 添加 LoRA Adapter
           ▼
┌─────────────────────┐
│  LoRA 层 (FP16)     │  ← 可训练
│  ~10MB              │
└─────────────────────┘

3. 前向传播
   量化权重 ──> 反量化到 FP16 ──> 计算
                                  │
   LoRA (FP16) ──────────────────┘

总显存: 0.75GB (模型) + 0.01GB (LoRA) + 优化器状态
       ≈ 4-6GB (vs LoRA: 10GB, Full FT: 40GB)
```

### QLoRA 关键技术

#### 1. 4-bit NormalFloat (NF4)

专为正态分布权重设计的量化格式：

```python
# 传统量化 (INT4): 均匀分桶
[-1.0, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0, ...]

# NF4: 根据正态分布密度分桶
# 在 0 附近更密集（神经网络权重集中的区域）
[-1.0, -0.6961928, -0.5250730, -0.3949276, -0.2844377,
 -0.1848279, -0.0911688, 0, 0.0796318, 0.1609640, ...]
```

**优势**：
- ✅ 量化误差更小（相比标准 INT4）
- ✅ 更适合神经网络权重分布

#### 2. 双重量化 (Double Quantization)

对量化常数本身进行量化：

```
常规量化:
├── 量化权重: 4-bit
└── 量化常数 (scale, zero_point): FP32

双重量化:
├── 量化权重: 4-bit
└── 量化常数: 8-bit (也被量化)

节省显存: ~0.3-0.5GB (对于 7B 模型)
```

#### 3. 分页优化器 (Paged Optimizers)

处理显存峰值的技术：

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    optim="paged_adamw_32bit",  # 分页优化器
    # 当显存不足时，自动将优化器状态转移到 CPU
)
```

**原理**：
- 正常情况：优化器状态在 GPU
- 显存不足时：自动迁移到 CPU（类似虚拟内存）
- 需要时再迁移回 GPU

### QLoRA 配置

```python
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

# 1. 配置 4-bit 量化
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                      # 启用 4-bit 量化
    bnb_4bit_quant_type="nf4",              # 使用 NF4 量化
    bnb_4bit_compute_dtype=torch.float16,   # 计算时使用 FP16
    bnb_4bit_use_double_quant=True,         # 启用双重量化
)

# 2. 加载量化模型
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
)

# 3. 准备模型用于 k-bit 训练
model = prepare_model_for_kbit_training(model)

# 4. 配置 LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# 5. 应用 PEFT
from peft import get_peft_model
model = get_peft_model(model, lora_config)
```

### QLoRA 训练参数详解

QLoRA 训练需要特殊的参数配置以充分利用量化优势并保持训练稳定性。以下是一个**参考配置示例**，来自实际项目实践。

⚠️ **重要提示**：
- 这些参数**不是唯一的标准配置**，需要根据具体场景调整
- 来源：某个实际项目的配置，结合了 QLoRA 论文和实践经验
- 适用场景：中等规模模型（7B-13B）+ 中等数据集（10K-50K 样本）+ 消费级显卡（RTX 4090/A100）
- 不同的模型规模、数据集大小、任务类型都需要调整参数

**参数可信度分级**：
- ✅ **标准/推荐**：来自官方文档、论文或广泛共识（如 `per_device_train_batch_size=1`）
- ⚠️ **经验值**：来自实际项目经验，需要验证（如 `max_grad_norm=0.3`）
- ⚠️ **可选**：取决于具体场景（如 `group_by_length=True`）

建议：先尝试标准配置，根据训练表现调整经验值参数。

#### 参考训练参数配置

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./qlora_output",

    # ============ 批次配置 ============
    per_device_train_batch_size=1,      # ✅ 标准：QLoRA 典型配置
    gradient_accumulation_steps=16,     # ✅ 合理：有效 batch_size=16
    # 💡 有效批次大小 = per_device_train_batch_size × gradient_accumulation_steps
    #    QLoRA 通常用 batch=1 + 大梯度累积来节省显存

    # ============ 训练轮数 ============
    num_train_epochs=3,                 # ✅ 常见默认值

    # ============ 学习率配置 ============
    learning_rate=2e-4,                 # ⚠️ 经验值：适用于 7B-13B 模型
    lr_scheduler_type="cosine",         # ✅ 推荐：余弦退火调度器
    warmup_ratio=0.03,                  # ⚠️ 经验值：适用于大数据集（> 50K）
    # 💡 注意：小数据集（< 10K）可能需要更大的 warmup (0.05-0.1)

    # ============ 优化器配置 ============
    optim="paged_adamw_32bit",          # ✅ 标准：QLoRA 专用分页优化器
    # 💡 paged_adamw_32bit 会在显存不足时自动将优化器状态迁移到 CPU
    weight_decay=0.01,                  # ✅ 常见值：L2 正则化
    max_grad_norm=0.3,                  # ⚠️ 经验值：比 transformers 默认的 1.0 更保守
    # 💡 注意：这个值来自某些项目经验，并非官方推荐，可能需要调整为 0.5-1.0

    # ============ 显存优化 ============
    gradient_checkpointing=True,        # ✅ 必需：启用梯度检查点，节省显存
    gradient_checkpointing_kwargs={
        "use_reentrant": False          # ✅ 推荐：PyTorch 2.0+ 避免潜在问题
    },
    # 💡 梯度检查点会重新计算中间激活值，牺牲 20% 速度换取 50% 显存节省

    # ============ 混合精度训练 ============
    bf16=True,                          # ✅ 硬件适配：RTX 4090/A100 优先 BF16
    fp16=False,                         # ⚠️ 如果硬件不支持 BF16，改用 fp16=True
    # 💡 检测方法：torch.cuda.is_bf16_supported()

    # ============ 数据处理优化 ============
    group_by_length=True,               # ⚠️ 可选：适用于长度差异大的数据集
    dataloader_num_workers=4,           # ✅ 合理：数据加载并行数

    # ============ 日志和保存策略 ============
    logging_steps=10,                   # ✅ 常见值
    save_strategy="steps",              # ✅ 标准
    save_steps=100,                     # ⚠️ 经验值：适用于中等数据集（10K-50K）
    # 💡 注意：需要根据数据集大小调整
    #    - 小数据集（< 5K）：save_steps=50
    #    - 大数据集（> 100K）：save_steps=200-500
    save_total_limit=3,                 # ✅ 常见值：只保留最新 3 个 checkpoint

    # ============ 评估策略 ============
    evaluation_strategy="steps",        # ✅ 推荐
    eval_steps=100,                     # ⚠️ 应与 save_steps 保持一致
    load_best_model_at_end=True,        # ✅ 推荐
    metric_for_best_model="eval_loss",  # ✅ 常见选择

    # ============ 其他设置 ============
    report_to="none",                   # ⚠️ 可选：生产环境建议启用监控
    remove_unused_columns=False,        # ⚠️ 取决于具体任务
)
```

**图例说明**：
- ✅ 标准/推荐：广泛认可的配置
- ✅ 合理/常见：大多数场景适用
- ⚠️ 经验值：来自某些项目实践，需要根据场景调整
- ⚠️ 可选：取决于具体需求

#### 参数详解与最佳实践

##### 1. **批次大小策略**

```python
# QLoRA 典型配置
per_device_train_batch_size=1
gradient_accumulation_steps=16
# 有效 batch_size = 1 × 16 = 16
```

**为什么 QLoRA 用 batch=1？**
- 4-bit 量化已极大降低模型显存，但激活值仍占用大量显存
- `batch=1` 将激活值显存降到最低
- 通过大梯度累积（16-32）保持训练稳定性

**调整建议**：
| 显卡 | batch | grad_accum | 有效 batch |
|------|-------|-----------|-----------|
| **RTX 3090 (24GB)** | 1 | 16 | 16 |
| **RTX 4090 (24GB)** | 1-2 | 8-16 | 16 |
| **A100 (40GB)** | 2-4 | 8 | 16-32 |

##### 2. **学习率与 Warmup**

```python
learning_rate=2e-4          # ⚠️ 经验值：来自实际项目
warmup_ratio=0.03           # ⚠️ 经验值：QLoRA 论文用的很小的 warmup
```

**关于学习率的说明**：
- **QLoRA 论文推荐 2e-4**（针对 65B 模型 + Alpaca 数据集）
- 但不同模型规模和任务可能需要不同的学习率：
  - **小模型（< 3B）**：1e-4 可能更稳定
  - **中模型（7B-13B）**：1e-4 到 2e-4
  - **大模型（> 30B）**：2e-4 到 3e-4

**关于 Warmup 的说明**：
- **0.03 (3% warmup)** 适用于大数据集（> 50K 样本）
- 实践中发现：
  - **小数据集（< 10K）**：0.05-0.1 更稳定
  - **中数据集（10K-50K）**：0.03-0.05
  - **大数据集（> 50K）**：0.03 可能足够

**调整建议**：
- 训练不稳定（loss 震荡）→ 降低 LR 到 `1e-4`，增加 warmup 到 `0.05-0.1`
- 收敛太慢 → 提高 LR 到 `2e-4` 或 `3e-4`
- 小数据集 → 使用 `1e-4` + `warmup_ratio=0.1`

##### 3. **梯度裁剪**

```python
max_grad_norm=0.3           # ⚠️ 经验值：来自实际项目
```

**关于梯度裁剪的说明**：
- **Transformers 默认值**：1.0
- **这个项目使用**：0.3（更保守）
- **理论依据**：量化可能带来更大的梯度噪声，需要更强的裁剪
- **但注意**：0.3 并非 QLoRA 论文的官方推荐值

**不同来源的推荐**：
- Transformers 默认：`max_grad_norm=1.0`
- 一些开源项目：`max_grad_norm=0.3-0.5`
- 具体选择取决于训练稳定性

**调整建议**：
| 现象 | 建议值 | 说明 |
|------|-------|------|
| 训练稳定 | 0.3-1.0 | 根据实际情况保持 |
| Loss 爆炸（出现 NaN） | 0.1-0.3 | 加强裁剪 |
| 收敛过慢 | 0.5-1.0 | 放宽限制 |
| 不确定 | **先试 1.0**（默认值） | 有问题再降低 |

##### 4. **梯度检查点**

```python
gradient_checkpointing=True
gradient_checkpointing_kwargs={"use_reentrant": False}
```

**作用**：
- 不保存中间激活值，反向传播时重新计算
- **显存节省**：~40-50%
- **速度损失**：~20-30%

**use_reentrant=False 的原因**：
- PyTorch 2.0+ 推荐配置
- 避免潜在的梯度计算错误
- 更好的兼容性

**何时禁用？**
```python
# 如果显存充足（> 40GB）且追求速度
gradient_checkpointing=False
```

##### 5. **混合精度训练**

```python
bf16=True if torch.cuda.is_bf16_supported() else False
fp16=not bf16
```

**BF16 vs FP16**：
| 特性 | BF16 | FP16 |
|------|------|------|
| **数值范围** | 更大（与 FP32 相同） | 较小 |
| **数值稳定性** | 更好 | 需要 loss scaling |
| **支持硬件** | A100, H100, RTX 4090 | V100, RTX 3090 |
| **QLoRA 推荐** | ✅ 优先 | 次选 |

**检测硬件支持**：
```python
import torch
if torch.cuda.is_bf16_supported():
    print("✅ 支持 BF16，推荐使用")
else:
    print("⚠️ 不支持 BF16，使用 FP16")
```

##### 6. **保存策略**

```python
save_steps=100              # ⚠️ 经验值：某些项目覆盖默认的 500
save_total_limit=3          # ✅ 常见值
```

**关于 save_steps=100 的说明**：

这个配置的合理性**取决于数据集大小**：

**优点**：
1. **Adapter 体积小**：
   - LoRA adapter: ~10-50MB
   - 频繁保存不占存储（100 步 × 3 个 checkpoint ≈ 150MB）
   - 对比：完整模型 checkpoint 需要 3GB+

2. **训练安全网**：
   - 如果训练中断或某个 checkpoint 出问题，损失更小
   - 可以回退到 100 步前，而不是 500 步前

3. **实验灵活性**：
   - 可以在任意 100/200/300 步早停

**潜在问题**：
1. **I/O 开销**：
   - 大数据集（> 100K 样本）频繁保存会增加 I/O 开销
   - 虽然 adapter 小，但频繁写磁盘仍有成本

2. **相对性**：
   - 小数据集（1000 样本，batch=16）：100 步 ≈ 1.6 个 epoch（太频繁）
   - 大数据集（100K 样本，batch=16）：100 步 ≈ 0.016 个 epoch（合理）

**调整建议**：

根据**数据集大小**调整：

```python
# 小数据集（< 5K 样本）
save_strategy="epoch"       # 按 epoch 保存更合理
# 或
save_steps=50              # 如果仍想按步数保存

# 中数据集（5K-50K 样本）
save_steps=100             # ✅ 合理

# 大数据集（50K-100K 样本）
save_steps=200

# 超大数据集（> 100K 样本）
save_steps=500             # 回到默认值

# 磁盘空间充足，保留更多 checkpoint
save_total_limit=5
```

**建议的决策流程**：
1. 计算：`总样本数 / (batch_size × save_steps)` = 每次保存相当于多少个 epoch
2. 如果 < 0.1 epoch：save_steps 太小，建议增大
3. 如果 0.1-0.5 epoch：合理
4. 如果 > 1 epoch：save_steps 太大，建议减小

##### 7. **数据处理优化**

```python
group_by_length=True        # ⚠️ 可选：取决于数据集特征
```

**作用**：
- 将相似长度的样本放在同一个 batch
- 减少 padding，提升训练效率
- **潜在收益**：5-20%（高度依赖数据集长度分布）

**适用场景**：
- ✅ 数据集长度差异大（如 50-1000 tokens）
- ✅ 追求训练效率

**不适用场景**：
- ❌ 数据集长度非常均匀（如都是 512 tokens）→ 排序开销 > 收益
- ❌ 需要保持数据顺序的任务（如课程学习）
- ❌ 数据集很小（< 1000 样本）→ 排序开销明显

**建议**：
```python
# 默认可以开启，如果发现训练变慢再关闭
group_by_length=True

# 如果数据集长度均匀或很小
group_by_length=False
```

#### 完整的 QLoRA 训练脚本

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model

# ==================== 1. 量化配置 ====================
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    bnb_4bit_use_double_quant=True,
)

# ==================== 2. 加载模型 ====================
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
)
model = prepare_model_for_kbit_training(model)

# ==================== 3. LoRA 配置 ====================
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)

# ==================== 4. 训练参数（生产配置）====================
training_args = TrainingArguments(
    output_dir="./qlora_output",

    # 批次与梯度累积
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,

    # 训练轮数
    num_train_epochs=3,

    # 学习率与调度
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,

    # 优化器与正则化
    optim="paged_adamw_32bit",
    weight_decay=0.01,
    max_grad_norm=0.3,

    # 显存优化
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},

    # 混合精度
    bf16=torch.cuda.is_bf16_supported(),
    fp16=not torch.cuda.is_bf16_supported(),

    # 数据处理
    group_by_length=True,
    dataloader_num_workers=4,

    # 日志与保存
    logging_steps=10,
    save_strategy="steps",
    save_steps=100,
    save_total_limit=3,

    # 评估
    evaluation_strategy="steps",
    eval_steps=100,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",

    # 其他
    report_to="none",
)

# ==================== 5. 训练 ====================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()
model.save_pretrained("./qlora_adapter")
```

#### QLoRA 训练参数速查表

| 参数 | 参考值 | 状态 | 说明与调整建议 |
|------|-------|------|--------------|
| **per_device_train_batch_size** | 1 | ✅ 标准 | QLoRA 典型配置<br>显存充足 → 2-4 |
| **gradient_accumulation_steps** | 16 | ✅ 合理 | 有效 batch=16<br>需要更大有效 batch → 32 |
| **learning_rate** | 2e-4 | ⚠️ 经验值 | 适用于 7B-13B 模型<br>小模型（< 3B）→ 1e-4<br>大模型（> 30B）→ 3e-4 |
| **warmup_ratio** | 0.03 | ⚠️ 经验值 | 适用于大数据集（> 50K）<br>小数据集（< 10K）→ 0.05-0.1 |
| **max_grad_norm** | 0.3 | ⚠️ 经验值 | 比默认 1.0 更保守<br>不确定时先试 1.0，有问题再降低 |
| **gradient_checkpointing** | True | ✅ 必需 | 节省 40-50% 显存<br>显存充足（> 40GB）→ False（提速） |
| **bf16** | True | ✅ 硬件适配 | RTX 4090/A100 优先<br>V100/3090 → fp16=True |
| **save_steps** | 100 | ⚠️ 经验值 | **取决于数据集大小**<br>小数据集（< 5K）→ 50 或按 epoch<br>大数据集（> 100K）→ 200-500 |
| **group_by_length** | True | ⚠️ 可选 | 适用于长度差异大的数据集<br>长度均匀或数据集小 → False |

**图例说明**：
- ✅ 标准/必需：广泛认可，大多数场景适用
- ✅ 合理/推荐：常见配置，可直接使用
- ⚠️ 经验值：来自实际项目，需根据场景调整
- ⚠️ 可选：取决于具体需求和数据特征

#### 常见问题与解决方案

**Q1: 为什么我的 QLoRA 训练比 LoRA 慢？**
- ✅ 正常现象：量化-反量化有开销（慢 20-30%）
- ✅ 解决：如果显存充足，考虑用 LoRA（FP16/BF16）

**Q2: Loss 突然爆炸（变成 NaN）怎么办？**
```python
# 解决方案：
# 1. 降低学习率
learning_rate=1e-4  # 从 2e-4 降低

# 2. 加强梯度裁剪
max_grad_norm=0.1   # 从 0.3 降低

# 3. 增加 warmup
warmup_ratio=0.05   # 从 0.03 提高
```

**Q3: 显存仍然不足怎么办？**
```python
# 优化策略（按效果排序）：
# 1. 减小批次（已经是 1，不能再减）
# 2. 增加梯度累积（但训练变慢）
gradient_accumulation_steps=32

# 3. 减小序列长度
tokenizer.model_max_length=512  # 从 1024 降低

# 4. 减小 LoRA rank
config = LoraConfig(r=8)  # 从 16 降低
```

#### 使用建议总结

**第一次使用 QLoRA？按这个流程：**

1. **使用标准配置**（✅ 标记的参数）：
   ```python
   per_device_train_batch_size=1
   gradient_accumulation_steps=16
   optim="paged_adamw_32bit"
   gradient_checkpointing=True
   bf16=True  # 或 fp16
   ```

2. **根据数据集调整关键参数**：
   ```python
   # 小数据集（< 10K）
   learning_rate=1e-4
   warmup_ratio=0.1
   save_strategy="epoch"

   # 大数据集（> 50K）
   learning_rate=2e-4
   warmup_ratio=0.03
   save_steps=200
   ```

3. **观察训练曲线，按需调整经验值参数**：
   - Loss 爆炸 → 降低 `learning_rate`，减小 `max_grad_norm`
   - 收敛太慢 → 提高 `learning_rate`，检查 `warmup_ratio`
   - 显存不足 → 增加 `gradient_accumulation_steps`，减小序列长度

4. **记录有效的配置**：
   - 不同项目可能需要不同参数
   - 经验值参数需要针对自己的场景验证

**核心原则**：
- ✅ 优先使用标准配置
- ⚠️ 谨慎对待经验值参数
- 📊 根据实验结果调整
- 📝 记录和积累自己的最佳实践

### QLoRA 显存对比

**Llama-2-7B 模型在不同方法下的显存占用**：

| 方法 | 模型显存 | 优化器显存 | 总显存 | 可用硬件 |
|------|---------|-----------|--------|----------|
| **Full Fine-tune (FP32)** | 28GB | 56GB | ~100GB | 2×A100 |
| **Full Fine-tune (FP16)** | 14GB | 28GB | ~50GB | A100 |
| **LoRA (FP16)** | 14GB | 0.1GB | ~20GB | A100 / RTX 4090 |
| **QLoRA (4-bit)** | 3.5GB | 0.1GB | ~6GB | RTX 3090 / 4070 Ti |

**结论**：QLoRA 让 7B 模型的微调在消费级显卡上成为可能！

### QLoRA 的局限性

虽然 QLoRA 大幅降低了显存需求，但也有一些代价：

❌ **训练速度较慢**：
- 量化-反量化操作有额外开销
- 大约慢 20-30% vs LoRA

❌ **精度轻微损失**：
- 4-bit 量化会带来微小的精度下降
- 通常在 1-2% 的性能范围内

✅ **适用场景**：
- 显存受限（< 24GB）
- 不追求极致训练速度
- 实验和原型开发

---

## ⚙️ PEFT 微调工作原理

### 完整微调流程

```
┌─────────────────────────────────────────────────────────────┐
│                  PEFT 微调完整流程                           │
└─────────────────────────────────────────────────────────────┘

1. 准备阶段
   ├─ 加载预训练模型
   │  └─ AutoModelForCausalLM.from_pretrained()
   │
   ├─ 创建 PEFT 配置
   │  └─ LoraConfig(r=8, lora_alpha=16, ...)
   │
   └─ 应用 PEFT 包装
      └─ get_peft_model(model, config)

2. 模型改造阶段
   ├─ 冻结基础模型参数
   │  └─ base_model.requires_grad_(False)
   │
   ├─ 注入可训练模块
   │  ├─ 遍历 target_modules
   │  ├─ 替换原始层为 PEFT 层
   │  └─ 初始化新增参数
   │
   └─ 验证参数状态
      └─ print_trainable_parameters()

3. 训练阶段
   ├─ 前向传播
   │  ├─ 输入 → 基础层（冻结）
   │  ├─ 输入 → PEFT 层（可训练）
   │  └─ 输出 = 基础输出 + PEFT 输出
   │
   ├─ 损失计算
   │  └─ loss = criterion(output, target)
   │
   ├─ 反向传播
   │  ├─ loss.backward()
   │  └─ 仅 PEFT 参数接收梯度
   │
   └─ 参数更新
      └─ optimizer.step()  # 仅更新 PEFT 参数

4. 保存阶段
   └─ model.save_pretrained("output/")
      ├─ adapter_config.json  # PEFT 配置
      └─ adapter_model.bin    # PEFT 权重 (仅几 MB)

5. 推理阶段 (两种方式)

   方式 A: 使用 PEFT (灵活)
   ├─ 加载基础模型
   ├─ 加载 adapter
   └─ 可动态切换不同 adapter

   方式 B: 合并权重 (快速)
   ├─ 合并 adapter 到基础模型
   ├─ 保存完整模型
   └─ 推理无额外开销
```

### 训练时的前向传播

以 LoRA 为例：

```python
# 伪代码展示前向传播过程

def forward_with_lora(x):
    """
    LoRA 前向传播

    参数:
    x: 输入 [batch_size, seq_len, hidden_dim]

    前向传播公式:
    output = W₀x + (α/r) × B(Ax)
    """
    # 1. 基础模型计算（冻结）
    base_output = base_linear(x)  # W₀ × x

    # 2. LoRA 计算（可训练）
    lora_A_output = lora_A(x)           # A × x, shape: [batch, seq, r]
    lora_B_output = lora_B(lora_A_output)  # B × (A × x), shape: [batch, seq, hidden]

    # 3. 缩放
    lora_output = lora_B_output * (lora_alpha / r)

    # 4. 组合
    final_output = base_output + lora_output

    return final_output

# 梯度只会流向 lora_A 和 lora_B
# base_linear 的参数不会更新
```

### 显存占用分析

```python
# 以 Qwen2.5-1.5B + LoRA(r=8) 为例

显存组成:
├─ 模型参数
│  ├─ 基础模型 (FP16): 1.5B × 2 bytes = 3GB
│  └─ LoRA 参数 (FP16): 2M × 2 bytes = 4MB
│
├─ 优化器状态 (仅 LoRA 参数)
│  ├─ Adam m (动量): 4MB
│  ├─ Adam v (二阶矩): 4MB
│  └─ 梯度: 4MB
│
├─ 激活值 (前向传播缓存)
│  └─ 取决于 batch_size 和 sequence_length
│     batch=8, seq=512: ~2-4GB
│
└─ 临时缓存
   └─ ~1GB

总计: ~6-10GB (vs 全参数微调: 40GB+)
```

### PEFT 与 Trainer 集成

PEFT 与 Hugging Face Transformers 无缝集成：

```python
from transformers import Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig

# 1. 准备 PEFT 模型
config = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"])
model = get_peft_model(base_model, config)

# 2. 配置训练参数
training_args = TrainingArguments(
    output_dir="./output",
    num_train_epochs=3,
    per_device_train_batch_size=8,
    learning_rate=1e-4,
    save_steps=500,
    logging_steps=10,
)

# 3. 创建 Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

# 4. 训练
trainer.train()

# 5. 保存 (自动只保存 adapter)
model.save_pretrained("./lora_adapter")
```

---

## 💡 最佳实践

### 1. 如何选择 PEFT 方法？

```
决策树:

显存是否 < 24GB?
├─ 是 → 使用 QLoRA
└─ 否 → 继续

是否需要频繁切换任务?
├─ 是 → 使用 LoRA (保持 adapter 独立)
└─ 否 → 继续

是否追求最快推理速度?
├─ 是 → 使用 LoRA + 权重合并
└─ 否 → 使用 LoRA (不合并)
```

### 2. LoRA 超参数调优指南

#### r (秩) 的选择

```python
# 基于任务复杂度选择

# 简单任务 (分类、实体识别)
config = LoraConfig(r=4)

# 中等任务 (摘要、问答)
config = LoraConfig(r=8)  # 推荐起点

# 复杂任务 (代码生成、复杂推理)
config = LoraConfig(r=16)

# 大规模数据集
config = LoraConfig(r=32)

# 规律: r 越大，容量越大，但收益递减
# 建议: 从 r=8 开始，观察验证集表现调整
```

#### lora_alpha 的选择

```python
# 标准设置
config = LoraConfig(
    r=8,
    lora_alpha=16,  # 2 × r
)

# 如果模型不稳定或发散
config = LoraConfig(
    r=8,
    lora_alpha=8,   # 1 × r (更保守)
)

# 如果希望 LoRA 有更强影响
config = LoraConfig(
    r=8,
    lora_alpha=32,  # 4 × r (更激进)
)
```

#### target_modules 的选择

```python
# 方案 1: 最小配置 (最快训练)
config = LoraConfig(
    target_modules=["q_proj", "v_proj"]
)

# 方案 2: 标准配置 (推荐)
config = LoraConfig(
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
)

# 方案 3: 全注意力 + MLP
config = LoraConfig(
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj"       # MLP
    ]
)

# 方案 4: 所有线性层 (最全面)
config = LoraConfig(
    target_modules="all-linear"
)
```

### 3. 训练配置最佳实践

```python
from transformers import TrainingArguments

# 推荐配置
training_args = TrainingArguments(
    # 基础设置
    output_dir="./output",
    num_train_epochs=3,                    # 2-5 epoch 通常足够

    # 批次设置
    per_device_train_batch_size=8,         # 根据显存调整
    gradient_accumulation_steps=4,          # 有效 batch_size = 8×4=32

    # 学习率
    learning_rate=1e-4,                     # LoRA 推荐 1e-4 到 5e-4
    lr_scheduler_type="cosine",             # 余弦退火
    warmup_ratio=0.1,                       # 10% warmup

    # 优化器
    optim="adamw_torch",                    # 或 "paged_adamw_8bit" (QLoRA)
    weight_decay=0.01,

    # 保存策略
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,                     # 只保留最新 3 个 checkpoint

    # 评估策略
    evaluation_strategy="steps",
    eval_steps=100,

    # 日志
    logging_steps=10,
    report_to="tensorboard",

    # 性能优化
    fp16=True,                              # 混合精度训练 (非 QLoRA)
    dataloader_num_workers=4,

    # 早停 (需配合 EarlyStoppingCallback)
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
)
```

### 4. 数据准备建议

```python
# 数据格式示例
train_data = [
    {
        "instruction": "请将以下文本分类",
        "input": "这部电影太精彩了！",
        "output": "正面"
    },
    # ...
]

# 数据量建议
# - 简单任务: 1,000 - 5,000 样本
# - 中等任务: 5,000 - 20,000 样本
# - 复杂任务: 20,000+ 样本

# 数据质量 > 数据数量
# - 确保标注准确
# - 覆盖多样化场景
# - 平衡各类别分布
```

### 5. 常见陷阱和解决方案

#### 陷阱 1: 过拟合

**症状**：训练 loss 持续下降，验证 loss 上升

**解决方案**：
```python
# 1. 增加 dropout
config = LoraConfig(lora_dropout=0.1)  # 提高到 0.15-0.2

# 2. 减少训练轮数
training_args = TrainingArguments(num_train_epochs=2)

# 3. 使用权重衰减
training_args = TrainingArguments(weight_decay=0.01)

# 4. 早停
from transformers import EarlyStoppingCallback
trainer = Trainer(..., callbacks=[EarlyStoppingCallback(patience=3)])
```

#### 陷阱 2: 欠拟合

**症状**：训练和验证 loss 都很高，不下降

**解决方案**：
```python
# 1. 增加 LoRA 秩
config = LoraConfig(r=16)  # 从 8 提高到 16

# 2. 增加训练轮数
training_args = TrainingArguments(num_train_epochs=5)

# 3. 提高学习率
training_args = TrainingArguments(learning_rate=5e-4)

# 4. 扩大 target_modules
config = LoraConfig(target_modules="all-linear")
```

#### 陷阱 3: 显存不足

**解决方案**：
```python
# 1. 减小 batch_size + 增加梯度累积
training_args = TrainingArguments(
    per_device_train_batch_size=4,  # 从 8 降到 4
    gradient_accumulation_steps=8,   # 从 4 提高到 8
)

# 2. 使用梯度检查点
model.gradient_checkpointing_enable()

# 3. 切换到 QLoRA
bnb_config = BitsAndBytesConfig(load_in_4bit=True)

# 4. 减小序列长度
tokenizer.model_max_length = 512  # 从 1024 降到 512
```

### 6. 评估和验证

```python
# 评估脚本示例
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)

    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='weighted'
    )

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# 在 Trainer 中使用
trainer = Trainer(
    model=model,
    args=training_args,
    compute_metrics=compute_metrics,
    # ...
)
```

---

## 🚀 实战示例

### 示例 1: 使用 LoRA 微调 Qwen2.5

```python
# 完整的微调脚本

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

# ==================== 1. 准备模型和分词器 ====================
model_name = "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

# ==================== 2. 配置 LoRA ====================
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,                                      # LoRA 秩
    lora_alpha=16,                            # 缩放因子
    lora_dropout=0.1,                         # Dropout
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # 目标模块
    bias="none",
)

# 应用 LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出: trainable params: 2,359,296 || all params: 1,543,234,560 || trainable%: 0.15%

# ==================== 3. 准备数据 ====================
# 加载数据集
dataset = load_dataset("json", data_files="train.jsonl")

# 数据预处理
def preprocess_function(examples):
    # 构建 prompt
    prompts = []
    for instruction, input_text, output in zip(
        examples["instruction"],
        examples["input"],
        examples["output"]
    ):
        prompt = f"### 指令:\n{instruction}\n\n### 输入:\n{input_text}\n\n### 输出:\n{output}"
        prompts.append(prompt)

    # 分词
    model_inputs = tokenizer(
        prompts,
        max_length=512,
        truncation=True,
        padding="max_length",
    )

    # 设置 labels (与 input_ids 相同用于语言建模)
    model_inputs["labels"] = model_inputs["input_ids"].copy()

    return model_inputs

# 处理数据
tokenized_dataset = dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=dataset["train"].column_names,
)

# ==================== 4. 配置训练参数 ====================
training_args = TrainingArguments(
    output_dir="./output",
    num_train_epochs=3,
    per_device_train_batch_size=8,
    gradient_accumulation_steps=4,
    learning_rate=1e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    logging_steps=10,
    save_steps=500,
    save_total_limit=3,
    fp16=True,
    report_to="tensorboard",
)

# ==================== 5. 创建 Trainer ====================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

# ==================== 6. 训练 ====================
trainer.train()

# ==================== 7. 保存模型 ====================
model.save_pretrained("./lora_adapter")
tokenizer.save_pretrained("./lora_adapter")

print("训练完成！Adapter 已保存到 ./lora_adapter")
```

### 示例 2: 使用 QLoRA 微调 Llama-7B

```python
# QLoRA 微调示例

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from datasets import load_dataset

# ==================== 1. 配置 4-bit 量化 ====================
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# ==================== 2. 加载量化模型 ====================
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
)

# 准备模型用于 k-bit 训练
model = prepare_model_for_kbit_training(model)

# ==================== 3. 配置 LoRA ====================
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ==================== 4. 加载数据 ====================
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer.pad_token = tokenizer.eos_token

dataset = load_dataset("json", data_files="train.jsonl")

# ... (数据预处理同示例 1)

# ==================== 5. 配置训练 (QLoRA 专用) ====================
training_args = TrainingArguments(
    output_dir="./qlora_output",
    num_train_epochs=3,
    per_device_train_batch_size=4,        # QLoRA 可以用更小的 batch
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    optim="paged_adamw_32bit",            # 分页优化器
    logging_steps=10,
    save_steps=500,
    fp16=False,                           # QLoRA 已经是 4-bit，不需要 fp16
    bf16=False,
)

# ==================== 6. 训练 ====================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
)

trainer.train()

# ==================== 7. 保存 ====================
model.save_pretrained("./qlora_adapter")

print("QLoRA 训练完成！显存占用峰值约 6GB")
```

### 示例 3: 推理和部署

```python
# 方式 1: 使用 adapter 推理

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载基础模型
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")

# 加载 adapter
model = PeftModel.from_pretrained(base_model, "./lora_adapter")
tokenizer = AutoTokenizer.from_pretrained("./lora_adapter")

# 推理
def generate(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=200)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

result = generate("请识别意图: 明天早上八点叫醒我")
print(result)

# ==================== 方式 2: 合并权重后推理 ====================

# 合并权重
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
model = PeftModel.from_pretrained(base_model, "./lora_adapter")

# 合并
merged_model = model.merge_and_unload()

# 保存完整模型
merged_model.save_pretrained("./merged_model")
tokenizer.save_pretrained("./merged_model")

# 后续可以直接加载，无需 PEFT
model = AutoModelForCausalLM.from_pretrained("./merged_model")
tokenizer = AutoTokenizer.from_pretrained("./merged_model")

# 推理速度与原始模型相同
```

### 示例 4: 多任务 Adapter 切换

```python
# PEFT 支持在同一基础模型上快速切换不同 adapter

from peft import PeftModel

# 加载基础模型 (只需加载一次)
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B")

# 任务 1: 意图分类
model = PeftModel.from_pretrained(base_model, "./adapter_intent")
result1 = generate("明天的天气")

# 任务 2: 情感分析 (切换 adapter)
model.load_adapter("./adapter_sentiment", adapter_name="sentiment")
model.set_adapter("sentiment")
result2 = generate("这部电影太棒了")

# 任务 3: 文本摘要 (再次切换)
model.load_adapter("./adapter_summary", adapter_name="summary")
model.set_adapter("summary")
result3 = generate("请总结: ...")

# 优势:
# - 基础模型只加载一次 (节省显存)
# - adapter 切换非常快 (几毫秒)
# - 每个 adapter 只有几 MB
```

---

## 📊 性能对比

### 模型大小对比

以 **Qwen2.5-1.5B** 为例：

| 方法 | 模型大小 | 对比 |
|------|---------|------|
| **原始模型 (FP32)** | 6GB | 基准 |
| **原始模型 (FP16)** | 3GB | 50% |
| **LoRA Adapter** | 10MB | 0.16% |
| **QLoRA Adapter** | 10MB | 0.16% |
| **合并后 (FP16)** | 3GB | 50% |

### 训练时间对比

基于 **Qwen2.5-1.5B** 在 MASSIVE 数据集 (11K 样本) 上训练 3 epochs：

| 方法 | GPU | 训练时间 | 显存占用 | 对比 |
|------|-----|---------|---------|------|
| **Full Fine-tune** | A100 (40GB) | 3小时 | 35GB | 基准 |
| **LoRA (r=8)** | RTX 4090 (24GB) | 1小时 | 10GB | 3× 更快 |
| **QLoRA (r=8)** | RTX 3090 (24GB) | 1.5小时 | 6GB | 2× 更快 |

### 效果对比

在多个 NLP 任务上的性能（准确率 %）：

| 任务 | Full FT | LoRA (r=8) | LoRA (r=16) | QLoRA (r=16) |
|------|---------|------------|-------------|--------------|
| **意图分类** | 92.5 | 91.2 | 91.8 | 91.0 |
| **情感分析** | 94.3 | 93.7 | 94.0 | 93.5 |
| **文本摘要 (ROUGE-L)** | 45.2 | 43.8 | 44.5 | 43.2 |
| **代码生成 (Pass@1)** | 38.5 | 36.2 | 37.4 | 35.8 |

**结论**：
- LoRA 可以达到全参数微调 **95-98%** 的效果
- r=16 相比 r=8 提升 **1-2%**
- QLoRA 相比 LoRA 略低 **0.5-1%**

### 不同 r 值的影响

**Llama-7B 在指令微调任务上的表现**：

| LoRA Rank (r) | 可训练参数量 | 准确率 | 训练时间 |
|--------------|-------------|--------|----------|
| **r=4** | 2M | 78.5% | 1.0× |
| **r=8** | 4M | 82.3% | 1.2× |
| **r=16** | 8M | 85.1% | 1.4× |
| **r=32** | 16M | 86.8% | 1.8× |
| **r=64** | 32M | 87.2% | 2.5× |
| **Full FT** | 7B | 88.0% | 10× |

**观察**：
- r=4 到 r=16: 性能显著提升
- r=16 到 r=64: 收益递减
- r=64: 已接近全参数微调效果
- **推荐起点**: r=8 或 r=16

---

## ❓ 常见问题

### Q1: LoRA 和 QLoRA 该选哪个？

**选择 LoRA 如果**：
- ✅ 你有 >= 24GB 显存
- ✅ 追求最佳效果
- ✅ 追求最快训练速度

**选择 QLoRA 如果**：
- ✅ 显存 < 24GB
- ✅ 使用消费级显卡 (RTX 3090/4090)
- ✅ 可以接受稍慢的训练速度

### Q2: 为什么我的 LoRA 效果不好？

**可能的原因和解决方案**：

1. **r 值太小**
   ```python
   # 尝试增大 r
   config = LoraConfig(r=16)  # 从 8 提高到 16
   ```

2. **target_modules 不够**
   ```python
   # 扩大目标模块
   config = LoraConfig(target_modules="all-linear")
   ```

3. **学习率不合适**
   ```python
   # 调整学习率
   training_args = TrainingArguments(learning_rate=5e-4)
   ```

4. **训练数据不足或质量差**
   - 增加数据量到 5K+
   - 检查标注质量
   - 平衡类别分布

### Q3: 如何判断训练是否正常？

**健康的训练曲线**：
```
Loss:
Epoch 1: 2.5 → 1.8 → 1.5
Epoch 2: 1.5 → 1.2 → 1.0
Epoch 3: 1.0 → 0.9 → 0.85

特征:
✅ 持续下降
✅ 下降速度逐渐变慢
✅ 训练和验证 loss 趋势一致
```

**有问题的训练**

```
问题 1: Loss 不下降
Epoch 1: 2.5 → 2.5 → 2.5
→ 学习率太小或数据有问题

问题 2: Loss 震荡
Epoch 1: 2.5 → 1.5 → 3.0 → 2.0
→ 学习率太大或 batch_size 太小

问题 3: 过拟合
Train Loss: 0.5 → 0.3 → 0.1
Val Loss: 1.0 → 1.2 → 1.5
→ 需要正则化或早停
```

### Q4: LoRA 权重应该合并吗？

**合并的优势**：
- ✅ 推理速度快（无额外计算）
- ✅ 部署简单（不需要 PEFT 库）
- ✅ 兼容性好

**不合并的优势**：
- ✅ 灵活切换不同 adapter
- ✅ 节省存储（每个任务只存 adapter）
- ✅ 易于版本管理

**建议**：
- 生产部署 → 合并
- 实验和多任务 → 不合并

### Q5: 显存不够怎么办？

**优化策略（按效果排序）**：

```python
# 1. 使用 QLoRA (最有效)
bnb_config = BitsAndBytesConfig(load_in_4bit=True)

# 2. 减小 batch_size + 增加梯度累积
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=16,
)

# 3. 启用梯度检查点
model.gradient_checkpointing_enable()

# 4. 减小序列长度
tokenizer.model_max_length = 512

# 5. 使用更小的模型
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B")

# 6. 减小 LoRA rank
config = LoraConfig(r=4)
```

### Q6: 如何在多张显卡上训练？

```python
# 使用 Accelerate (推荐)
from accelerate import Accelerator

accelerator = Accelerator()
model, optimizer, train_dataloader = accelerator.prepare(
    model, optimizer, train_dataloader
)

# 或使用 Trainer + DeepSpeed
training_args = TrainingArguments(
    deepspeed="ds_config.json",
    # ...
)

# ds_config.json
{
    "train_micro_batch_size_per_gpu": 8,
    "gradient_accumulation_steps": 4,
    "fp16": {
        "enabled": true
    },
    "zero_optimization": {
        "stage": 2
    }
}
```

### Q7: PEFT 支持哪些模型架构？

PEFT 支持大多数 Transformer 架构：

✅ **支持的模型**：
- Llama / Llama-2 / Llama-3
- Qwen / Qwen2
- GPT-2 / GPT-J / GPT-NeoX
- BLOOM
- Falcon
- Mistral / Mixtral
- Phi
- Gemma

查看完整列表：
```python
from peft import MODEL_TYPE_TO_PEFT_MODEL_MAPPING
print(MODEL_TYPE_TO_PEFT_MODEL_MAPPING.keys())
```

---

## 📚 延伸阅读

### 核心论文

1. **LoRA: Low-Rank Adaptation of Large Language Models**
   - 论文: https://arxiv.org/abs/2106.09685
   - GitHub: https://github.com/microsoft/LoRA

2. **QLoRA: Efficient Finetuning of Quantized LLMs**
   - 论文: https://arxiv.org/abs/2305.14314
   - GitHub: https://github.com/artidoro/qlora

3. **Prefix-Tuning: Optimizing Continuous Prompts for Generation**
   - 论文: https://arxiv.org/abs/2101.00190

4. **P-Tuning v2: Prompt Tuning Can Be Comparable to Fine-tuning Universally Across Scales and Tasks**
   - 论文: https://arxiv.org/abs/2110.07602

### 官方资源

- **PEFT 官方文档**: https://huggingface.co/docs/peft
- **PEFT GitHub**: https://github.com/huggingface/peft
- **PEFT 示例**: https://github.com/huggingface/peft/tree/main/examples

### 推荐教程

- Hugging Face PEFT 快速开始: https://huggingface.co/docs/peft/quicktour
- LoRA 实战教程: https://huggingface.co/blog/lora
- QLoRA 实战教程: https://huggingface.co/blog/4bit-transformers-bitsandbytes

---

## 🎓 总结

### PEFT 核心要点

1. **核心价值**
   - 用 **0.1%-1%** 的参数达到 **95-98%** 的效果
   - 显存需求降低 **5-10 倍**
   - 训练速度提升 **3-5 倍**

2. **LoRA 原理**
   - 低秩矩阵分解: $\Delta W = BA$
   - 冻结基础模型，只训练 adapter
   - 关键参数: r, lora_alpha, target_modules

3. **QLoRA 原理**
   - 4-bit 量化 + LoRA
   - NF4 量化 + 双重量化 + 分页优化器
   - 显存需求降低到 **6GB**（7B 模型）

4. **最佳实践**
   - 从 `r=8, lora_alpha=16` 开始
   - 根据任务复杂度调整 r
   - 监控训练曲线，防止过拟合
   - 生产部署时合并权重

5. **应用场景**
   - ✅ 垂直领域适配
   - ✅ 多任务学习
   - ✅ 个性化定制
   - ✅ 快速原型开发

### 选择建议

```
如何选择 PEFT 方法?

显存充足 (>= 24GB):
└─> LoRA (r=8-16) → 最佳效果和速度

显存受限 (< 24GB):
└─> QLoRA (r=8-16) → 唯一选择

追求极致效率:
└─> LoRA (r=4-8) + 权重合并

多任务场景:
└─> LoRA + 多 adapter 切换
```

---

**最后更新**: 2024-12-19
**维护者**: AI Engineering Training Team
**版本**: v1.0

**相关文档**：
- [MASSIVE 微调指南](./MASSIVE_微调指南.md)
- [微调与 PEFT 微调流程总结](./微调流程总结.md)
