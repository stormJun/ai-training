# RAG LlamaIndex 学习文档

本文对应目录：`03_rag_and_retrieval/llamaindex_and_ragas/code/llamaindex`，用于帮助你快速理解每个示例文件“在做什么、能学到什么”。

## 1. 目录定位

`code/llamaindex` 里的内容可以按 4 类理解：

1. 入门与基础链路：从读文件到索引再到问答
2. 解析与切片：Document/Node、不同切片策略
3. 检索与后处理：向量检索、混合检索、相似度过滤
4. 查询增强与结构化数据：Prompt 模板、HyDE、Text-to-SQL

## 2. 文件逐个说明

| 文件 | 主要功能 | 你会学到什么 |
| --- | --- | --- |
| `llamaindex_01_quickstart.ipynb` | LlamaIndex 入门总览，包含 `SimpleDirectoryReader + VectorStoreIndex + OpenAILike/DashScopeEmbedding` 的基础 RAG 流程 | 如何配置 `Settings.llm/embed_model`，如何把文档读入并建立最小可问答链路 |
| `llamaindex_03_node_basics.ipynb` | 讲解 `Document` / `TextNode` 及节点切分 | LlamaIndex 内部数据单元如何组织，节点如何影响召回质量 |
| `llamaindex_04_custom_loader.ipynb` | 有一些是需要自定义的loader所以如何自己定义： 演示 `SmartPDFLoader` 与自定义 `BaseReader` | 如何扩展数据接入层，支持你自己的文档解析逻辑 |
| `llamaindex_05_chunking_strategies.ipynb` | 对比多种切片器：`TokenTextSplitter`、`SentenceSplitter`、`SentenceWindowNodeParser`、`SemanticSplitterNodeParser`、`MarkdownNodeParser` | 不同 chunk 策略对检索精度、上下文完整性的影响 |
| `llamaindex_06_similarity_postprocessor.py` | 检索后用 `SimilarityPostprocessor` 做阈值过滤 | 如何清理低相关结果，减少噪声上下文 |
| `llamaindex_07_prompt_template.ipynb` | `SummaryIndex` + `PromptTemplate` 自定义提示词 | 如何改写问答/总结模板，让输出更贴合业务表达 |
| `llamaindex_08_hyde_query_transform.ipynb` | `TransformQueryEngine` + `HyDEQueryTransform` 查询改写 | 如何在检索前增强用户问题，提升召回命中率 |
| `llamaindex_09_text2sql_demo.ipynb` | LlamaIndex Text-to-SQL，含 `NLSQLTableQueryEngine` 与表 schema 检索 | 如何把自然语言问题映射到 SQL，并在多表场景下做结构化查询 |
| `llamaindex_10_es_hybrid_retrieval.ipynb` | Elasticsearch 向量+关键词混合检索（`AsyncDenseVectorStrategy/AsyncSparseVectorStrategy/AsyncBM25Strategy`） | 如何搭建 Hybrid Search，平衡语义召回与关键词召回 |

## 3. 每个文件核心写了什么（稍详细）

1. `llamaindex_01_quickstart.ipynb`
- 主要代码：从本地文档到最小 RAG 闭环（读文档 -> 建索引 -> 问答）。
- 核心 API：`Settings`、`OpenAILike`、`DashScopeEmbedding`、`SimpleDirectoryReader`、`VectorStoreIndex`。
- 大概用法：先设置 `Settings.llm/embed_model`，再 `documents = SimpleDirectoryReader(...).load_data()`，然后 `index = VectorStoreIndex.from_documents(documents)`，最后 `index.as_query_engine().query("...")`。

2. `llamaindex_03_node_basics.ipynb`
- 主要代码：展示 `Document` 如何被拆分成可检索节点（`TextNode`）。
- 核心 API：`Document`、`TextNode`、`TokenTextSplitter`（或同类 NodeParser）。
- 大概用法：先构造 `Document`，再通过 splitter 生成节点，观察节点文本与元数据结构。

3. `llamaindex_04_custom_loader.ipynb`
- 主要代码：先用现成 Loader，再自定义 Reader 接入业务数据。
- 核心 API：`SmartPDFLoader`、`BaseReader`、`Document`、`load_data(...)`。
- 大概用法：继承 `BaseReader` 实现 `load_data`，返回 `list[Document]`；随后可直接喂给 `VectorStoreIndex`。

