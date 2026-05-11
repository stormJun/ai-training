# rerank重排详解

## 1. 什么是第二阶段重排

在 RAG 流程里，第二阶段重排（Rerank）发生在“第一阶段召回”之后、“生成答案”之前。

它的作用不是去全库里找文档，而是对第一阶段已经召回出来的候选文档再做一次更细粒度的相关性判断，然后重新排序，留下最相关的前几条。

典型流程是：

```text
用户问题
  -> 第一阶段召回（向量检索 / 混合检索）
  -> 候选文档 topN
  -> 第二阶段重排（Rerank）
  -> 保留 topK
  -> 送给大模型生成答案
```

它的输入通常是：

- `query`
- 第一阶段召回得到的候选文档列表 `topN`

它的输出通常是：

- 每个候选文档的相关性分数
- 按分数重新排序后的文档列表

## 2. 为什么需要重排

只靠第一阶段召回，经常会出现“语义看起来像，但并不是真正相关”的情况。

例如查询：

```text
Python 异常处理最佳实践
```

向量召回结果可能是：

1. Python 异常处理语法
2. Java 异常处理最佳实践
3. Python 文件操作
4. Python 异常类型
5. Python 基础教程

这里的问题是：

- `Python` 和 `Java` 都属于“异常处理”语义域，容易被一起召回
- “异常处理”和“文件操作”在向量空间里可能也比较接近
- “基础教程”虽然和 Python 相关，但对当前问题不够聚焦

所以重排的意义就是：

- 把真正最相关的结果排到前面
- 压低语义相似但事实不对、主题漂移、层级不匹配的结果
- 提高最终送给生成模型的上下文质量

## 3. 它和向量召回的本质区别

### 3.1 向量召回：独立编码，再做匹配

向量召回通常是：

```text
q_vec = f(q)
d_vec = f(d)
score = sim(q_vec, d_vec)
```

这里的 `bi-encoder` 中，`bi` 指的是 `query` 和 `document` 两路独立编码，不是指 `bidirectional`。

也就是：

- query 单独编码成向量
- document 单独编码成向量
- 再在向量空间里比较相似度

它的优点是：

- 快
- 可借助 ANN 索引做大规模搜索
- 适合全库粗召回

它的短板是：

- query 和 doc 没有在 token 级做充分交互
- 对否定、数字、单位、版本号、实体关系等细节不够敏感
- 文档要被压缩成固定维度向量，存在信息瓶颈

### 3.2 Rerank：联合输入，直接判别相关性

Rerank 更接近：

```text
score = g(q, d)
```

这里的 `cross-encoder` 中，`cross` 指的是 `query` 和 `document` 放在一起做交叉式联合编码，而不是两路独立编码。

也就是：

- query 和 document 一起输入模型
- 模型直接判断“这条 doc 对当前 query 到底有多相关”

它的优点是：

- 精度更高
- 能建模 token 级交互
- 更适合处理复杂语义约束

它的代价是：

- 成本更高
- 不能拿来做全库首轮搜索
- 只能对有限候选做精排

这里“只能对有限候选做精排”背后的原因是：

- 向量召回可以提前把所有文档编码成向量，查询来了以后只需要做近邻检索
- rerank 不能这样提前把 `(query, doc)` 的联合判断结果预先算好
- 因为每次 query 变化后，都要重新对每一条候选文档做一次联合打分

也就是说，向量召回更像：

$$
q \rightarrow \mathbf{q}, \quad d \rightarrow \mathbf{d}, \quad \mathrm{score} = \mathrm{sim}(\mathbf{q}, \mathbf{d})
$$

而 rerank 更像：

$$
\mathrm{score} = g(q, d)
$$

这里的 $g(q,d)$ 必须对每个 `(query, doc)` 单独执行一次。

如果候选库有几十万、几百万甚至更多文档，那么：

- 全量跑 rerank 的计算成本和时延都太高
- 工程上无法作为首轮召回使用

所以它更适合的角色是：

- 第一阶段先用 embedding / BM25 / 混合检索，从全库里捞出少量候选
- 第二阶段再让 rerank 对这几十条候选做高精度排序

一句话理解就是：

- embedding 负责“从大库里快速捞人”
- rerank 负责“对已经入围的候选精确排座次”

因此工程上通常采用：

```text
先粗召回（几十条） -> 再重排（保留前几条）
```

## 4. 第二阶段重排常见的两类实现

### 4.1 本地重排

本地重排通常指不用专门的外部 rerank 模型，而是在已有召回结果基础上做进一步打分与重排。

常见做法包括：

- token 相似度重算
- 向量分数和词项分数做融合
- 结合 metadata / rank feature 做补分
- 阈值过滤、相对分差过滤

它的特点是：

- 成本低
- 可控性强
- 部署简单
- 精度通常不如专用 rerank 模型

适合：

- 预算有限
- 延迟要求高
- 已有混合检索体系，想先做轻量增强

### 4.2 模型重排

模型重排是使用专门的 reranker 模型对 `(query, doc)` 做联合打分。

常见类型包括：

