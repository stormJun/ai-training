ch then verifies these proposed
tokens in parallel and accepts those that match its own predictions.

This approach was inspired from two key observations:

1.  Some tokens are easier to generate than others: Many next tokens are
    obvious from context and can be proposed by a smaller model.
2.  The bottleneck for inference is usually memory not compute.

Speculative decoding is inspired by an optimisation technique called
**speculative execution**, which was generalised further
probabilistically and applied to autoregressive models. Briefly:

- **Speculative execution**: Let’s assume we have two slow steps: first
  compute $`Y = f(X)`$, then compute $`Z = g(Y)`$. Normally, we can’t
  start $`g(Y)`$ until we know $`Y`$, forcing strict serial dependence.
  Speculative execution says “What if I can *guess* $`Y`$ using a
  **cheap approximation** $`f^{}(X)`$, then start $`g(f^{}(X))`$ in
  parallel?” Once the original $`f(X)`$ finishes, I check the guess. If
  it matches, I saved time by parallelising something that was
  originally serial. If it doesn’t, I discard the speculative work and
  fall back to the original. Either way, correctness is guaranteed, but
  when the guesser is good, we gain significant speedup.

- **Speculative sampling**: LLMs don’t produce a single next token, but
  rather a probability distribution from which we sample the next token
  (side note: think softmax over the vocabulary). This makes the output
  stochastic, not deterministic. So this new method extends the above by
  introducing a probabilistic acceptance rule. At each step we have
  $`f(X)`$, the true distribution from the large model, and
  $`f^{*}(X)`$, an approximate distribution from a smaller model. We let
  the draft sample a token and immediately start downstream computation
  with it. There’s a caveat, though: because the output is stochastic,
  we can’t just accept if the draft and target happen to pick the same
  token. With vocabularies in the tens of thousands, that would almost
  always fail, wasting work.

- **Speculative decoding**: Speculative sampling fixes this by
  introducing a **probabilistic filter**. When the draft model samples a
  token, we check how much probability the large model assigns to that
  token. If the large model also thinks it’s likely, we accept the
  draft’s choice with high probability. If the large model thinks it’s
  less likely, we reject more often and fall back to resampling directly
  from the large
  model<span class="sidenote-ref"></span><span class="sidenote"
  style="counter-increment:none">
  ![](./paged_attention_assets/27_image.webp) The baseline (dotted line)
  corresponds to naïve decoding: always one token per step. With
  speculative decoding, as α increases (draft guesses are more often
  correct) and as γ grows, the effective tokens per iteration rises
  significantly. For example, with γ = ∞ and α close to 0.9, the system
  can generate nearly 10 tokens per iteration, compared to just 1 in the
  baseline. We just gained free parallelism! Better draft models and
  larger lookaheads directly translate into higher speedups. </span>.
  With this approach, we are guaranteed that despite the lower cost, the
  generated samples come from exactly the same probability distribution
  as those produced by naïve decoding.

