h，因为更长的提示意味着需要处理更多的 token，并且在到达第一次预测之前，需要计算更多的注意力键和值。尽管这会随着输入大小扩展，但在服务过程中，这通常不是主要问题。

![TTFT](./paged_attention_assets/08_ttft.svg)

**解码**

在预填充之后，LLM 进入 **decode** 阶段，在这个阶段它会按顺序逐个生成新 token。解码的每一次迭代都会取当前序列（随着新 token 被追加而不断增长），并执行一次前向传播来预测下一个 token。与完整可用的提示不同，新 token 严格地一个接一个到达。每一步解码本质上都是串行的，因此在生成 token *t* 之前，我们无法计算 token *t+1*。

这使得解码与预填充在本质上不同。在实践中，它通常不是计算受限，而是受内存带宽限制，因为每个新 token 都需要从内存中取回模型权重，并读取已存储的 KV 缓存。GPU 最终花在搬运数据上的时间，往往比真正执行计算的时间还多。

正如 TTFT 衡量预填充一样，**Inter-token Latency (ITL)** 衡量的是在解码期间生成每个后续 token 所需的平均时间。

在聊天机器人这类交互式应用中，**TTFT** 和 **ITL** 都至关重要。用户不希望在看到第一个响应之前等待太久，同时他们也期望之后的 token 流能够平滑且速度合理。其他重要的推理指标还包括 **Total Latency (E2EL)** 和 **Token Generation Time**。<span class="sidenote-ref"></span>  
<span class="sidenote">  
![InferenceMetics](./paged_attention_assets/09_inferencemetics.svg)  
从用户与推理服务之间的 token 生成过程来看推理指标。  
</span>

这种两阶段拆分也解释了为什么并行服务多个请求具有挑战性：预填充阶段可能开销较重，但每个请求只运行一次；而解码阶段可能持续很久（每个请求可能顺序生成数百个 token），并长期占用资源。许多 LLM 服务优化手段，例如 **continuous batching**、**speculative decoding** 和 **prefill/decode scheduling**，其目标都是在这些阶段中持续让 GPU 保持忙碌，同时避免某个慢请求成为其他请求的瓶颈。（我会在附录中介绍 batching 和 speculative decoding。与我们接下来会看到的 paged KV caching 类似，这些技术已经在现代推理系统中实现，例如 vLLM 和 TensorRT-LLM。）

![ITL](./paged_attention_assets/10_itl.svg)

## 为什么解码需要 KV 缓存

鉴于解码具有**顺序性**，如果采用朴素方法来生成输出 token，速度将慢得难以接受。如果我们在每一步都必须为整个不断增长的序列从头重新计算每一层的激活值，工作量将会爆炸式增长。在实践中，这只是在重复计算之前已经算过的结果。我们本来就已经是**内存受限**，因此绝不能让情况变得更糟。

为了看清朴素解码有多浪费，考虑这样一组数字。假设提示有 1000 个 token，而我们想生成 100 个输出 token。如果没有缓存，模型在生成第一个输出时需要处理完整的 1000 个 token，生成下一个时需要处理 1001 个，再下一个则是 1002 个，如此继续，总计会远远超过 100,000 次 token 计算。

有了缓存，模型只需要处理一次这 1000 个提示 token，然后在此基础上计算 100 个新 token，总计只需 1,100 次计算，工作量几乎减少了两个数量级。诀窍在于避免重新处理序列中更早的 token：一旦提示被处理完，其中间结果就可以在未来所有解码步骤中复用。在实践中，这只需通过向 K 和 V 张量追加内容来实现。

### 键值（KV）缓存

解码阶段的一个核心优化是 **KV caching**。每个新 token 都依赖于所有先前 token 的 key 和 value 张量。这些既包括预填充阶段输入 token 的 K 和 V，也包括解码过程中生成的任何新 K 和 V。为了避免在每一步都重新计算这些张量，它们会被**缓存**在 GPU 内存中。随着每个新 token 到来，模型只需将它新产生的 K 和 V 追加到这个持续增长的缓存中，而后续步骤再从中读取。推理过程看起来就是这样：

