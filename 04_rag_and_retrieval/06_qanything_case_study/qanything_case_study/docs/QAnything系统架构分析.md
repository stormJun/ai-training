# QAnything 系统架构分析文档

## 1. 系统概述

QAnything 是一个基于 RAG (Retrieval-Augmented Generation) 架构的本地知识库问答系统。系统支持多种文档格式的上传、解析、向量化存储和智能问答，采用微服务架构设计，具有良好的可扩展性和可维护性。

### 1.1 核心特性

- **多格式文档支持**: 支持 PDF、Word、Excel、Markdown 等多种文档格式
- **混合检索**: 结合向量检索和全文检索，提高检索准确率
- **层次化存储**: 采用父子文档检索策略，优化上下文完整性
- **智能重排序**: 使用 Rerank 模型对检索结果进行二次排序
- **流式输出**: 支持 LLM 流式响应，提升用户体验
- **多知识库管理**: 支持多用户、多知识库的隔离管理

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层 (Frontend)                      │
│                    http://localhost:8777/qanything/          │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                     API 服务层 (Sanic)                        │
│                  sanic_api.py :8777                          │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐
    │ 知识库管理   │ │ 文档问答    │ │ Bot管理  │
    │  Service    │ │  Service   │ │ Service  │
    └──────┬──────┘ └─────┬──────┘ └────┬─────┘
           │              │              │
┌──────────▼──────────────▼──────────────▼────────────────────┐
│                    核心业务层 (LocalDocQA)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 文档解析      │  │ 向量检索     │  │ LLM 问答生成      │  │
│  │  Pipeline    │  │ Retriever   │  │   Generator      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
┌──────────▼──────────────▼──────────────▼────────────────────┐
│                      服务连接层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Embedding │  │ Rerank   │  │   OCR    │  │ PDF Parser │  │
│  │ Service  │  │ Service  │  │ Service  │  │  Service   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
┌──────────▼──────────────▼──────────────▼────────────────────┐
│                      数据存储层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Milvus  │  │   MySQL  │  │   ES     │  │   MinIO    │  │
│  │向量数据库 │  │ 元数据库  │  │全文搜索  │  │ 对象存储   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
03_rag_and_retrieval/qanything_case_study/
├── qanything_kernel/              # 核心代码包
│   ├── configs/                   # 配置文件
│   │   └── model_config.py        # 模型配置、提示词模板
│   ├── connector/                 # 外部服务连接器
│   │   ├── database/              # 数据库连接器
│   │   │   ├── faiss/             # Faiss 向量数据库
│   │   │   ├── milvus/            # Milvus 向量数据库
│   │   │   └── mysql/             # MySQL 关系数据库
│   │   ├── embedding/             # 嵌入模型连接器
│   │   ├── llm/                   # 大语言模型连接器
│   │   └── rerank/                # 重排序模型连接器
│   ├── core/                      # 核心业务逻辑
│   │   ├── chains/                # 处理链
│   │   ├── retriever/             # 检索器
│   │   │   ├── parent_retriever.py    # 父文档检索器
│   │   │   ├── vectorstore.py         # Milvus 客户端
│   │   │   └── elasticsearchstore.py  # ES 客户端
│   │   ├── tools/                 # 工具模块
│   │   └── local_doc_qa.py        # 核心问答类
│   ├── dependent_server/          # 微服务
│   │   ├── embedding_server/      # 嵌入服务
│   │   ├── rerank_server/         # 重排序服务
│   │   ├── ocr_server/            # OCR 服务
│   │   ├── pdf_parser_server/     # PDF 解析服务
│   │   └── insert_files_serve/    # 文件插入服务
│   ├── qanything_server/          # 主服务
│   │   └── sanic_api.py          # Sanic API 服务器
│   └── utils/                     # 工具类
│       ├── loader/                # 文件加载器
│       └── splitter/              # 文本分割器
├── scripts/                       # 脚本文件
│   └── entrypoint.sh             # 启动脚本
├── front_end/                     # 前端代码
├── requirements.txt               # Python 依赖
└── docker-compose-win.yaml        # Docker 配置
```

---

## 3. 核心组件详解

### 3.1 API 服务层 (sanic_api.py)

**文件位置**: `qanything_kernel/qanything_server/sanic_api.py`

#### 主要功能
- 基于 Sanic 框架的异步 Web 服务器
- 提供 RESTful API 接口
- 支持多 Worker 模式 (默认 4 个)
- 配置 CORS 跨域支持
- 请求体最大 128MB

#### 核心 API 接口

| 接口路径 | 方法 | 功能描述 |
|---------|------|---------|
| `/api/local_doc_qa/new_knowledge_base` | POST | 新建知识库 |
| `/api/local_doc_qa/upload_files` | POST | 上传文件 |
| `/api/local_doc_qa/local_doc_chat` | POST | 问答接口 |
| `/api/local_doc_qa/list_knowledge_base` | POST | 知识库列表 |
| `/api/local_doc_qa/list_files` | POST | 文件列表 |
| `/api/local_doc_qa/delete_files` | POST | 删除文件 |
| `/api/local_doc_qa/delete_knowledge_base` | POST | 删除知识库 |
| `/api/local_doc_qa/new_bot` | POST | 新建 Bot |
| `/api/local_doc_qa/get_rerank_results` | POST | 获取 Rerank 结果 |

#### 启动流程

```python
# 1. 服务初始化
app = Sanic("QAnything")
app.config.CORS_ORIGINS = "*"
app.config.REQUEST_MAX_SIZE = 128 * 1024 * 1024

