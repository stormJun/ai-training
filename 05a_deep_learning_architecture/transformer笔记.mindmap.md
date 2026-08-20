---
title: Transformer 与 MiniMind 系统复习导图
markmap:
  colorFreezeLevel: 2
  maxWidth: 300
---

# Transformer 与 MiniMind 系统复习

## 1. 全局主线

### 核心任务
- 因果语言建模
  - 输入：已知 token 序列
  - 目标：预测下一个 token
  - 约束：不能读取未来 token
- 同一主干，两种用法
  - 训练：并行预测多个位置
  - 推理：每轮产生一个新 token
  - 模型结构相同
  - 参数状态不同
    - 训练：计算梯度并更新
    - 推理：参数冻结

### 七阶段数据流
- 阶段1：文本表示
  - `Tokenizer -> token ids`
  - `Embedding -> token vectors`
  - 位置信息
- 阶段2：堆叠 $L$ 个 Decoder Block
  - Attention：跨 token 交互
  - MLP：单 token 特征加工
  - 残差 + Norm：保持信息与稳定优化
- 阶段3：上下文表示 $H$
  - 每个 token 得到因果上下文向量
- 阶段4：`LM Head`
  - 隐藏空间 $D \rightarrow$ 词表空间 $V$
- 阶段5：概率、损失或采样
  - 训练：交叉熵
  - 推理：选择新 token
- 阶段6：训练闭环
  - `Loss -> backward -> optimizer.step()`
- 阶段7：自回归生成
  - `prefill -> decode -> append -> repeat`

### 形状不变骨架
- 经典列向量写法
  - $X\in\mathbb{R}^{D\times N}$
  - 每列是一个 token
- PyTorch 写法
  - `hidden_states [B,T,D]`
  - $B$：batch size
  - $T$：序列长度
  - $D$：hidden size
- Block 输入输出
  - `[B,T,D] -> [B,T,D]`
  - 残差加法要求形状一致
  - 堆叠只改变数值，不改变主形状

### MiniMind 调用链
- `tokenizer / chat_template`
  - 生成 `input_ids [B,T]`
- `MiniMindModel`
  - Embedding
  - $L=8$ 个 Block
  - final RMSNorm
- `MiniMindForCausalLM`
  - `lm_head`
  - loss
  - `generate()`
- 默认维度
  - `vocab_size=6400`
  - `hidden_size=768`
  - `Hq=8`
  - `Hkv=4`
  - `head_dim=96`
  - `intermediate_size=2432`

## 2. 输入表示与位置

### Tokenizer：文本到 id
- 职责
  - 切分文本
  - 子词合并
  - token 映射为整数 id
- 常见算法
  - BPE：合并高频相邻符号
  - WordPiece：用频率分数选择合并
    - $\operatorname{score}(A,B)=\frac{\operatorname{freq}(AB)}{\operatorname{freq}(A)\operatorname{freq}(B)}$
  - Unigram：从大词表逐步裁剪
- 实际切词的不确定性
  - 空格可能并入 token
  - 一个词可能拆成多个 token
  - 笔记中的 `it/eats/apple` 只是矩阵示意
- MiniMind 落点
  - `model/tokenizer.json`
  - BBPE / ByteLevel
  - 词表 6400
  - 对话控制符占用预留 id
  - `tokenizer_config.json`
    - 包含 `chat_template`

### Embedding：id 到向量
- 参数表
  - 经典示意：`[50000,128]`
  - MiniMind：`[6400,768]`
- 数学本质
  - `weight[input_ids]`
  - 是索引查表，不是矩阵乘法
- 输出形状
  - `input_ids [B,T]`
  - `hidden_states [B,T,D]`
- 训练特性
  - Embedding 是可学习参数
  - 本 batch 只更新查过的行
- MiniMind 落点
  - `nn.Embedding(vocab_size, hidden_size)`
  - 查表后进入 dropout
  - 默认 `dropout=0.0`

### 经典正弦位置编码
- 直接加入残差流
  - $X=\operatorname{Embedding}(token)+PE$
