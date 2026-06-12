<!-- Converted from llamaindex_05_chunking_strategies.ipynb -->

```python
from dotenv import load_dotenv
load_dotenv()
```

```python
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import Document


doc = Document(
    text=("""
    ### 第七条 事假
    1. 员工因私事必须本人处理的，可申请事假。
    2. 事假需提前申请并获直属主管批准，紧急情况可事后补办手续。
    3. 事假为无薪假，按日扣除相应工资。
    4. 每月事假原则上不超过3天，全年累计不超过15天，特殊情况需经人力资源部及公司领导审批。
    """
    ),
    metadata={"title": "Vacation Questions"}
)

# Token 切片

splitter = TokenTextSplitter(
    chunk_size=32,
    chunk_overlap=4,
    separator="\n"
)

nodes = splitter.get_nodes_from_documents([doc])

for node in nodes:
    print(node.text)
    print(node.metadata)
```

```python
# 句子切片
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.node_parser import SentenceWindowNodeParser
sentence_splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50
)
# evaluate_splitter(sentence_splitter, documents, question, ground_truth, "Sentence")
```

```python
# 句子窗口切片
sentence_window_splitter = SentenceWindowNodeParser.from_defaults(
    window_size=3,
    window_metadata_key="window",
    original_text_metadata_key="original_text"
)
# 注意：句子窗口切片需要特殊的后处理器
from llama_index.core.node_parser import MetadataReplacementPostProcessor
query_engine = index.as_query_engine(
    similarity_top_k=5,
    streaming=True,
    node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")]
)
# evaluate_splitter(sentence_window_splitter, documents, question, ground_truth, "Sentence Window")
```

```python
# 语义切片
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core import Settings
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
Settings.embed_model = DashScopeEmbedding(
    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
    embed_batch_size=6,
    embed_input_length=8192
)
semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=Settings.embed_model
)
# evaluate_splitter(semantic_splitter, documents, question, ground_truth, "Semantic")
```

```python
# markdown 切片
from llama_index.core.node_parser import MarkdownNodeParser
markdown_splitter = MarkdownNodeParser()
# evaluate_splitter(markdown_splitter, documents, question, ground_truth, "Markdown")
```