4. `llamaindex_05_chunking_strategies.ipynb`
- 主要代码：同一份文本采用多种切片策略做对比实验。
- 核心 API：`TokenTextSplitter`、`SentenceSplitter`、`SentenceWindowNodeParser`、`SemanticSplitterNodeParser`、`MarkdownNodeParser`。
- 大概用法：分别初始化不同 parser，执行切分后比较 chunk 粒度、上下文连续性与检索效果。

5. `llamaindex_06_similarity_postprocessor.py`
- 主要代码：先检索，再做相似度阈值过滤。
- 核心 API：`index.as_retriever(similarity_top_k=...)`、`retrieve(...)`、`SimilarityPostprocessor(similarity_cutoff=...)`。
- 大概用法：`nodes = retriever.retrieve(query)` 后调用 `postprocess_nodes(nodes)`，对比过滤前后结果质量。

6. `llamaindex_07_prompt_template.ipynb`
- 主要代码：替换默认提示词模板，控制回答风格与结构。
- 核心 API：`PromptTemplate`、`SummaryIndex`、`as_query_engine(...)`（模板注入）。
- 大概用法：先定义 `PromptTemplate`，再在 query engine 构建时传入模板参数，最后比较回答差异。

7. `llamaindex_08_hyde_query_transform.ipynb`
- 主要代码：对原始 query 做 HyDE 改写，再执行检索问答。
- 核心 API：`HyDEQueryTransform`、`TransformQueryEngine`。
- 大概用法：先构建基础 query engine，再用 `TransformQueryEngine(base_engine, query_transform=HyDEQueryTransform(...))` 包装。

8. `llamaindex_09_text2sql_demo.ipynb`
- 主要代码：将自然语言问题转 SQL 并查询数据库结果。
- 核心 API：`SQLDatabase`、`NLSQLTableQueryEngine`、`SQLTableNodeMapping`、`SQLTableRetrieverQueryEngine`。
- 大概用法：先把 SQLAlchemy 连接包装成 `SQLDatabase`，再初始化 `NLSQLTableQueryEngine` 或“表结构检索 + SQL 查询”组合引擎。

9. `llamaindex_10_es_hybrid_retrieval.ipynb`
- 主要代码：在 Elasticsearch 向量库上配置不同检索策略并对比。
- 核心 API：`ElasticsearchStore`、`StorageContext`、`VectorStoreIndex`、`AsyncDenseVectorStrategy`、`AsyncSparseVectorStrategy`、`AsyncBM25Strategy`。
- 大概用法：创建不同 strategy 的 ES store，构建索引后执行 query，对比 dense/sparse/BM25/hybrid 的召回表现。

## 4. Python 脚本重点

### 4.1 `llamaindex_06_similarity_postprocessor.py`

核心流程：

1. 先做原始向量检索 `similarity_top_k=5`
2. 打印原始候选节点及分数
3. 使用 `SimilarityPostprocessor(similarity_cutoff=0.71)` 过滤
4. 对比过滤前后节点数量和内容

适用场景：你希望提升检索上下文纯度，减少无关片段进入生成阶段。

## 5. 建议学习顺序

1. `llamaindex_01_quickstart.ipynb`
2. `llamaindex_03_node_basics.ipynb` + `llamaindex_05_chunking_strategies.ipynb`
3. `llamaindex_06_similarity_postprocessor.py`
4. `llamaindex_07_prompt_template.ipynb` + `llamaindex_08_hyde_query_transform.ipynb`
5. `llamaindex_09_text2sql_demo.ipynb` + `llamaindex_10_es_hybrid_retrieval.ipynb`

## 6. 运行提示

1. 先在 `03_rag_and_retrieval/llamaindex_and_ragas/code/.env` 配置 `DASHSCOPE_API_KEY`
2. 运行脚本时建议从 `03_rag_and_retrieval/llamaindex_and_ragas` 根目录启动：
   - `python code/llamaindex/llamaindex_06_similarity_postprocessor.py`
3. notebook 建议在 JupyterLab 中打开 `code/llamaindex/` 目录后按顺序学习

## 7. 每个文件最小示例（速查）