- 公式
  - $PE(pos,2i)=\sin\left(pos/10000^{2i/D}\right)$
  - $PE(pos,2i+1)=\cos\left(pos/10000^{2i/D}\right)$
- 特性
  - 值域有界
  - 多频率表示多尺度位置
  - $PE(pos+k)=R(k)PE(pos)$
  - 无可学习位置参数
- 边界
  - 可计算超长位置
  - 不保证超出训练长度后可靠外推

### RoPE：位置进入 Q/K
- 核心改变
  - 不把位置向量加到 Embedding
  - 每层 Attention 内旋转 Q/K
  - V 不参与旋转
- 二维旋转
  - $(x,y)\mapsto(x\cos\theta-y\sin\theta,\ x\sin\theta+y\cos\theta)$
  - 角度由 token 位置与频率决定
- 为什么只旋转 Q/K
  - Q/K 决定位置匹配分数
  - V 是匹配后被加权汇总的内容
- 形状
  - RoPE 宽度是 `head_dim=96`
  - 不是 `hidden_size=768`
- MiniMind 落点
  - 预计算 `freqs_cos/freqs_sin`
  - `apply_rotary_pos_emb(q,k,cos,sin)`
  - `start_pos` 切片配合 KV Cache
  - 可选 YaRN 频率缩放
    - 只在 `inference_rope_scaling=True` 启用

### 经典 PE 与 RoPE 对比
- 注入位置
  - 经典 PE：Embedding 后相加
  - RoPE：Attention 内旋转 Q/K
- 作用宽度
  - 经典 PE：$D$
  - RoPE：`head_dim`
- 相对位置
  - 经典 PE：需由模型学习利用
  - RoPE：Q/K 点积自然带相对旋转关系

## 3. 因果自注意力

### Q/K/V 投影
- 不是直接切分 hidden 维度
- 每个头从完整 token 向量独立投影
  - $Q=XW_Q$
  - $K=XW_K$
  - $V=XW_V$
- 语义分工
  - Q：当前位置想查询什么
  - K：每个位置提供什么索引
  - V：真正被汇总的内容

### Scaled Dot-Product Attention
- 标准行向量公式
  - $A=\operatorname{Softmax}\left(QK^{\mathsf T}/\sqrt{d_k}+M\right)$
  - $O=AV$
- 笔记列向量公式
  - $A=\operatorname{Softmax}_{rows}\left(Q^{\mathsf T}K/\sqrt{d_k}+M\right)$
  - $O=VA^{\mathsf T}$
- 缩放项
  - 分母：$\sqrt{d_k}$
  - 目的：减小分数方差
  - 避免 Softmax 过早饱和
- 功能
  - 跨 token 信息交互
  - 每个 query 加权汇总允许访问的 V

### 多头注意力 MHA
- 多个独立子空间
  - 每头有独立 $W_Q/W_K/W_V$
  - 可学习不同关系模式
- 合并过程
  - 各头独立计算 Attention
  - `concat(heads)`
  - $W_O$ 融合
- 形状不变
  - 输入 `[B,T,D]`
  - 输出 `[B,T,D]`

### MiniMind 注意力形状
- Q 投影
  - `[B,T,768] -> [B,T,8,96]`
- K/V 投影
  - `[B,T,768] -> [B,T,4,96]`
- 转置后
  - Q：`[B,8,T,96]`
  - K/V：`[B,4,T,96]`
- GQA 对齐后
  - K/V：`[B,8,T,96]`
- 分数
  - `[B,8,T,T]`
- 合并后
  - `[B,T,768]`

### 因果掩码 causal mask
- 放置位置
  - $QK^{\mathsf T}$ 之后
  - Softmax 之前
- 处理方式
  - 严格上三角填 $-\infty$
  - Softmax 后未来位置权重为 0
- 因果可见性
  - 位置 1：只看自己
  - 位置 2：看位置 1~2
  - 位置 $t$：看位置 $1\ldots t$
