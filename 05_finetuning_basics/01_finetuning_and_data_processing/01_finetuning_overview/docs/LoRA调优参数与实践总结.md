# LoRA 调优参数与实践总结

## 1. 先给一个结论

LoRA 调优不能只盯着 `r`、`alpha`、`dropout` 这些参数。

对于意图识别、槽位抽取、结构化输出这类任务，更常见的真实情况是：

- 数据口径不一致，影响比调参更大
- prompt 不一致，影响比调参更大
- 空槽位负样本不足，会直接导致模型幻觉
- 训练轮数太少，往往比 LoRA rank 更容易成为瓶颈

所以更务实的经验是：

**先修数据和 prompt，再调训练超参数，最后才细抠 LoRA 容量。**

这也是 [FINE_TUNING_ROOT_CAUSE_ANALYSIS.md](/Users/songxijun/workspace/hailinpython2/docs/1.1/modelops/technical/FINE_TUNING_ROOT_CAUSE_ANALYSIS.md) 里最重要的实践结论。

---

## 2. LoRA 是什么

LoRA 的核心思想是：

- 冻结大部分基座模型参数
- 只在部分线性层上增加低秩矩阵
- 只训练这部分增量参数

因此，LoRA 调优的本质是：

- 决定把增量参数加在哪些层
- 决定增量参数容量有多大
- 决定训练过程如何更稳定

---

## 3. LoRA 最常见的调优参数

### 3.1 `r`

`r` 是 LoRA 的秩，决定低秩矩阵容量。

可以简单理解为：

- `r` 越小，参数更少，训练更省
- `r` 越大，表达能力更强，但显存和训练成本更高

常见取值：

- `4`
- `8`
- `16`
- `32`
- `64`

经验上：

- 简单分类任务：`8`
- 一般结构化抽取：`16`
- 更复杂的生成或多槽位任务：`16~32`

在 Qwen 7B 这类模型上，如果只注入 `q_proj/v_proj`，`r=16` 往往比 `r=8` 更稳。

---

### 3.2 `lora_alpha`

`lora_alpha` 是 LoRA 的缩放系数。

最终更新强度大致可以理解为：

```text
effective scale ≈ alpha / r
```

因此它通常和 `r` 配套调整。

常见经验：

- `alpha ≈ 2 * r`

典型搭配：

- `r=8 -> alpha=16`
- `r=16 -> alpha=32`
- `r=32 -> alpha=64`

如果 `alpha` 太小，LoRA 更新信号可能太弱；如果太大，训练更容易不稳定。

---

### 3.3 `lora_dropout`

这是 LoRA 分支上的 dropout，用来抑制过拟合。

常见取值：

- `0`
- `0.05`
- `0.1`

经验上：

- 数据量大、样本稳定：可以从 `0` 或 `0.05` 起
- 数据量小、容易过拟合：常用 `0.05`
- 一般不建议一开始就设得太高

对很多任务来说，`lora_dropout` 的影响通常小于：

- 数据质量
- `num_epochs`
- `r`
- `target_modules`

---

### 3.4 `target_modules`

这是 LoRA 调优里最关键的参数之一。

它决定：

- LoRA 挂在哪些层
- 哪些线性层会引入可训练增量

对 Qwen 系列模型，常见目标层有：

- 轻量配置：`["q_proj", "v_proj"]`
- 更强配置：`["q_proj", "k_proj", "v_proj", "o_proj"]`
- 更大容量配置：再加 `gate_proj`, `up_proj`, `down_proj`

经验上：

- 想省显存、省训练时间：先从 `q_proj + v_proj` 开始
- 效果不够：扩大到 attention 全层
- 仍不够：再考虑把 MLP 层纳入

很多时候效果上不去，不一定是 `r` 太小，而是注入范围太轻。

---

### 3.5 `bias`

常见取值：

- `none`
- `all`
- `lora_only`

最常用的是：

```python
bias = "none"
```

因为这样最简单，也最常见。

---

### 3.6 `task_type`

这不是决定效果的核心超参数，但配置必须正确。

常见有：

- `CAUSAL_LM`
- `SEQ_CLS`