1. `llamaindex_01_quickstart.ipynb`
```python
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels

Settings.llm = OpenAILike(model="qwen-plus", api_base="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key="YOUR_KEY", is_chat_model=True)
Settings.embed_model = DashScopeEmbedding(model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3)
docs = SimpleDirectoryReader("code/data").load_data()
index = VectorStoreIndex.from_documents(docs)
print(index.as_query_engine().query("怎么休事假？"))
```

2. `llamaindex_03_node_basics.ipynb`
```python
from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import TokenTextSplitter

doc = Document(text="这里是一段长文本...")
splitter = TokenTextSplitter(chunk_size=128, chunk_overlap=20)
nodes = splitter.get_nodes_from_documents([doc])
print(type(nodes[0]), nodes[0].text[:50])
```

3. `llamaindex_04_custom_loader.ipynb`
```python
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

class MyReader(BaseReader):
    def load_data(self, file, extra_info=None):
        text = open(file, "r", encoding="utf-8").read()
        return [Document(text=text, metadata=extra_info or {})]
```

4. `llamaindex_05_chunking_strategies.ipynb`
```python
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser

s1 = SentenceSplitter(chunk_size=256, chunk_overlap=30)
s2 = SemanticSplitterNodeParser(...)
# 对同一文档分别切片，比较 node 数量与内容边界
```

5. `llamaindex_06_similarity_postprocessor.py`
```python
from llama_index.core.postprocessor import SimilarityPostprocessor

retriever = index.as_retriever(similarity_top_k=5)
nodes = retriever.retrieve("怎么休事假？")
post = SimilarityPostprocessor(similarity_cutoff=0.71)
filtered_nodes = post.postprocess_nodes(nodes)
print(len(nodes), len(filtered_nodes))
```

6. `llamaindex_07_prompt_template.ipynb`
```python
from llama_index.core import PromptTemplate

qa_tmpl = PromptTemplate("请用中文分点回答：{query_str}")
query_engine = index.as_query_engine(text_qa_template=qa_tmpl)
print(query_engine.query("这份制度的重点是什么？"))
```

7. `llamaindex_08_hyde_query_transform.ipynb`
```python
from llama_index.core.indices.query.query_transform.base import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine

hyde = HyDEQueryTransform(include_original=True)
hyde_engine = TransformQueryEngine(index.as_query_engine(), query_transform=hyde)
print(hyde_engine.query("员工请假要提前多久申请？"))
```

8. `llamaindex_09_text2sql_demo.ipynb`
```python
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

sql_db = SQLDatabase(engine, include_tables=["city_stats"])
qe = NLSQLTableQueryEngine(sql_database=sql_db)
print(qe.query("人口最多的城市是哪个？"))
```

9. `llamaindex_10_es_hybrid_retrieval.ipynb`
```python
from llama_index.vector_stores.elasticsearch import ElasticsearchStore, AsyncDenseVectorStrategy
from llama_index.core import StorageContext, VectorStoreIndex

store = ElasticsearchStore(index_name="demo", retrieval_strategy=AsyncDenseVectorStrategy())
storage = StorageContext.from_defaults(vector_store=store)
index = VectorStoreIndex.from_documents(docs, storage_context=storage)
print(index.as_query_engine().query("混合检索怎么做？"))
```

## 8. `llamaindex_05_chunking_strategies.ipynb` 切片原理补充

本 notebook 里主要演示了 5 种切片方式，核心差异是“按什么边界切”和“是否保留上下文窗口”。

1. `TokenTextSplitter`
- 原理：按 token 数硬切分，保证 chunk 大小可控。
- notebook 参数：`chunk_size=32`、`chunk_overlap=4`、`separator="\\n"`。
- 适用：需要严格控制上下文长度、追求稳定吞吐时。
- 风险：可能切断语义完整句，导致检索命中但回答上下文不完整。

2. `SentenceSplitter`
- 原理：优先按句子边界切分，再按 `chunk_size/chunk_overlap` 合并句子块。
- notebook 参数：`chunk_size=512`、`chunk_overlap=50`。
- 适用：通用文本问答，兼顾语义完整度和长度控制。
- 风险：长句或格式混乱文本时，句界识别效果会下降。

