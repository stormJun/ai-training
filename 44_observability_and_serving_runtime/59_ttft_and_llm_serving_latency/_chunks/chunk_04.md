 **internal fragmentation**, but that
is bounded by at most $`B - 1`$ token slots per request, not the whole
context length if you remember from before. The block size **$`B - 1`$**
trades pointer chasing against packing efficiency. Larger blocks reduce
lookups but make reuse coarser. Smaller blocks increase flexibility and
reduce unused slots in the last block, at the cost of a few more
lookups.

This is an example of how memory sharing would look like with initially
two prompts that share the same prefix or prompt. When later they want
to produce new tokens the cache manager allocates a fresh block for that
request and does a copy on write, copying the same KV caches to another
area which then allows each request to have its own "copy" and block
which is used to place its new tokens.

![memshare](./paged_attention_assets/21_memshare.gif)

This layout directly fixes what we saw earlier. **Internal
fragmentation** shrinks because the system never reserves worst case
slabs. It allocates only the blocks that are actually used, one block at
a time as decode progresses. **External fragmentation** largely
disappears because allocation is always in identical blocks, so free
space does not turn into unusable holes. Any free block can be assigned
to any request, and the block table hides the fact that blocks are
scattered.

There are also practical wins for batching and decoding. Continuous
batching is smoother because requests of very different lengths can be
mixed without wasting memory. Memory sharing avoids duplication and is
cheap to represent. If you sample multiple completions from the same
prompt or run beams that share an early prefix, all those paths can
share the same physical prefix blocks and diverge only when new tokens
are produced. The block table simply points more than one request to the
same read only blocks, which saves memory without copying. Finally,
paging gives a clear behaviour under pressure. If the pool runs out of
free blocks when the scheduler wants to advance a batch, the system can
pause new prefill work, evict lower priority requests by returning their
blocks to the pool, or fall back to recompute strategies where
acceptable. All of these choices happen at the level of KV blocks, which
keeps the policy simple and predictable.

## Paged Attention Mechanism

**PagedAttention** is the compute side that makes paged KV caching
actually work. Classic attention assumes the keys and values for a
sequence sit in one contiguous buffer. PagedAttention removes that
assumption. It cuts the cache for each request into equal sized KV
blocks as we saw previously, then drives attention by following the
request’s block table so that blocks can live anywhere in GPU memory
while the maths remains identical to standard attention.

Here is a simple example with the query token *soon*. The past tokens of
this sequence are spread across three different KV blocks:

- Block 1 stores sing, calm, night, bring
- Block 3 stores peace, soon
- Block 7 stores Sun, sets, low, bid

<div style="text-align:center">

<img src="./paged_attention_assets/22_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

Even though these tokens live in non-contiguous memory, the block table
ensures the kernel can still traverse them in the correct logical order
and compute attention as if they were all next to each other in a single
buffer.

The blocks are numbered $`j = 1,2,3,\ldots`$. Block $`j`$ simply
contains the keys and values for the $`B`$ tokens whose positions fall
in that range:

``` math
K_{j} = \left\lbrack k_{(j - 1)B + 1},\ldots,k_{jB} \right\rbrack,\qquad V_{j} = \left\lbrack v_{(j - 1)B + 1},\ldots,v_{jB} \right\rbrack.
```

So $`K_{1}`$ holds the first $`B`$ keys of the sequence, $`K_{2}`$ holds
the next $`B`$, and so on. $`V_{j}`$ is the same idea for values.

For the current query token $`i`$ with query vector $`q_{i}`$ and head
dimension $`d`$, we can compute attention by visiting these blocks one
by one. Written in block form:

``` math
A_{ij}\; = \;\frac{\exp\!\left( q_{i}^{\top}K_{j}\,/\,\sqrt{d} \right)}{\sum_{t = 1}^{\lceil i/B\rceil}\exp\!\left( q_{i}^{\top}K_{t}\,/\,\sqrt{d} \right)},
```

 

``` math
o_{i}\; = \;\sum_{j = 1}^{\lceil i/B\rceil}V_{j}\, A_{ij}^{\top}.
```

Here $`A_{ij} = \left( a_{i,(j - 1)B + 1},\ldots,a_{i,jB} \right)`$ is
the vector of attention weights for the tokens inside block $`j`$. The
vector $`o_{i}`$ is the usual attention output for token $`i`$.

What the kernel does is straightforward. It walks the request’s block
table in logical order. For each block $`j`$ it looks up where that
block lives in GPU memory, loads the keys $`K_{j}`$, forms the partial
scores

``` math
q_{i}^{\top}K_{j}/\sqrt{d},
```

