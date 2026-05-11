ch 随后会并行验证这些提议的 token，并接受那些与其自身预测相匹配的 token。

这种方法受到两个关键观察的启发：

1.  有些 token 比其他 token 更容易生成：许多下一个 token 从上下文中就很明显，可以由更小的模型提出。
2.  推理的瓶颈通常是内存而不是计算。

推测解码的灵感来自一种称为 **推测执行** 的优化技术，后来这一技术被进一步以概率方式泛化，并应用到自回归模型上。简而言之：

- **推测执行**：假设我们有两个缓慢的步骤：先计算 $`Y = f(X)`$，再计算 $`Z = g(Y)`$。通常，在知道 $`Y`$ 之前，我们无法开始计算 $`g(Y)`$，这就强制形成了严格的串行依赖。推测执行则说：“如果我可以用一个 **廉价近似** $`f^{}(X)`$ 来*猜测* $`Y`$，然后并行启动 $`g(f^{}(X))`$ 会怎样？” 一旦原始的 $`f(X)`$ 完成，我就检查这个猜测。如果匹配，那么我通过将原本串行的部分并行化节省了时间；如果不匹配，我就丢弃推测性的工作并回退到原始流程。无论哪种情况，正确性都能得到保证；而当猜测器足够好时，我们就能获得显著的加速。

- **推测采样**：LLM 不会只产生一个确定的下一个 token，而是产生一个概率分布，我们再从中采样出下一个 token（顺便一提：可以理解为对词表做 softmax）。这使得输出是随机的，而不是确定性的。因此，这种新方法通过引入概率接受规则扩展了上述思路。在每一步中，我们有 $`f(X)`$，即大模型给出的真实分布；以及 $`f^{*}(X)`$，即小模型给出的近似分布。我们让草稿模型采样一个 token，并立即用它启动后续计算。不过这里有一个注意点：因为输出是随机的，我们不能仅仅在草稿模型和目标模型恰好选中同一个 token 时才接受。面对数以万计的词表，这几乎总会失败，从而浪费工作。

- **推测解码**：推测采样通过引入一个 **概率过滤器** 修复了这个问题。当草稿模型采样出一个 token 时，我们检查大模型给这个 token 分配了多大的概率。如果大模型也认为它很可能出现，我们就以较高概率接受草稿模型的选择。如果大模型认为它不太可能，我们就会更频繁地拒绝，并回退为直接从大模型重新采样
  model<span class="sidenote-ref"></span><span class="sidenote"
  style="counter-increment:none">
  ![](./paged_attention_assets/27_image.webp) 基线（虚线）对应朴素解码：每一步始终只生成一个 token。采用推测解码后，随着 α 增大（草稿猜测更频繁地正确）以及 γ 增长，每次迭代的有效 token 数会显著上升。例如，当 γ = ∞ 且 α 接近 0.9 时，系统每次迭代几乎可以生成 10 个 token，而基线中只有 1 个。我们就这样获得了免费的并行性！更好的草稿模型和更大的前瞻长度会直接转化为更高的加速比。 </span>。
  采用这种方法，我们可以保证，尽管成本更低，生成的样本仍然来自与朴素解码完全相同的概率分布。