- 训练为什么必须掩码
  - 整段序列一次输入
  - 不掩码会泄露未来答案
  - 造成训练/推理不一致

### causal mask 在不同场景
- 训练整段并行
  - `Q:T / K:T`
  - 需屏蔽未来 key
- 推理 prefill
  - `Q:T / K:T`
  - 仍需因果掩码
- 无 KV Cache 整段重算
  - `Q:T / K:T`
  - 仍需因果掩码
- KV Cache 单 token 解码
  - `Q:1 / K:past+1`
  - K/V 只含过去和当前位置
  - 没有未来 key
  - 显式三角掩码可省略
  - MiniMind 的 $1\times1$ 上三角掩码全为 0

### attention_mask：padding 屏蔽
- 与 causal mask 不同
  - causal mask：屏蔽未来
  - attention_mask：屏蔽 padding key
- MiniMind 手写路径
  - padding 位置加 `-1e9`
- 训练数据的现实
  - 右侧 padding
  - 有效 token 在因果规则下看不到右侧 pad
  - `labels=-100` 让 pad 位置不计 loss

### GQA：Grouped Query Attention
- MHA / GQA / MQA
  - MHA：`8Q / 8KV`
  - GQA：`8Q / 4KV`
    - 每 2 个 Q 头共享 1 组 K/V
  - MQA：`8Q / 1KV`
    - 全部 Q 头共享 1 组 K/V
- MiniMind 实现
  - `Hq=8`
  - `Hkv=4`
  - `repeat_kv(x,2)` 对齐计算头数
  - KV Cache 保存 repeat 前的 4 头
- 收益
  - 减少 K/V 投影量
  - KV Cache 约减半
  - 减少增量解码显存带宽
- 代价
  - K/V 独立表达能力减少
  - $QK^{\mathsf T}$ 仍按 8 个 Q 头计算
- 易混点
  - GQA 只改变头共享
  - 不改变因果规则
  - 不决定是否显式构造 mask

### QK-Norm
- Q/K 各自进入 RMSNorm
- 位置
  - Q/K 投影后
  - RoPE 前
- 目的
  - 约束 Q/K 尺度
  - 防止 attention logits 爆炸

### SDPA 与 FlashAttention
- 普通 Attention 中间量
  - `scores [B,H,T,T]`
  - `probs [B,H,T,T]`
  - 序列翻倍，元素数约 4 倍
- FlashAttention 核心
  - Q/K/V 分块
  - 块放入片上高速存储
  - 融合 `QKᵀ -> Mask -> Softmax -> PV`
  - 不写回完整 $T\times T$ 矩阵
- 在线 Softmax
  - $m_j$：运行最大值
  - $l_j$：运行指数和
  - $Z_j$：未归一化的 Value 累加
  - 新最大值出现时重缩放旧结果
  - $O=Z_{final}/l_{final}$
- 算法性质
  - 是精确 Softmax Attention
  - 不是稀疏或近似 Attention
  - 算术复杂度仍是 $O(T^2d)$
  - 主要减少 HBM IO 和中间激活
- PyTorch SDPA
  - `F.scaled_dot_product_attention(...)`
  - 是统一调度接口
  - 可选 FlashAttention 内核
  - 可选 memory-efficient 内核
  - 可回退 math 实现
- MiniMind 的 `flash_attn=True`
  - 只代表允许走 SDPA
  - 不保证底层选中 FlashAttention
  - 无直接 `flash-attn` 依赖
- MiniMind 路径
  - 无 padding 整段训练：SDPA
  - 无 padding prefill：SDPA
  - 存在 padding：手写路径
  - 存在历史 cache：手写路径
  - 单 token decode：手写路径

## 4. Decoder Block 与前馈层

### 经典 Post-Norm Block
- 顺序
  - `Attention -> Residual Add -> LayerNorm`
  - `MLP -> Residual Add -> LayerNorm`
- 公式
  - $y=\operatorname{Norm}(x+F(x))$
