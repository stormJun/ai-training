# LlamaIndex 学习文档

> 官方文档: https://developers.llamaindex.ai/python/framework/
>
> 最后更新: 2026-03-10

---

## 目录

1. [简介](#1-简介)
2. [安装与设置](#2-安装与设置)
3. [核心概念](#3-核心概念)
4. [快速开始](#4-快速开始)
5. [数据加载](#5-数据加载)
6. [索引与存储](#6-索引与存储)
7. [查询引擎](#7-查询引擎)
8. [聊天引擎](#8-聊天引擎)
9. [Agent 智能体](#9-agent-智能体)
10. [Workflows 工作流](#10-workflows-工作流)
11. [模型配置](#11-模型配置)
12. [最佳实践](#12-最佳实践)
13. [常见问题](#13-常见问题)

---

## 1. 简介

### 1.1 什么是 LlamaIndex?

LlamaIndex 是构建 LLM 驱动应用的首选框架，专注于**上下文增强 (Context Augmentation)**。它提供了以下核心能力：

- **数据连接器 (Data Connectors)**: 从各种数据源（API、PDF、SQL 等）摄取数据
- **数据索引 (Data Indexes)**: 将数据结构化为 LLM 易于消费的中间表示
- **引擎 (Engines)**: 提供自然语言访问数据的接口
  - **查询引擎 (Query Engine)**: 用于问答（如 RAG 流程）
  - **聊天引擎 (Chat Engine)**: 用于多轮对话交互
- **智能体 (Agents)**: 由 LLM 驱动、通过工具增强的知识工作者
- **工作流 (Workflows)**: 将以上所有组件组合成事件驱动系统

---

## 2. 安装与设置

### 2.1 快速安装

```bash
pip install llama-index
```

这个安装包包含：
- `llama-index-core`: 核心库
- `llama-index-llms-openai`: OpenAI LLM 集成
- `llama-index-embeddings-openai`: OpenAI Embedding 集成
- `llama-index-readers-file`: 文件读取器

### 2.2 自定义安装

如果使用其他 LLM 或本地模型，可以按需安装：

```bash
# 使用 Ollama + HuggingFace Embeddings
pip install llama-index-core llama-index-readers-file llama-index-llms-ollama llama-index-embeddings-huggingface

# 使用 DashScope (阿里云)
pip install llama-index-llms-dashscope llama-index-embeddings-dashscope
```

---

## 3. 核心概念

### 3.1 核心组件架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LlamaIndex 架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Documents  │───▶│   Nodes     │───▶│   Index     │     │
│  │  (原始文档)  │    │  (切片单元)  │    │   (索引)    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                              │              │
│                                              ▼              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Query     │◀───│  Retriever  │◀───│   Vector    │     │
│  │   Engine    │    │   (检索器)   │    │   Store     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐    ┌─────────────┐                        │
│  │  Response   │◀───│    LLM      │                        │
│  │  (响应)     │    │   (大模型)   │                        │
│  └─────────────┘    └─────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心概念对照表

| 概念 | 说明 | 代码示例 |
|------|------|----------|
| **Document** | 原始文档对象，包含文本和元数据 | `Document(text="...", metadata={})` |
| **Node** | 切片后的检索单元 | `TextNode(text="...", id_="...")` |
| **Index** | 索引结构，支持高效检索 | `VectorStoreIndex.from_documents(docs)` |
| **Retriever** | 从索引中检索相关节点 | `index.as_retriever(similarity_top_k=5)` |
| **QueryEngine** | 端到端的问答接口 | `index.as_query_engine()` |
| **ChatEngine** | 多轮对话接口 | `index.as_chat_engine()` |
| **Agent** | LLM 驱动的智能体 | `FunctionAgent(tools=[...], llm=...)` |



---

## 4. 快速开始

### 4.1 最简 RAG 示例（5 行代码）

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
# 1. 加载文档
documents = SimpleDirectoryReader("data").load_data()
# 2. 创建索引
index = VectorStoreIndex.from_documents(documents)
# 3. 查询
query_engine = index.as_query_engine()
response = query_engine.query("什么是 RAG?")
print(response)
```

---

## 5. 数据加载

### 5.1 SimpleDirectoryReader

最简单的文件加载方式：

```python
from llama_index.core import SimpleDirectoryReader
# 加载目录下所有文件
documents = SimpleDirectoryReader("data").load_data()
# 加载特定文件
documents = SimpleDirectoryReader(
    input_files=["file1.pdf", "file2.txt"]
).load_data()
# 加载特定类型文件
documents = SimpleDirectoryReader(
    "data",
    required_exts=[".pdf", ".txt"],
    exclude=[".git", ".DS_Store"]
).load_data()
# 递归加载
documents = SimpleDirectoryReader(
    "data",
    recursive=True,
    exclude_hidden=True
).load_data()
```

### 5.2 Document 和 Node

```python
from llama_index.core import Document, TextNode

# 手动创建 Document
doc = Document(
    text="这是文档内容",
    metadata={
        "author": "张三",
        "category": "技术文档",
        "created_at": "2024-01-01"
    }
)
# 手动创建 Node
node = TextNode(
    text="这是节点内容",
    id_="unique-node-id",
    metadata={"source": "manual"}
)

# Document 会自动转换为 Node
print(f"Document ID: {doc.id_}")
print(f"Document Text Length: {len(doc.text)}")
```

### 5.3 LlamaHub 数据连接器

LlamaHub 提供了 100+ 数据连接器：

```python
# 安装特定连接器
# pip install llama-index-readers-database
# pip install llama-index-readers-web

# 示例：从数据库读取
from llama_index.readers.database import DatabaseReader

reader = DatabaseReader(
    sql_database="postgresql://user:pass@localhost/db"
)
documents = reader.load_data(query="SELECT * FROM articles")

# 示例：从网页读取
from llama_index.readers.web import SimpleWebPageReader

reader = SimpleWebPageReader(html_to_text=True)
documents = reader.load_data(
    urls=["https://example.com/article"]
)
```

### 5.4 自定义数据加载器

```python
from llama_index.core import Document
from typing import List
import pathlib

def load_custom_documents(directory: str) -> List[Document]:
    """自定义文档加载器"""
    documents = []
    for file_path in pathlib.Path(directory).glob("**/*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        doc = Document(
            text=text,
            metadata={
                "filename": file_path.name,
                "path": str(file_path)
            }
        )
        documents.append(doc)
    return documents

# 使用自定义加载器
documents = load_custom_documents("data")
```

---

## 6. 索引与存储

### 6.1 VectorStoreIndex

最常用的向量索引：

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# 从文档创建
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)

# 从节点创建
from llama_index.core.node_parser import SentenceSplitter

parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = parser.get_nodes_from_documents(documents)
index = VectorStoreIndex(nodes)

# 直接插入节点
index = VectorStoreIndex([])
for node in nodes:
    index.insert(node)
```

### 6.2 切片策略

```python
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
    HierarchicalNodeParser
)
from llama_index.embeddings.openai import OpenAIEmbedding

# 1. 句子切片器（推荐）
splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50,
    paragraph_separator="\n\n"
)

# 2. 语义切片器（按语义边界切分）
semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=OpenAIEmbedding()
)

# 3. 层级切片器（父子节点）
hierarchical_splitter = HierarchicalNodeParser.from_defaults(
    chunk_sizes=[2048, 512, 128]
)

# 使用切片器
nodes = splitter.get_nodes_from_documents(documents)
```

### 6.3 向量存储集成

```python
# 使用 Chroma
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db.get_or_create_collection("my_collection")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

# 使用 Milvus
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core import StorageContext

vector_store = MilvusVectorStore(
    uri="./milvus_demo.db",
    collection_name="my_collection",
    dim=1536,
    overwrite=True
)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)
```

### 6.4 持久化存储

```python
# 保存索引
index.storage_context.persist(persist_dir="./storage")

# 加载索引
from llama_index.core import StorageContext, load_index_from_storage

storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)

# 从向量存储加载
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_collection("my_collection")
vector_store = ChromaVectorStore(chroma_collection=collection)
index = VectorStoreIndex.from_vector_store(vector_store)
```

---

## 7. 查询引擎

### 7.1 基本查询

```python
from llama_index.core import VectorStoreIndex

# 创建查询引擎
query_engine = index.as_query_engine()

# 同步查询
response = query_engine.query("你的问题")
print(response)

# 异步查询
response = await query_engine.aquery("你的问题")
print(response)

# 获取来源信息
print(response.source_nodes)
for node in response.source_nodes:
    print(f"Score: {node.score}")
    print(f"Text: {node.node.text[:100]}...")
```

### 7.2 查询引擎配置

```python
# 配置检索参数
query_engine = index.as_query_engine(
    similarity_top_k=5,           # 返回 top-k 相似节点
    response_mode="compact",      # 响应模式
    streaming=True,               # 启用流式输出
)

# 响应模式
# - "compact": 紧凑模式（默认）
# - "refine": 迭代优化模式
# - "tree_summarize": 树状总结模式
# - "simple_summarize": 简单总结模式
# - "no_text": 只返回检索结果，不生成回答
```

### 7.3 检索器

```python
# 获取检索器
retriever = index.as_retriever(
    similarity_top_k=5
)

# 检索节点
nodes = retriever.retrieve("你的问题")
for node in nodes:
    print(f"Score: {node.score}")
    print(f"Node ID: {node.node_id}")
    print(f"Text: {node.node.text[:100]}...")

# 使用 MMR 减少冗余
retriever = index.as_retriever(
    similarity_top_k=10,
    vector_store_query_mode="mmr",
    mmr_threshold=0.5
)
```

### 7.4 后处理器

```python
from llama_index.core.postprocessor import (
    SimilarityPostprocessor,
    KeywordNodePostprocessor,
    LongContextReorder
)

# 相似度过滤
similarity_processor = SimilarityPostprocessor(
    similarity_cutoff=0.7
)

# 关键词过滤
keyword_processor = KeywordNodePostprocessor(
    required_keywords=["关键词1", "关键词2"],
    exclude_keywords=["排除词"]
)

# 长上下文重排序（将相关内容放到开头和结尾）
reorder_processor = LongContextReorder()

# 组合使用
query_engine = index.as_query_engine(
    similarity_top_k=10,
    node_postprocessors=[
        similarity_processor,
        keyword_processor,
        reorder_processor
    ]
)
```

### 7.5 流式输出

```python
# 启用流式输出
query_engine = index.as_query_engine(streaming=True)

# 流式查询
streaming_response = query_engine.query("你的问题")

# 迭代输出
for text in streaming_response.response_gen:
    print(text, end="", flush=True)

# 异步流式
async for text in await query_engine.astream_query("你的问题"):
    print(text, end="", flush=True)
```

---

## 8. 聊天引擎

### 8.1 基本聊天

```python
from llama_index.core import VectorStoreIndex

# 创建聊天引擎
chat_engine = index.as_chat_engine()

# 单轮对话
response = chat_engine.chat("你好，请介绍一下你自己")
print(response)

# 多轮对话
response = chat_engine.chat("你能详细解释一下吗？")
print(response)

# 重置对话历史
chat_engine.reset()
```

### 8.2 聊天模式

```python
# 简单模式（每次独立查询）
chat_engine = index.as_chat_engine(
    chat_mode="simple",
    verbose=True
)

# 精简模式（使用历史对话优化回答）
chat_engine = index.as_chat_engine(
    chat_mode="refine",
    verbose=True
)

# 上下文模式（将历史对话作为上下文）
chat_engine = index.as_chat_engine(
    chat_mode="context",
    verbose=True
)

# ReAct 模式（使用 Agent 进行对话）
chat_engine = index.as_chat_engine(
    chat_mode="react",
    verbose=True
)

# OpenAI 模式（使用 OpenAI 函数调用）
chat_engine = index.as_chat_engine(
    chat_mode="openai",
    verbose=True
)
```

### 8.3 聊天历史管理

```python
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.storage.chat_store import SimpleChatStore

# 使用内存缓冲
memory = ChatMemoryBuffer.from_defaults(
    token_limit=4096  # 限制历史 token 数
)

chat_engine = index.as_chat_engine(
    chat_mode="context",
    memory=memory
)

# 持久化聊天历史
chat_store = SimpleChatStore()
chat_engine = index.as_chat_engine(
    chat_mode="context",
    chat_store=chat_store,
    chat_store_key="user_123"  # 用户标识
)

# 保存聊天历史
chat_store.persist(persist_dir="./chat_store")

# 加载聊天历史
chat_store = SimpleChatStore.from_persist_dir("./chat_store")
```

---

## 9. 模型配置

### 9.1 LLM 配置

```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

# OpenAI
Settings.llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000
)

# 指定不同模型
gpt4 = OpenAI(model="gpt-4o")
gpt35 = OpenAI(model="gpt-3.5-turbo")

# 在查询引擎中使用
query_engine = index.as_query_engine(llm=gpt4)
```

### 9.2 Embedding 配置

```python
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding

# OpenAI Embedding
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    dimensions=1536
)

# 使用其他 Embedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)
```

### 9.3 使用本地模型 (Ollama)

```python
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

# 确保 Ollama 服务已启动
# ollama serve
# ollama pull llama2

Settings.llm = Ollama(
    model="llama2",
    request_timeout=60.0
)

Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text"
)

# 使用方式相同
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("你的问题")
```

### 9.4 多模态模型

```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

# 使用 GPT-4 Vision
Settings.llm = OpenAI(model="gpt-4o")

# 处理图像
from llama_index.core.schema import ImageDocument

image_doc = ImageDocument(
    image_path="image.png",
    text="图像描述"
)

# 或从 URL 加载
image_doc = ImageDocument(
    image_url="https://example.com/image.png"
)

# 查询图像
from llama_index.multi_modal_llms.openai import OpenAIMultiModal

mm_llm = OpenAIMultiModal(model="gpt-4o", max_new_tokens=1000)
response = mm_llm.complete(
    prompt="描述这张图片",
    image_documents=[image_doc]
)
print(response.text)
```

---

## 10. 最佳实践

### 10.1 切片策略选择

| 场景 | 推荐策略 | 参数建议 |
|------|----------|----------|
| 通用文档 | SentenceSplitter | chunk_size=512, overlap=50 |
| 长文档 | SemanticSplitter | buffer_size=1 |
| 层级结构 | HierarchicalNodeParser | chunk_sizes=[2048, 512, 128] |
| 代码文件 | CodeSplitter | 根据语言调整 |

### 10.2 检索优化

```python
# 1. 使用混合检索
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever

vector_retriever = VectorIndexRetriever(index=index, similarity_top_k=5)
bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=5)

# 融合检索器
fusion_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=10,
    mode="reciprocal_rerank"
)

# 2. 使用重排序
from llama_index.postprocessor.cohere_rerank import CohereRerank

cohere_rerank = CohereRerank(
    api_key="your-cohere-api-key",
    top_n=5
)

query_engine = index.as_query_engine(
    similarity_top_k=10,
    node_postprocessors=[cohere_rerank]
)

# 3. 相似度过滤
from llama_index.core.postprocessor import SimilarityPostprocessor

query_engine = index.as_query_engine(
    similarity_top_k=10,
    node_postprocessors=[
        SimilarityPostprocessor(similarity_cutoff=0.7)
    ]
)
```

### 10.3 Prompt 优化

```python
from llama_index.core import PromptTemplate

# 自定义 QA Prompt
qa_template = PromptTemplate(
    """你是一个专业的问答助手。请仅根据以下上下文回答问题。
如果上下文中没有相关信息，请明确说明"根据提供的资料无法回答该问题"。

上下文:
{context_str}

问题: {query_str}

请提供准确、简洁的回答，并在回答中引用相关来源：

答案:"""
)

# 使用自定义 Prompt
query_engine = index.as_query_engine(
    text_qa_template=qa_template
)

# 精炼 Prompt（用于 refine 模式）
refine_template = PromptTemplate(
    """原始问题: {query_str}
现有回答: {existing_answer}
新的上下文: {context_msg}

请根据新的上下文，改进现有回答。如果新的上下文没有提供有用信息，保持原回答不变。

改进后的回答:"""
)

query_engine = index.as_query_engine(
    response_mode="refine",
    text_qa_template=qa_template,
    refine_template=refine_template
)
```

### 10.4 性能优化

```python
# 1. 批量处理
from llama_index.core import SimpleDirectoryReader

# 并行加载
documents = SimpleDirectoryReader(
    "data",
    num_files_limit=100
).load_data(
    num_workers=4  # 并行加载
)

# 2. 缓存
from llama_index.core import Settings
from llama_index.core.storage import StorageContext

# 启用缓存
Settings.embed_model.cache_folder = "./embedding_cache"

# 3. 异步操作
import asyncio

async def process_queries(queries):
    tasks = [query_engine.aquery(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results

# 4. 减少节点数量
query_engine = index.as_query_engine(
    similarity_top_k=3  # 减少返回节点数
)
```

### 10.5 错误处理

```python
from llama_index.core import VectorStoreIndex
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_query(query_engine, query: str) -> str:
    """安全的查询函数"""
    try:
        response = query_engine.query(query)
        return str(response)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return f"抱歉，查询过程中出现错误: {str(e)}"

# 带重试的查询
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def query_with_retry(query_engine, query: str):
    return await query_engine.aquery(query)
```

---

## 附录

### A. 常用向量数据库

| 数据库 | 特点 | 适用场景 |
|--------|------|----------|
| Chroma | 轻量级，本地存储 | 开发测试 |
| Milvus | 高性能，分布式 | 大规模生产 |
| Pinecone | 云托管，免维护 | 快速部署 |
| Qdrant | 高效，Rust 实现 | 性能敏感 |
| Weaviate | 语义搜索 | 复杂查询 |

### B. 学习资源

- [LlamaIndex 官方文档](https://developers.llamaindex.ai/)
- [LlamaHub 数据连接器](https://llamahub.ai/)
- [LlamaIndex GitHub](https://github.com/run-llama/llama_index)
- [LlamaIndex Discord 社区](https://discord.gg/dGcwcsnxhU)

### C. 版本兼容性

```python
# 检查版本
import llama_index
print(llama_index.__version__)

# 推荐版本
# llama-index >= 0.10.0
# Python >= 3.8
```

---

**文档维护**: AI Training Team
**最后更新**: 2026-03-10