<div style="text-align:center">

<img src="./paged_attention_assets/11_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

代价的来源不仅在于缓存本身的大小，还在于反复加载和更新大型 K 与 V 张量所带来的内存带宽成本。在标准多头注意力中，每个头都维护自己的 K 和 V，因此存储开销和带宽开销都会随着头数直接扩展。对于大模型来说，这使得缓存成为推理中的主要瓶颈之一。

为了降低这些成本，人们提出了多种注意力机制。它们的目标都是在尽可能保持模型质量的同时，缩小 KV 占用或减少内存传输。我不会深入介绍每种机制的细节，但这里简要概述其中最知名的几种：

- [**Multi-Query Attention (MQA)**](https://arxiv.org/pdf/1911.02150)：  
  一层中的所有头共享同一组 K 和 V，而不是各自维护自己的 K 和 V。这显著降低了解码期间的缓存大小和内存读取量，不过通常会以一定的模型质量损失为代价。

- [**Grouped Query Attention (GQA)**](https://arxiv.org/pdf/2305.13245)：  
  这是 MQA 和完整多头注意力之间的折中方案。Query 头会被划分为多个组，每组共享一个 K 和 V。这样既保留了 MQA 的大部分效率优势，又保留了更多多头注意力的精度。LLaMA 2 就是使用 GQA 的著名例子。

更新近的方法则更进一步，将 K 和 V 压缩到潜在空间中<span class="sidenote-ref"></span> <span class="sidenote"
style="counter-increment:none">
![MLA](./paged_attention_assets/12_mla.webp) 在 **MLA** 中，K 和 V 被压缩到一个由所有头复用的共享潜在空间中。这减小了 KV 缓存大小，但也带来了扩展问题：这个潜在表示必须在每个 GPU 上完整保留，因此无法在分布式推理中高效切分。![GLA](./paged_attention_assets/13_gla.webp) **GLA** 通过将头拆分成多个组来解决这个问题，每组拥有自己的潜在表示。这样缓存就能自然地分布到多个 GPU 上，每个设备只持有自己那一部分。这使得并行成为可能，同时不会增加单设备内存。通过将 K 和 V 折叠为低秩投影，GLA 还释放了参数预算，可用于更宽的投影或更多的 query 头。结果是更好的扩展性、跨 batch 更平滑的延迟，以及更适合硬件的效率，尤其是在长上下文或大负载下。 </span>：

- [**Multi head Latent Attention (MLA)**](https://arxiv.org/pdf/2405.04434)：将 K 和 V 存储在一个学习得到的低维潜在空间中，并在需要时进行投影进出。这样可以减少 KV 缓存大小和带宽占用，同时用少量额外的投影计算作为交换。这一机制因在 DeepSeek V2 及其后续模型中的使用而广为人知。

- [**Grouped Tied Attention (GTA)**](https://arxiv.org/pdf/2505.21487)：  
  在每个组内绑定 keys 和 values，从而减少缓存大小和解码时的内存流量，同时保持与 GQA 相当的质量。绑定的 KV 向量通过一次单独投影创建。完整向量会被缓存，并直接作为 value 使用（不进行旋转）。对于 key，只取前一半且不旋转，而后一半则来自一个带有 RoPE 的单头独立投影，并广播到所有组。这样可以将 KV 缓存减半、减少内存流量，并且相较于 GQA 将算术强度翻倍。

- [**Grouped Latent Attention (GLA)**](https://arxiv.org/pdf/2505.21487)：  
  将 K 和 V 存储在一种为高效并行切分而优化的潜在表示中。这样既实现了类似 MLA 的压缩效果，又更加适合硬件，也更适用于分布式推理。

## 朴素 KV 缓存的问题

虽然 KV 缓存解决了重复计算的问题，但它也将瓶颈大幅转移到了内存上，并且随着上下文长度增长，引入了严重的内存管理问题。每个活跃请求都会随着 token 一个接一个地产生一串 key 和 value，而这串数据必须驻留在 GPU 上，以便在解码期间快速读取。一旦我们尝试同时服务多个请求，比如使用 continuous batching，吞吐量就不再受计算限制，而变成受内存限制。这主要是由两点导致的：第一，随着 KV 缓存大小增长，我们能够在一个 batch 中同时处理的请求数会受到限制，从而降低吞吐量；第二，当内存分配不高效时，朴素的 KV 缓存会导致严重的碎片化，包括内部碎片和外部碎片。

### 内存扩展

KV 缓存的内存使用量会随着序列长度线性增长，并消耗大量 GPU 内存。对于每个生成的 token，缓存都必须为每个 transformer 层和每个头存储一个 key 向量和一个 value 向量。我们以 LLaMA-2–13B 为例来看具体数字。缓存大小可以估算为：

``` math
KV_{cache\_ size} = 2\times bytes\times n_{layers}\times B\times n_{heads}\times d_{head}\times n_{seq}
```

其中  
$`n_{layers}`$ = transformer 层（block）的数量  
$`B`$ = batch 大小  
$`n_{heads}`$ = 注意力头数<span class="sidenote-ref"></span><span class="sidenote">对于 MQA，这会降为 1；对于 GQA，则取决于组数。</span>  
$`d_{head}`$ = 每个头的维度  
$`n_{seq}`$ = 序列长度或上下文长度  
2 = 每层分别用于 Key 和 Value 的两个缓存<span class="sidenote-ref"></span><span class="sidenote">这正是 MLA 和 GLA 主要减少的部分，会从 2 变成 1！</span>

根据我们刚刚给出的公式来计算，对于采用 FP16（每个元素 2 字节）的 LLaMA-2-13B，在标准多头注意力配置下（40 层、40 个头、$`d_{head}`$ = 5120/40 = 128，默认上下文长度为 4096 token），每个 token 的 KV 缓存大约为 0.78125 MiB。对于完整的 4096 token 窗口，KV 缓存大小约为 3.125 GiB。当我们增大 batch size 时，总内存占用会线性增长，因为每增加一个序列，每个 token 还会额外增加约 0.78125 MiB。

现在我们已经理解，KV 缓存会阻止我们处理或生成非常长的序列（即成为长上下文窗口的障碍），也会阻止我们处理大 batch，因此也就阻止了我们最大化硬件效率。<span class="sidenote-ref"></span> <span class="sidenote"
style="counter-increment:none">
<img src="./paged_attention_assets/14_memlay.webp"
style="width:280px;max-width:none;display:block;margin:0 auto"
alt="memlay" /> 在 NVIDIA A100 40 GB 上，一个 13B FP16 模型大约使用 ≈26 GB 来存放权重，只剩下 ≈12 GB 可用于 KV 缓存。在完整多头注意力下，每个 token 的 KV 大约是 ≈0.8 MB，因此这张卡总共大约只能容纳 ≈15k 个 token 的 KV。若上下文窗口为 2048 token，这大约意味着一次可驻留 ≈7 个序列。提示 token 只是占用了 2048 配额中的一部分，因此并发度大致不变，但每个序列可生成的新 token 会更少。实际上的启示是，解码吞吐量受 KV 容量上限所限制。Paged KV caching 是我们这里关注的重点，但 KV 量化（我会在附录中讨论）以及能够缩小 KV 占用的替代注意力机制同样有帮助。
</span>

这是其中一个问题，接下来我们将看到内存碎片问题。

| Model       | n_layers | n_heads | d_head | d_model |
|-------------|----------|---------|--------|---------|
| Llama-2-7B  | 32       | 32      | 128    | 4096    |
| Llama-2-13B | 40       | 40      | 128    | 5120    |
| OPT-7B      | 32       | 32      | 128    | 4096    |
| OPT-13B     | 40       | 40      | 128    | 5120    |
| OPT-30B     | 48       | 56      | 128    | 7168    |
| OPT-66B     | 64       | 72      | 128    | 9216    |
| OPT-175B    | 96       | 96      | 128    | 12288   |

### 连续批处理中的碎片化