# 2. 加载核心组件
@app.before_server_start
async def init_local_doc_qa(app, loop):
    local_doc_qa = LocalDocQA(args.port)
    local_doc_qa.init_cfg(args)
    app.ctx.local_doc_qa = local_doc_qa

# 3. 启动服务
app.run(host='0.0.0.0', port=8777, workers=4)
```

---

### 3.2 核心业务层 (LocalDocQA)

**文件位置**: `qanything_kernel/core/local_doc_qa.py`

#### 类结构

```python
class LocalDocQA:
    def __init__(self, port):
        self.port = port
        self.milvus_cache = None
        self.embeddings: YouDaoEmbeddings = None
        self.rerank: YouDaoRerank = None
        self.milvus_kb: VectorStoreMilvusClient = None
        self.retriever: ParentRetriever = None
        self.milvus_summary: KnowledgeBaseManager = None
        self.es_client: StoreElasticSearchClient = None
```

#### 核心方法

##### 1. `get_knowledge_based_answer()` - 知识库问答主流程

```python
async def get_knowledge_based_answer(
    self, model, max_token, kb_ids, query, retriever,
    custom_prompt, time_record, temperature, api_base,
    api_key, api_context_length, top_p, top_k, web_chunk_size,
    chat_history=None, streaming=True, rerank=False,
    only_need_search_results=False, need_web_search=False,
    hybrid_search=False
):
```

**流程图**:

```
用户查询
    │
    ▼
┌───────────────────┐
│ 1. 问题重写        │ (如果有历史对话)
│ RewriteQuestion   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. 文档检索        │
│ - Milvus 向量检索  │
│ - ES 全文检索      │ (可选)
│ - 网页搜索         │ (可选)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. 文档重排序      │ (可选)
│ Rerank Model      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Token 管理     │
│ - 计算可用 token   │
│ - 裁剪文档         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. Prompt 构建    │
│ - 系统提示         │
│ - 上下文文档       │
│ - 用户问题         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. LLM 生成       │
│ - 流式输出         │
│ - 图片相关性计算   │
└────────┬──────────┘
         │
         ▼
      返回答案
```

##### 2. `get_source_documents()` - 文档检索

```python
async def get_source_documents(
    self, query, retriever: ParentRetriever,
    kb_ids, time_record, hybrid_search, top_k
):
    # 1. 从 Milvus 检索
    query_docs = await retriever.get_retrieved_documents(
        query, partition_keys=kb_ids,
        time_record=time_record,
        hybrid_search=hybrid_search,
        top_k=top_k
    )

    # 2. 过滤已删除的文件
    for doc in query_docs:
        if retriever.mysql_client.is_deleted_file(doc.metadata['file_id']):
            continue
        source_documents.append(doc)

    return source_documents
```

##### 3. `reprocess_source_documents()` - Token 管理

```python
def reprocess_source_documents(
    self, custom_llm, query, source_docs, history, prompt_template
):
    # 计算可用 token 数
    limited_token_nums = (
        custom_llm.token_window
        - custom_llm.max_token
        - custom_llm.offcut_token
        - query_token_num
        - history_token_num
        - template_token_num
    )

    # 贪心算法填充文档
    for doc in source_docs:
        if total_token_num + doc_token_num <= limited_token_nums:
            new_source_docs.append(doc)
            total_token_num += doc_token_num
        else:
            break

    return new_source_docs, limited_token_nums