3. `SentenceWindowNodeParser`
- 原理：以“当前句”为检索单元，同时把前后窗口句写入元数据，查询时再替换回窗口文本。
- notebook 参数：`window_size=3`，并配合 `MetadataReplacementPostProcessor(target_metadata_key="window")`。
- 适用：需要“精准命中一句 + 回答时保留上下文”。
- 风险：如果不配后处理器，返回内容可能过短，回答信息不足。

4. `SemanticSplitterNodeParser`
- 原理：先做句向量，再根据语义变化点切分；当相邻片段差异超过阈值时断开。
- notebook 参数：`buffer_size=1`、`breakpoint_percentile_threshold=95`，且依赖 embedding 模型。
- 适用：主题切换明显、段落结构不规整的文本。
- 风险：依赖 embedding 质量；阈值过高会切得过粗，过低会切得过碎。

5. `MarkdownNodeParser`
- 原理：按 Markdown 结构（标题层级、段落块）切分，优先保留文档层次信息。
- notebook 参数：默认 `MarkdownNodeParser()`。
- 适用：规范的 Markdown 文档（知识库、技术文档、SOP）。
- 风险：对非 Markdown 或格式脏数据收益有限。

实践建议：

1. 纯文本先用 `SentenceSplitter` 作为基线。
2. 文档结构清晰（标题分层明显）优先试 `MarkdownNodeParser`。
3. 查询粒度细、上下文依赖强时用 `SentenceWindowNodeParser + MetadataReplacementPostProcessor`。
4. 主题跳跃明显时再引入 `SemanticSplitterNodeParser`，并调 `breakpoint_percentile_threshold`。

## 9. 借鉴式补充：为什么学习 LlamaIndex 要看“复杂流程”

很多同学会问：为什么不能只做“读文档 -> 向量检索 -> 让 LLM 回答”？  
答案是：可以做原型，但一旦进入真实业务，稳定性、成本、可解释性会迅速暴露问题。

### 9.1 简单版 vs 工程版

简单版（原型验证）：

```python
docs = SimpleDirectoryReader("code/data").load_data()
index = VectorStoreIndex.from_documents(docs)
answer = index.as_query_engine().query("问题")
```

工程版（质量可控）：

```python
# 1) 选合适切片策略（句子/窗口/语义/markdown）
nodes = node_parser.get_nodes_from_documents(docs)

# 2) 查询改写（如 HyDE）
query_engine = TransformQueryEngine(base_engine, query_transform=HyDEQueryTransform(...))

# 3) 检索后过滤
retrieved = retriever.retrieve(query)
filtered = SimilarityPostprocessor(similarity_cutoff=...).postprocess_nodes(retrieved)

# 4) 模板化回答
engine = index.as_query_engine(text_qa_template=PromptTemplate(...))
answer = engine.query(query)
```

### 9.2 每层复杂性的必要性（对应本目录示例）

1. 切片策略（`llamaindex_05_chunking_strategies.ipynb`）  
- 不做会怎样：检索粒度和语义边界不可控，常见问题是“命中片段太碎”或“一个 chunk 太大导致噪声多”。  
- 怎么做：基线先用 `SentenceSplitter(chunk_size, chunk_overlap)`；需要上下文补全时用 `SentenceWindowNodeParser(window_size=...)`；结构化文档用 `MarkdownNodeParser()`。  
- 验收指标：命中率提高、完整度提高、冗余度不显著上升。  
- 常见坑：只调 `chunk_size` 不调 `overlap`；窗口模式忘记配 `MetadataReplacementPostProcessor`。  

2. 查询改写（`llamaindex_08_hyde_query_transform.ipynb`）  
- 不做会怎样：短问题、口语化问题、指代不清问题容易召回失败。  
- 怎么做：在原 `query_engine` 前包一层 `TransformQueryEngine(..., query_transform=HyDEQueryTransform(...))`，让检索查询更“可召回”。  
- 验收指标：同一问题下，召回文档相关性提升，低相关候选减少。  
- 常见坑：把 HyDE 当万能增强；如果原问题已很精准，HyDE 可能带来额外 token 和延迟。  

3. 检索后处理（`llamaindex_06_similarity_postprocessor.py`）  
- 不做会怎样：`top_k` 结果中混入边缘相关文本，回答容易“看起来有依据但跑题”。  
- 怎么做：先 `retriever.retrieve(query)`，再 `SimilarityPostprocessor(similarity_cutoff=...)` 过滤低分节点。  
- 验收指标：冗余度下降、回答相关性提升，且命中率不明显下降。  
- 常见坑：阈值设太高导致“过滤过度”，上下文不够反而答不全。  

