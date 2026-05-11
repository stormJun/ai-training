h, since a longer prompt means more tokens to process and more
attention keys and values to compute before reaching the first
prediction. Although this scales with input size, it is generally not
the main problem in serving.

![TTFT](./paged_attention_assets/08_ttft.svg)

**Decoding**

After prefill, the LLM enters the **decode** stage where it generates
new tokens sequentially, one at a time. Each iteration of decode takes
the current sequence (which keeps growing as new tokens are appended)
and performs a forward pass to predict the next token. Unlike the
prompt, which is available in full, new tokens arrive strictly one after
another. Each decode step is inherently serial, so we cannot compute
token *t+1* until token *t* has been generated.

This makes decoding fundamentally different from prefill. It is not
compute bound in practice but rather memory-bound, since each new token
requires fetching the model weights and reading the stored KV cache from
memory. GPUs end up spending more time moving data than performing
computation.

Just as TTFT measures prefill, **Inter-token Latency (ITL)** measures
the average time it takes to generate each subsequent token during
decoding.

In interactive applications like chatbots, both **TTFT** and **ITL** are
critical. Users do not want to wait too long before seeing the first
response, and they also expect a smooth, reasonably fast stream of
tokens thereafter. Other important inference metrics include **Total
Latency (E2EL)** and **Token Generation
Time**.<span class="sidenote-ref"></span>  
<span class="sidenote">  
![InferenceMetics](./paged_attention_assets/09_inferencemetics.svg)  
Inference metrics viewed on a token generation process between a user
and an inference service.  
</span>

This two-phase breakdown also explains why serving many requests in
parallel is challenging: the prefill stage can be heavy but runs once
per request, whereas the decode stage can drag on (possibly hundreds of
tokens generated sequentially per request) and tie up resources. Many
LLM serving optimisations, such as **continuous batching**,
**speculative decoding**, and **prefill/decode scheduling**, aim to keep
the GPU busy across these phases without letting one slow request
bottleneck others. (I cover batching and speculative decoding in the
appendix. Similar to what we will see next with paged KV caching, these
techniques are implemented in modern inference systems such as vLLM and
TensorRT-LLM.)

![ITL](./paged_attention_assets/10_itl.svg)

## Why Decoding Needs KV Caching

Given the **sequential** nature of decoding, a naive approach to
generate output tokens would be prohibitively slow. If we had to
recompute every layer’s activations from scratch for the entire growing
sequence at each step, the workload would explode. In practice, we would
just be recomputing results that were already calculated earlier. We are
already **memory-bound**, so making things worse is not an option.

To see how wasteful naive decoding would be, consider some numbers.
Imagine a prompt of 1000 tokens and we want 100 tokens of output.
Without caching, the model would process the full 1000 tokens for the
first output, then 1001 for the next, then 1002 for the one after, and
so on, adding up to well over 100,000 token computations.

With caching, the model only needs to handle the 1000 prompt tokens once
and then compute each of the 100 new tokens on top, for a total of just
1,100 computations, nearly two orders of magnitude less work. The trick
is to avoid reprocessing tokens from earlier in the sequence: once the
prompt is processed, its intermediate results can be reused for all
future decoding steps. In practice, this is done simply by appending to
the K and V tensors.

### Key-Value (KV) Caching

A core optimisation in the decode phase is **KV caching**. Each new
token depends on the key and value tensors of all previous tokens. These
include both the input tokens’ K and V from prefill and any new K and V
generated during decoding. To avoid recomputing these tensors at every
step, they are **cached** in GPU memory. With each new token, the model
simply appends its fresh K and V to this running cache, and subsequent
steps read from it. The inference process would then look like this:

<div style="text-align:center">

<img src="./paged_attention_assets/11_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

Where the cost comes from is not only the size of the cache but also the
memory-bandwidth cost of repeatedly loading and updating the large K and
V tensors. With standard multi-head attention, each head maintains its
own K and V, so both storage and bandwidth scale directly with the
number of heads. For large models, this makes the cache one of the main
bottlenecks in inference.

To reduce these costs, a number of attention mechanisms have been
proposed. They all aim to shrink the KV footprint or reduce memory
transfers, while preserving model quality as much as possible. I won't
go into details of each mechanism but here is a brief overview of the
most well-known ones:

