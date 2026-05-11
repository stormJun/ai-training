# TTFT 经典资料整理

TTFT（Time To First Token）通常指一次请求从进入服务到产出第一个 token 的耗时。它往往不只是“模型算得慢”，而是 prefill、调度、KV cache、批处理策略、流式输出链路共同作用的结果。理解 TTFT，最好把它和 ITL（Inter-Token Latency）、throughput、prefill / decode 分离、scheduler 设计放在一起看。

## 建议阅读顺序

1. 先看 **Efficient Memory Management for Large Language Model Serving with PagedAttention**，建立 vLLM / KV cache / 连续批处理的基础认识。
2. 再看 **Paged Attention from First Principles: A View Inside vLLM**，把抽象概念还原到更直观的工程实现视角。
3. 接着看 **vLLM Performance and Tuning**，理解真实系统里 TTFT、吞吐和调参之间的关系。
4. 然后看 **Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve**，理解 prefill / decode 解耦与调度优化如何改善首 token 延迟。
5. 再看 **POD-Attention: Unlocking Full Prefill-Decode Overlap for Faster LLM Inference**，理解更激进的 prefill-decode overlap 思路。
6. 最后看一篇偏工程实践的 TTFT / streaming latency 测量文章，把论文视角落到指标采集与用户体验上。

## 资料清单

### 1. Efficient Memory Management for Large Language Model Serving with PagedAttention

- 类型：paper
- 为什么重要：这是理解 vLLM、PagedAttention、KV cache 管理和连续批处理的起点。虽然它不只讨论 TTFT，但很多首 token 延迟优化都建立在更高效的内存与调度能力之上。
- 阅读关注点：
  - PagedAttention 为什么能减少 KV cache 碎片与内存浪费
  - 连续批处理如何影响等待时间与整体吞吐
  - 请求到达后，系统在哪些阶段会额外放大 TTFT
  - 为什么 serving 系统优化不等同于单卡算子优化

### 2. Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve

- 类型：paper
- 为什么重要：这篇工作直接讨论吞吐与时延的权衡，尤其适合理解 TTFT 为什么常常会被批处理策略拖慢，以及 scheduler 如何在高负载下改善体验。
- 阅读关注点：
  - Sarathi-Serve 如何拆分和组织 prefill 与 decode
  - 哪些设计是在优化平均吞吐，哪些是在优化首 token 体验
  - 调度策略怎样影响短请求与长请求之间的公平性
  - 论文如何定义和报告 latency 指标

### 3. vLLM Performance and Tuning

- 类型：official doc
- 为什么重要：这是把论文概念转成工程操作的关键材料。它能帮助你把 TTFT 放进真实部署参数、批大小、并发、chunked prefill 等调优语境中理解。
- 阅读关注点：
  - 文档里如何区分 TTFT、ITL、throughput 等指标
  - 哪些参数最容易影响首 token 延迟
  - 在不同 workload 下，吞吐优先和时延优先的配置差异
  - 如何用压测结果判断瓶颈在 prefill、decode 还是调度

### 4. Paged Attention from First Principles: A View Inside vLLM

- 类型：explanatory article
- 为什么重要：它适合作为 PagedAttention 论文的补充材料，帮助把“页式 KV 管理”与真实推理路径联系起来，更容易建立 TTFT 的系统级直觉。
- 阅读关注点：
  - 请求生命周期里 KV cache 是怎样被组织和复用的
  - 为什么内存布局会进一步影响调度弹性
  - PagedAttention 对首 token 阶段和后续 decode 阶段的不同影响
  - 阅读时把文章解释和 vLLM 官方调优文档对照起来

### 5. POD-Attention: Unlocking Full Prefill-Decode Overlap for Faster LLM Inference

- 类型：paper
- 为什么重要：这篇工作代表了更偏前沿的方向：不再只做“更好的批处理”，而是尝试让 prefill 与 decode 更充分重叠，从而进一步压缩响应等待时间。
- 阅读关注点：
  - 它试图解决的核心瓶颈到底出现在 prefill 还是 decode
  - overlap 机制成立的前提条件是什么
  - 这种方法对 TTFT、ITL、吞吐分别可能带来什么影响
  - 它与 Sarathi-Serve 的调度思想有何异同

### 6. Practical article on TTFT / streaming latency measurement

- 类型：explanatory article
- 为什么重要：补上一层工程视角。很多团队知道 TTFT 重要，但没有统一测量口径；这类文章通常会把用户感知、流式输出、服务链路与 benchmark 指标连接起来。
- 阅读关注点：
  - TTFT 的测量起点与终点如何定义
  - 流式返回时，首字节、首 token、完整响应之间如何区分
  - 哪些中间件、网关、序列化或网络因素会污染 TTFT 指标
  - 如何把线上观测与离线 benchmark 对齐

## 统一观察框架

阅读每篇资料时，建议统一比较以下几个维度：

- TTFT：首 token 何时开始出现，主要受什么影响
- ITL：后续 token 的间隔是否稳定
- Throughput：系统是否通过牺牲首 token 体验换取更高吞吐
- Prefill：长上下文输入阶段的主要成本在哪里
- Decode：逐 token 生成阶段的主要瓶颈是什么
- Scheduler：系统如何决定谁先算、谁等待、谁被合批
- KV Cache：缓存布局、分页、复用方式如何影响整体延迟
- Streaming：用户真正感知到的“开始回答”时间如何被服务链路放大或缩小

## 关联主题

- `../../../24_tooling_and_automation_workflows/25_vllm_wrapper_demo/`：从工程封装角度理解 vLLM 的实际使用方式
- `../../../40_fastapi_llm_serving/`：对照 API 服务链路，理解 TTFT 不只发生在模型内部
- `../../46_ray_serve_streaming/`：从流式输出视角观察“用户何时看到第一个 token”
- `../50_performance_benchmarking/`：把 TTFT、吞吐、压测方法放进统一性能分析框架
- `../../../53_model_extensions/53_slm_optimization/`：对照更小模型或推理优化场景，理解时延优化的不同抓手
