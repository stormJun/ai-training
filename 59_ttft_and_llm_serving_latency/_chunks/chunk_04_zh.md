**内部碎片**，但其上界至多是每个请求 $`B - 1`$ 个 token 槽位，而不是像你之前记得的那样与整个上下文长度相关。块大小 **$`B - 1`$** 是在指针追踪与装箱效率之间进行权衡。较大的块会减少查找次数，但会让复用变得更粗粒度。较小的块会提高灵活性，并减少最后一个块中的未使用槽位，但代价是需要多做几次查找。

这是一个示例，展示了当初始有两个共享相同前缀或提示词的 prompt 时，内存共享会是什么样子。之后当它们想要生成新的 token 时，缓存管理器会为该请求分配一个新的块，并执行写时复制，把相同的 KV 缓存复制到另一块区域中，从而让每个请求都拥有自己的“副本”和块，用来放置它的新 token。

![memshare](./paged_attention_assets/21_memshare.gif)

这种布局直接修复了我们之前看到的问题。**内部碎片**会缩小，因为系统不再预留最坏情况大小的整块区域。它只分配实际使用到的块，并且随着解码推进一次只分配一个块。**外部碎片**也基本消失了，因为分配总是以相同大小的块进行，所以空闲空间不会变成不可用的空洞。任何空闲块都可以分配给任何请求，而块表会隐藏这些块在物理上是分散的这一事实。

对于批处理和解码，这种方式也带来了一些实际收益。连续批处理会更加顺滑，因为可以混合长度差异很大的请求而不浪费内存。内存共享避免了重复，并且表示成本很低。如果你从同一个 prompt 中采样多个补全结果，或者运行共享早期前缀的 beam，那么所有这些路径都可以共享相同的物理前缀块，只在生成新 token 时才发生分叉。块表只需将多个请求同时指向同一组只读块，这样就能在不复制的情况下节省内存。最后，分页在高压场景下提供了清晰的行为。如果当调度器想推进一个 batch 时，池中已经没有空闲块，系统可以暂停新的预填充工作，通过将低优先级请求的块归还到池中来驱逐它们，或者在可接受时退回到重计算策略。所有这些选择都发生在 KV 块这一层级，因此策略保持简单且可预测。

## Paged Attention 机制

**PagedAttention** 是让分页式 KV 缓存真正运作起来的计算侧机制。经典 attention 假设一个序列的 key 和 value 位于一个连续缓冲区中。PagedAttention 去掉了这个假设。它像我们之前看到的那样，将每个请求的缓存切分成大小相等的 KV 块，然后通过跟随该请求的块表来驱动 attention，这样块就可以存在于 GPU 内存中的任意位置，同时数学结果仍与标准 attention 完全一致。

下面是一个使用查询 token *soon* 的简单示例。这个序列的历史 token 分布在三个不同的 KV 块中：

- 块 1 存储 sing、calm、night、bring
- 块 3 存储 peace、soon
- 块 7 存储 Sun、sets、low、bid

<div style="text-align:center">

<img src="./paged_attention_assets/22_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

即使这些 token 存在于非连续内存中，块表仍能确保内核按照正确的逻辑顺序遍历它们，并计算 attention，就好像它们都紧挨着位于同一个缓冲区中一样。

这些块编号为 $`j = 1,2,3,\ldots`$。块 $`j`$ 只是包含位置落在该范围内的那 $`B`$ 个 token 的 key 和 value：

``` math
K_{j} = \left\lbrack k_{(j - 1)B + 1},\ldots,k_{jB} \right\rbrack,\qquad V_{j} = \left\lbrack v_{(j - 1)B + 1},\ldots,v_{jB} \right\rbrack.
```

因此，$`K_{1}`$ 保存序列中前 $`B`$ 个 key，$`K_{2}`$ 保存接下来的 $`B`$ 个，依此类推。$`V_{j}`$ 对 value 也是同样的道理。