- `cross-encoder reranker`：把 `query` 和 `doc` 一起输入编码模型，直接输出一个相关性分数，精度通常较高。
- `LLM reranker`：直接用大语言模型来判断候选文档是否相关，更强调“由 LLM 来完成重排”这件事。
- `生成式 reranker`：把重排改写成生成任务，例如让模型输出 `yes/no`、`relevant/irrelevant` 或等级分，再把输出映射成排序分数。

Qwen3 这里讨论的 `yes/no` 打分方式，不属于传统的 `cross-encoder reranker`；它更适合归类为 `LLM reranker` / `生成式 reranker`。不过从输入形式看，它和 `cross-encoder` 一样，都是把 `query` 与 `doc` 放在一起做联合建模。

它的特点是：

- 精度更高
- 对复杂语义更敏感
- 推理成本更高

适合：

- 候选集已经缩小到几十条以内
- 更关注答案质量
- 愿意为精排付出额外推理成本

## 5. rerank 训练整体链路：论文、Qwen3 仓库与 ms-swift 如何配合

这一节不再从“推理如何打分”切入，而是从训练角度把整条链路串起来：

- 论文里定义了什么
- `Qwen3-Embedding` 仓库提供了什么
- `ms-swift` 里真正是怎么训练起来的

### 面试总结

如果面试里要你用几句话讲清楚 `Qwen3 rerank` 的训练链路，可以这样回答：

- `Qwen3 rerank` 把重排定义成一个 `point-wise` 的 `yes/no` 二分类任务，训练目标是：

$$
L_{\mathrm{reranking}} = - \log p\bigl(l \mid \mathcal{P}(q, d)\bigr)
$$

- 它底层还是 `Transformer CausalLM`，不是传统分类头 reranker；只是把 `query + doc + instruction` 放进同一个上下文里，让模型判断下一个 token 更像 `yes` 还是 `no`。
- `Qwen3-Embedding` 主要提供论文、模型、推理示例和训练说明；真正执行训练的是 `ms-swift`。
- `ms-swift` 里通过 `task_type=generative_reranker` 把模型注册成生成式 reranker，再 patch `lm_head`，只保留 `yes/no` 两个 token 的打分。
- 训练时，`RerankerTrainer` 只取最后一个有效位置的输出，因为那里对应 assistant 即将输出第一个 token，也就是 `yes` 或 `no`。
- 训练时使用的主线是 `pointwise`，`ms-swift` 用 `pointwise_reranker` 去实现；框架也支持 `listwise_reranker`，但那是扩展能力，不等于主训练流程一定这样训练。
- 原始样本通常是“一个 query + 多个正负文档”，再由 collator 展开成带标签的训练样本。
- 如果继续追问模型合并，可以补一句：论文说 SFT 后还做了基于 `slerp` 的 checkpoint merge，但这个 `slerp` 合并细节没有在 `Qwen3-Embedding` 和 `ms-swift` 仓库里完整公开；`ms-swift` 里的 `merge_lora` 不是同一个概念。

### 5.1 先看论文：Qwen3 是怎么定义 rerank 训练任务的

论文里和训练最相关的内容主要有三层。

第一层是任务形式。论文在模型架构部分明确说：

- reranking 使用 `LLM`
- 在单个上下文中做 `point-wise reranking`
- 把相似性判断写成 `binary classification problem`

这句话的含义是：

- 每次训练看的不是一组候选一起排序
- 而是单独拿一个 `(query, doc)` 对来判断
- 标签只有两类：
  - 相关
  - 不相关

第二层是打分方式。论文在模型架构部分还明确说：

- 对输入 `Instruction + Query + Document`
- 评估下一个 token 是 `yes` 或 `no` 的可能性
- 再据此得到相关性分数

也就是说，论文里的 Qwen3 rerank 从一开始就是“生成式 yes/no 判别”。

第三层是训练目标。论文在训练目标部分写的是：

$$
L_{\mathrm{reranking}} = - \log p\bigl(l \mid \mathcal{P}(q, d)\bigr)
$$

其中：

- $\mathcal{P}(q, d)$ 表示包装好的输入模板
- `l` 是标签
- 正样本时 $l = \mathrm{yes}$
- 负样本时 $l = \mathrm{no}$

所以从论文角度看，Qwen3 rerank 的训练本质是：

- 一个 `pointwise` 的 `yes/no` 判别任务

另外，论文还提到：

- reranker 的训练采用两阶段方案：
  - 高质量监督微调
  - 模型合并
- reranker 不包含 embedding 那种第一阶段弱监督预训练

这一点和 embedding 模型的训练路径是不同的。

这里的“模型合并”，论文明确提到使用的是 `slerp`，也就是 `Spherical Linear Interpolation`，中文一般翻译为“球面线性插值”。

它的核心思想是：

- 不直接只用某一个 checkpoint
- 也不是简单地把多个 checkpoint 做普通加权平均
- 而是在参数空间中，沿着两个向量之间更平滑的“球面路径”做插值

如果是普通线性插值，公式通常写成：