- [**Multi-Query Attention (MQA)**](https://arxiv.org/pdf/1911.02150):
  All heads in a layer share a single set of K and V instead of
  maintaining their own. This significantly reduces both cache size and
  memory reads during decode, though it usually comes at some cost in
  model quality.

- [**Grouped Query Attention (GQA)**](https://arxiv.org/pdf/2305.13245):
  A middle ground between MQA and full multi-head attention. Query heads
  are split into groups, and each group shares one K and V. This keeps
  much of the efficiency benefit of MQA while retaining more of the
  accuracy of multi-head attention. LLaMA 2 is a well-known example that
  uses GQA.

More recent approaches go further by compressing K and V into latent
spaces<span class="sidenote-ref"></span> <span class="sidenote"
style="counter-increment:none">
![MLA](./paged_attention_assets/12_mla.webp) In **MLA**, K and V are
compressed into a shared latent space reused by all heads. This cuts the
KV cache size, but it creates a scaling issue as the latent must be kept
whole on every GPU, so it cannot be sharded efficiently in distributed
inference. ![GLA](./paged_attention_assets/13_gla.webp) **GLA** fixes
this by splitting heads into groups, each with its own latent. Now the
cache divides naturally across GPUs, with each device holding only its
share. This enables parallelism without increasing per-device memory. By
collapsing K and V into low-rank projections, GLA also frees parameter
budget for wider projections or more query heads. The result is better
scaling, smoother latency across batches, and more hardware-friendly
efficiency, especially for long contexts or large workloads. </span>:

- [**Multi head Latent Attention
  (MLA)**](https://arxiv.org/pdf/2405.04434): Stores K and V in a
  learned low-dimensional latent space and projects in and out as
  needed. This can reduce KV cache size and bandwidth while trading a
  small amount of extra compute for the projections. This is famously
  used in DeepSeek V2 and later follow ups.

- [**Grouped Tied Attention (GTA)**](https://arxiv.org/pdf/2505.21487):
  Ties keys and values within each group, reducing cache size and memory
  traffic at decode while maintaining GQA-level quality. The tied KV
  vectors are created using a single projection. The full vector is
  cached and used as the value (without rotation). For the key, only the
  first half is taken unrotated, while the second half comes from a
  separate one-head projection with RoPE, broadcast across groups. This
  halves the KV cache, cuts memory traffic, and doubles arithmetic
  intensity compared to GQA.

- [**Grouped Latent Attention
  (GLA)**](https://arxiv.org/pdf/2505.21487): Stores K and V in a latent
  representation optimised for efficient parallel sharding. This
  achieves MLA-like compression while being more hardware-friendly and
  more suitable for distributed inference.

## The Problem with Naive KV Caching

While KV caching solves the redundant recomputing issue, it shifts the
bottleneck heavily to memory and introduces significant memory
management problems as context lengths grow. Every active request grows
a trail of keys and values token by token, and that trail must live on
the GPU for fast reads during decode. As soon as we try to serve many
requests together using continuous batching for ex., throughput stops
being compute bound and becomes memory bound. This is mainly due to two
things: first, as the KV cache size grows, we are limited in how many
requests we can process together in a batch, which reduces throughput,
and second, when memory is not allocated efficiently, naive KV caching
leads to severe fragmentation, both internal and external.

### Memory scaling

The KV cache’s memory usage scales linearly with sequence length,
consuming substantial GPU memory. For each generated token, caches must
store a key and value vector per transformer layer and head. Let’s put
numbers on this with LLaMA-2–13B. The cache size can be estimated by:

``` math
KV_{cache\_ size} = 2\times bytes\times n_{layers}\times B\times n_{heads}\times d_{head}\times n_{seq}
```

where  
$`n_{layers}`$ = number of transformer layers (blocks)  
$`B`$ = batch size  
$`n_{heads}`$ = number of attention
heads<span class="sidenote-ref"></span><span class="sidenote">For MQA
that reduces to just 1 and for GQA that depends on the number of
groups.</span>  
$`d_{head}`$ = per-head dimension  
$`n_{seq}`$ = sequence or context length  
2 = two caches per layer for Key and
Value<span class="sidenote-ref"></span><span class="sidenote">This is
the main component MLA and GLA reduce, making that 1 instead of
2!</span>

Calculating using the formula we just stated, for LLaMA-2-13B in FP16 (2
bytes per element), with standard multi-head attention (40 layers, 40
heads, and $`d_{head}`$ equal to 5120/40 = 128 over its default
4096-token context, the per-token KV cache comes to approximately
0.78125 MiB. For the full 4096 token window, the KV cache size is about
3.125 GiB. When we increase batch size, the total memory footprint
scales linearly with each additional sequence adding a further ~0.78125
MiB per token.

We now understand that the KV cache prevents us from processing or
generating very long sequences (i.e. obstacle long context windows) and
from processing large batches and therefore from maximizing our hardware
efficiency.<span class="sidenote-ref"></span> <span class="sidenote"
style="counter-increment:none">
<img src="./paged_attention_assets/14_memlay.webp"
style="width:280px;max-width:none;display:block;margin:0 auto"
alt="memlay" /> On an NVIDIA A100 40 GB, a 13B FP16 model uses ≈26 GB
for weights, leaving ≈12 GB for the KV cache. With full multi-head
attention the KV per token is ≈0.8 MB, so the card can hold ≈15k tokens
of KV in total. With a 2048-token context window, that works out to ≈7
sequences resident at once. Prompt tokens simply consume part of the
2048 budget, so concurrency stays about the same while fewer new tokens
can be produced per sequence. The practical takeaway is that decode
throughput is capped by KV capacity. Paged KV caching is what we focus
on here, but KV quantisation (which I discuss in the appendix) and
alternative attention mechanisms that shrink the KV footprint also help.
</span>

Thats one issue, next we will see the memory fragmentation issue.

| Model       | n_layers | n_heads | d_head | d_model |
|-------------|----------|---------|--------|---------|
| Llama-2-7B  | 32       | 32      | 128    | 4096    |
| Llama-2-13B | 40       | 40      | 128    | 5120    |
| OPT-7B      | 32       | 32      | 128    | 4096    |
| OPT-13B     | 40       | 40      | 128    | 5120    |
| OPT-30B     | 48       | 56      | 128    | 7168    |
| OPT-66B     | 64       | 72      | 128    | 9216    |
| OPT-175B    | 96       | 96      | 128    | 12288   |

### Fragmentation in continuous batch