```

---

### 3.3 检索器 (ParentRetriever)

**文件位置**: `qanything_kernel/core/retriever/parent_retriever.py`

#### 设计理念

采用**父子文档检索策略**，解决向量检索上下文不完整的问题：

```
原始文档
    │
    ├── 父文档 (800 tokens) ──► 存储到 MySQL (完整上下文)
    │       │
    │       ├── 子文档1 (400 tokens) ──► 向量化存储到 Milvus
    │       ├── 子文档2 (400 tokens) ──► 向量化存储到 Milvus
    │       └── 子文档3 (400 tokens) ──► 向量化存储到 Milvus
```

**检索流程**:
1. 用户查询向量化
2. 在 Milvus 中检索相似的**子文档**
3. 根据子文档的 `doc_id` 从 MySQL 获取对应的**父文档**
4. 返回完整的父文档作为上下文

#### 类结构

```python
class ParentRetriever:
    def __init__(self, vectorstore_client, mysql_client, es_client):
        # 父文档分割器 (800 tokens)
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=0,
            length_function=num_tokens_embed
        )

        # 子文档分割器 (400 tokens)
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=100,
            length_function=num_tokens_embed
        )

        # 初始化检索器
        self.retriever = SelfParentRetriever(
            vectorstore=vectorstore_client.local_vectorstore,
            docstore=MysqlStore(mysql_client),
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
        )
```

#### 混合检索策略

```python
async def get_retrieved_documents(
    self, query, partition_keys, time_record, hybrid_search, top_k
):
    # 1. Milvus 向量检索
    milvus_docs = await self.retriever.aget_relevant_documents(query)

    if not hybrid_search:
        return milvus_docs

    # 2. Elasticsearch 全文检索
    es_docs = await self.es_store.asimilarity_search(
        query, k=top_k, filter=filter
    )

    # 3. 合并去重
    merged_docs = milvus_docs + [去重后的 es_docs]

    return merged_docs
```

**优势**:
- **向量检索**: 语义相似度高，适合模糊查询
- **全文检索**: 关键词精确匹配，适合专有名词
- **混合检索**: 结合两者优势，提高召回率

---

## 4. 数据存储层

### 4.1 数据库架构

| 数据库 | 用途 | 端口 | 数据类型 |
|-------|------|------|---------|
| **Milvus** | 向量存储 | 19540 | 文档向量、子文档索引 |
| **MySQL** | 元数据存储 | 3316 | 父文档内容、知识库信息、用户信息 |
| **Elasticsearch** | 全文搜索 | 9210 | 文档全文索引 |
| **MinIO** | 对象存储 | 9000 | 原始文件、模型文件 |

### 4.2 数据流转

```
上传文件
    │
    ▼
┌──────────────┐
│ PDF Parser   │ ──► 提取文本、表格、图片
│ OCR Service  │ ──► 识别图片文字
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Text Splitter│ ──► 分割为父子文档
└──────┬───────┘
       │
       ├──────────────────┬─────────────────┐
       ▼                  ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   MySQL     │   │   Milvus    │   │     ES      │
│ (父文档)     │   │ (子文档向量) │   │ (全文索引)   │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## 5. AI 服务层

### 5.1 微服务架构

| 服务名称 | 端口 | 功能 | 后端实现 |
|---------|------|------|---------|
| **embedding_server** | 9001 | 文本向量化 | ONNX Runtime |
| **rerank_server** | 8001 | 文档重排序 | ONNX Runtime |
| **ocr_server** | 7001 | 文字识别 | PaddleOCR |
| **pdf_parser_server** | 9009 | PDF 解析 | PyMuPDF |
| **insert_files_server** | 8110 | 文件插入 | - |

### 5.2 Embedding 服务

**文件位置**: `qanything_kernel/dependent_server/embedding_server/`

**核心功能**:
- 将文本转换为向量表示
- 支持批量处理
- 使用 ONNX Runtime 加速推理

**配置**:
```python
LOCAL_EMBED_SERVICE_URL = "localhost:9001"
LOCAL_EMBED_MODEL_NAME = 'embed'
LOCAL_EMBED_MAX_LENGTH = 512
LOCAL_EMBED_BATCH = 1
```