updates a **running softmax
normaliser**<span class="sidenote-ref"></span>  
<span class="sidenote" style="counter-increment:none">I couldn't find
more info on whether that is exactly the same as the online softmax used
in [Flash Attention](https://arxiv.org/pdf/2307.08691), but it is likely
very similar.</span> that spans all seen blocks, then multiplies the
normalised weights with the values $`V_{j}`$ and adds the result into
$`o_{i}`$. Because the softmax runs across several blocks, the kernel
keeps a running maximum and a running sum while it streams. This gives
exactly the same numbers you would get if all keys and values sat in one
contiguous array.

Now let’s see some numbers to understand what this approach optimised
for:

Previous systems wasted **60%–80%** of the KV cache memory, whereas vLLM
achieves near-optimal memory usage with less than **4%** waste. Because
of this improved memory efficiency, we can require fewer GPUs to achieve
the same output, so throughput is significantly higher than that of
other inference engines. This virtual memory-inspired attention design
therefore bounds **internal fragmentation** by the size of the blocks
and eliminates **external fragmentation**. The following plot from the
paper shows the different types of memory waste for the same model
across three different serving systems compared to vLLM’s paged
attention:

<div style="text-align:center">

<img src="./paged_attention_assets/23_transformers.webp"
style="width:70.0%" alt="Transformers" />

</div>

Before concluding, it is important to note a caveat when applying the
virtual memory and paging technique to other GPU workloads. The idea of
virtual memory and paging is effective for managing the KV cache in LLM
serving because the workload requires dynamic memory allocation and
performance is bound by GPU memory capacity. However, this does not
generally hold for every other AI workload. In DNN training, the tensor
shapes are typically static, so memory allocation can be optimised ahead
of time. In serving DNNs that are not LLMs, an increase in memory
efficiency may not result in performance gains since the workload is
primarily compute-bound. In such scenarios, introducing vLLM’s
techniques could even degrade performance due to the extra overhead of
memory indirection and non-contiguous block access. That said, it would
still be exciting to see these techniques applied to other workloads
with properties similar to LLM serving.

------------------------------------------------------------------------

## Appendix: Other Inference Optimisation Techniques

### Static vs Continous Batching

Batching helps mitigate the memory bandwidth constraints LLMs face,
since they often waste a lot of GPU compute by shuttling data and
loading parameters. Instead of loading model parameters for every
request, you load them once and use them to process many input sequences
or requests. This uses the chip memory bandwidth more efficiently,
leading to higher compute utilisation, higher throughput, and cheaper
LLM inference.

**Static batching** is the traditional style, where the server waits
until a fixed number of requests arrive and then processes them together
as a single batch. It is called static because the batch size stays
constant until inference completes.

- The first request in a batch is forced to wait for the last one,
  adding unnecessary delay. Picture a printer that won’t start printing
  until you’ve queued up a set number of documents, regardless of how
  long it takes for the last document to arrive.

- Not all requests in a batch are created equal. In LLM inference, some
  requests may generate very short responses, while others could involve
  lengthy, step-by-step reasoning. Since all requests in the batch must
  wait until the slowest one finishes, this can lead to wasted compute
  resources and increased latency.

Without restrictive assumptions on user input and model output lengths,
unoptimised production grade LLM systems cannot serve traffic without
underutilising GPUs and incurring unnecessary cost. We need to optimise
how we serve LLMs for their power to be broadly accessible.

![StaticBatching](./paged_attention_assets/24_staticbatching.webp)

Instead of waiting until every sequence in a batch has finished
generation, in the paper [Orca: A Distributed Serving System for
Transformer Based Generative
Models](https://www.usenix.org/conference/osdi22/presentation/yu) they
implement **iteration level scheduling** where the batch size is chosen
per iteration. The result is that once a sequence in a batch has
finished generation, a new sequence can be inserted in its place,
yielding higher GPU utilisation than static batching. There is sometimes
confusion in the literature that calls this dynamic, but **continuous**
fits better, with **dynamic** reserved for a different
strategy.<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![BatchingTypes](./paged_attention_assets/25_batchingtypes.svg) In
**static batching** the server waits until a fixed number of requests
arrive and then processes them together as a single batch. **Dynamic
batching** still collects incoming requests into batches, but it does
not insist on a fixed batch size. Instead it uses a time window and
processes whatever arrives in that window. If the batch hits its size
limit sooner, it launches immediately. This is like a bus that leaves on
a strict schedule or whenever it is full, whichever comes first.
**Continuous batching** does not wait for all sequences in a batch to
finish, it groups sequences at the iteration level. </span> .If you are
interested, this blog post: [How continuous batching enables 23x
throughput in LLM inference while reducing p50
latency](https://www.anyscale.com/blog/continuous-batching-llm-inference),
explains this in more detail. Thanks to the authors as well for
providing the figures above that help visualise these strategies.

![Continous-batching](./paged_attention_assets/26_continous-batching.webp)

### Speculative Decoding

The vanilla generation process outputs only one token at a time at each
decoding step. The main point however is that to generate K tokens, you
would need to do K forward passes of the model, and as explained in the
post this is sequential by nature which doesn’t again utilise compute
resources well as step t+1 depends on generations up until step t.

So, token generation time increases linearly. That actually also ties to
the different batching strategies explained above, because in the static
batching scenarios, throughput is bottlenecked by this linear growth. So
more supporting arguments for why continuous batching mitigates this
bottleneck.

The larger the LLM, the more competent it can be. However, these larger
models are also slower, as each decoding step needs to read the entirety
of the model’s weights.

The team from Google Research therefore proposed **speculative
decoding** in [Fast Inference from Transformers via Speculative
Decoding](https://arxiv.org/pdf/2211.17192). The algorithm speeds up
generation for autoregressive models by computing several tokens in
parallel through a draft "smaller" model which proposes several draft
tokens ahead and a larger model whi