- 特点
  - 子层输出加回主干
  - 完整梯度还需经过 Norm 导数
  - 深层训练对初始化和学习率更敏感

### MiniMind Pre-Norm Block
- 顺序
  - `RMSNorm -> Attention -> Residual Add`
  - `RMSNorm -> MLP/MoE -> Residual Add`
- 公式
  - $y=x+F(\operatorname{Norm}(x))$
- 优化特性
  - 残差主干有更直接的恒等梯度路径
  - 更适合堆叠深层网络
  - 不等于梯度绝对不消失/爆炸
- 最终收尾
  - 全部 Block 后再做一次 RMSNorm

### 残差连接
- 通用公式
  - $y=x+F(x)$
- 学习含义
  - $F(x)$ 学“需要改多少”
  - 不需重建完整输出
- 形状条件
  - $x$ 与 $F(x)$ 必须同形
- 梯度理解
  - 未经 Norm 时：$\partial y/\partial x=1+\partial F/\partial x$
  - 改善优化条件
  - 不是梯度永远等于 1

### LayerNorm
- 对每个 token 的 hidden 维度独立归一化
- 不依赖 batch 统计
- 公式
  - $\operatorname{LN}(x)=\gamma\odot\frac{x-\mu}{\sqrt{\sigma^2+\varepsilon}}+\beta$
- 操作
  - 减均值
  - 除标准差
  - 学习 $\gamma,\beta$

### RMSNorm
- 仍是每 token 独立归一化
- 公式
  - $\operatorname{RMSNorm}(x)=\gamma\odot\frac{x}{\sqrt{\frac{1}{d}\sum_i x_i^2+\varepsilon}}$
- 与 LayerNorm 差异
  - 不减均值
  - 不学习偏置 $\beta$
  - 只控制整体幅度
- MiniMind 实现
  - 先转 float32 计算均方与开方
  - 再转回原 dtype
  - 目的：降低低精度误差

### 经典 FFN
- 单 token 内部加工
  - token 之间无通信
  - 同一套权重应用到每个 token
- 两矩阵单路结构
  - $\operatorname{FFN}(x)=\operatorname{Act}(xW_{up})W_{down}$
  - $D\rightarrow D_{ff}\rightarrow D$
- 经典示意
  - $D_{ff}=4D$
  - ReLU / GELU

### SwiGLU
- 双分支三矩阵
  - `gate_proj`：门控分支
  - `up_proj`：内容分支
  - `down_proj`：降回 hidden size
- 公式
  - $\operatorname{SwiGLU}(x)=\left(\operatorname{SiLU}(xW_{gate})\odot xW_{up}\right)W_{down}$
- 门控含义
  - SiLU 信号不限于 $[0,1]$
  - 可增强、抑制或改变特征符号
  - 是逐维调制，不是二值开关
- MiniMind 形状
  - `[B,T,768]`
  - 两分支 `[B,T,2432]`
  - 逐元素相乘 `[B,T,2432]`
  - 降维 `[B,T,768]`
- 易混点
  - 不只是把 GELU 换成 SiLU
  - 改变了 MLP 数据流拓扑
  - 仍不负责 token 间通信

### MoE：可切换的稀疏 FFN
- 替换位置
  - 只替换 MLP 子层
  - Attention / RoPE / GQA / Mask 不变
- 组成
  - Router：为每个 token 计算专家分数
  - $E$ 个 Expert
  - 每个 Expert 是独立 SwiGLU
- 路由
  - $\operatorname{MoE}(x)=\sum_{i\in TopK(x)}g_i(x)Expert_i(x)$
  - 每个 token 只执行 Top-$K$ 专家
  - 输出按路由权重加权汇总
- MiniMind 默认
  - `num_experts=4`
  - `num_experts_per_tok=1`
  - `use_moe=False` 默认不启用
- Router 与 SwiGLU gate 不同
  - Router gate：选哪些 Expert
  - `gate_proj`：Expert 内部特征调制