$$
\mathrm{lerp}(\mathbf{w}_1, \mathbf{w}_2; t) = (1 - t)\mathbf{w}_1 + t\mathbf{w}_2
$$

其中：

- $\mathbf{w}_1, \mathbf{w}_2$ 表示两个 checkpoint 的参数向量
- $t \in [0, 1]$ 表示插值系数

而 `slerp` 的公式是：

$$
\mathrm{slerp}(\mathbf{w}_1, \mathbf{w}_2; t)
=
\frac{\sin((1-t)\theta)}{\sin\theta}\mathbf{w}_1
+
\frac{\sin(t\theta)}{\sin\theta}\mathbf{w}_2
$$

其中：

$$
\theta = \arccos\left(\frac{\mathbf{w}_1 \cdot \mathbf{w}_2}{\|\mathbf{w}_1\|\|\mathbf{w}_2\|}\right)
$$

这里的 $\theta$ 表示两个参数向量之间的夹角。

可以把它直观理解成：

- `lerp` 是在两个点之间走直线
- `slerp` 是在归一化后的球面上沿弧线移动

在模型合并场景里，使用 `slerp` 的目的通常是：

- 更平滑地融合多个 checkpoint
- 尽量保留不同 checkpoint 的有用方向信息
- 提升最终模型在不同数据分布下的鲁棒性和泛化能力

所以论文里说的模型合并，可以理解成：

$$
\text{多个 SFT checkpoint}
\xrightarrow{\text{slerp}}
\text{一个更稳健的最终模型}
$$

不过要注意：

- 论文说明了它使用 `slerp` 做模型合并
- 但没有公开展开到“具体选哪些 checkpoint、插值系数如何设置、是否分阶段多次合并”的实现细节
- `ms-swift` 里常见的 `merge_lora` 也不是这里说的 `slerp` checkpoint merge，它们是两件不同的事

### 5.2 再看 Qwen3-Embedding 仓库：它提供了什么

`Qwen3-Embedding` 仓库没有把完整训练框架都写在 examples 里，它主要提供三类东西：

1. 论文与技术说明  
- 告诉你 rerank 的设计思想、输入模板和训练目标

2. 推理示例  
- 如 `examples/qwen3_reranker_transformers.py`
- 这类文件主要用于说明：
  - 训完以后如何打分
  - 如何从最后一个位置取 `yes/no`
- 它们不是完整训练实现

3. 训练说明  
- `docs/training/SWIFT.md`
- 告诉你官方推荐通过 `swift sft` 来训练

所以可以把 `Qwen3-Embedding` 仓库理解成：

- 论文 + 模型 + 推理示例 + 训练入口说明

而真正执行训练的代码，是交给 `ms-swift` 的。

### 5.3 训练入口：ms-swift 从命令行是怎么开始的

如果看 `ms-swift` 本地源码，Qwen3 reranker 的官方训练脚本是：

- [qwen3_reranker.sh](/Users/songxijun/workspace/otherProject/ms-swift/examples/train/reranker/qwen3/qwen3_reranker.sh)