### 5.3 Rerank 服务

**文件位置**: `qanything_kernel/dependent_server/rerank_server/`

**核心功能**:
- 对检索结果进行二次排序
- 计算查询与文档的相关性分数
- 过滤低分文档 (阈值: 0.28)

**Rerank 流程**:
```python
# 1. 初次过滤
source_documents = await self.rerank.arerank_documents(query, docs)

# 2. 分数过滤 (score >= 0.28)
filtered_documents = [doc for doc in source_documents if doc.metadata['score'] >= 0.28]

# 3. 相对差异过滤 (分数差异 > 50%)
saved_docs = [source_documents[0]]
for doc in source_documents[1:]:
    relative_difference = (saved_docs[0].metadata['score'] - doc.metadata['score']) / saved_docs[0].metadata['score']
    if relative_difference > 0.5:
        break
    saved_docs.append(doc)
```

---

## 6. 配置详解 (model_config.py)

**文件位置**: `qanything_kernel/configs/model_config.py`

### 6.1 检索参数

```python
# 向量检索返回文档数
VECTOR_SEARCH_TOP_K = 30

# 向量检索分数阈值
VECTOR_SEARCH_SCORE_THRESHOLD = 0.3

# ES 检索返回文档数
ES_TOP_K = 30
```

### 6.2 文本分割参数

```python
# 子文档大小
DEFAULT_CHILD_CHUNK_SIZE = 400

# 父文档大小
DEFAULT_PARENT_CHUNK_SIZE = 800

# 分隔符 (优先级从高到低)
SEPARATORS = ["\n\n", "\n", "。", "，", ",", ".", ""]
```

### 6.3 提示词模板

#### 系统提示词 (SYSTEM)

```python
SYSTEM = """
You are always a reliable assistant that can answer questions with the help of external documents.

### Global Answering Rules:
1. **Strict content matching**:
    - Your responses should always be based on the reference information provided.
    - Do not speculate or invent information that is not present in the documents.
2. **Answer format**:
    - Provide well-structured answers, using headings, bullet points, or tables when appropriate.
3. **No redundancy**:
    - If different parts of the reference contain overlapping information, merge and summarize them.
4. **Flexible use of information sources**:
    - During the inference and reasoning process, use the "Information Sources" module to track document citations.
    - **Do not include the full "Information Sources" section in the final user-facing answer**.
5. **Start the "Inferred Answer" Section**:
    - Directly start the user-facing response with "According to the reference information".
"""
```

#### 指令模板 (INSTRUCTIONS)

```python
INSTRUCTIONS = """
- Task: Answer the question "{{question}}" strictly based on the reference information.

### Answering Steps:
1. **Use of Information Sources** (Internal step):
    - During the inference process, use the "Information Sources" section to gather and organize the relevant document citations.
    - **Each reference** must be listed in the following format:
        - **ID**: [REF.1]
            - **Title**: (The filename or title)
            - **Section**: (Specify the section or subheading)
            - **Abstract**: (Summarize the most relevant content)
2. **Start the "Inferred Answer Section"**:
    - Directly begin with "According to the reference information".
    - If completely irrelevant, respond with: "抱歉，检索到的参考信息并未提供任何相关的信息，因此无法回答。"
"""
```

---

## 7. 部署架构

### 7.1 Docker Compose 配置

**文件位置**: `docker-compose-win.yaml`

```yaml
services:
  # Elasticsearch 全文搜索
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.2
    ports: ["9210:9200"]
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false

  # Milvus 依赖服务
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z

  # Milvus 向量数据库
  standalone:
    image: milvusdb/milvus:v2.4.8
    ports: ["19540:19530"]
    depends_on: [etcd, minio]

  # MySQL 元数据库
  mysql:
    image: mysql:8.4
    ports: ["3316:3306"]
    environment:
      - MYSQL_ROOT_PASSWORD=123456

  # QAnything 主服务
  qanything_local:
    image: xixihahaliu01/qanything-win:v1.5.1
    ports: ["8777:8777"]
    depends_on: [standalone, mysql, elasticsearch]
```

### 7.2 启动流程 (entrypoint.sh)