如果是 Qwen 指令微调或结构化输出微调，通常使用：

```python
task_type = "CAUSAL_LM"
```

---

## 4. 和 LoRA 一起影响效果的训练超参数

严格来说，下面这些不是 LoRA 自身参数，但在实际训练里经常比 LoRA 参数更重要。

### 4.1 `learning_rate`

LoRA 常用学习率通常比全参训练更大。

常见范围：

- `1e-4`
- `2e-4`
- `3e-4`

常见起点：

```text
2e-4
```

如果扩大了 `target_modules` 或提高了 `r` 之后训练不稳，可以适当降低学习率。

---

### 4.2 `num_epochs`

这往往是最容易被低估的参数。

很多效果问题，不是 LoRA 参数不对，而是训练轮数太少。

常见范围：

- `2`
- `3`
- `5`

在前面那份根因分析文档里，一个很明确的结论就是：

- `num_epochs=1` 很可能欠拟合
- 先提高到 `3 epoch`，通常比盲目细调 LoRA 参数更值得优先做

---

### 4.3 `batch_size`

影响训练稳定性和吞吐。

显存不够时，通常结合：

- `gradient_accumulation_steps`

一起看有效 batch size。

---

### 4.4 `gradient_accumulation_steps`

这是小卡训练里非常常见的参数。

作用是：

- 单步 batch 放不下时，累积多个 step 的梯度
- 让有效 batch size 变大

---

### 4.5 `max_seq_length`

它会直接影响：

- 显存
- 截断风险
- prompt 是否被截掉
- 输出 JSON 是否被截掉

但不能盲目设大。

根因分析文档给出的实践很重要：

- 先用 tokenizer 统计真实 token 长度
- 再决定 `max_seq_length`
- 不要凭感觉把它调到 `1024/2048`

如果当前数据在 `256` 就够，那盲目调大只会浪费资源。

---

### 4.6 `weight_decay`

常见值：

- `0`
- `0.01`

一般不是第一优先级参数，但在扩大 LoRA 容量后，可以作为稳定性辅助项。

---

### 4.7 `warmup_ratio`

常见范围：

- `0.03`
- `0.05`
- `0.1`

一般作为训练稳定性的小调节项，不是第一优先级。

---

## 5. QLoRA 相关参数

如果不是纯 LoRA，而是 `QLoRA`，还会经常看到这些参数：

### 5.1 `load_in_4bit`

表示是否以 4bit 加载基座模型。

### 5.2 `bnb_4bit_quant_type`

常见值：

- `nf4`

这是 QLoRA 里很常见的选择。

### 5.3 `bnb_4bit_use_double_quant`

是否做双重量化。

常见配置：

- `True`

### 5.4 `bnb_4bit_compute_dtype`

常见：

- `torch.bfloat16`
- `torch.float16`

这些参数解决的是：

- 训练阶段怎么把大模型装进显存

它们和部署前的 `GPTQ / AWQ / INT8` 不是一回事。

---

## 6. 结合实践看，LoRA 调优到底先调什么

这是最重要的一节。

如果只看参数列表，很容易陷入“是不是先把 `r` 从 8 改成 16，再把 dropout 调一调”的思路。

但从 [FINE_TUNING_ROOT_CAUSE_ANALYSIS.md](/Users/songxijun/workspace/hailinpython2/docs/1.1/modelops/technical/FINE_TUNING_ROOT_CAUSE_ANALYSIS.md) 的实践看，真实优先级不是这样。

### 6.1 第一优先级：先修数据和 prompt

在那份文档里，最核心的结论是：

- 错误主体是 slot 类错误
- 优先级应是“数据口径统一 + 抑制查询幻觉 + 补齐混淆对”
- 再谈超参搜索

具体包括：

- 统一槽位标注口径
- 减少 event_name 过度拆分
- 人名归属规则统一
- 时间格式统一
- 增加空槽位负样本
- 明确 system prompt 中“不要猜测、不要补默认值”
- 确保训练、评估、前端测试的 prompt 模板一致

这类工作通常比调 `lora_dropout` 更有价值。

---

### 6.2 第二优先级：先排除明显欠拟合