4. Prompt 模板化（`llamaindex_07_prompt_template.ipynb`）  
- 不做会怎样：回答风格飘忽，格式不稳定，难以用于前端固定展示或自动评测。  
- 怎么做：用 `PromptTemplate` 显式约束输出结构（如分点、引用、长度限制），通过 `as_query_engine(text_qa_template=...)` 注入。  
- 验收指标：格式一致性提升（如固定三点输出），人工评阅成本下降。  
- 常见坑：模板约束过强，导致答案僵硬或漏答；模板未区分“事实回答”与“总结回答”场景。  

5. 总结：为什么这些层要组合使用  
- 切片决定“检什么”；改写决定“怎么检”；后处理决定“留什么”；模板决定“怎么答”。  
- 单点优化往往只能解决一个症状，分层组合才能稳定提升整体体验。

### 9.3 成本与收益（学习视角）

1. 简单链路  
收益：上手快，1 天内能跑通。  
成本：效果波动大，问题定位困难。

2. 分层增强链路  
收益：质量、稳定性、可解释性明显提升。  
成本：需要多做参数对比和评测，开发复杂度更高。

### 9.4 如何落地到你的实践

1. 第一步先跑通 `llamaindex_01_quickstart.ipynb`，确认最小闭环。  
2. 第二步加 `llamaindex_05_chunking_strategies.ipynb`，把切片策略做成可对比实验。  
3. 第三步加 `llamaindex_06_similarity_postprocessor.py` 和 `llamaindex_08_hyde_query_transform.ipynb`。  
4. 第四步再用 `llamaindex_07_prompt_template.ipynb` 做回答结构与可控性收口。  

结论：  
LlamaIndex 的“复杂”不是为了堆 API，而是把 RAG 从“能跑”提升到“可控、可解释、可上线”。

### 9.5 典型失败案例与对应改进（建议直接复现）

1. 案例 A：问题短且模糊，检索不稳定  
- 示例问题：`请假规则是什么？`  
- 常见现象：简单链路返回“泛化制度描述”，遗漏“事假无薪、天数上限”等关键点。  
- 改进组合：`HyDEQueryTransform` + `SentenceSplitter/SentenceWindowNodeParser`。  
- 对应文件：`llamaindex_08_hyde_query_transform.ipynb`、`llamaindex_05_chunking_strategies.ipynb`。  
- 验收标准：回答中是否覆盖关键约束项（提前申请、审批链路、天数上限、薪资规则）。  

2. 案例 B：检索命中了但上下文噪声大  
- 示例问题：`事假每年最多几天？`  
- 常见现象：`top_k` 里混入不相关 chunk，答案带入无关条款。  
- 改进组合：`SimilarityPostprocessor(similarity_cutoff=...)`。  
- 对应文件：`llamaindex_06_similarity_postprocessor.py`。  
- 验收标准：过滤后 chunk 数下降，同时答案相关性提升、冗余下降。  

3. 案例 C：答案能答但风格不稳定  
- 示例问题：`把请假规则总结成三点`  
- 常见现象：回答结构不稳定，有时分点有时大段描述。  
- 改进组合：`PromptTemplate` 固定输出格式。  
- 对应文件：`llamaindex_07_prompt_template.ipynb`。  
- 验收标准：输出格式稳定（固定三点），可直接复用于前端展示。  

### 9.6 参数调优优先级（避免盲调）

按这个顺序调，收益通常更稳定：

1. 先调切片：`chunk_size/chunk_overlap/window_size`。  
2. 再调检索：`similarity_top_k`。  
3. 再调过滤：`similarity_cutoff`。  
4. 最后调模板与输出格式。  

经验规则：

1. 召回不足：增大 `chunk_size` 或 `top_k`，再看是否需要 HyDE。  
2. 噪声太多：降低 `top_k` 或提高 `similarity_cutoff`。  
3. 答案结构不稳：优先用 `PromptTemplate`，不要先改检索。  
4. 长文档跨段丢信息：优先试 `SentenceWindowNodeParser`。  

## 10. LlamaIndex `Document` 结构补充（常用）

