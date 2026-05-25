# LlamaIndex + Elasticsearch 混合检索整理笔记

> 来源主题：高级 RAG 检索策略之混合检索（Hybrid Retrieval）  
> 参考链接：<https://zhaozhiming.github.io/2024/06/01/llamaindex-llama3-es-hybrid-search/>

## 1. 核心结论

混合检索（融合检索、多路召回）本质是：**同一个问题，用多种检索方式并行召回，再融合排序得到最终结果**。  
在 RAG 场景中，单一路径常有盲区：

1. 纯向量检索：语义强，但可能丢关键词精确匹配。
2. 纯关键词检索（BM25）：精确匹配强，但语义泛化弱。

因此推荐：**BM25 + Dense/Sparse Vector + RRF 融合 + Rerank 重排**。

---

## 2. 混合检索流程

1. 查询输入（可选：LLM 改写/扩写查询）。
2. 多路检索并行执行（如 BM25、Dense、Sparse）。
3. 结果去重与融合（常见算法：RRF）。
4. 可选二次重排（Rerank）。
5. 送入生成模型回答。

工程价值：

1. 提升召回全面性（兼顾语义与关键词）。
2. 降低“检索偏科”风险。
3. 在复杂问答中通常优于单一路径检索。

---

## 3. 环境与组件角色

示例体系中包含 4 类模型/服务：

1. LLM：Llama3（本地部署，OpenAI 兼容接口）。
2. Embedding：用于向量化文档与查询（示例用 TEI 部署）。
3. Rerank：对候选结果重新排序（示例用 TEI 部署）。
4. 向量/检索引擎：Elasticsearch（支持 BM25、Dense、Sparse）。

---

## 4. LlamaIndex 接入要点

## 4.1 接入本地 LLM（OpenAILike）

`OpenAILike` 是快速接入 OpenAI 兼容 API 的轻量方式。

关键参数：

1. `model`：模型名（例如 `llama3`）。
2. `api_base`：本地服务地址。
3. `api_key`：必须传（可填占位值）。
4. `is_chat_model=True`：声明对话模型。

## 4.2 接入 Elasticsearch

通过 `ElasticsearchStore` 指定 ES 索引和地址，作为检索/向量存储后端。

---

## 5. 三类检索策略

## 5.1 全文检索（BM25）

使用 `AsyncBM25Strategy()`。  
优势：关键词精确匹配强，适合实体名、版本号、术语检索。

## 5.2 向量检索（Dense）

使用 `AsyncDenseVectorStrategy()`（默认常见路径）。  
优势：语义理解强，适合表达变化较大的自然语言查询。

## 5.3 稀疏向量检索（Sparse）

使用 `AsyncSparseVectorStrategy(model_id=...)`。  
优势：可与 ES 稀疏能力结合，兼顾一定语义与词项稀疏特征。

---

## 6. 混合检索与 RRF 融合

## 6.1 直接 Hybrid

`AsyncDenseVectorStrategy(hybrid=True)` 可启用混合检索能力。  
若环境/版本限制不能直接用 ES 内建融合，可自行实现 RRF。

## 6.2 RRF（Reciprocal Rank Fusion）思路

对于多个检索器结果，按排名累加倒数分：

$$
\text{score}(d)=\sum_{r \in R}\frac{1}{k+\text{rank}_r(d)}
$$

其中：

1. `R`：检索器集合（如 BM25、Dense）。
2. `rank_r(d)`：文档 `d` 在检索器 `r` 的排名（从 0 或 1 开始，代码保持一致即可）。
3. `k`：平滑常数（常见如 60）。

效果：对“多路都靠前”的文档给更高融合分，降低单一路径偏差。

### 一个直观例子

假设有两个检索器：`BM25` 和 `Dense`，每个返回 Top3：

1. BM25 排名：`A(1), B(2), C(3)`
2. Dense 排名：`B(1), D(2), A(3)`

取 `k=60`，按公式计算：

1. `score(A) = 1/(60+1) + 1/(60+3) = 1/61 + 1/63 ≈ 0.032266`
2. `score(B) = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ≈ 0.032522`
3. `score(C) = 1/(60+3) = 1/63 ≈ 0.015873`
4. `score(D) = 1/(60+2) = 1/62 ≈ 0.016129`

最终融合排序：

1. `B`（两个检索器都靠前，得分最高）
2. `A`（两个检索器都出现，但一个靠后）
3. `D`（只在 Dense 出现，但排名较靠前）
4. `C`（只在 BM25 出现，且排名更靠后）

这说明 RRF 的核心特性是：

1. 同时被多路检索命中的文档更容易排到前面。
2. 排名越靠前，贡献越大。
3. 不依赖不同检索器的原始分数可比性，只依赖“名次”。

---

## 7. 异步并行与自定义融合检索器

工程上建议：

1. 用 `aretrieve` 并行跑多路检索，减少串行等待。
2. 将多路结果汇总为 `results_dict`。
3. 用 `fuse_results` 做 RRF 融合排序。
4. 封装 `FusionRetriever(BaseRetriever)`，统一对外 `retrieve`。

这样可以把“多检索器 + 融合逻辑”模块化，便于扩展更多召回源。

---

## 8. 融合后再 Rerank

RRF 融合后的分值偏“排名融合分”，不一定等价语义相关性分。  
推荐在融合后接 `Rerank` 再做一次候选精排，典型方式：

1. `RetrieverQueryEngine(fusion_retriever, node_postprocessors=[rerank])`
2. 最终再给 LLM 生成答案。

收益：

1. 答案来源更集中。
2. 错误上下文干扰更少。
3. 生成质量更稳定。

---

## 9. 一份最小工程化组合（建议）

1. 文档入库：`SentenceSplitter(chunk_size=256, chunk_overlap=50)`。
2. 双路检索：`BM25 + Dense`（必要时加 Sparse）。
3. 融合：RRF（或 ES 原生融合）。
4. 精排：Rerank（top_n 控制上下文规模）。
5. 回答：`RetrieverQueryEngine` + LLM。

---

## 10. 常见坑

1. 只做单路检索：覆盖面不足，问法变化时波动大。
2. `top_k` 过大不加重排：噪声上下文增多。
3. 忽略异步并行：混合检索延迟明显升高。
4. 把融合分当最终相关性分：缺少 rerank 时质量不稳。
5. Embedding/Rerank/LLM 模型不匹配：整体效果上限受限。

---

## 11. 与本目录 Notebook 的对应关系

本笔记对应：

- `llamaindex_10_es_hybrid_retrieval.ipynb`

可与以下内容联动学习：

1. `llamaindex_05_chunking_strategies.ipynb`（切片影响召回上限）。
2. `llamaindex_08_hyde_query_transform.ipynb`（查询改写提升召回命中）。
3. `llamaindex_06_similarity_postprocessor.py`（后处理降噪）。