在那份文档里，当前配置里最直接的问题之一是：

- `num_epochs=1`

实践建议是：

- 先把 `num_epochs` 提到 `3`
- 再看验证集指标是否明显改善

因为如果模型还没学够，这时去细调 LoRA 参数，收益通常不大。

---

### 6.3 第三优先级：再看 LoRA 容量是否不足

当下面这些前提已经满足：

- 数据口径已经统一
- prompt 已经统一
- 训练轮数已经合理
- 解码方式稳定

这时候如果指标仍然上不去，再考虑：

- `r` 是否太小
- `target_modules` 是否太轻

那份文档的经验结论很明确：

- 如果只注入 `q_proj/v_proj`
- 那么 `r=16` 比 `r=8` 更值得优先尝试

这比一开始就盲调很多小参数更有针对性。

---

### 6.4 第四优先级：最后再调细节项

例如：

- `lora_dropout`
- `weight_decay`
- `warmup_ratio`
- `early_stopping`

这些参数有价值，但通常不是最先解决主要问题的地方。

---

## 7. 一个更务实的调参顺序

如果是 Qwen 7B 做意图识别或槽位抽取，推荐按下面顺序排查和调优。

### 第一步：检查数据和 prompt

- schema 是否稳定
- 槽位值是否可追溯到输入原文
- 空槽位样本是否足够
- intent 边界是否冲突
- 训练/评估/线上 prompt 是否一致
- 是否明确要求严格 JSON、空槽位输出 `[]`

### 第二步：检查训练是否欠拟合

- `num_epochs` 是否太小
- loss 是否还在下降
- 验证集指标是否还在提升

### 第三步：调整核心训练参数

- `learning_rate`
- `num_epochs`
- `batch_size`
- `max_seq_length`

### 第四步：调整 LoRA 容量

- `target_modules`
- `r`
- `lora_alpha`

### 第五步：再调稳定性细节

- `lora_dropout`
- `weight_decay`
- `warmup_ratio`

---

## 8. 一套常见起手配置

对于 Qwen 7B 做结构化任务，一个常见起手配置可以是：

```python
LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"],
    bias="none",
    task_type="CAUSAL_LM",
)
```

训练参数可以从下面起步：

```python
learning_rate = 2e-4
num_epochs = 3
batch_size = 4
gradient_accumulation_steps = 4
max_seq_length = 256  # 先按真实 token 分布验证
```

如果效果不够，再逐步升级为：

- 扩大 `target_modules`
- 继续保留 `alpha ≈ 2r`
- 再根据验证集决定是否继续放大 `r`

---

## 9. 什么时候说明 LoRA 容量真的不够

下面这些现象更像是容量不足，而不是数据问题：

- 数据口径已经统一，但指标长期上不去
- 训练 loss 已下降并趋稳，但验证集不再提升
- 常见模式仍大面积抽不准，不只是长尾样本
- 增加 `num_epochs` 后仍改善有限
- 多槽位组合、复杂边界样本表现持续很差

这时再去怀疑：

- `r` 太小
- `target_modules` 太少

会更合理。

---

## 10. 什么时候不要急着调 LoRA 参数

下面这些现象，往往说明先别急着改 `r`：

- 同一语义在训练集有多种标注口径
- 查询类样本大量出现默认值幻觉
- prompt 模板训练和评估不一致
- 输出 JSON 格式经常漂移
- 解码时还在采样，导致结果不稳定

这些问题不先解决，LoRA 参数调得再细，收益通常也有限。

---

## 11. 总结

LoRA 最常见的调优参数是：

- `r`
- `lora_alpha`
- `lora_dropout`
- `target_modules`

但在真实项目里，效果往往同样甚至更强依赖：

- `learning_rate`
- `num_epochs`
- `batch_size`
- `max_seq_length`
- 数据口径
- prompt 一致性

结合根因分析文档里的实践，更值得记住的结论是：

**对结构化任务，最优先的不是细抠 LoRA 参数，而是先修数据规范、prompt 约束和负样本分布；在此基础上，再用 `num_epochs`、`r`、`target_modules` 去补足模型容量。**