在新版 LlamaIndex 中，`Document` 可理解为面向文档场景的 `Node` 封装。  
日常最常接触的是 `text + metadata + id_`，但完整字段可以按下面三类理解。

### 10.1 核心内容字段

1. `text_resource`
2. `image_resource`
3. `audio_resource`
4. `video_resource`
5. `text_template`

说明：文本 RAG 通常只会直接用到 `text_resource`（兼容访问方式是 `text`）。

### 10.2 通用元数据与索引字段（继承能力）

1. `id_`（兼容属性：`doc_id`、`node_id`）
2. `embedding`
3. `metadata`（兼容旧名：`extra_info`）
4. `excluded_llm_metadata_keys`
5. `excluded_embed_metadata_keys`
6. `metadata_template`
7. `metadata_separator`（兼容别名：`metadata_seperator`）
8. `relationships`

### 10.3 常见兼容行为

1. `Document(text="...")` 仍可直接构造文本文档。  
2. `doc.text` 仍可读写文本（底层映射到 `text_resource`）。  
3. `doc.doc_id` 可作为 `id_` 的兼容入口。  
4. 旧参数 `extra_info` 依旧兼容，但新代码建议统一使用 `metadata`。  

### 10.4 metadata 的实用价值

1. 检索过滤：按 `source/category/year` 等字段筛选候选。  
2. 结果溯源：在回答中展示文件名、页码、章节路径。  
3. 权限与路由：按租户、部门、文档类型做访问控制或查询路由。  

实践建议：

1. metadata 保持扁平结构，value 尽量用基础类型（`str/int/float/bool`）。  
2. 对不需要参与 embedding 的字段加入 `excluded_embed_metadata_keys`。  
3. 对不需要暴露给 LLM 的字段加入 `excluded_llm_metadata_keys`。  

### 10.5 最小示例（推荐写法）

```python
from llama_index.core import Document

doc = Document(
    text="员工事假须提前 3 天申请，连续超过 5 天需部门负责人审批。",
    id_="hr_policy_001",
    metadata={
        "source": "employee_handbook.pdf",
        "category": "hr_policy",
        "year": 2025,
        "section_path": "请假制度/事假",
        "page": 12,
    },
    excluded_embed_metadata_keys=["source", "page"],
    excluded_llm_metadata_keys=["year"],
)
```

这段写法对应的工程目标是：既能做过滤与溯源，也能避免无关 metadata 污染 embedding 或回答内容。

### 10.6 metadata 机制补充（你需要记住的四点）

在 LlamaIndex 里，元数据本质是 `dict`，建议重点记这四件事：

1. 挂载位置  
- `Document.metadata`  
- `Node.metadata`

2. 传播规则  
- `Document` 被切成多个 `Node` 后，metadata 会继承到每个 node。  
- 因此在文档入口补齐 `source/page/section_path/category`，后续检索和溯源会更省事。

3. 主要用途  
- 检索过滤：按 `source/year/category` 等字段筛选。  
- 溯源展示：回答里标注文件名、页码、章节路径。  
- 辅助检索效果：metadata 可参与上下文组织与召回。

4. 注意事项  
- 很多向量库要求 metadata 为扁平结构。  
- key 用字符串，value 用基础类型（如 `str/int/float`，常见场景也可用 `bool`）。  
- 避免塞复杂嵌套对象（如深层 dict/list），以免过滤或存储兼容性出问题。

## 11. LlamaIndex 数据提取管道设计模式（实战）

本节给出一套在业务中更稳的“数据提取到入库”设计方式，目标是提升可维护性、可解释性和扩展性。

### 11.1 主流程：分层流水线模式

推荐主链路：

`Loader -> Normalize -> Route -> Parse -> Chunk -> Metadata Extract -> Quality Gate -> Embed -> Index/Store`

对应含义：

1. `Loader`：读取 PDF/Markdown/HTML/代码等原始文档。  
2. `Normalize`：统一编码、清理噪声、标准化换行和空白。  
3. `Route`：按文件类型路由到不同解析与切片策略。  
4. `Parse`：结构化提取（标题、段落、表格、代码块等）。  
5. `Chunk`：按句子/窗口/语义/格式进行切分。  
6. `Metadata Extract`：补齐 `source/page/section/type/version`。  
7. `Quality Gate`：过滤空块、重复块、异常超长块。  
8. `Embed`：生成向量。  
9. `Index/Store`：写入向量库与原文存储。