```bash
#!/bin/bash

# 1. 创建软链接 (模型文件)
ln -s /root/models/linux_onnx/embedding_model_configs_v0.0.1 .
ln -s /root/models/linux_onnx/rerank_model_configs_v0.0.1 .
ln -s /root/models/ocr_models .

# 2. 启动微服务
nohup python3 rerank_server.py > logs/rerank_server.log 2>&1 &
nohup python3 embedding_server.py > logs/embedding_server.log 2>&1 &
nohup python3 pdf_parser_server.py > logs/pdf_parser_server.log 2>&1 &
nohup python3 ocr_server.py > logs/ocr_server.log 2>&1 &
nohup python3 insert_files_server.py --port 8110 > logs/insert_files_server.log 2>&1 &

# 3. 启动主服务
nohup python3 sanic_api.py --host 0.0.0.0 --port 8777 --workers 1 > logs/main_server.log 2>&1 &

# 4. 监控启动状态
while ! grep -q "Starting worker" logs/main_server.log; do
    echo "Waiting for the backend service to start..."
    sleep 5
done

echo "QAnything 后端服务已就绪!"
```

---

## 8. 性能优化策略

### 8.1 检索优化

#### 1. 向量索引优化
```python
# Milvus 索引配置
index_params = {
    "metric_type": "IP",  # 内积距离
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}
```

#### 2. 批量处理
```python
# Embedding 批量处理
embeddings = await self.embeddings.aembed_documents(documents)
```

#### 3. 缓存机制
```python
# 知识库缓存
CACHED_VS_NUM = 100  # 缓存 100 个知识库
```

### 8.2 Token 优化

#### 1. 动态 Token 分配
```python
def reprocess_source_documents(self, custom_llm, query, source_docs, history, prompt_template):
    # 计算各部分 token 占用
    query_token_num = custom_llm.num_tokens_from_messages([query])
    history_token_num = custom_llm.num_tokens_from_messages(history)
    template_token_num = custom_llm.num_tokens_from_messages([prompt_template])

    # 计算可用 token
    limited_token_nums = (
        token_window - max_token - offcut_token
        - query_token_num - history_token_num - template_token_num
    )
```

#### 2. 文档去重
```python
# 去除重复文档
source_documents = deduplicate_documents(source_documents)
```

### 8.3 并发优化

#### 1. 异步处理
```python
# 异步检索
async def get_source_documents(self, query, retriever, kb_ids, time_record, hybrid_search, top_k):
    query_docs = await retriever.get_retrieved_documents(...)

# 异步 Rerank
source_documents = await self.rerank.arerank_documents(query, source_documents)
```

#### 2. 多 Worker 模式
```python
# Sanic 多 Worker
app.run(host='0.0.0.0', port=8777, workers=4)
```

---

## 9. 关键技术点

### 9.1 父子文档检索

**问题**: 向量检索返回的文档片段可能缺乏上下文

**解决方案**:
1. 文档分割为父子两层
2. 子文档用于向量检索 (粒度细，命中率高)
3. 父文档用于上下文提供 (信息完整)

**代码实现**:
```python
# parent_retriever.py
class SelfParentRetriever(ParentDocumentRetriever):
    async def _aget_relevant_documents(self, query: str):
        # 1. 检索子文档
        sub_docs = await self.vectorstore.asimilarity_search_with_score(query)

        # 2. 获取父文档 ID
        ids = [d.metadata[self.id_key] for d in sub_docs]

        # 3. 从 MySQL 获取父文档
        docs = await self.docstore.amget(ids)

        return docs
```

### 9.2 混合检索

**问题**: 单一向量检索无法处理专有名词和关键词

**解决方案**:
1. Milvus 向量检索 (语义相似)
2. Elasticsearch 全文检索 (关键词匹配)
3. 合并去重

**代码实现**:
```python
# parent_retriever.py
async def get_retrieved_documents(self, query, partition_keys, time_record, hybrid_search, top_k):
    # 1. Milvus 检索
    milvus_docs = await self.retriever.aget_relevant_documents(query)

    # 2. ES 检索
    es_docs = await self.es_store.asimilarity_search(query, k=top_k, filter=filter)

    # 3. 去重合并
    milvus_doc_ids = [d.metadata['doc_id'] for d in milvus_docs]
    for d in es_docs:
        if d.metadata['doc_id'] not in milvus_doc_ids:
            milvus_docs.append(d)

    return milvus_docs
```