- 负载均衡
  - 风险：路由坍塌
  - 热门专家过载
  - 冷门专家缺少梯度
  - $L_{aux}\approx\lambda E\sum_i f_ip_i$
  - MiniMind `router_aux_loss_coef=5e-4`
- 参数与算力分离
  - 总参数：保存全部专家
  - 激活参数：每 token 只用 Top-$K$
  - 当前单设备权重显存仍更大
- DeepSeekMoE 扩展
  - Shared Experts：每 token 必经
  - Routed Experts：Top-$K$ 选择
  - 更多、更细粒度专家
  - MiniMind 当前未实现

### 堆叠 $L$ 层
- 不是 RNN 循环
- 是结构相同的 Block 堆叠
- 每层权重独立
- 每层分工
  - Attention：列间交流
  - MLP/MoE：列内加工
- MiniMind
  - `for layer in self.layers`
  - $L=8$
  - 各层共用当前 RoPE 位置切片

## 5. 输出、目标与数据

### 上下文表示 $H$
- 全部 Block 后得到
  - 经典：$H\in\mathbb{R}^{D\times N}$
  - MiniMind：`[B,T,768]`
- 每个位置
  - 融合自己和左侧上下文
  - 不包含未来信息
- MiniMind 收尾
  - final RMSNorm
  - 同时返回 `past_key_values`
  - 可选返回 MoE `aux_loss`

### LM Head
- 功能
  - 隐藏空间转换为词表 logits
  - $D\rightarrow V$
- 公式
  - $logits=HW_{lm}$
- 形状
  - 训练：`[B,T,D] -> [B,T,V]`
  - 推理：只需最后位置 `[B,1,V]`
- MiniMind
  - `nn.Linear(768,6400,bias=False)`
  - `logits_to_keep`
    - `1`：只算最后位置
    - `0`：全部位置
  - 当前 `generate()` 未自动传 `logits_to_keep=1`

### Embedding / LM Head 权重共享
- `tie_word_embeddings=True`
- 同一份 `[V,D]` 矩阵
  - 输入：id 查行
  - 输出：与每个词向量打分
- 收益
  - 减少参数
  - 输入/输出语义空间对齐
  - 两处梯度累加到同一权重

### Next-token 错位
- 原始序列
  - `[BOS, 猫, 吃, 鱼, EOS]`
- 监督对
  - `BOS -> 猫`
  - `猫 -> 吃`
  - `吃 -> 鱼`
  - `鱼 -> EOS`
- MiniMind 切片
  - `x = logits[..., :-1, :]`
  - `y = labels[..., 1:]`
  - 去掉 logits 最后位
  - 去掉 labels 第一位

### Softmax 与交叉熵
- Softmax
  - $p_i=\frac{e^{z_i}}{\sum_j e^{z_j}}$
  - 把 logits 转成概率分布
- 单位置交叉熵
  - $L=-\log p(y)$
- 实际实现
  - `F.cross_entropy(logits,labels)`
  - 内部融合 log-softmax + NLL
  - 用 LogSumExp 提高数值稳定性
  - 训练不需显式生成概率

### `ignore_index=-100`
- 含义
  - label 为 `-100` 的位置不计 loss
  - `-100` 不是 token id
- 用途
  - 忽略 padding
  - SFT 只监督 assistant 区间
- 核心认识
  - 模型结构没变
  - labels 决定“哪些位置学什么”

### 预训练数据
- 流程
  - 原始 text
  - tokenizer
  - `[BOS] + content + [EOS]`
  - 截断到 `max_length`
  - 右侧填 pad
- `input_ids`
  - 完整序列
- `labels`
  - 复制 `input_ids`
  - padding 改成 `-100`
- 学习范围
  - 所有非 padding 位置的 next-token

### SFT 数据
- 输入
  - 结构化 `messages`
  - system / user / assistant
- `apply_chat_template`
  - 展开角色控制符
  - 可包含 `<think>`
  - 可包含工具调用标记
- `input_ids`
  - 包含整个对话
- `labels`
  - assistant 回复区间：真实 token id
  - 其他区间：`-100`