For more details and examples, Google Research also put out this [blog
post](https://research.google/blog/looking-back-at-speculative-decoding/)
to explain the concept in more detail.

In the original paper, **speculative decoding** demonstrated a **2×–3×**
wall-time speedup on models like T5-XXL, while maintaining identical
output distributions.

<a
href="https://storage.googleapis.com/gweb-research2023-media/media/SpeculativeDecoding-1-Illustration.mp4"
style="z-index:2147483647!important;position:absolute!important;top:8px!important;left:8px!important;width:16px!important;height:16px!important;min-width:16px!important;min-height:16px!important;max-width:16px!important;max-height:16px!important"
target="_blank"><img src="./paged_attention_assets/28_image.png"
style="width:16px!important;height:16px!important;min-width:16px!important;min-height:16px!important;max-width:16px!important;max-height:16px!important" /></a>

### Quantisation

Another very important and heavily researched optimisation direction is
also **quantisation**. State-of-the-art models nowadays are casually in
the order of billions of parameters. To put this into perspective,
[Hunyuan-Large](https://arxiv.org/abs/2411.02265), an open-source
Mixture-of-Experts model, has **389 billion total parameters** with only
**52 billion active per inference step**—“only,” I say
sarcastically—that is still massive. DeepSeek-V3 has **671 billion total
parameters**, with about **37 billion active** during token generation.
You get the point.

Even though active parameters are much smaller than the total weights,
inference still requires **all parameters in memory** (for example, GPU
VRAM) since different experts are chosen for every layer and every
token. This means the total model size sets the minimum memory
requirement. A natural direction, then, is to make models smaller so
they require less memory. But what does “smaller” mean?

Parameters are usually stored as **floating-point numbers**, and
inference involves huge amounts of floating-point operations (FLOPs).
There are different floating-point precisions. Intuitively, by lowering
the precision we massively reduce memory usage, albeit at the potential
cost of accuracy. Finding that balance is a major research focus. Before
continuing, it makes sense to point out the main floating-point
precisions: <span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![](./paged_attention_assets/29_image.svg) </span>

![precisions](./paged_attention_assets/30_precisions.svg)

There are others too, but these are the main ones. In practice,
quantisation today often uses **integer-based
formats**<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none">
![ranges](./paged_attention_assets/31_ranges.webp) The more bits used to
represent a value, the more precise it is. A larger range is covered and
the distance between neighbouring values is smaller—hence higher
precision. </span>.

Inference also needs memory beyond just weights (e.g. the KV we have
been talking about until now), but let’s see how much memory DeepSeek-V3
would need solely to load the full weights ignoring the cache for now:

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

Clearly, no GPU can hold 1,342 GB. In practice, inference is distributed
across thousands of GPUs using methods like **tensor parallelism** and
**pipeline parallelism**. I won’t dive into those here, but they’re
worthwhile topics. What you can clearly see here however, is that just
by reducing precision, memory needs shrink drastically. Beyond memory
savings, integer formats like int8 or int4 may even be faster than
floating-point on some
hardware<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none"> On NVIDIA H100 Tensor Cores, peak INT8
throughput reaches ~2000 TOPS compared to ~1000 TFLOPS for FP16/BF16.
</span>.

#### Quantisation mapping

The main idea is that we want to take floats in some big range
$`\lbrack\alpha,\beta\rbrack`$ and squash them into integers in a
smaller range $`\lbrack\alpha_{q},\beta_{q}\rbrack`$. For signed INT8,
for example, that range is $`\lbrack - 128,127\rbrack`$. To make this
work, we assume a straight-line relationship between the float $`x`$ and
its quantised integer $`x_{q}`$. For more detail checkout [Lei
Mao’s](https://leimao.github.io/article/Neural-Networks-Quantization/)
blog post where he goes in depth into this. It helped me understand this
more clearly:

``` math
x = c(x_{q} + d)
```

Here $`c`$ is the scale, i.e how many float units each integer step
covers, and $`d`$ is just an offset. If we want to go the other way
(float to integer), we flip the line and round:

``` math
x_{q} = {round}\!\left( \frac{x}{c} - d \right)
```

The line has to hit the ends of both ranges, so we require:

``` math
\beta = c(\beta_{q} + d),\qquad\alpha = c(\alpha_{q} + d)
```

Subtracting these two equations gives:

``` math
\beta - \alpha = c(\beta_{q} + d) - c(\alpha_{q} + d)
```

Using distributive law:

``` math
\beta - \alpha = c(\beta_{q} - \alpha_{q})
```

which means:

``` math
c = \frac{\beta - \alpha}{\beta_{q} - \alpha_{q}}
```

Once we know $`c`$, we can plug it back into
$`\alpha = c(\alpha_{q} + d)`$ to get $`d`$:

``` math
\alpha = c\alpha_{q} + cd
```
``` math
d = \frac{\alpha}{c} - \alpha_{q}
```

and replacing $`c`$ gives:

``` math
d = \alpha\frac{\beta_{q} - \alpha_{q}}{\beta - \alpha} - \alpha_{q} = \frac{\alpha\beta_{q} - \beta\alpha_{q}}{\beta - \alpha}
```

That’s the general form tho. In practice libraries usually call
$`s = c`$ the **scale** and $`z = - d`$ the **zero point**, and the
final formulas you actually use look like this:

``` math
x = s(x_{q} - z)
```
``` math
x_{q} = {round}\!\left( \frac{x}{s} + z \right)
```

with

``` math
s = \frac{\beta - \alpha}{\beta_{q} - \alpha_{q}},\qquad z = {round}\!\left( \alpha_{q} - \frac{\alpha}{s} \right)
```

Let's run this through an example visually to map the concepts better
assuming we having a vector of 5 weights that are represented in FP32
and we would want to quantise to
int8.<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none"> In practice we do not map the entire
precision range in FP32 for thats \[-3.4e38, 3.4e38\] into INT8.
Instead, we take the actual data we want to store, find its minimum and
maximum, and fit that interval into the INT8 code range. </span>

![quant](./paged_attention_assets/32_quant.svg)

#### Symmetric vs Asymmetric Quantisation

Notice the difference. In **asymmetric quantisation** we use the true
data range, so $`\alpha`$ is the minimum of the tensor and $`\beta`$ is
the maximum. That choice gives a non-zero 0 point in code space, which
is why in the first example 0 in float was stored as the code $`21`$. We
also use the full set of INT8 codes end to end. In **symmetric
quantisation** we centre the float range around 0 by taking $`a`$ to be
the larger of the absolute min and max, then map the interval from
$`- a`$ to $`+ a`$ onto a perfectly centred code range with zero point
$`z = 0`$.

Comparing the two modes:

With asymmetric quantisation we pin the real minimum to the smallest
code and the real maximum to the largest code, so the data is spread
across all buckets. Nothing is wasted. With symmetric quantisation we
force the float interval to sit around zero. If the tensor is mostly on
one side, many buckets represent values you will never see. The extreme
case is after ReLU where everything is non negative. Asymmetric uses all
256 codes across the useful region. Symmetric keeps 128 codes for
negatives that never appear.

In asymmetric mode however, the zero points require additional logic in
hardware. That extra handling can add a little latency and complexity,
depending on the implementation.