### 11.2 常用设计模式（建议组合使用）

1. 策略模式（按类型切换）  
- `pdf/md/code/html` 使用不同 parser 和 splitter。  
- 避免“一套切分规则处理所有文档”。

2. 兜底链模式（解析容错）  
- 主解析器失败时自动降级到备选解析器。  
- 避免单个脏文件拖垮整批任务。

3. 元数据优先模式  
- 先提元数据，再进入切片与索引。  
- 为后续检索过滤、溯源展示、权限控制打基础。

4. 增量幂等模式  
- 用 `doc_id + content_hash` 做去重与增量更新。  
- 文档未变化则跳过重处理，降低成本。

5. 质量闸门模式  
- 入库前检查：空文本、重复率、长度分布、异常字符占比。  
- 防止低质量 chunk 进入检索链路。

6. 可观测模式  
- 记录每阶段耗时、失败率、chunk 数、平均 chunk 长度。  
- 便于快速定位是“解析问题”还是“切分问题”。

### 11.3 最小实现骨架（示意）

```python
from llama_index.core.ingestion import IngestionPipeline

pipeline = IngestionPipeline(
    transformations=[
        normalize_text,          # 统一清洗
        route_by_filetype,       # 按文件类型路由
        parse_with_fallback,     # 主解析器 + 兜底解析器
        split_with_strategy,     # 句子/窗口/Markdown/代码切分
        extract_metadata,        # 补齐 source/page/section/type
        quality_gate_filter,     # 空块/重复/超长过滤
        embed_model,             # 向量化
    ]
)

nodes = pipeline.run(documents=documents)
```

### 11.4 调整原则（和你现有实践一致）

1. 主力切片优先用句子切片与句子窗口切片（可解释性强、调试成本低）。  
2. 结构化文档优先用特定格式切分（如 `MarkdownNodeParser`、代码按函数/类切分）。  
3. 语义切分按需使用，不作为所有场景默认方案。  
4. 参数按文件类型动态配置，不用单一固定参数。  

一句话：把管道做成“可路由、可回退、可观测、可增量”的系统，比只追求单点检索精度更容易长期稳定上线。

## 12. LlamaHub（Reader 生态）补充

`LlamaHub` 可以理解为 LlamaIndex 的“数据连接器/Reader 集合”，用于把外部数据源快速接入 RAG 流程。

### 12.1 它解决什么问题

1. 降低接入成本：减少自己写 Reader/解析器的重复工作。  
2. 统一接口：不同数据源都尽量产出 `Document`，便于接入同一条索引管道。  
3. 提升迭代速度：先用现成 Reader 跑通，再按业务做定制优化。

### 12.2 常见数据源类型

1. 本地文件与对象存储（PDF、Markdown、TXT、S3 等）。  
2. 企业知识库（Notion、Confluence、Google Drive 等）。  
3. 网页与 API 数据。  
4. 数据库与业务系统导出数据。

### 12.3 最小接入流程（建议）

1. 明确目标数据源和更新频率。  
2. 安装对应 reader 插件包（按数据源选择）。  
3. 使用 Reader 拉取数据，统一为 `Document`。  
4. 进入你在第 11 章的管道：清洗 -> 切片 -> 元数据 -> 向量化 -> 索引。  
5. 增加增量同步（`doc_id + content_hash`）避免全量重建。

### 12.4 示例（伪代码骨架）

```python
# 1) 初始化某个数据源 Reader（不同数据源类名不同）
reader = SomeDataSourceReader(config=...)

# 2) 拉取并转成 Document 列表
documents = reader.load_data()

# 3) 交给统一 ingestion pipeline
nodes = pipeline.run(documents=documents)
```

### 12.5 选型建议

1. 先选“维护成本最低”的官方/社区 Reader，优先跑通业务闭环。  
2. 遇到格式脏数据、权限模型复杂、同步策略特殊，再自定义 Reader。  
3. 无论使用哪种 Reader，都要统一补齐 metadata（`source/page/section/type/version`）。  

一句话：`LlamaHub` 主要价值不是“提高模型能力”，而是“更快、更标准地接入数据源”。