- 本质
  - 仍是 next-token 预测
  - 改变的是有效 loss 位置

## 6. 训练闭环

### 基本闭环
- 前向
  - 阶段1~5
  - 得到 `loss`
  - MoE 时加 `aux_loss`
- 反向传播
  - `loss.backward()`
  - 梯度沿计算图反向传播
- 参数更新
  - AdamW
  - `optimizer.step()`
  - `optimizer.zero_grad()`
- 循环
  - 换下一 batch
  - 重复直到收敛

### 更新范围
- Embedding / LM Head
- 每层 Q/K/V/O 投影
- RMSNorm 缩放参数
- SwiGLU 的 gate/up/down
- MoE Router 与 Expert
- 位置注意
  - 固定 RoPE sin/cos 表不是可学习参数

### AdamW
- Adam 的自适应动量更新
- 解耦权重衰减
- 与普通 L2 惩罚的更新位置不同

### 学习率调度
- MiniMind：余弦退火
- 公式
  - $lr(t)=lr_{base}\left[0.1+0.45\left(1+\cos\frac{\pi t}{T}\right)\right]$
- 变化
  - 从 $1.0\,lr_{base}$ 平滑降到 $0.1\,lr_{base}$
- 目的
  - 前期较大步伐学习
  - 后期细化参数

### 混合精度
- `autocast`
  - 适合的算子使用 fp16/bfloat16
  - 数值敏感算子保留 float32
- 收益
  - 减少激活显存
  - 利用低精度硬件加速
- GradScaler
  - fp16 放大 loss
  - 防止小梯度下溢
  - 更新前 `unscale_`
- bfloat16
  - 动态范围较大
  - MiniMind 中通常不启用 GradScaler

### 梯度累积
- 动机
  - 显存无法放入大 batch
- 方法
  - 连续多个小 batch 只 backward
  - loss 先除以累积步数
  - 满 $N$ 步再 optimizer step
- 效果
  - 近似大 batch 的平均梯度
  - 不减少总计算量

### 梯度裁剪
- 计算所有参数梯度的 L2 总范数
- 超过阈值时整体等比缩小
- MiniMind 示意
  - `clip_grad_norm_(...,1.0)`
- 目的
  - 防止异常 batch 造成梯度爆炸

### 梯度累积收尾
- epoch 末尾 batch 可能不满累积步数
- 需额外执行一次更新
- 避免丢失已累积梯度

### 断点续训
- checkpoint 不只保存模型权重
- 还保存
  - optimizer 状态
  - GradScaler 状态
  - epoch / step
  - 学习率调度进度
- 只加载权重的风险
  - 丢失 Adam 动量
  - 调度器从错误位置开始

### 分布式与工程配套
- DDP
  - `DistributedSampler` 切分数据
  - 多卡同步梯度
- `torch.compile`
  - 可选编译优化
- 监控
  - wandb
  - swanlab
- 保存
  - 权重可转 half + CPU 后写盘

### 同一主干，不同目标
- 预训练 / SFT
  - 有效位置 next-token CE
- 蒸馏
  - 真实标签 CE
  - teacher/student 分布 KL
- DPO
  - chosen/rejected 回复
  - policy/reference 对数概率差
- PPO
  - rollout + reward
  - policy + critic
  - 裁剪策略目标
- GRPO
  - 同 prompt 多条回复
  - 组内相对奖励
  - 无 critic
- 核心认识
  - 前向主干可复用
  - 数据组织和 loss 定义不同

## 7. 推理与自回归生成

### 聊天入口
- 结构化 `messages`
- `apply_chat_template(add_generation_prompt=True)`
  - 添加 system/user/assistant 控制符
  - 末尾补“轮到 assistant”的起始标记
- tokenizer
  - `input_ids`
  - `attention_mask`
- `model.generate(...)`

### 自回归循环
- 第一轮
  - 处理整个 prompt
  - 取最后位 logits
  - 采样 next token