### 9.3 Rerank 重排序

**问题**: 向量检索的相似度分数不够准确

**解决方案**:
1. 使用 Rerank 模型重新计算相关性
2. 三层过滤策略

**代码实现**:
```python
# local_doc_qa.py
if rerank and len(source_documents) > 1:
    # 1. Rerank 重排序
    source_documents = await self.rerank.arerank_documents(query, source_documents)

    # 2. 绝对分数过滤 (score >= 0.28)
    source_documents = [doc for doc in source_documents if doc.metadata['score'] >= 0.28]

    # 3. 相对差异过滤 (分数差异 > 50%)
    saved_docs = [source_documents[0]]
    for doc in source_documents[1:]:
        relative_difference = (saved_docs[0].metadata['score'] - doc.metadata['score']) / saved_docs[0].metadata['score']
        if relative_difference > 0.5:
            break
        saved_docs.append(doc)
```

### 9.4 流式输出

**问题**: LLM 生成耗时长，用户等待体验差

**解决方案**:
1. 异步生成器
2. SSE (Server-Sent Events) 协议

**代码实现**:
```python
# local_doc_qa.py
async def get_knowledge_based_answer(..., streaming=True):
    async for answer_result in custom_llm.generatorAnswer(prompt, history, streaming):
        resp = answer_result.llm_output["answer"]

        if streaming:
            # SSE 格式
            resp = 'data: ' + json.dumps({'answer': resp}, ensure_ascii=False)

        yield response, history

    # 发送结束标志
    if streaming:
        response['result'] = "data: [DONE]\n\n"
        yield response, history
```

---

## 10. 扩展性设计

### 10.1 插件化架构

**连接器模式**:
```python
# 统一接口
class BaseEmbeddings:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    async def aembed_query(self, text: str) -> List[float]:
        pass

# 具体实现
class YouDaoEmbeddings(BaseEmbeddings):
    ...

class OpenAIEmbeddings(BaseEmbeddings):
    ...
```

### 10.2 多 LLM 支持

```python
# connector/llm/
├── base/
│   └── llm_base.py         # 基类
├── openai_llm.py           # OpenAI
├── azure_llm.py            # Azure
└── local_llm.py            # 本地模型
```

### 10.3 多数据库支持

```python
# connector/database/
├── faiss/                  # Faiss
├── milvus/                 # Milvus
├── weaviate/               # Weaviate
└── pinecone/               # Pinecone
```

---

## 11. 监控与日志

### 11.1 日志系统

**日志分类**:
```python
# 自定义日志器
from qanything_kernel.utils.custom_log import (
    debug_logger,    # 调试日志
    qa_logger,       # 问答日志
    rerank_logger,   # Rerank 日志
    insert_logger    # 插入日志
)
```

**日志示例**:
```python
# 记录检索时间
debug_logger.info(f"retriever_search time: {time_record['retriever_search']}s")

# 记录 Rerank 分数
debug_logger.info(f"rerank step1 scores: {[doc.metadata['score'] for doc in source_documents]}")

# 记录 Token 使用
debug_logger.info(f"token_window = {custom_llm.token_window}, max_token = {custom_llm.max_token}")
```

### 11.2 性能监控

**时间记录**:
```python
time_record = {
    'condense_q_chain': 0.0,           # 问题重写时间
    'retriever_search': 0.0,           # 检索时间
    'rerank': 0.0,                     # Rerank 时间
    'reprocess': 0.0,                  # 文档处理时间
    'llm_first_return': 0.0,           # LLM 首次返回时间
    'llm_completed': 0.0,              # LLM 完成时间
    'prompt_tokens': 0,                # Prompt Token 数
    'completion_tokens': 0,            # Completion Token 数
    'total_tokens': 0                  # 总 Token 数
}
```

---

## 12. 最佳实践

### 12.1 文档上传建议

1. **单文件大小**: 建议 < 10MB
2. **字符数限制**: 单文件 < 1,000,000 字符
3. **格式优化**:
   - PDF: 使用文字版 PDF (非扫描版)
   - Word: 使用标题层级结构
   - Markdown: 合理使用标题和分段

### 12.2 检索参数调优

```python
# 高准确率场景
VECTOR_SEARCH_TOP_K = 10
rerank = True

# 高召回率场景
VECTOR_SEARCH_TOP_K = 50
hybrid_search = True

# 平衡场景
VECTOR_SEARCH_TOP_K = 30
rerank = True
hybrid_search = True
```