如需更多细节和示例，Google Research 也发布了这篇[博客文章](https://research.google/blog/looking-back-at-speculative-decoding/)，更详细地解释了这个概念。

在原始论文中，**推测解码** 在 T5-XXL 等模型上展示了 **2×–3×** 的墙钟时间加速，同时保持输出分布完全一致。

<a
href="https://storage.googleapis.com/gweb-research2023-media/media/SpeculativeDecoding-1-Illustration.mp4"
style="z-index:2147483647!important;position:absolute!important;top:8px!important;left:8px!important;width:16px!important;height:16px!important;min-width:16px!important;min-height:16px!important;max-width:16px!important;max-height:16px!important"
target="_blank"><img src="./paged_attention_assets/28_image.png"
style="width:16px!important;height:16px!important;min-width:16px!important;min-height:16px!important;max-width:16px!important;max-height:16px!important" /></a>

### 量化

另一个非常重要且被大量研究的优化方向是 **量化**。如今最先进的模型动辄就是数十亿参数。为了帮助理解，[Hunyuan-Large](https://arxiv.org/abs/2411.02265) 这个开源的 Mixture-of-Experts 模型，总参数量达到 **3890 亿**，而每一步推理中只有 **520 亿参数处于激活状态**——“只有”，我这是带着讽刺地说——这依然极其庞大。DeepSeek-V3 的**总参数量为 6710 亿**，其中在 token 生成期间约有 **370 亿参数处于激活状态**。你懂我的意思了。

尽管激活参数远小于总权重，但推理仍然需要 **将所有参数都载入内存**（例如 GPU 显存），因为每一层、每一个 token 所选择的 expert 都可能不同。这意味着，总模型大小决定了最低内存需求。因此，一个很自然的方向就是让模型变小，从而降低其内存需求。但“变小”究竟是什么意思呢？

参数通常以 **浮点数** 形式存储，而推理涉及海量的浮点运算（FLOPs）。浮点数有不同的精度。直观地说，降低精度可以极大减少内存占用，但代价可能是准确性下降。如何找到这个平衡点，是当前研究的重点之一。在继续之前，先说明几种主要的浮点精度是有意义的：<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![](./paged_attention_assets/29_image.svg) </span>

![precisions](./paged_attention_assets/30_precisions.svg)

还有其他格式，但这些是最主要的几种。在实践中，如今的量化通常也会使用**基于整数的格式**<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![ranges](./paged_attention_assets/31_ranges.webp) 用于表示一个值的比特数越多，它就越精确。可覆盖的范围更大，相邻值之间的间距也更小——因此精度更高。 </span>。

推理所需的内存也不仅仅是权重（例如我们前面一直在讨论的 KV），但我们先看看如果仅仅为了加载完整权重、暂时忽略缓存，DeepSeek-V3 需要多少内存：

``` math
\text{Memory} = \frac{\text{No.~of~Bits}}{8}\times\text{No.~of~Parameters}
```
  
``` math
64\ \text{bits} = \frac{64}{8}\times 671\ \text{B} \approx 5,368\ \text{GB}
```
  
``` math
32\ \text{bits} = \frac{32}{8}\times 671\ \text{B} \approx 2,684\ \text{GB}
```
  
``` math
16\ \text{bits} = \frac{16}{8}\times 671\ \text{B} \approx 1,342\ \text{GB}
```
  
``` math
8\ \text{bits} = \frac{8}{8}\times 671\ \text{B} \approx 671\ \text{GB}
```
  
``` math
4\ \text{bits} = \frac{4}{8}\times 671\ \text{B} \approx 335.5\ \text{GB}
```

显然，没有任何 GPU 能容纳 1,342 GB。在实践中，推理会通过 **张量并行（tensor parallelism）** 和 **流水线并行（pipeline parallelism）** 等方法分布到成千上万张 GPU 上。我这里不展开讲这些，但它们都很值得深入了解。不过从这里你可以非常清楚地看到，仅仅通过降低精度，内存需求就会大幅下降。除了节省内存之外，像 int8 或 int4 这样的整数格式在某些硬件上甚至可能比浮点格式更快<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none"> 在 NVIDIA H100 Tensor Cores 上，INT8 的峰值吞吐量约为 2000 TOPS，而 FP16/BF16 约为 1000 TFLOPS。
</span>。

#### 量化映射

核心思想是，我们希望把位于某个较大范围 $`\lbrack\alpha,\beta\rbrack`$ 内的浮点数，压缩到一个更小范围 $`\lbrack\alpha_{q},\beta_{q}\rbrack`$ 内的整数。以有符号 INT8 为例，这个范围就是 $`\lbrack - 128,127\rbrack`$。为了实现这一点，我们假设浮点值 $`x`$ 与其量化后的整数值 $`x_{q}`$ 之间存在一条直线关系。想看更详细的推导，可以参考 [Lei Mao 的](https://leimao.github.io/article/Neural-Networks-Quantization/)博客文章，他在这方面讲得很深入。这篇文章帮助我更清楚地理解了这个过程：

``` math
x = c(x_{q} + d)
```

这里，$`c`$ 是缩放因子，也就是每一个整数步长对应多少浮点单位；而 $`d`$ 只是一个偏移量。如果我们想反过来（从浮点到整数），就把这条直线翻转过来并进行四舍五入：

``` math
x_{q} = {round}\!\left( \frac{x}{c} - d \right)
```

这条直线必须同时命中两个范围的端点，因此我们要求：

``` math
\beta = c(\beta_{q} + d),\qquad\alpha = c(\alpha_{q} + d)
```

将这两个方程相减可得：

``` math
\beta - \alpha = c(\beta_{q} + d) - c(\alpha_{q} + d)
```

使用分配律：

``` math
\beta - \alpha = c(\beta_{q} - \alpha_{q})
```

这意味着：

``` math
c = \frac{\beta - \alpha}{\beta_{q} - \alpha_{q}}
```

一旦知道了 $`c`$，我们就可以把它代回
$`\alpha = c(\alpha_{q} + d)`$ 中，从而求出 $`d`$：

``` math
\alpha = c\alpha_{q} + cd
```
``` math
d = \frac{\alpha}{c} - \alpha_{q}
```

把 $`c`$ 替换进去可得：

``` math
d = \alpha\frac{\beta_{q} - \alpha_{q}}{\beta - \alpha} - \alpha_{q} = \frac{\alpha\beta_{q} - \beta\alpha_{q}}{\beta - \alpha}
```

这就是一般形式。不过在实践中，库通常把
$`s = c`$ 称为 **scale（缩放因子）**，把 $`z = - d`$ 称为 **zero point（零点）**，而你实际会用到的最终公式是这样的：

``` math
x = s(x_{q} - z)
```
``` math
x_{q} = {round}\!\left( \frac{x}{s} + z \right)
```

其中

``` math
s = \frac{\beta - \alpha}{\beta_{q} - \alpha_{q}},\qquad z = {round}\!\left( \alpha_{q} - \frac{\alpha}{s} \right)
```

让我们通过一个可视化示例来更好地理解这些概念。假设我们有一个由 5 个权重组成的向量，它们用 FP32 表示，而我们想把它量化为 int8。<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none"> 在实践中，我们不会把 FP32 的整个精度范围 \[-3.4e38, 3.4e38\] 映射到 INT8。
相反，我们会取需要存储的实际数据，找出其最小值和最大值，再把这个区间拟合到 INT8 的编码范围中。 </span>

![quant](./paged_attention_assets/32_quant.svg)

#### 对称量化与非对称量化

注意其中的差异。在 **非对称量化** 中，我们使用真实的数据范围，因此 $`\alpha`$ 是张量的最小值，$`\beta`$ 是最大值。这样的选择会在编码空间中得到一个非零的 0 点，这也是为什么在第一个例子中，浮点中的 0 被存储为编码 $`21`$。同时，我们也会从头到尾用满所有 INT8 编码。在 **对称量化** 中，我们通过取绝对值更大的那个边界作为 $`a`$，将浮点范围围绕 0 居中，然后把从 $`- a`$ 到 $`+ a`$ 的区间映射到一个完全居中的编码范围，此时零点为 $`z = 0`$。

比较这两种模式：

在非对称量化中，我们把真实的最小值固定映射到最小编码，把真实的最大值固定映射到最大编码，因此数据会分布到所有桶中，没有浪费。在对称量化中，我们强制让浮点区间围绕零点分布。如果张量的大多数值都位于零的一侧，那么很多桶会表示你根本不会见到的值。一个极端例子是在 ReLU 之后，所有值都非负。非对称量化会将全部 256 个编码都用于有意义的区域；而对称量化会保留 128 个编码给根本不会出现的负值。

不过在非对称模式下，零点会给硬件带来额外的处理逻辑。根据具体实现，这种额外处理可能会增加少量延迟和复杂度。