对于当前查询 token $`i`$，其查询向量为 $`q_{i}`$，头维度为 $`d`$，我们可以通过逐块访问这些块来计算 attention。用块的形式写出来就是：

``` math
A_{ij}\; = \;\frac{\exp\!\left( q_{i}^{\top}K_{j}\,/\,\sqrt{d} \right)}{\sum_{t = 1}^{\lceil i/B\rceil}\exp\!\left( q_{i}^{\top}K_{t}\,/\,\sqrt{d} \right)},
```

 

``` math
o_{i}\; = \;\sum_{j = 1}^{\lceil i/B\rceil}V_{j}\, A_{ij}^{\top}.
```

这里，$`A_{ij} = \left( a_{i,(j - 1)B + 1},\ldots,a_{i,jB} \right)`$ 是块 $`j`$ 内各个 token 的 attention 权重向量。向量 $`o_{i}`$ 则是 token $`i`$ 的标准 attention 输出。

内核所做的事情其实很直接。它按逻辑顺序遍历请求的块表。对于每个块 $`j`$，它会查找该块在 GPU 内存中的位置，加载 key $`K_{j}`$，形成局部分数

``` math
q_{i}^{\top}K_{j}/\sqrt{d},
```

更新一个**运行中的 softmax
归一化器**<span class="sidenote-ref"></span>  
<span class="sidenote" style="counter-increment:none">我没找到更多信息来确认它是否与 [Flash Attention](https://arxiv.org/pdf/2307.08691) 中使用的 online softmax 完全相同，但它们很可能非常相似。</span>，该归一化器跨越所有已经看到的块，然后将归一化后的权重与 value $`V_{j}`$ 相乘，并把结果累加到 $`o_{i}`$ 中。由于 softmax 是跨多个块运行的，内核会在流式处理中维护一个运行最大值和一个运行求和。这样得到的数值与所有 key 和 value 都放在一个连续数组中时完全相同。

现在让我们看一些数字，以理解这种方法优化的目标：

之前的系统会浪费 **60%–80%** 的 KV 缓存内存，而 vLLM 能够以不到 **4%** 的浪费实现接近最优的内存使用。由于这种内存效率的提升，我们可以用更少的 GPU 达到相同的输出，因此吞吐量显著高于其他推理引擎。这种受虚拟内存启发的 attention 设计，因此将**内部碎片**限制在块大小范围内，并消除了**外部碎片**。下面这张来自论文的图展示了：在相同模型下，与 vLLM 的 paged attention 相比，三种不同 serving 系统中的不同类型的内存浪费情况：

<div style="text-align:center">

<img src="./paged_attention_assets/23_transformers.webp"
style="width:70.0%" alt="Transformers" />

</div>

在结束之前，必须指出一个将虚拟内存和分页技术应用到其他 GPU 工作负载时的注意事项。虚拟内存和分页的思路之所以对 LLM serving 中的 KV 缓存管理有效，是因为这种工作负载需要动态内存分配，而且性能受限于 GPU 内存容量。然而，这一点并不普遍适用于所有其他 AI 工作负载。在 DNN 训练中，张量形状通常是静态的，因此内存分配可以提前优化。而在服务那些非 LLM 的 DNN 时，即便提升了内存效率，也未必会带来性能收益，因为这类工作负载主要受计算能力限制。在这种场景下，引入 vLLM 的技术甚至可能因为额外的内存间接访问开销和非连续块访问而降低性能。话虽如此，如果能看到这些技术被应用到其他具有与 LLM serving 相似特性的工作负载上，仍然会是一件很令人兴奋的事。

------------------------------------------------------------------------

## 附录：其他推理优化技术

### 静态批处理 vs 连续批处理

批处理有助于缓解 LLM 面临的内存带宽限制，因为它们往往会在搬运数据和加载参数时浪费大量 GPU 计算资源。你不必为每个请求都加载一次模型参数，而是只加载一次，然后用它来处理许多输入序列或请求。这样可以更高效地利用芯片的内存带宽，从而带来更高的计算利用率、更高的吞吐量以及更低成本的 LLM 推理。

**静态批处理**是传统风格，即服务器会等待直到有固定数量的请求到达，然后将它们作为一个 batch 一起处理。之所以称为静态，是因为 batch 大小在推理完成之前保持不变。

- 一个 batch 中最先到达的请求必须等待最后一个请求，造成不必要的延迟。可以把它想象成一台打印机：在排队的文档数量达到固定值之前，它不会开始打印，而不管最后一份文档要多久才会到。

- 同一个 batch 中的请求并不都是一样的。在 LLM 推理中，一些请求可能只会生成很短的回复，而另一些则可能涉及冗长的、逐步展开的推理。由于 batch 中所有请求都必须等到最慢的那个完成，这会导致计算资源浪费并增加延迟。

如果不对用户输入和模型输出长度作出严格假设，未经优化的生产级 LLM 系统就无法在不让 GPU 利用不足并产生不必要成本的情况下服务流量。我们必须优化 LLM 的服务方式，才能让它们的能力被广泛使用。

![StaticBatching](./paged_attention_assets/24_staticbatching.webp)

与其等待一个 batch 中的每个序列都完成生成，在论文 [Orca: A Distributed Serving System for
Transformer Based Generative
Models](https://www.usenix.org/conference/osdi22/presentation/yu) 中，他们实现了**迭代级调度**，其中 batch 大小是按每次迭代来选择的。结果是，一旦 batch 中某个序列完成生成，就可以立即插入一个新序列来替代它，从而比静态批处理获得更高的 GPU 利用率。文献中有时会把这称为 dynamic，但 **continuous** 更贴切，而 **dynamic** 更适合保留给另一种策略。<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![BatchingTypes](./paged_attention_assets/25_batchingtypes.svg) 在
**静态批处理**中，服务器会等待直到有固定数量的请求到达，然后把它们作为单个 batch 一起处理。**动态批处理**仍然会把传入请求收集成 batch，但它不坚持固定的 batch 大小。相反，它使用一个时间窗口，并处理该窗口内到达的所有请求。如果 batch 更早达到大小上限，就会立即启动。这就像一辆公交车：要么按固定时刻发车，要么坐满就走，哪个先发生就按哪个来。**连续批处理**不会等待一个 batch 中所有序列都完成，而是在迭代层面上对序列进行分组。</span>。如果你感兴趣，这篇博客：[How continuous batching enables 23x
throughput in LLM inference while reducing p50
latency](https://www.anyscale.com/blog/continuous-batching-llm-inference)，对这一点有更详细的解释。也感谢作者们提供了上面的图，帮助可视化这些策略。

![Continous-batching](./paged_attention_assets/26_continous-batching.webp)

### 推测式解码

最基础的生成过程在每一步解码时一次只输出一个 token。不过关键在于，要生成 K 个 token，你就需要做 K 次模型前向传播；正如文中解释的那样，这在本质上是顺序执行的，因为第 t+1 步依赖于直到第 t 步为止的生成结果，因此同样无法很好地利用计算资源。

因此，token 生成时间会线性增长。这实际上也与上面解释的不同批处理策略有关，因为在静态批处理场景中，吞吐量正是被这种线性增长所限制。所以，这也进一步说明了为什么连续批处理可以缓解这一瓶颈。

LLM 越大，能力通常越强。然而，这些更大的模型也更慢，因为每一步解码都需要读取整个模型的权重。

因此，Google Research 团队在 [Fast Inference from Transformers via Speculative
Decoding](https://arxiv.org/pdf/2211.17192) 中提出了**推测式解码**。该算法通过一个起草用的“更小”模型并行计算多个 token，从而加速自回归模型的生成；这个小模型会预先提出若干个草稿 token，而一个更大的模型 whi