### 12.3 Token 配置建议

| 场景 | token_window | max_token | history_len |
|------|--------------|-----------|-------------|
| 简单问答 | 4096 | 512 | 0 |
| 多轮对话 | 8192 | 1024 | 3 |
| 长文档分析 | 16384 | 2048 | 1 |

---

## 13. 常见问题与解决方案

### 13.1 检索不到相关文档

**原因**:
1. 向量相似度分数过低
2. 文档未正确解析
3. 知识库 ID 配置错误

**解决方案**:
```python
# 1. 降低分数阈值
VECTOR_SEARCH_SCORE_THRESHOLD = 0.2

# 2. 开启混合检索
hybrid_search = True

# 3. 检查文档解析日志
tail -f logs/debug_logs/insert_files_server.log
```

### 13.2 LLM 回答不准确

**原因**:
1. 上下文文档不足
2. Prompt 设计不合理
3. Token 裁切过度

**解决方案**:
```python
# 1. 增加 TOP_K
VECTOR_SEARCH_TOP_K = 50

# 2. 自定义 Prompt
custom_prompt = "请基于提供的文档详细回答问题，引用具体段落..."

# 3. 增加 token_window
api_context_length = 16384
```

### 13.3 响应速度慢

**原因**:
1. 检索文档过多
2. Rerank 耗时长
3. LLM 生成慢

**解决方案**:
```python
# 1. 减少 TOP_K
VECTOR_SEARCH_TOP_K = 10

# 2. 关闭 Rerank (牺牲精度换速度)
rerank = False

# 3. 使用更快的 LLM
model = "gpt-3.5-turbo"  # 而非 gpt-4
```

---

## 14. 未来优化方向

### 14.1 性能优化

- [ ] 引入向量数据库缓存 (Redis)
- [ ] 实现 Rerank 模型量化 (INT8)
- [ ] 支持多模态检索 (图文混合)

### 14.2 功能扩展

- [ ] 支持知识图谱
- [ ] 集成 Agent 框架 (LangChain Agent)
- [ ] 实现多轮对话记忆管理

### 14.3 架构优化

- [ ] 微服务拆分 (更细粒度)
- [ ] 引入消息队列 (RabbitMQ/Kafka)
- [ ] 实现分布式部署 (Kubernetes)

---

## 15. 总结

QAnything 是一个设计精良的 RAG 系统，具有以下特点:

### 优势
1. **架构清晰**: 分层设计，职责明确
2. **扩展性强**: 插件化架构，易于扩展
3. **性能优秀**: 异步处理，多级缓存
4. **功能完善**: 混合检索、Rerank、流式输出

### 核心创新点
1. **父子文档检索**: 平衡检索精度和上下文完整性
2. **三层 Rerank 过滤**: 提高答案相关性
3. **动态 Token 管理**: 最大化利用上下文窗口

### 适用场景
- 企业知识库问答
- 技术文档检索
- 客服机器人
- 个人知识管理

---

## 附录

### A. 关键文件索引

| 文件路径 | 功能描述 |
|---------|---------|
| `qanything_kernel/core/local_doc_qa.py` | 核心问答逻辑 |
| `qanything_kernel/core/retriever/parent_retriever.py` | 父文档检索器 |
| `qanything_kernel/configs/model_config.py` | 系统配置 |
| `qanything_kernel/qanything_server/sanic_api.py` | API 服务 |
| `scripts/entrypoint.sh` | 启动脚本 |

### B. 环境变量

```bash
# Docker 环境变量
GATEWAY_IP=host.docker.internal    # 网关 IP
GPUID=0                            # GPU ID
USER_IP=0.0.0.0                    # 用户访问 IP
```

### C. 端口映射

| 服务 | 容器端口 | 主机端口 |
|------|---------|---------|
| QAnything API | 8777 | 8777 |
| Milvus | 19530 | 19540 |
| MySQL | 3306 | 3316 |
| Elasticsearch | 9200 | 9210 |
| Embedding | 9001 | - |
| Rerank | 8001 | - |
| OCR | 7001 | - |
| PDF Parser | 9009 | - |

---

**文档版本**: v1.0
**最后更新**: 2025-03-07
**作者**: Claude AI
**适用版本**: QAnything v1.5.1
