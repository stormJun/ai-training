# 从第一性原理理解分页注意力：深入 vLLM 内部视角

*2025 年 9 月 11 日*

大型语言模型（LLM）的**训练**发生在高度并行、**计算受限**的工作负载中，但为它们提供服务则非常不同：**推理**是**内存受限**且顺序执行的。优化推理至关重要，因为没有人会使用一个响应速度落后于打字速度的聊天机器人，也不会使用一个需要几分钟才能回复的工具。从商业角度看，从每块 GPU 中榨取更多性能能够直接降低成本并最大化投资回报率（ROI）。

一个关键瓶颈是 **key-value（KV）缓存**，它在解码期间存储上下文信息。早期系统由于碎片化浪费了 **60-80%** 的这部分内存，从而限制了吞吐量。Kwon 等人在 [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/pdf/2309.06180) 中提出的 **PagedAttention**，通过借鉴操作系统中的虚拟内存思想解决了这个问题。结果是，内存利用率接近最优，浪费低于 **4%**，且**吞吐量提高了 2-3 倍**。

在这篇文章中，我将从第一性原理出发进行构建：先讨论训练与推理工作负载的区别，再讲朴素的 KV 缓存、操作系统类比，最后说明分页式 KV 缓存和 PagedAttention 如何让 LLM 服务更快、更高效。这些技术已经被主流推理系统支持，例如 [vLLM](https://github.com/vllm-project/vllm)、[TensorRT LLM](https://github.com/NVIDIA/TensorRT-LLM) 和 [Hugging Face TGI](https://github.com/huggingface/text-generation-inference/tree/main)。在附录中，我还会介绍其他推理优化技术，例如连续批处理（continuous batching）、投机解码（speculative decoding），并简要提及量化（quantisation）。

## LLM 训练 vs 推理

为了理解推理面临的挑战，将 LLM 在训练中如何使用与在部署中如何使用进行对比会很有帮助。高层次来看，训练是模型从数据中学习的过程：它通过网络各层向前传播进行预测（**forward pass**，前向传播），将这些预测与已知目标进行比较，通过**损失函数**计算**损失**（即我们距离正确预测有多远），然后通过**反向传播**以及某种形式的梯度下降来调整权重。<span class="sidenote-ref"></span> <span class="sidenote">
<img src="./paged_attention_assets/01_mlp.gif"
style="width:375px;max-width:none;display:block;margin:0 auto"
alt="MLP" /> 这一流程构成了任何神经网络架构的核心：输入从左到右穿过各层，直到输出与目标进行比较并计算损失。随后网络沿相反方向传播，每一层为自己的权重计算梯度，并将误差向后传递，直到第一层，此时我们就得到了所有参数的梯度。<img src="./paged_attention_assets/02_blocks.webp"
style="width:330px;max-width:none;display:block;margin:0 auto"
alt="blocks" /> 对每一层来说，这意味着前向步骤产生继续向后流动的输出，而反向步骤则为权重计算梯度，并把误差向后传递。
<img src="./paged_attention_assets/03_opt.webp"
style="width:330px;max-width:none;display:block;margin:0 auto"
alt="opt" /> 一旦有了梯度，优化器就会结合这些梯度及其内部状态来更新权重，使网络从错误中学习。一次前向传播、损失计算、反向传播和参数更新构成一个训练步骤，并在多个 **epoch** 中重复许多次，以逐步提升预测质量。图示来源：[Data-Parallel Distributed Training of Deep Learning Models](https://siboehm.com/articles/22/data-parallel-training) </span>

训练，尤其是大型语言模型的训练，在计算成本上极其昂贵。这种规模的模型会在由 GPU、TPU 或其他专用加速器（例如 Cerebras Wafer Scale）组成的大规模集群上进行训练。<span class="sidenote-ref"></span> <span class="sidenote">
<img src=""
style="width:330px;max-width:none;display:block;margin:0 auto"
data-uaythywtmvkoxauxidjzryzu3nevtm1lvwm15kza0l2dvwdeyk09nb3p0azq5lytoz0hunwvwnnruwtn4qw1urnnzsjh1v3htbe0=""
alt="Cerebras" /> 左图是一家名为 Cerebras 的初创公司推出的新型 AI 芯片，它是目前已投产中最大的芯片，拥有 4 万亿个晶体管和大约 90 万个计算核心。在推理场景下，它运行 OpenAI 的 GPT-OSS 120B 时，无论是单用户还是多用户设置，速度都约为 **2,700 tokens/sec**。相比之下，NVIDIA Blackwell DGX B200 对单用户大约可达到 **900 tokens/sec**，而在 10 个用户同时使用时会下降到 **580 tokens/sec**。关于硬件差异的拆解，可参见联合创始人兼首席系统架构师 Jean-Philippe Fricker 的[这场演讲](https://youtu.be/7GV_OdqzmIU?si=HW99JXE1MrLbMlTg)。你也可以试试他们的[聊天服务](https://chat.cerebras.ai/)，亲身感受高吞吐推理在实际中的表现。我认为，在我们深入这篇博客之前，这是理解“快速推理”究竟是什么样子的一个很好的入门材料。顺便说明一下，我与他们没有任何关联。我在这里写的一切都纯粹出于兴趣。  
</span>、Graphcore IPU 或 Tenstorrent 硬件。尽管 NVIDIA GPU 仍然是目前最常见的选择，但训练运行大体上属于一次性开销，通常耗资数千万美元。相比之下，推理则是在固定这些已学到的权重后，使用模型为新的输入生成预测或回复。这个区别听起来很直接，但在实践中，两者的工作流差异非常大，因此也需要不同的优化策略。

所有 LLM 的核心都是 **transformer** 架构，它由论文 [“Attention Is All You Need”](https://arxiv.org/pdf/1706.03762) 首次提出。尽管此后出现了许多变体和改进，它依然是当前最先进模型的基础。下图左侧是原始的**仅解码器（decoder-only）** transformer，右侧则是 Llama-2 70B 架构，展示了其中一些后续的改进：

<div style="text-align:center">

<img src="./paged_attention_assets/04_transformers.svg"
style="width:70.0%" alt="Transformers" />

</div>

网络的流程始于原始文本——无论是训练数据还是推理时的真实提示词。模型并不能直接理解人类字符，因此第一步是**分词（tokenisation）**。这会将文本拆分为模型可以处理的一串 token id。然后，每个 id 会通过**嵌入（embeddings）**映射到一个稠密向量空间中，从而为模型提供输入的数值表示。同时，还会给这些向量加入**位置编码（positional encodings）**，以便模型知道每个 token 在序列中的位置。

接下来，这个序列会穿过一叠 transformer 解码器块。每一层都让 token 通过带有**因果掩码（causal mask）**的**多头注意力（multihead-attention）**彼此交互，从而保持语言的*自回归（autoregressive）*特性。在此基础上，序列再经过前馈变换，对特征进行扩展和筛选。网络还具有**残差连接（residual connections）**，即把某一层的输入加回到它的输出中，以防信号衰减，同时还有**归一化（normalisation）**来稳定权重。

这里有一些值得注意的架构差异。例如，LLaMA-2 70B 使用了 Grouped Query Attention（GQA），这是一种能够降低内存需求的注意力变体。大多数现代 LLM 还会将归一化层放在每个块之前，而不是像原始 Transformer 那样放在之后。尽管如此，其高层流程仍然相同：分词后的输入进入模型，带有上下文信息的嵌入输出出来。

在堆叠的末端，模型会把所有内容重新投影回词表空间，从而生成下一个可能 token 的概率分布。在训练期间，这个分布会与序列中每个位置的真实下一个 token 进行比较。这就是为什么人们常说 LLM 是在**下一个 token 预测任务**上训练出来的。训练还包括进一步的阶段，例如基于人类反馈的强化学习（RLHF），它会将模型调教得更像现代聊天系统中那样以更符合人类习惯的方式进行回答。

<div style="text-align:center">

<img src="./paged_attention_assets/05_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

为了在转向推理前把这件事讲具体一点，考虑这个示例序列 Coffee solves everything，并在开头加上一个序列起始 token \[SOS\]。我们将该序列按适当方式进行分词。<span class="sidenote-ref"></span> <span class="sidenote">
<img src="./paged_attention_assets/06_tokenised.webp"
style="width:250px;max-width:none;display:block;margin:0 auto"
alt="tokenised" /> 例如，这个序列在 GPT-4o 分词器中会被拆成 4 个 token，其 id 分别是 \[90651, 6615, 3350, 28997\]。
</span> 然后，在每个位置上，模型都要预测下一个词。\[SOS\] 预测 Coffee，\[SOS Coffee\] 预测 solves，\[SOS Coffee solves\] 预测 everything，以此类推，直到模型预测出一个序列结束 token \[EOS\]。

现在关键点来了。在训练期间，我们已经知道完整序列。这使我们能够在一次前向传播中将整个序列送入 transformer。因果掩码保证 token $`t`$ 不会关注 token $`t + 1`$，因此自回归属性得到了保留，但所有位置的预测都可以并行计算。GPU 非常擅长这种并行处理，因此其计算核心会被工作充分填满。换句话说，训练是计算受限的。所谓**计算受限（compute-bound）**，是指提高硬件的原始计算能力会直接加快训练速度，而内存带宽并不是限制因素。

推理的本质则不同。模型看不到未来的 token，因此在提示词之后，它无法并行处理整个序列。它必须一次只前进一步、生成一个 token，并将每个新 token 追加到上下文中。这意味着 GPU 不再是在许多 token 上同时执行针对 AI 工作负载高度优化的大型稠密矩阵乘法，而是在处理由内存访问主导的小规模重复步骤——一遍又一遍地加载模型权重和缓存的激活值。

这种工作负载的转变非常重要。当瓶颈从重计算转移到频繁的数据搬运时，性能就会下降。搬运数据总是比对它做数学计算更昂贵。这就是为什么推理往往是**内存受限**的，而训练仍然是计算受限的。

## 推理的两个阶段

当用户发送一个提示词时，整个推理过程会分为两个阶段：

- **Prefill（提示阶段）**：模型读取整个输入提示词，并为生成第一个 token 做准备。
- **Decoding（解码）**：逐个、按顺序产生 token 的迭代循环。

这两个阶段的特征和瓶颈都非常不同。

<div style="text-align:center">

<img src="./paged_attention_assets/07_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

**Prefill**

在 prefill 期间，模型仍然可以利用并行性来处理提示词 token。所有输入 token（假设提示词长度为 N 个 token）会在一次前向传播中一起送入 transformer 网络。这通常是一个大型矩阵乘法工作负载，会让 GPU 的计算单元保持繁忙。因此，prefill 通常是计算受限的。事实上，除了没有反向传播之外，这个过程与训练有更多相似之处。

这一阶段的输出是模型预测出的第一个 token，以及为每个注意力层中每个提示词 token 存储的一组 key/value 向量，通常称为 **KV cache**。我们暂时先忽略这一点，稍后再回到它。现在只需先认为这个过程的结果是一个新的预测 token。

从请求发出到第一个 token 被预测出来所经历的时间，是一个重要的推理指标，称为 **time to first token（TTFT）**。TTFT 会随着提示词长度的增加而增长