- 后续轮次
  - 新 token 拼到序列末尾
  - 再次前向
  - 每轮生成 1 个 token
- 终止
  - 生成 EOS
  - 或达到 `max_new_tokens`

### 采样处理顺序
- 1. 温度
  - $logits\leftarrow logits/T$
  - $T<1$：分布更尖锐
  - $T>1$：分布更平坦
- 2. 重复惩罚
  - 针对已出现 token
  - 正 logits 除以惩罚系数
  - 负 logits 乘以惩罚系数
- 3. top-k
  - 只保留分数最高的 $k$ 个 token
  - 其余置 $-\infty$
- 4. top-p
  - 概率从高到低排序
  - 保留累积概率达到 $p$ 的最小集合
  - 其余置 $-\infty$
- 5. 选择
  - 采样：`multinomial(softmax(logits))`
  - 贪心：`argmax(logits)`

### 训练/推理 Softmax 差异
- 训练
  - 全部有效位置
  - Softmax 隐藏在 cross-entropy 内部
  - 用于计算 loss
- 推理
  - 只关心最后位置
  - 显式 Softmax
  - 用于采样或贪心选择

### 朴素重算
- 每轮将完整序列重新输入
- 重复计算所有旧 token
- 对当前长度 $N$
  - 每轮重新做整段 Attention
  - 生成越长，重复开销越大

### KV Cache
- 缓存内容
  - 每层历史 K
  - 每层历史 V
  - 不缓存历史 Q
- prefill
  - 整个 prompt 一次并行计算
  - 使用因果掩码
  - 产生各层 K/V Cache
- decode
  - 每轮只喂新 token
  - 只计算新 token 的 Q/K/V
  - 新 K/V 追加到 cache
  - 新 Q 与全部历史 K 做注意力
- 为什么可复用
  - 旧 token 在 prefill 时看不到未来
  - 新 token 不会反向改写旧隐藏状态
  - 旧 K/V 计算一次即可重复使用

### KV Cache 形状
- repeat 前的缓存
  - `[B,past_len+seq_len,Hkv,head_dim]`
  - MiniMind：`[B,T,4,96]`
- repeat 后用于注意力
  - `[B,Hq,past_len+seq_len,head_dim]`
- 单步 Q
  - `[B,Hq,1,head_dim]`
- 单步 score
  - `[B,Hq,1,past_len+1]`

### KV Cache 显存
- 估算公式
  - $M_{KV}\approx2LBTH_{kv}d_{head}s$
- 变量
  - $2$：K 和 V
  - $L$：层数
  - $B$：batch size
  - $T$：上下文长度
  - $H_{kv}$：KV 头数
  - $d_{head}$：头维度
  - $s$：每元素字节数
- 增长特性
  - 随上下文长度线性增长
  - 是长上下文推理的显存瓶颈
- GQA 的作用
  - 减少 $H_{kv}$
  - 直接缩小 cache

### RoPE 与增量位置
- 新 token 位置由 `past_len` 决定
- 从 sin/cos 表切取对应位置
- 不能每轮都从位置 0 开始
- 否则缓存 K 与新 Q 的相对位置会错乱

### 批量生成
- 每条序列有独立 `finished` 标志
- 已生成 EOS 的序列
  - 强制输出 EOS 占位
  - 等待其他序列完成
- 所有序列完成后提前结束

### 推理工程细节
- `@torch.inference_mode()`
  - 不建立反向计算图
  - 降低显存占用
- streamer
  - 每产生一个 token 立即推送
  - 实现打字机效果
- attention mask 增长
  - 每追加一个 token
  - mask 同步追加一个有效位

### 四类优化的分工
- GQA
  - 减少 K/V 头数与 KV Cache
- FlashAttention
  - 优化一次 Attention 的数据搬运
- KV Cache
  - 避免解码时重算历史 K/V
- causal mask
  - 定义可见性
  - 是正确性约束，不是加速算法
- 组合关系
  - 可同时使用
  - 彼此不自动开启
  - 处于不同工程层面
