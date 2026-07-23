# Paged Attention from First Principles: A View Inside vLLM

*11 Sep, 2025*

Large language models (LLMs) are **trained** in highly parallel,
**compute-bound** workloads, but serving them is very different:
**inference** is **memory-bound** and sequential. Optimising inference
is critical because no one will use a chatbot that lags behind typing or
a tool that takes minutes to respond. On the business side, squeezing
more out of each GPU directly reduces costs and maximises ROI.

A key bottleneck is the **key-value (KV) cache**, which stores
contextual information during decoding. Prior systems wasted **60-80%**
of this memory due to fragmentation, limiting throughput.
**PagedAttention**, proposed by Kwon et al. in [Efficient Memory
Management for Large Language Model Serving with
PagedAttention](https://arxiv.org/pdf/2309.06180), solves this by
borrowing the idea of virtual memory from operating systems. The result
is near optimal memory usage with under **4%** waste and **2-3x higher
throughput**.

In this post I will build up from first principles, starting with
training versus inference workloads, moving to naive KV caching, the OS
analogy, and finally how paged KV caching and PagedAttention make LLM
serving faster and more efficient. These techniques are already
supported in major inference systems such as
[vLLM](https://github.com/vllm-project/vllm), [TensorRT
LLM](https://github.com/NVIDIA/TensorRT-LLM), and [Hugging Face
TGI](https://github.com/huggingface/text-generation-inference/tree/main).
In the appendix, I also go through other inference optimisation
techniques like continuous batching, speculative decoding, and touch
briefly on quantisation.

## LLM Training vs Inference

To understand the inference challenges, it helps to contrast how LLMs
are used in training versus how they are used in deployment. At a high
level, training is when the model learns from data, making predictions
by going forward through the network’s layers (the **forward pass**),
comparing those predictions to the known targets, calculating the
**loss** through a **loss function** (i.e. how far we are from the
correct predictions), and then adjusting the weights via
**backpropagation** and some form of gradient
descent.<span class="sidenote-ref"></span> <span class="sidenote">
<img src="./paged_attention_assets/01_mlp.gif"
style="width:375px;max-width:none;display:block;margin:0 auto"
alt="MLP" /> That flow is the core of any neural network’s architecture,
the input moves left to right through the layers until the output is
compared to the target and the loss is calculated. The network then
flows in the opposite direction, each layer computing gradients for its
weights and passing error backwards until the first layer, at which
point we have gradients for all
parameters.<img src="./paged_attention_assets/02_blocks.webp"
style="width:330px;max-width:none;display:block;margin:0 auto"
alt="blocks" /> For each layer this means the forward step produces the
output that flows onward, while the backward step calculates gradients
for the weights and sends the error backwards.
<img src="./paged_attention_assets/03_opt.webp"
style="width:330px;max-width:none;display:block;margin:0 auto"
alt="opt" /> Once gradients are available, the optimiser updates the
weights using them along with its internal state, teaching the network
from its errors. One forward pass, loss calculation, backward pass, and
update makes a training step, repeated many times across **epochs** to
gradually improve predictions. Visuals taken from: [Data-Parallel
Distributed Training of Deep Learning
Models](https://siboehm.com/articles/22/data-parallel-training) </span>

Training especially for large language models is extremely expensive in
terms of compute. Models at this scale are trained on massive clusters
of GPUs, TPUs, or other specialised accelerators like Cerebras Wafer
Scale<span class="sidenote-ref"></span> <span class="sidenote">
<img src=""
style="width:330px;max-width:none;display:block;margin:0 auto"
data-uaythywtmvkoxauxidjzryzu3nevtm1lvwm15kza0l2dvwdeyk09nb3p0azq5lytoz0hunwvwnnruwtn4qw1urnnzsjh1v3htbe0=""
alt="Cerebras" /> On the left is a new AI chip from a startup named
Cerebras, the largest in production with 4 trillion transistors and
about 900,000 compute cores. In inference, it runs OpenAI’s GPT-OSS 120B
at around **2,700 tokens/sec** for both single-user and multi-user
setups. By comparison, NVIDIA Blackwell DGX B200 reaches about **900
tokens/sec** for one user and drops to **580 tokens/sec** with ten
users. For a breakdown of the hardware differences, see [this
talk](https://youtu.be/7GV_OdqzmIU?si=HW99JXE1MrLbMlTg) by Jean-Philippe
Fricker, the co-founder and chief system architect. You can also try
their [chat service](https://chat.cerebras.ai/) to get a feel for
high-throughput inference in practice. I think it’s a good primer to
understand what fast inference really looks like before we dig deep into
this blog. Just want to note that I have no affiliation with them.
Everything I write here is based on pure interest.  
</span>, Graphcore IPUs, or Tenstorrent hardware. Although NVIDIA GPUs
remain the most common choice today, training runs are more or less a
one-time expense, often costing tens of millions of dollars. Inference,
by contrast, is when we fix those learned weights and use the model to
generate predictions or responses for new inputs. While this distinction
sounds straightforward, the workflows differ significantly in practice,
and they require different optimisation strategies.

At the heart of all LLMs is the **transformer** architecture, introduced
in the [“Attention Is All You Need”](https://arxiv.org/pdf/1706.03762)
paper. Despite many variations and improvements since, it remains the
foundation of state-of-the-art models. On the left below is the original
**decoder-only** transformer, and on the right is the Llama-2 70B
architecture, which illustrates some of these later refinements:

<div style="text-align:center">

<img src="./paged_attention_assets/04_transformers.svg"
style="width:70.0%" alt="Transformers" />

</div>

The flow of the network starts from raw text whether that is training
data or actual prompts during inference. The model does not understand
human characters directly, so the first step is **tokenisation**. This
breaks the text down into a sequence of token ids that the model can
process. Each id is then mapped into a dense vector space through
**embeddings**, which gives the model a numerical representation of the
input. **Positional encodings** are added to these vectors as well so
that the model can tell where each token sits in the sequence.

From there, the sequence flows through the stack of transformer decoder
blocks. Each layer lets tokens interact with one another through
**multihead-attention** with a **causal mask** to preserve the
*autoregressive* property of language. This builds richer context before
passing through feedforward transformations that expand and filter
features. Networks also have **residual connections**, which add the
input of a layer back to its output so the signal does not fade, as well
as **normalisation** to stabilise the weights.

There are some architectural differences to note. For example, LLaMA-2
70B uses Grouped Query Attention (GQA), a variant of attention that
reduces memory demands. Most modern LLMs also place the normalisation
layer before each block rather than after, which is different from the
original Transformer. Still, the high-level flow remains the same:
tokenised input goes in, contextualised embeddings come out.

At the end of the stack, the model projects everything back onto the
vocabulary space, producing a distribution over the next possible
tokens. During training, this is compared to the ground truth next
tokens for every position in the sequence. This is why LLMs are often
described as being trained on **next token prediction tasks**. There are
further stages of training, such as reinforcement learning with human
feedback (RLHF), which tune the model to respond in a more human-like
way as we experience in modern chat systems.

<div style="text-align:center">

<img src="./paged_attention_assets/05_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

To make this concrete before moving to inference, consider the example
sequence Coffee solves everything, with a start-of-sequence token
\[SOS\] at the beginning. We feed in the sequence, tokenised
appropriately<span class="sidenote-ref"></span> <span class="sidenote">
<img src="./paged_attention_assets/06_tokenised.webp"
style="width:250px;max-width:none;display:block;margin:0 auto"
alt="tokenised" /> This sequence for example is split into 4 tokens by
the GPT-4o tokeniser with ids \[90651, 6615, 3350, 28997\] respectively.
</span>, and at each position the model is asked to predict the next
word. \[SOS\] predicts Coffee, \[SOS Coffee\] predicts solves, \[SOS
Coffee solves\] predicts everything, and so on until the model predicts
an end-of-sequence token \[EOS\].

Now here is the crucial point. During training, we already know the full
sequence. This allows us to feed the entire sequence through the
transformer in a single forward pass. The causal mask ensures that token
$`t`$ does not attend to token $`t + 1`$, so the autoregressive property
is respected, but the predictions for all positions are computed in
parallel. GPUs excel at this parallelism, so their compute cores are
fully saturated with work. In other words, training is compute bound. By
**compute-bound**, we mean that increasing the raw computational power
of the hardware directly speeds up training, while memory bandwidth is
not the limiting factor

Inference is different in nature. The model does not see the future
tokens, so it cannot process the entire sequence in parallel after the
prompt. It must step through one token at a time, with each new token
appended to the context. That means the GPU is no longer crunching
large, dense matrix multiplications that are heavily optimised for AI
workloads across many tokens at once. Instead, it is handling small,
repeated steps dominated by memory access, loading model weights and
cached activations again and again.

This shift in workload is important. When the bottleneck moves from
heavy compute to frequent data movement, performance drops. Moving data
is always more expensive than doing math on it. This is why inference
tends to be **memory-bound**, while training remains compute-bound.

## The Two Phases of Inference

The entire inference process when a user sends a prompt is split into
two phases:

- **Prefill (prompt phase)**: The model reads the entire input prompt
  and prepares to generate the first token.
- **Decoding**: The iterative loop where tokens are produced one by one
  sequentially.

These two phases have very different characteristics and bottlenecks.

<div style="text-align:center">

<img src="./paged_attention_assets/07_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

**Prefill**

During prefill, the model can still leverage its parallelism to process
the prompt tokens. All the input tokens (say the prompt is N tokens
long) are fed through the transformer network together in one forward
pass. This is typically a large matrix multiplication workload which
keeps the GPU’s compute units busy. As a result, prefill is usually
compute bound. In fact, this process shares more of the characteristics
of training, without the backpropagation of course.

The output of this stage is the first predicted token by the model and a
set of key/value pair vectors stored for each attention layer of each
prompt token, commonly known as the **KV cache**. We will ignore this
for now and return to it later. For now, just assume the end of this
process is a new predicted token.

The time until this first token is predicted is an important inference
metric called **time to first token (TTFT)**. TTFT grows with prompt
lengt