如果直接看官方示例脚本，[qwen3_reranker.sh](/Users/songxijun/workspace/otherProject/ms-swift/examples/train/reranker/qwen3/qwen3_reranker.sh#L1) 写的是：

```bash
# 2*20GiB
# 表示示例大致按 2 张 20GiB 显存的卡来配置

# losses: swift/loss
# 提醒你对应的 loss 实现在 ms-swift/swift/loss 目录

CUDA_VISIBLE_DEVICES=0,1 \
# 指定使用第 0、1 张 GPU

NPROC_PER_NODE=2 \
# 当前机器上启动 2 个训练进程，通常对应 2 张卡各 1 个进程

swift sft \
# 使用 ms-swift 的 SFT 训练入口启动训练

    --model Qwen/Qwen3-Reranker-4B \
# 基座模型，使用 Qwen3-Reranker-4B

    --task_type generative_reranker \
# 任务类型设为“生成式 reranker”
# 这会触发 ms-swift 走 generative_reranker 的那套 trainer/model patch 逻辑

    --loss_type pointwise_reranker \
# 损失函数设为 pointwise reranker
# 表示把每个 (query, doc) 单独看成一个 0/1 判别样本来训练

    --tuner_type lora \
# 微调方式使用 LoRA，而不是全参数微调

    --lora_rank 8 \
# LoRA 的秩 r，控制低秩增量矩阵的容量

    --lora_alpha 32 \
# LoRA 的缩放系数，通常和 rank 配合控制更新幅度

    --learning_rate 5e-5 \
# 学习率

    --target_modules all-linear \
# 对所有线性层注入 LoRA

    --dataset MTEB/scidocs-reranking \
# 训练数据集，这里用的是 MTEB 中的 scidocs-reranking 数据

    --attn_impl flash_attn \
# 注意力实现使用 FlashAttention，以提升速度并节省显存

    --padding_free true \
# 启用 padding-free 训练，尽量减少 padding 带来的显存和算力浪费

    --torch_dtype bfloat16 \
# 模型训练使用 bfloat16 精度

    --load_from_cache_file true \
# 允许优先从缓存加载数据集处理结果，减少重复预处理开销

    --split_dataset_ratio 0.02 \
# 从训练数据中切出 2% 作为验证集

    --eval_strategy steps \
# 按训练 step 周期性做评估

    --output_dir output \
# 训练输出目录

    --save_steps 50 \
# 每 50 个 step 保存一次 checkpoint

    --eval_steps 50 \
# 每 50 个 step 做一次验证

    --save_total_limit 2 \
# 最多保留 2 个 checkpoint，避免占用过多磁盘

    --logging_steps 5 \
# 每 5 个 step 打一次日志

    --num_train_epochs 1 \
# 训练 1 个 epoch

    --max_length 4096 \
# 单条样本的最大 token 长度

    --per_device_train_batch_size 1 \
# 每张卡上的训练 batch size 为 1

    --per_device_eval_batch_size 1 \
# 每张卡上的验证 batch size 为 1

    --gradient_accumulation_steps 8 \
# 梯度累计 8 步
# 因此等效总 batch 会比单卡 batch_size=1 更大

    --dataloader_num_workers 4 \
# dataloader 使用 4 个 worker 进程

    --dataset_num_proc 4 \
# 数据集预处理使用 4 个并行进程

    --warmup_ratio 0.05 \
# 学习率 warmup 比例为 5%

    --dataloader_drop_last true \
# dataloader 丢弃最后一个不完整 batch

    --deepspeed zero2
# 使用 DeepSpeed ZeRO-2 做显存优化
```

- 最关键的参数有三个：

- `--model Qwen/Qwen3-Reranker-4B`
- `--task_type generative_reranker`
- `--loss_type pointwise_reranker`

这三个参数分别决定了：

- 训练对象是谁  
  `Qwen3-Reranker`

- 任务按什么方式组织  
  `generative_reranker`

- 损失按什么方式计算  
  `pointwise_reranker`

这一层已经说明：

- 训练主体不是 examples 脚本
- 而是 `swift sft` 这套训练框架

如果把它按训练意义重新概括，可以拆成 4 组参数：

- 任务定义相关：
  - `--model`
  - `--task_type`
  - `--loss_type`

- 微调方式相关：
  - `--tuner_type`
  - `--lora_rank`
  - `--lora_alpha`
  - `--target_modules`

- 数据与训练过程相关：
  - `--dataset`
  - `--max_length`
  - `--per_device_train_batch_size`
  - `--gradient_accumulation_steps`
  - `--num_train_epochs`
  - `--learning_rate`
  - `--warmup_ratio`

- 工程加速与资源相关：
  - `CUDA_VISIBLE_DEVICES`
  - `NPROC_PER_NODE`
  - `--attn_impl`
  - `--padding_free`
  - `--torch_dtype`
  - `--deepspeed`

### 5.4 trainer 是怎么选出来的

`ms-swift` 会先根据 `task_type` 选择 trainer。

对应代码：

- [trainer_factory.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/trainers/trainer_factory.py#L13)

这里能看到：

- `reranker -> RerankerTrainer`
- `generative_reranker -> RerankerTrainer`

这说明：

- 普通 reranker 和生成式 reranker 共用一套 trainer 外壳
- 两者真正的差别，不在 trainer 类名
- 而在模型输出的组织方式和 loss 的定义方式

### 5.5 为什么 Qwen3 的 rerank 训练还是 CausalLM

这一步在：

- [model_meta.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/model/model_meta.py#L301)

这里有个重要分叉：

- `reranker`
  - 默认会走分类式思路
  - 往往需要 `num_labels`

- `generative_reranker`
  - 明确设置 `num_labels = None`
  - 表示它不走传统分类头
  - 而是保留 `CausalLM` 结构

这和论文的设计完全一致：

- Qwen3 rerank 不是“给编码器加个分类头”
- 而是“保留生成式 LLM，再把它用在 yes/no 判别上”

### 5.6 最关键的一步：ms-swift 如何把 CausalLM 变成生成式 reranker

这一步是整个链路里最重要的实现点。

对应代码：

- [register.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/model/register.py#L319)

当模型被识别为 `generative_reranker` 时，`ms-swift` 会调用：

- `_patch_generative_reranker()`

真正 patch 的位置在：

- [register.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/model/register.py#L325)

它做了这样一件事：

- 拿到 tokenizer
- 拿到模型的 `lm_head`
- 重写 `lm_head` 的 forward

也就是说，模型虽然还是 `CausalLM`，但它最后一层输出的解释方式被改了。

这里的 `lm_head` 可以理解成 `CausalLM` 最后的输出层，它在整个流程里的位置是：

$$
\text{input ids}
\rightarrow
\text{token embedding}
\rightarrow
\text{Transformer blocks}
\rightarrow
\text{hidden states}
\rightarrow
\text{lm\_head}
\rightarrow
\text{logits}
$$

也就是说：

- 前面的 `Transformer blocks` 负责建模上下文
- `lm_head` 负责把最后的 hidden states 映射成输出分数
- 它处在整个模型的最后一层输出位置

这里说的“重写 `lm_head` 的 forward”，意思不是改动整个 Transformer 主干，而是：

- 保留前面的 `Transformer blocks`
- 只替换最后这层 `lm_head` 的前向计算逻辑
- 让它不再输出“整个词表上的 logits”
- 而是直接输出 rerank 任务需要的 `yes/no` 相关分数

### 5.7 `yes/no` 分数具体是怎么从模型里拿出来的

被 `_patch_generative_reranker()` 调用的核心函数在：

- [torch_utils.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/utils/torch_utils.py#L294)

它的核心逻辑可以概括成 5 步：

1. 读取正负标签 token  
- 默认正例 token 是 `yes`
- 默认负例 token 是 `no`

2. 找到这两个 token 在词表里的 id

3. 从 `lm_head_weight` 中只抽出 `yes/no` 这两个 token 对应的权重

4. 用这两个权重对 hidden states 做线性投影

5. 返回一个单分数：

$$
z = \mathrm{logit}_{\mathrm{yes}} - \mathrm{logit}_{\mathrm{no}}
$$

这一点非常关键。

原始 `CausalLM` 本来会输出：

$$
\text{logits over the whole vocabulary}
$$

但在 `generative_reranker` 模式下，`ms-swift` 主动把它压缩成：

$$
\mathrm{logit}_{\mathrm{yes}} - \mathrm{logit}_{\mathrm{no}}
$$

所以从训练视角看，模型最终学的不是“整个词表该怎么分布”，而是：

- 正样本时，让 `yes` 比 `no` 更强
- 负样本时，让 `no` 比 `yes` 更强

### 5.8 数据是怎么组织的

在 `ms-swift` 中，reranker 的原始训练样本一般不是单条 `(q, d)`，而是：

- 一个 query
- 若干正例文档
- 若干负例文档

官方说明文档：

- [Reranker.md](/Users/songxijun/workspace/otherProject/ms-swift/docs/source/BestPractices/Reranker.md#L69)

字段是：

- `messages`
- `positive_messages`
- `negative_messages`

所以原始样本更接近：

$$
\text{query} + \text{positive set} + \text{negative set}
$$

而不是立即就是训练时的一条 pair。

### 5.9 数据是怎么展开成训练 batch 的

真正把原始样本展开成训练 batch 的地方在：

- [template/base.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/template/base.py#L1651)

`_reranker_data_collator()` 会做这些事：

1. 读取环境变量  
- `MAX_POSITIVE_SAMPLES`
- `MAX_NEGATIVE_SAMPLES`

2. 对每个 query：
- 采样若干正例
- 采样若干负例

3. 把它们展开成训练样本  
- 正例标 `1`
- 负例标 `0`

4. 把展开后的样本放进同一个 batch

所以训练时真正送进模型的，已经变成：

$$
\{(q_i, d_i, y_i)\}_{i=1}^{N}, \quad y_i \in \{0, 1\}
$$

如果后面使用 `listwise`，这些样本在 batch 中仍然保留“一个正例在前、多个负例在后”的组结构，方便组内计算 loss。

### 5.10 trainer 在训练时取模型哪个位置

训练主逻辑在：

- [reranker_trainer.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/trainers/reranker_trainer.py#L17)

这里最关键的是：

- 先执行 `outputs = model(**inputs)`
- 如果 `task_type == generative_reranker`
- 就只取最后一个有效位置的 logits

核心代码是：

```python
last_valid_indices = -1 if attention_mask is None else get_last_valid_indices(attention_mask)
batch_indices = torch.arange(logits.shape[0], device=logits.device)
outputs.logits = logits[batch_indices, last_valid_indices]
```

这一步的含义是：

- 不拿整段每个位置都算 loss
- 只拿最后一个有效位置

原因是：

- 这个位置正好对应“assistant 即将输出第一个 token”
- 而对于 Qwen3 rerank，这个 token 就应该是 `yes` 或 `no`

所以训练时这一步和论文里的 yes/no 任务形式是直接对应的。

### 5.11 pointwise loss 是怎么实现的

loss 的映射关系在：

- [mapping.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/loss/mapping.py#L6)

这里能看到：

- `pointwise_reranker -> PointwiseRerankerLoss`
- `listwise_reranker -> ListwiseRerankerLoss`

真正的 pointwise 实现在：

- [reranker.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/loss/reranker.py#L12)

它做的事非常直接：

1. 取 `outputs.logits`
2. 把它压成单列分数
3. 把标签转成浮点型
4. 用 `BCEWithLogitsLoss`

这意味着：

- 输入是一条 `(query, doc)` 的单分数
- 标签是 `0/1`
- 正样本希望分数更大
- 负样本希望分数更小

如果把这个分数记作：

$$
z = \mathrm{logit}_{\mathrm{yes}} - \mathrm{logit}_{\mathrm{no}}
$$

那么：

- 正样本时，希望 `z` 尽量大
- 负样本时，希望 `z` 尽量小

`PointwiseRerankerLoss` 在代码里虽然直接调用的是 `BCEWithLogitsLoss`，但它对应的数学形式可以写成：

$$
\mathcal{L}_{\mathrm{BCE}}(z, y)
=
- \Bigl[
y \log \sigma(z) + (1-y)\log\bigl(1-\sigma(z)\bigr)
\Bigr]
$$

其中：

$$
\sigma(z) = \frac{1}{1 + e^{-z}}
$$

这里：

- $z$ 是模型输出的单分数
- $y \in \{0, 1\}$ 是标签
- 当 $y = 1$ 时，表示正样本
- 当 $y = 0$ 时，表示负样本

这个点很重要：

- `PointwiseRerankerLoss` 不是“只做一个 sigmoid 就结束了”
- 它的本质是：先对分数 $z$ 做 `sigmoid`，再计算二分类交叉熵
- 只是代码实现里没有把这两步拆开手写，而是直接用 `BCEWithLogitsLoss` 一步完成
- `BCEWithLogitsLoss` 可以理解成“`sigmoid + binary cross entropy` 的数值稳定封装”

把两种情况分别展开，就是：

正样本时：

$$
\mathcal{L}(z, 1) = - \log \sigma(z)
$$

负样本时：

$$
\mathcal{L}(z, 0) = - \log \bigl(1-\sigma(z)\bigr)
$$

而由于这里

$$
z = \mathrm{logit}_{\mathrm{yes}} - \mathrm{logit}_{\mathrm{no}}
$$

所以：

- 当 $z$ 越大，模型越倾向于 `yes`
- 当 $z$ 越小，模型越倾向于 `no`

这和论文中的：

$$
- \log p\bigl(l \mid \mathcal{P}(q, d)\bigr)
$$

在目标上是一致的。更具体地说：

- 正样本时，对应的是

$$
- \log p\bigl(\mathrm{yes} \mid \mathcal{P}(q, d)\bigr)
$$

- 负样本时，对应的是

$$
- \log p\bigl(\mathrm{no} \mid \mathcal{P}(q, d)\bigr)
$$

区别只是：

- 论文给的是数学定义
- `ms-swift` 给的是工程实现

### 5.12 listwise loss 为什么也会出现

Qwen3 论文主文描述的是 pointwise 风格，但 `ms-swift` 框架还额外支持 `listwise`。

实现位置：

- [reranker.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/loss/reranker.py#L23)

它的思路是：

1. 在 batch 中找到正样本位置
2. 以正样本为起点划分组
3. 每组默认是：
   - 第一个样本为正例
   - 后面跟若干负例
4. 对组内所有分数做 `CrossEntropyLoss`
5. 目标是让正例在组内得分最高

所以：

- `pointwise` 学的是：这条文档是否相关
- `listwise` 学的是：这一组候选里谁应该排第一

要特别区分：

- 论文主文并没有说 Qwen3 一定用 listwise
- `listwise` 是 `ms-swift` 提供的扩展训练方式

### 5.13 训练指标是怎么做的

训练时的预测和指标逻辑在：

- [mixin.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/trainers/mixin.py#L1045)

对 reranker / generative_reranker：

- 如果是 `listwise_reranker`
  - 会恢复组内预测

- 否则默认：

$$
\hat{y} = \mathbb{1}(z > 0)
$$

这正好对应前面的 `yes-no` 分数：

- 如果 `yes` 比 `no` 更大
- 那么分数就大于 0
- 模型就判为正类

### 5.14 最终把整条训练链路串起来

到这里，可以把整条 rerank 训练链路串成一句完整的话：

$$
\text{论文定义 pointwise 的 yes/no 训练目标}
\rightarrow
\text{Qwen3-Embedding 提供模型说明、推理示例与 SWIFT 训练入口}
\rightarrow
\text{ms-swift 负责真正训练：数据展开} \rightarrow \text{CausalLM patch} \rightarrow \text{最后位置 logits} \rightarrow \text{pointwise/listwise loss}
$$

如果按执行顺序展开，可以写成：

1. 用 `swift sft` 启动训练  
2. 指定 `task_type=generative_reranker`  
3. `TrainerFactory` 选择 `RerankerTrainer`  
4. 模型保留 `CausalLM` 结构  
5. `register.py` patch `lm_head`，只保留 `yes/no` 分数  
6. `template/base.py` 把原始正负样本展开  
7. `RerankerTrainer` 只取最后一个有效位置  
8. `loss/reranker.py` 用 pointwise 或 listwise 计算 loss  

### 5.15 哪些文件最值得优先读

如果你后面还要继续自己读源码，最值得优先读的是这几处：

- 训练脚本入口  
  [qwen3_reranker.sh](/Users/songxijun/workspace/otherProject/ms-swift/examples/train/reranker/qwen3/qwen3_reranker.sh)

- 官方 reranker 说明  
  [Reranker.md](/Users/songxijun/workspace/otherProject/ms-swift/docs/source/BestPractices/Reranker.md)

- trainer 选择逻辑  
  [trainer_factory.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/trainers/trainer_factory.py)

- generative_reranker 的模型 patch  
  [register.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/model/register.py)

- `yes/no` 分数生成  
  [torch_utils.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/utils/torch_utils.py)

- 训练时的 logits 裁剪  
  [reranker_trainer.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/trainers/reranker_trainer.py)

- loss 实现  
  [reranker.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/loss/reranker.py)

- 数据展开  
  [template/base.py](/Users/songxijun/workspace/otherProject/ms-swift/swift/template/base.py#L1651)

## 6. Rerank 推理整体链路：Qwen3 仓库与 vLLM 如何配合

这一节沿用前面训练链路的写法，只是把重点从“怎么训练”换成“怎么打分”。

### 面试总结

如果面试里要你简要说明 `Qwen3 rerank` 的 vLLM 推理逻辑，可以这样回答：

- `Qwen3 rerank` 推理时不会生成长答案，而是把 `query + document + instruction` 放进同一个上下文里，只判断下一 token 更像 `yes` 还是 `no`。
- 在 vLLM 里，这件事是通过 `SamplingParams(max_tokens=1, allowed_token_ids=[yes, no])` 实现的，也就是只允许模型生成一个 token，并且这个 token 只能从 `yes/no` 里选。
- 模型返回后，代码会取最后一步里 `yes` 和 `no` 的 logprob，再把它们做归一化。
- 最终得到的分数本质上就是：

$$
p(\mathrm{yes} \mid q, d)
$$

- 这个概率就被当作 rerank score，分数越高表示文档越相关。

### 6.1 先看 Qwen3-Embedding 仓库：它同时给了 transformers 与 vLLM 两种推理示例

Qwen3 官方仓库里，和 rerank 推理最相关的两个示例是：

- [qwen3_reranker_transformers.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_transformers.py#L1)
- [qwen3_reranker_vllm.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_vllm.py#L1)

前者更适合理解模型原理，后者更适合解释：

- 如果实际部署时走 `vLLM`
- `Qwen3 reranker` 是怎么做推理的

这一节后面都以 `vLLM` 的推理路径为主。

### 6.2 在 vLLM 示例里，一条样本是怎么组织的

在 `qwen3_reranker_vllm.py` 里，每条样本本质上仍然是：

$$
(q, d)
$$

只是会先被包装成聊天模板。

对应代码在：

- [qwen3_reranker_vllm.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_vllm.py#L50)

它会把输入组织成：

- `system`：要求模型只能回答 `yes` 或 `no`
- `user`：包含 `Instruct + Query + Document`

也就是说，输入本质上还是：

$$
\text{Instruct} + \text{Query} + \text{Document}
$$

只是被放进了 chat template 中。

### 6.3 vLLM 推理时，模型和参数是怎么初始化的

vLLM 示例里最关键的初始化在：

- [qwen3_reranker_vllm.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_vllm.py#L28)

这里做了几件重要的事：

1. 加载 tokenizer  
2. 记录 `yes/no` 对应 token id  
3. 构造 `SamplingParams`  
4. 初始化 `LLM(...)`

这里最关键的是 `SamplingParams`：

```python
self.sampling_params = SamplingParams(
    temperature=0,
    top_p=0.95,
    max_tokens=1,
    logprobs=20,
    allowed_token_ids=[self.true_token, self.false_token],
)
```

它的含义是：

- `temperature=0`
  - 让输出尽可能走确定性路径
- `max_tokens=1`
  - 只生成 1 个 token
- `allowed_token_ids=[yes, no]`
  - 明确限制模型只能在 `yes/no` 两个 token 里选
- `logprobs=20`
  - 返回候选 token 的对数概率，方便后面手动取分数

这一步很关键，因为它说明：

- vLLM 推理时并不是让模型自由长生成
- 而是把生成空间限制成 `yes/no` 二选一

### 6.4 vLLM 推理时，一条样本如何进入模型

在示例里，输入会先经过：

- `tokenizer.apply_chat_template(...)`

对应代码在：

- [qwen3_reranker_vllm.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_vllm.py#L60)

然后它会：

1. 把聊天模板转成 token ids  
2. 截断到最大长度  
3. 在末尾补上 assistant 的起始后缀  
4. 包装成 `TokensPrompt`

所以真正送进 vLLM 的，不是原始字符串，而是：

$$
\text{prompt token ids}
$$

这一点和前面的训练逻辑是呼应的：

- 训练时要把 `query + doc` 组织成模型能学习 `yes/no` 的格式
- 推理时也要把它组织成模型能在最后一步输出 `yes/no` 的格式

### 6.5 vLLM 推理时，是怎么得到 yes/no 分数的

推理主逻辑在：

- [qwen3_reranker_vllm.py](/Users/songxijun/workspace/otherProject/Qwen3-Embedding/examples/qwen3_reranker_vllm.py#L65)

关键调用是：

```python
outputs = self.lm.generate(messages, self.sampling_params, use_tqdm=False)
```

这里虽然调用的是 `generate`，但要注意：

- 它不是在做长文本生成
- 因为 `max_tokens=1`
- 而且 `allowed_token_ids` 已经限制成 `yes/no`

所以这一步本质上是在问模型：

$$
\text{下一 token 更像 yes 还是 no?}
$$

随后代码会从返回结果里取：

```python
final_logits = outputs[i].outputs[0].logprobs[-1]
```

这里拿到的不是整段文本，而是最后一步候选 token 的对数概率信息。

然后再分别读取：

- `yes` 的 logprob
- `no` 的 logprob

### 6.6 vLLM 推理时，最终分数是怎么计算出来的

示例代码后面会做：

```python
true_score = math.exp(true_logit)
false_score = math.exp(false_logit)
score = true_score / (true_score + false_score)
```

对应的数学形式就是：

$$
\mathrm{score}
=
\frac{\exp(\mathrm{logit}_{\mathrm{yes}})}
{\exp(\mathrm{logit}_{\mathrm{yes}}) + \exp(\mathrm{logit}_{\mathrm{no}})}
$$

也可以理解成：

$$
\mathrm{score} = p(\mathrm{yes} \mid q, d)
$$

这个分数有几个特点：

- 范围在 $(0,1)$
- 越接近 1，表示越相关
- 越接近 0，表示越不相关

所以从 vLLM 推理的视角看，Qwen3 reranker 的核心并不是“生成一句回答”，而是：

- 拿到 `yes/no` 两个候选的概率
- 把 `yes` 的概率当成相关性分数

### 6.7 把整条 rerank 推理链路串起来

到这里，可以把整条推理链路概括成一句完整的话：

$$
\text{构造 } (q, d) \text{ 输入}
\rightarrow
\text{按 chat template 编码}
\rightarrow
\text{限制只生成 1 个 token，且只能是 yes/no}
\rightarrow
\text{读取 yes/no 的 logprob}
\rightarrow
\text{把 yes 概率转成最终 rerank score}
$$

如果按执行顺序拆开，可以写成：

1. 组织 `instruction + query + document`  
2. 用 chat template 转成 token 序列  
3. 用 `TokensPrompt` 送入 vLLM  
4. 设置 `max_tokens=1`  
5. 设置 `allowed_token_ids=[yes, no]`  
6. 调用 `generate(...)`  
7. 从返回结果中取 `yes/no` 的 logprob  
8. 计算 `yes` 的归一化概率作为分数  

### 6.8 训练链路和推理链路的对比

| 对比项 | 训练链路 | 推理链路 |
| --- | --- | --- |
| 目标 | 让模型学会如何判断相关性 | 用已经训练好的模型输出相关性分数 |
| 输入组织 | 一个 query 搭配多个正负文档，再展开成训练样本 | 通常直接输入单个 `(query, doc)` |
| 是否有标签 | 有，标签通常是 $y \in \{0,1\}$ | 没有标签 |
| 模型输出关注点 | 关注 `yes/no` 对应的分数差 | 关注 `yes` 的最终概率或相关性分数 |
| 关键中间量 | $$z = \mathrm{logit}_{\mathrm{yes}} - \mathrm{logit}_{\mathrm{no}}$$ | $$p(\mathrm{yes}\mid q,d)$$ |
| 最后一个位置 | 只取最后一个有效位置，用来和标签计算 loss | 只取最后一个有效位置，用来生成最终 score |
| 后处理 | 送入 `PointwiseRerankerLoss` 或 `ListwiseRerankerLoss` | 做归一化，得到 $(0,1)$ 区间分数 |
| 是否计算 loss | 计算 | 不计算 |
| 是否反向传播 | 会做 `backward` 更新参数 | 不做反向传播 |
| 参数是否变化 | 会更新模型参数 | 不更新模型参数 |
| 典型实现入口 | `swift sft`、`RerankerTrainer`、`PointwiseRerankerLoss` | `qwen3_reranker_vllm.py`、`LLM.generate(...)` |
| 最终产物 | 一个训练好的 reranker 模型 | 一组 rerank score |

## 7. 第二阶段重排的工程含义

第二阶段重排解决的是 `Precision@TopK` 问题，也就是：

- 候选里可能已经有正确答案
- 但顺序还不够好
- 需要把真正最相关的几条推到最前面

它不能解决的是：

- 第一阶段完全没召回到正确文档

也就是说：

- 召回负责把正确答案“捞进来”
- 重排负责把正确答案“排靠前”

如果首轮召回没有真阳性，重排再强也无能为力。

## 8. 什么时候该优先上 rerank

比较适合上 rerank 的场景：

- `top_k` 需要取得比较大
- 召回结果里噪声较多
- 查询里有否定、数字、单位、版本号、实体歧义
- 对最终回答质量要求高

一般经验上：

- 小规模、简单问答：可以先只做召回
- 候选超过十条后：通常值得加 rerank
- 如果预算允许：优先让 rerank 处理几十条候选，再保留前几条给生成模型

## 9. 一句话总结

第二阶段重排的本质是：

- 第一阶段先把“可能相关”的文档找出来
- 第二阶段再用更强的判别能力对这些候选做精排

而像 Qwen3 这样的生成式 rerank，本质上是：

- 把 `query + doc` 一起送进模型
- 不让它长生成
- 只看它下一步更想输出 `yes` 还是 `no`
- 用这个倾向作为相关性分数
