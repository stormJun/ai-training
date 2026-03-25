# RAG (Retrieval-Augmented Generation) 系统学习指南

> 本文档是 RAG RAG 系统学习的总览性指南,整合了 LlamaIndex、RAGAS 评估、混合检索等核心内容。

## 📚 目录

1. [RAG 概述与架构](#1-rag-概述与架构)
2. [RAG主流程](#2-rag主流程)
3. [核心组件详解](#3-核心组件详解)
4. [RAGAS 评估体系](#4-ragas-评估体系)
5. [混合检索策略](#5-混合检索策略)
6. [工程化最佳实践](#6-工程化最佳实践)
7. [学习路径与资源](#7-学习路径与资源)
8. [RAG vs 微调选择指南](#8-rag-vs-微调选择指南)
9. [Agentic RAG - 智能体增强检索](#9-agentic-rag---智能体增强检索)

---

## 1. RAG 概述与架构

### 1.1 什么是 RAG

RAG (Retrieval-Augmented Generation) 是一种将检索和生成相结合的技术架构,通过从知识库中检索相关信息来增强大语言模型的回答能力。

### 1.3 RAG 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      RAG 系统架构                            │
└─────────────────────────────────────────────────────────────┘
用户查询
    ↓
┌──────────────────────────────────────────────────────────┐
│              1. 查询处理层 (Query Processing)             │
│  • 查询理解与改写 (HyDE, Query Expansion)                │
│  • 意图识别                                              │
│  • 查询向量化                                            │
│  • 实体识别与关系抽取 (NER, Relation Extraction)         │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│              2. 检索层 (Retrieval)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ 向量检索  │  │ 全文检索  │  │ 混合检索  │  │知识图谱  ││
│  │ (Milvus) │  │(ES/BM25) │  │ (Hybrid) │  │(Neo4j)   ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
│  • 相似度计算          • 实体关系查询                     │
│  • Top-K 检索          • 多跳推理                         │
│  • 结果合并与去重      • 路径检索                         │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│              3. 后处理层 (Post-processing)                │
│  • 重排序 (Re-ranking)                                   │
│  • 相似度过滤 (Similarity Filtering)                     │
│  • 上下文窗口优化                                        │
│  • 知识融合 (Knowledge Fusion)                           │
│    - 向量结果 + 图谱三元组融合                            │
│    - 事实一致性校验                                      │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│              4. 生成层 (Generation)                       │
│  • Prompt 构造                                           │
│  • 上下文整合                                            │
│  • 结构化知识注入 (Structured Knowledge Injection)       │
│  • LLM 生成回答                                          │
└──────────────────────────────────────────────────────────┘
    ↓
最终答案 (带引用来源 + 知识溯源)
```

**知识图谱在RAG中的作用**:

```
┌─────────────────────────────────────────────────────────┐
│         知识图谱增强的RAG系统 (KG-Enhanced RAG)         │
└─────────────────────────────────────────────────────────┘

1. 实体关系检索
   查询: "马斯克的公司有哪些？"
   传统RAG: 文本匹配 → 可能漏掉关联公司
   KG-RAG: 实体链接 → (马斯克)-[创立]->(特斯拉, SpaceX, Neuralink)

2. 多跳推理
   查询: "特斯拉的竞争对手的CEO是谁？"
   传统RAG: 难以处理
   KG-RAG:
     (特斯拉)-[竞争]->(比亚迪)-[CEO]->(王传福)
     (特斯拉)-[竞争]->(蔚来)-[CEO]->(李斌)

3. 知识融合
   向量检索: "Python由Guido van Rossum创建" (相似度0.88)
   知识图谱: (Python)-[创建者]->(Guido van Rossum)
   融合结果: 结构化事实 + 文本描述

4. 实时知识更新
   向量库: 需要重新索引
   知识图谱: 直接修改三元组 (实体, 关系, 实体)
```

**知识图谱 vs 向量检索对比**:

| 维度 | 向量检索 | 知识图谱 | 混合检索 |
|------|---------|---------|---------|
| **擅长** | 语义理解、模糊匹配 | 精确关系、多跳推理 | 综合优势 |
| **查询类型** | "如何使用Python？" | "马斯克的公司有哪些？" | 所有类型 |
| **知识更新** | 需重建索引 | 直接修改三元组 | 灵活更新 |
| **可解释性** | 低 (黑盒向量) | 高 (明确路径) | 中等 |
| **成本** | 中等 (向量计算) | 高 (图谱构建) | 最高 |
| **适用场景** | 通用问答 | 结构化知识、推理 | 企业级应用 |

## 2. RAG主流程

RAG 系统的完整工作周期包含 5 个核心阶段，每个阶段都有明确的目标和关键技术：

```
┌─────────────────────────────────────────────────────────┐
│              RAG 系统完整工作周期                        │
└─────────────────────────────────────────────────────────┘

  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  加载    │───→│  索引    │───→│  存储    │
  	(Load)  │    │ (Index) │    │ (Store) │
  └─────────┘    └─────────┘    └─────────┘
       ↑                              │
       │                              ↓
  ┌─────────┐                   ┌─────────┐
  │  评估    │←─────────────────│  查询    │
  │(Evaluate)│                   │ (Query) │
  └─────────┘                   └─────────┘
```

**能力视角总览（框架无关）**:

| 阶段 | 实现形态 | 主要功能 | 关键组件（示例） |
|------|---------|---------|---------|
| **加载** | Reader/Connector | 数据加载与解析 | `Reader`、`Document` |
| **索引** | Parser + Embedder + Index | 切片、向量化、索引构建 | `Splitter`、`EmbeddingModel`、`Index` |
| **存储** | DocStore + VectorStore | 持久化存储 | `StorageContext`、向量库客户端 |
| **查询** | Retriever + Reranker + Generator | 检索、重排序、生成 | `QueryEngine`、`Retriever`、`Reranker` |
| **评估** | Evaluation Pipeline | 质量评估与优化 | 自动指标、人工评测、A/B |

> **说明**: 本节以概念和工程职责为主。具体实现可映射到任意框架（如 LlamaIndex/LangChain/自研检索服务等）。

### 2.1 加载阶段 (Load)

> **实现重点**: 加载阶段关注“多源接入 + 格式解析 + 元数据保真”，与具体框架无关。

**目标**: 将各种来源的原始数据转换为结构化的文档对象

**核心任务**:

```
原始数据 → 文档加载器 → Document 对象
```

**核心组件**:

```
┌──────────────────────────────────────────────────┐
│          加载阶段核心组件                         │
└──────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐
│  连接器       │─────────→│  文档对象     │
│ (Connector)  │         │ (Document)   │
└──────────────┘         └──────────────┘
       ↓                        ↓
  数据源适配              结构化数据
```

1. **连接器 (Connector/Reader)**
   - **作用**: 从不同数据源读取数据并转换为 Document 对象
   - **类型**:
     - `SimpleDirectoryReader`: 本地文件目录
     - `PyMuPDFReader`: PDF 文档
     - `DatabaseReader`: 数据库
     - `WebPageReader`: 网页
     - `NotionPageReader`: Notion 页面
   - **职责**: 处理文件格式、编码、元数据提取

   **自定义加载器开发**:

   ```python
   from llama_index.core.readers.base import BaseReader
   from llama_index.core.schema import Document
   from typing import List, Optional
   
   class CustomDocumentReader(BaseReader):
       """自定义文档加载器示例"""
   
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
   
       def load_data(
           self,
           file_path: str,
           extra_info: Optional[dict] = None
       ) -> List[Document]:
           """
           加载数据的核心方法
           Args:
               file_path: 文件路径
               extra_info: 额外的元数据
           Returns:
               Document 对象列表
           """
           # 1. 读取文件内容
           with open(file_path, 'r', encoding='utf-8') as f:
               content = f.read()
           # 2. 处理特殊格式（如加密文档）
           if self._is_encrypted(file_path):
               content = self._decrypt(content)
           # 3. 提取元数据
           metadata = {
               "source": file_path,
               "file_type": self._get_file_type(file_path),
               "created_at": self._get_creation_time(file_path),
               "author": self._extract_author(content)
           }
           # 合并额外信息
           if extra_info:
               metadata.update(extra_info)
           # 4. 创建 Document 对象
           return [Document(text=content, metadata=metadata)]
   
   # 使用自定义加载器
   custom_reader = CustomDocumentReader()
   documents = custom_reader.load_data(
       "./data/special_file.custom",
       extra_info={"category": "technical"}
   )
   ```
   
   **文档处理配置详解**:
   
   ```python
   from llama_index.core import SimpleDirectoryReader
   
   # 1. 基础配置
   reader = SimpleDirectoryReader(
       input_dir="./data",                    # 输入目录
       input_files=["./file1.pdf"],           # 或指定文件列表
       exclude=["*.tmp", "*.bak"],            # 排除文件模式
       exclude_hidden=True,                    # 排除隐藏文件（默认True）
       recursive=True,                         # 递归读取子目录
       required_exts=[".pdf", ".md", ".txt"],  # 只读取指定扩展名
       show_progress=True,                     # 显示进度条
       num_files_limit=100                     # 限制文件数量
   )
   
   documents = reader.load_data()
   
   # 2. 高级配置
   def custom_metadata_func(file_path: str) -> dict:
       """自定义元数据提取函数"""
       return {
           "source": file_path,
           "author": extract_author(file_path),
           "created_at": get_creation_time(file_path),
           "modified_at": get_modified_time(file_path),
           "file_size": get_file_size(file_path),
           "category": classify_document(file_path)
       }
   
   reader = SimpleDirectoryReader(
       input_dir="./data",
       file_metadata=custom_metadata_func,  # 自定义元数据提取
       exclude=["*.tmp"],
       recursive=True
   )
   
   # 3. 处理特殊文件
   # - 加密文档
   # - 损坏文件
   # - 大文件分块读取
   ```
   
   **支持的文件格式**:
   
   | 文件类型 | 加载器 | 特点 | 配置参数 |
   |---------|--------|------|---------|
   | **PDF** | `PyMuPDFReader` | 保留格式，提取表格 | `extract_images=True` |
   | **Word** | `DocxReader` | 支持样式和表格 | - |
   | **Markdown** | `MarkdownReader` | 保留结构 | `remove_hyperlinks=True` |
   | **CSV** | `PandasCSVReader` | 结构化数据 | `pandas_config={}` |
   | **JSON** | `JSONReader` | 嵌套结构 | `levels=3` |
   | **代码** | `SimpleDirectoryReader` | 按文件加载 | `required_exts=[".py"]` |
   | **图像** | `ImageReader` | OCR提取文字 | `ocr_engine="tesseract"` |
   | **音频** | `AudioTranscriber` | 语音转文字 | `model="whisper"` |
   | **视频** | `VideoTranscriber` | 提取字幕 | - |
   
   
   
   **数据层架构图**:
   
   ```
   ┌─────────────────────────────────────────────────────┐
   │           数据层 (Data Layer)                        │
   └─────────────────────────────────────────────────────┘
   
   数据源
   ├── 文件系统 (本地文件)
   ├── 数据库 (SQL/NoSQL)
   ├── API (远程接口)
   ├── 云存储 (S3/OSS)
   └── 实时流 (消息队列)
        ↓
   ┌──────────────────┐
   │  BaseReader      │  ← 抽象基类
   │  (抽象接口)      │
   └──────────────────┘
        ↓
   ┌──────────────────────────────────────────┐
   │        具体加载器实现                      │
   ├──────────────────────────────────────────┤
   │ SimpleDirectoryReader (通用文件)         │
   │ PyMuPDFReader (PDF)                      │
   │ DocxReader (Word)                        │
   │ DatabaseReader (数据库)                  │
   │ CustomReader (自定义)                    │
   └──────────────────────────────────────────┘
        ↓
   ┌──────────────────┐
   │  Document 对象    │
   │  + metadata       │
   └──────────────────┘
        ↓
   索引构建
   ```
   
2. **文档对象 (Document)**
   - **作用**: RAG 系统中的基本数据单元
   
   - **结构**:
     ```python
     Document(
         text="文档内容",
         metadata={
             "source": "文件路径",
             "author": "作者",
             "created_at": "创建时间"
         },
         doc_id="唯一标识"
     )
     ```
   
3. **节点 (Node)**
   
   - **作用**: Document 切片后的最小检索单元
   - **类型**:
     - `TextNode`: 文本节点
     - `ImageNode`: 图像节点
     - `IndexNode`: 索引节点
   - **关系**:
     ```
     Document (1个文档)
         ↓ 切片
     Node 1, Node 2, Node 3... (多个节点)
     ```
   - **示例**:
     ```python
     from llama_index.core.schema import TextNode
     node = TextNode(
         text="这是一个节点的文本内容",
         metadata={"source": "doc1", "page": 1},
         relationships={
             "prev_node": "node_0",
             "next_node": "node_2"
         }
     )
     ```

**详细流程**:

```python
# 1. 数据源识别
data_sources = {
    "文件系统": ["PDF", "Word", "Markdown", "TXT", "HTML"],
    "数据库": ["MySQL", "PostgreSQL", "MongoDB"],
    "网络": ["网页", "API", "Notion", "Confluence"],
    "云存储": ["S3", "OSS", "Google Drive"]
}
# 2. 文档加载
from llama_index.core import SimpleDirectoryReader, Document
# 基础加载
documents = SimpleDirectoryReader(
    input_dir="./data",
    required_exts=[".pdf", ".md"],  # 文件类型过滤
    exclude=["*.tmp", "*.bak"],      # 排除文件
    recursive=True,                   # 递归读取
    show_progress=True                # 显示进度
).load_data()
# 3. 元数据提取
for doc in documents:
    doc.metadata = {
        "source": "file_path",
        "created_at": "2024-01-01",
        "author": "unknown",
        "category": "tech_doc",
        "language": "zh-CN"
    }
# 4. 文档清洗
def clean_document(doc):
    # 去除多余空白
    doc.text = " ".join(doc.text.split())
    # 去除特殊字符
    doc.text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', doc.text)
    # 标准化格式
    doc.text = doc.text.lower()
    return doc
```

**关键考虑**:
- **文件格式支持**: 确保能正确解析各种格式
- **编码处理**: 统一 UTF-8 编码，处理乱码
- **元数据保留**: 保留文件名、时间戳、作者等信息
- **错误处理**: 跳过损坏文件，记录错误日志

**常用加载器**:

| 加载器 | 适用场景 | 特点 |
|--------|----------|------|
| `SimpleDirectoryReader` | 本地文件目录 | 简单易用，支持多种格式 |
| `PyMuPDFReader` | PDF 文档 | 保留格式，提取表格 |
| `NotionPageReader` | Notion 页面 | 支持块级解析 |
| `DatabaseReader` | 数据库 | SQL 查询转文档 |
| `WebPageReader` | 网页内容 | 支持 JS 渲染 |

### 2.2 索引阶段 (Index)

> **实现重点**: 索引阶段关注“切片质量 + 向量质量 + 索引组织”，不依赖单一框架。

**目标**: 将文档转换为可高效检索的结构化索引

**核心任务**:
```
Document → 切片 → Node → Embedding → 索引结构
```

**实战最稳切片组合策略**:

> **结构感知 + 递归 + 轻量滑窗（overlap） + 混合检索(BM25+向量+知识图谱) + 重排**
> 这套组合通常比"只用一种切片"效果更好

**核心组件**:

```
┌──────────────────────────────────────────────────┐
│          索引阶段核心组件                         │
└──────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  切片器       │───→│  嵌入模型     │───→│  索引结构     │
│ (Splitter)   │    │ (Embedding)  │    │ (Index)      │
└──────────────┘    └──────────────┘    └──────────────┘
       ↓                   ↓                   ↓
   Node 对象           向量表示            可检索结构
```

#### 2.2.1 切片器 (Node Parser/Splitter)
   - **作用**: 将 `Document` 切成可检索、可溯源、长度可控的最小单元。

 **通用切片类型详解（便于理解）**:

   | 类型 | 是什么 | 怎么切 | 优点 | 风险 | 何时用 | 起步参数/建议 |
   |---|---|---|---|---|---|---|
   | 固定长度切片（Fixed-size） | 按固定 token/字符上限切片，长度最可控。 | 从头到尾按 `chunk_size` 切，通常带 `overlap`。 | 实现简单、吞吐高、易做容量规划。 | 可能把一句话或一个语义单元硬切开。 | 第一版系统、实时性要求高、文本结构规整。 | `chunk_size=500`，`overlap=50~100`（token）。 |
   | 句子切片（Sentence-based） | 优先在句号/问号/换行等自然边界切。 | 先句子分割，再按长度合并到目标 chunk。 | 语义完整度好、可解释性强、调试直观。 | 长句多时 chunk 长度波动。 | 中文知识库、FAQ、说明文、制度文档。 | `chunk_size=400~700`，`overlap=10%~20%`。 |
   | 递归切片（Recursive） | 按分隔符优先级逐层细分（先粗后细）。 | 先按 `\n\n`，再按 `\n`，再按句号等，直到满足长度约束。 | 兼顾边界自然与长度可控，泛化好。 | 分隔符体系设计不当会不稳定。 | 多格式混合文档、跨团队知识库。 | `separators=[\"\\n\\n\",\"\\n\",\"。\",\"；\",\"，\",\" \"]`。 |
   | 结构感知切片（Structure-aware） | 按标题层级、版面块、表格块、代码块切。 | 先解析结构，再在结构内做长度控制。 | 保留章节逻辑，结果更“成段落、成主题”。 | 依赖解析质量（尤其 PDF/扫描件）。 | Markdown、HTML、PDF 报告、手册、技术文档。 | 结构优先，长度策略次之。 |
   | 语义切片（Semantic） | 用 embedding 识别语义突变点再切。 | 句子向量化，算相邻相似度，在低相似位置断开。 | 主题完整性最好，适合长文多主题。 | 成本高、参数敏感、调试复杂。 | 高价值知识库、主题跳跃明显、精度优先。 | 基线稳定后再引入，小流量 A/B。 |
   | 代码切片（Code-aware） | 按函数、类、模块、代码块边界切分。 | 优先语法边界（函数/类），再做长度控制。 | 避免拆散函数逻辑，代码问答效果更好。 | 跨函数依赖可能分散。 | 代码助手、SDK 文档、架构问答。 | 按语言设 `max_chars/chunk_size`，保留文件路径元数据。 |
   | 父子切片（Parent-Child） | 大块做父块，小块做子块；召回先子后父。 | 子块精确匹配，命中后回填父块上下文。 | 兼顾命中细节与回答完整上下文。 | 索引体积和链路复杂度上升。 | 合同、制度、SOP、规范文档。 | 常见 `parent_size:child_size=3:1~6:1`。 |
   | 窗口增强（Window Augmentation） | 给命中块追加前后上下文窗口（非独立切分法）。 | 命中后补前后 N 句或 N tokens，再参与生成。 | 明显降低“答对句子但答错语境”。 | 上下文过大引噪声并增加 token 成本。 | 图表、局部描述、上下文依赖强的问题。 | `window_size=1~3` 或 `context_tokens=80~200`。 |

   **LlamaIndex（落地视角）**:
   - 常用切片器：`TokenTextSplitter`、`SentenceSplitter`、`MarkdownNodeParser`。
   - 语义切片：`SemanticSplitterNodeParser`。
   - 代码切片：`CodeSplitter`。
   - 父子切片：`HierarchicalNodeParser`（子块召回后补父块上下文）。
   - 窗口增强：`SentenceWindow` 类方案。

   **LangChain（落地视角）**:
   - 常用切片器：`CharacterTextSplitter`、`TokenTextSplitter`、`RecursiveCharacterTextSplitter`。
   - 结构感知：`MarkdownHeaderTextSplitter`、`HTMLHeaderTextSplitter`。
   - 语义切片：`SemanticChunker`（实验/扩展方案）。
   - 父子检索：`ParentDocumentRetriever`。
   - 窗口增强：通常用 Retriever 后处理或自定义 window 逻辑。

   **RAGFlow（落地视角）**:
   - 通用切片：`chunk_token_num + delimiter + overlapped_percent`（`naive_merge` 路径）。
   - 结构感知：`DeepDOC`（版面块）+ Markdown/HTML 专用解析分支。
   - 语义切片：默认无独立“语义切分器”，通常依赖规则切分 + 混合检索 + 重排补偿。
   - 父子检索：`children_delimiter + mom_id + retrieval_by_children`。
   - 窗口增强：`table_context_size` / `image_context_size`。

   **Dify（落地视角，面试 1 分钟）**:
   1. 先定文档形态：`doc_form` 分为 `text_model`、`qa_model`、`hierarchical_model`。
   2. 再定切片规则：`process_rule.mode` 是 `automatic` / `custom` / `hierarchical`，并落库到 `dataset_process_rules`。
   3. `automatic` 也有默认切片参数（如 `max_tokens`、`chunk_overlap`）；`custom/hierarchical` 则由用户显式配置 `separator/max_tokens/chunk_overlap`。
   4. Dify 有递归切片：`custom/hierarchical` 走 `FixedRecursiveCharacterTextSplitter`（先按 `separator` 固定切，超长再递归拆）；`automatic` 走 `EnhanceRecursiveCharacterTextSplitter`（也是递归字符切分）。
   5. 执行链路是统一流水线：`IndexingRunner` 按 `extract -> transform -> _load_segments -> _load` 依次处理。
   6. `transform` 前会先清洗文本（`CleanProcessor`），常见是去噪字符、去多余空格、按规则去 URL/邮箱。
   7. 父子模式里，`parent_mode=paragraph` 是“先切父再切子”；`parent_mode=full-doc` 是“整文做父块再切子块”。
   8. 检索侧本质是“子块负责命中，父块负责补上下文”，所以能兼顾精确度和回答完整性。
   9. 入库层会写 `DocumentSegment`，父子模式还会写 `ChildChunk`；后续支持 `regenerate_child_chunks` 重建子块。
   10. 索引技术上，`high_quality` 走向量索引，`economy` 走关键词索引；前者效果优先，后者成本优先。
   11. 一句话总结：Dify 的切片是“配置驱动 + 统一管道 + 父子增强 + 索引分层”的工程化方案。

   **Dify 父子切片（面试可直接回答）**:
   1. 开关有两个：`doc_form=hierarchical_model` + `process_rule.mode=hierarchical`，两者同时满足才进入父子切片链路。
   2. 父块策略看 `parent_mode`：`paragraph` 是“先切父块再切子块”；`full-doc` 是“整篇文档作为一个父块，再切子块”。
   3. 子块参数来自 `subchunk_segmentation`（`separator/max_tokens/chunk_overlap`）；父块参数来自 `segmentation`（`paragraph` 模式下生效）。
   4. 变换阶段由 `ParentChildIndexProcessor.transform()` 产出 `Document(children=...)` 结构，父块和子块会各自产生 `doc_id/doc_hash`。
   5. 入库时 `DatasetDocumentStore.add_documents(save_child=True)` 会写两层数据：父块进 `DocumentSegment`，子块进 `ChildChunk`。
   6. 建索引时核心索引对象是子块：`ParentChildIndexProcessor.load()` 取 `document.children` 写入向量库（高质量索引路径）。
   7. 检索/启用时会从 `segment.get_child_chunks()` 还原子块，因此在线召回通常是“先命中子块，再回填父块上下文”。
   8. 文档更新后可用 `regenerate_child_chunks=true` 触发子块重建：先清旧子块索引，再按当前规则重切并重建向量。
   9. 一句话总结：Dify 父子切片本质是“父块管上下文，子块管召回精度”。

   **实战参数起步值（生产可调）**:

   1. `chunk_size`: 300~800 tokens（中文知识库常从 500 起步）。
   2. `overlap`: 10%~20%（一般不超过 25%）。
   3. `children_delimiter`: 用于“子块精确召回 + 父块回填”场景。
   4. 结构化文档优先结构感知切片，纯文本优先句子/递归切片。
   5. 先把切片做可解释，再谈语义切分和复杂动态策略。

   **实战最稳组合策略**:

   > **结构感知（有标题/版面时优先） + 递归切片（兜底） + 轻量 overlap（10%~20%）**
   > 这不是“所有场景最优”，但通常是生产里最稳的切片基线。

   **经验总结（切片视角）**:
   1. 先保证可解释性，再追求复杂语义切分；能看懂切片问题，调参才有效。
   2. `overlap` 建议先从 `10%~15%` 起步，超过 `20%` 往往噪声和成本上升更快。
   3. 结构化文档（Markdown/PDF 手册）优先结构感知；纯文本优先递归或句子切片。
   4. 这套组合适合作为默认模板，后续按文档类型做小范围差异化（FAQ/代码/合同）。

   **需要换策略的场景**:
   - FAQ/短文本：句子切片通常更好。
   - 条款/制度/合同：父子切片通常更好。
   - 代码库：代码感知切片通常更好。
   - 表格主导：先结构化抽取，再切片通常更好。

#### 2.2.2 嵌入模型 (Embedding Model)
   - **作用**: 将文本转换为高维向量表示
   - **常用模型**:
     - `DashScopeEmbedding`: 通义千问 Embedding（中文优化）
     - `OpenAIEmbedding`: OpenAI Embedding
   - **特点**:
     - 语义相似的文本在向量空间中距离更近
     - 支持跨语言检索
     - 向量维度通常 768-3072

#### 2.2.3 索引 (Index)
   - **作用**: 组织和存储 Node 的数据结构，支持高效检索（类似数据库索引）
   - **主要类型**:

   **常见索引类型详解（框架无关）**:

   | 索引类型 | 检索方式 | 适用场景 | 特点 | 示例 |
   |---------|---------|---------|------|------|
   | `SummaryIndex` | 遍历所有节点 | 文档总结、全面分析 | 保证节点有序，便于按顺序访问 | "总结所有文档的要点" |
   | `DocumentSummaryIndex` | 文档摘要检索 | 大规模文档、快速定位 | 为每个文档生成简短摘要 | "查找关于AI的文档" |
   | `VectorStoreIndex` | 向量相似度 | 语义检索、概念查询 | 将文本转换为向量，使用数学方法对相似节点分组 | "如何提高效率？" |
   | `TreeIndex` | 层级检索 | 结构化查询、目录式文档 | 采用树状结构层级化组织节点 | "技术文档的章节导航" |
   | `KeywordTableIndex` | 关键词匹配 | 精确检索、专有名词 | 建立关键词与节点之间的联系 | "查找包含'Python'的文档" |
   | `KnowledgeGraphIndex` | 图谱检索 | 复杂关系、推理查询 | 用于存储大量连接信息并作为知识图谱 | "马斯克的公司有哪些？" |
   | `ComposableGraph` | 组合索引 | 复杂场景、多维度检索 | 允许创建复杂的索引结构 | "先按时间再按主题检索" |

   **各索引类型详细说明**:

   **a) SummaryIndex (列表索引)**
   ```python
   from llama_index.core import SummaryIndex
   
   # 创建 SummaryIndex
   index = SummaryIndex.from_documents(documents)
   
   # 特点:
   # - 保证节点有序
   # - 便于按顺序访问所有节点
   # - 适合需要遍历所有内容的场景
   
   # 使用场景: 文档总结、全面分析
   query_engine = index.as_query_engine(response_mode="tree_summarize")
   response = query_engine.query("总结这些文档的核心要点")
   ```

   **b) DocumentSummaryIndex (文档摘要索引)**
   ```python
   from llama_index.core import DocumentSummaryIndex
   
   # 创建 DocumentSummaryIndex
   index = DocumentSummaryIndex.from_documents(
       documents,
       llm=llm  # 需要 LLM 生成摘要
   )
   
   # 特点:
   # - 为每个文档生成简短摘要
   # - 检索时先匹配摘要，再返回完整文档
   # - 适合大规模文档库
   
   # 使用场景: 大规模文档、快速定位
   query_engine = index.as_query_engine()
   response = query_engine.query("查找关于机器学习的文档")
   ```

   **c) VectorStoreIndex (向量索引) ⭐ 最常用**
   ```python
   from llama_index.core import VectorStoreIndex
   
   # 创建 VectorStoreIndex
   index = VectorStoreIndex.from_documents(
       documents,
       embed_model=embed_model
   )
   
   # 特点:
   # - 将文本转换为向量嵌入
   # - 使用数学方法对相似节点进行分组
   # - 支持语义相似度检索
   
   # 使用场景: 语义检索、概念查询、同义词匹配
   query_engine = index.as_query_engine(similarity_top_k=5)
   response = query_engine.query("如何提高工作效率？")
   # 可以匹配到 "优化工作流程"、"提升生产力" 等语义相关内容
   ```

   **d) TreeIndex (树索引)**
   ```python
   from llama_index.core import TreeIndex
   
   # 创建 TreeIndex
   index = TreeIndex.from_documents(documents)
   
   # 特点:
   # - 采用树状结构层级化组织节点
   # - 自顶向下搜索
   # - 支持多级摘要
   
   # 使用场景: 结构化查询、目录式文档、层级导航
   query_engine = index.as_query_engine(child_branch_factor=2)
   response = query_engine.query("技术文档的第三章讲了什么？")
   ```

   **TreeIndex 与父子切片的关系（易混点）**:
   1. `TreeIndex` 是“索引层”的组织方式，用树结构做层级检索与导航。
   2. 父子切片（Parent-Child）是“切分层”的策略，解决子块命中与父块上下文回填。
   3. 两者可以组合：先做结构感知/父子切片，再把节点组织进树索引。
   4. 目录导航、章节问答偏向 `TreeIndex`；细粒度证据命中偏向父子切片。

   **e) KeywordTableIndex (关键词表索引)**
   ```python
   from llama_index.core import KeywordTableIndex
   
   # 创建 KeywordTableIndex
   index = KeywordTableIndex.from_documents(documents)
   
   # 特点:
   # - 建立关键词与节点之间的映射关系
   # - 精确匹配关键词
   # - 适合专有名词检索
   
   # 使用场景: 精确检索、专有名词、代码片段
   query_engine = index.as_query_engine()
   response = query_engine.query("查找包含 'Python 3.9' 的内容")
   ```

   **f) KnowledgeGraphIndex (知识图谱索引)**
   ```python
   from llama_index.core import KnowledgeGraphIndex
   
   # 创建 KnowledgeGraphIndex
   index = KnowledgeGraphIndex.from_documents(
       documents,
       storage_context=storage_context,
       max_triplets_per_chunk=10
   )
   
   # 特点:
   # - 用于存储大量连接信息
   # - 作为知识图谱使用
   # - 支持关系推理
   
   # 使用场景: 复杂关系查询、多跳推理
   query_engine = index.as_query_engine()
   response = query_engine.query("马斯克的公司有哪些？这些公司的股价如何？")
   ```

   **g) ComposableGraph (可组合图)**
   ```python
   from llama_index.core import ComposableGraph
   
   # 创建多个子索引
   summary_index = SummaryIndex.from_docs(docs1)
   vector_index = VectorStoreIndex.from_docs(docs2)
   
   # 组合成复合索引
   graph = ComposableGraph.build_from_indices(
       children_indices=[summary_index, vector_index],
       index_summaries=["文档总结索引", "向量检索索引"]
   )
   
   # 特点:
   # - 允许创建复杂的索引结构
   # - 支持多维度检索
   # - 可以组合不同类型的索引
   
   # 使用场景: 复杂场景、多维度检索、混合策略
   query_engine = graph.as_query_engine()
   response = query_engine.query("综合分析所有文档")
   ```

   **索引选择指南**:

   ```python
   def select_index_type(use_case, document_structure, query_type):
       """根据使用场景选择合适的索引类型"""
   
       # 1. 语义检索 → VectorStoreIndex
       if query_type == "semantic":
           return "VectorStoreIndex"
   
       # 2. 文档总结 → SummaryIndex
       elif query_type == "summarization":
           return "SummaryIndex"
   
       # 3. 精确匹配 → KeywordTableIndex
       elif query_type == "exact_match":
           return "KeywordTableIndex"
   
       # 4. 层级结构 → TreeIndex
       elif document_structure == "hierarchical":
           return "TreeIndex"
   
       # 5. 大规模文档 → DocumentSummaryIndex
       elif use_case == "large_scale":
           return "DocumentSummaryIndex"
   
       # 6. 关系推理 → KnowledgeGraphIndex
       elif query_type == "reasoning":
           return "KnowledgeGraphIndex"
   
       # 7. 复杂场景 → ComposableGraph
       elif use_case == "complex":
           return "ComposableGraph"
   
       # 默认: VectorStoreIndex (最通用)
       else:
           return "VectorStoreIndex"
   
   # 使用示例
   index_type = select_index_type(
       use_case="semantic_search",
       document_structure="flat",
       query_type="semantic"
   )
   # 返回: "VectorStoreIndex"
   ```

   **索引性能对比**:

   | 索引类型 | 构建速度 | 查询速度 | 内存占用 | 召回率 | 精度 |
   |---------|---------|---------|---------|--------|------|
   | `SummaryIndex` | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | 100% | 高 |
   | `DocumentSummaryIndex` | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 90% | 高 |
   | `VectorStoreIndex` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 85% | 高 |
   | `TreeIndex` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 80% | 中 |
   | `KeywordTableIndex` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 70% | 高 |
   | `KnowledgeGraphIndex` | ⭐⭐ | ⭐⭐⭐ | ⭐ | 75% | 高 |
   | `ComposableGraph` | ⭐⭐ | ⭐⭐⭐ | ⭐ | 85% | 高 |

   **实战建议**:

   1. **通用场景**: 优先使用 `VectorStoreIndex`
   2. **需要总结**: 使用 `SummaryIndex` 或 `DocumentSummaryIndex`
   3. **精确匹配**: 使用 `KeywordTableIndex`
   4. **复杂关系**: 使用 `KnowledgeGraphIndex`
   5. **多维度需求**: 使用 `ComposableGraph` 组合多种索引

   **索引构建示例**:

   ```python
   # 方式 1: 从文档直接构建
   index = VectorStoreIndex.from_documents(documents)
   
   # 方式 2: 从节点构建
   index = VectorStoreIndex(nodes)
   
   # 方式 3: 增量添加
   for doc in new_docs:
       index.insert(doc)
   
   # 方式 4: 持久化
   index.storage_context.persist(persist_dir="./storage")
   
   # 方式 5: 加载已有索引
   from llama_index.core import load_index_from_storage
   index = load_index_from_storage(storage_context)
   ```


**详细流程**:

```python
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.dashscope import DashScopeEmbedding

# 1. 文档切片 (Chunking)
splitter = SentenceSplitter(
    chunk_size=512,        # 切片大小 (tokens)
    chunk_overlap=50,      # 重叠部分
    paragraph_separator="\n\n"
)

nodes = splitter.get_nodes_from_documents(documents)

print(f"原始文档数: {len(documents)}")
print(f"切片后节点数: {len(nodes)}")
# 示例输出:
# 原始文档数: 10
# 切片后节点数: 156

# 2. 向量化 (Embedding)
embed_model = DashScopeEmbedding(
    model_name="text-embedding-v3"
)

# 为每个节点生成向量
for node in nodes:
    node.embedding = embed_model.get_text_embedding(node.text)

# 3. 索引构建 (Indexing)
index = VectorStoreIndex(
    nodes,
    embed_model=embed_model,
    show_progress=True
)

# 4. 索引类型选择
index_types = {
    "VectorStoreIndex": {
        "用途": "向量检索",
        "优点": "语义理解能力强",
        "适用": "概念查询、同义词"
    },
    "SummaryIndex": {
        "用途": "列表式遍历",
        "优点": "不丢失信息",
        "适用": "文档总结、全面分析"
    },
    "KeywordTableIndex": {
        "用途": "关键词检索",
        "优点": "精确匹配",
        "适用": "专有名词、代码"
    },
    "TreeIndex": {
        "用途": "层级检索",
        "优点": "结构化查询",
        "适用": "目录式文档"
    }
}
```

### 2.3 存储阶段 (Store)

> **实现重点**: 存储阶段关注“索引持久化 + 检索性能 + 成本与可靠性”。

**目标**: 持久化索引和文档数据，支持高效的向量检索

**核心任务**:

```
索引数据 → 向量数据库 → 持久化存储
```

**核心组件**:

```
┌──────────────────────────────────────────────────┐
│          存储阶段核心组件                         │
└──────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  向量存储     │    │  文档存储     │    │  索引存储     │
│ (Vector Store)│   │ (Doc Store)  │    │ (Index Store)│
└──────────────┘    └──────────────┘    └──────────────┘
       ↓                   ↓                   ↓
   向量+元数据         原始文档            索引元数据
```

1. **存储上下文 (StorageContext)**
   - **作用**: 统一管理所有存储组件的容器
   - **组成**:
     
     ```python
     from llama_index.core import StorageContext
     
     storage_context = StorageContext.from_defaults(
         vector_store=vector_store,      # 向量存储
         docstore=docstore,              # 文档存储
         index_store=index_store         # 索引存储
     )
     ```
   
2. **向量存储 (Vector Store)**
   - **作用**: 存储节点向量和元数据，支持向量检索
   - **主流选择**:
   - **Milvus** **Elasticsearch**
   
3. **文档存储 (Document Store)**
   - **作用**: 存储原始文档和节点数据
   - **实现**:
     - `SimpleDocumentStore`: 内存存储
     - `MongoDocumentStore`: MongoDB 存储
   - **用途**: 支持文档去重、增量更新

4. **索引存储 (Index Store)**
   - **作用**: 存储索引的元数据和配置
   - **内容**:
     - 索引类型
     - 节点映射关系
     - 配置参数

**详细流程**:

```python
from llama_index.core import StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore

# 1. 向量存储配置
vector_store = MilvusVectorStore(
    uri="http://localhost:19530",
    collection_name="my_knowledge_base",
    dim=1024,  # embedding 维度
    index_params={
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
)

# 2. 存储上下文
storage_context = StorageContext.from_defaults(
    vector_store=vector_store,
    docstore=SimpleDocumentStore(),    # 文档存储
    index_store=SimpleIndexStore()      # 索引存储
)

# 3. 持久化索引
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    show_progress=True
)

# 保存到磁盘
index.storage_context.persist(persist_dir="./storage")

# 4. 加载已有索引
from llama_index.core import load_index_from_storage

storage_context = StorageContext.from_defaults(
    persist_dir="./storage"
)
index = load_index_from_storage(storage_context)

# 5. 增量更新
def update_index(new_documents):
    # 添加新文档
    for doc in new_documents:
        index.insert(doc)

    # 重新持久化
    index.storage_context.persist()
```

**存储架构**:

```
┌─────────────────────────────────────────────┐
│           RAG 存储架构                       │
└─────────────────────────────────────────────┘
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 向量存储      │  │ 文档存储      │  │ 索引存储      │
│ (Vector Store)│  │ (Doc Store)  │  │ (Index Store)│
└──────────────┘  └──────────────┘  └──────────────┘
      ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ • Milvus     │  │ • 原始文档    │  │ • 索引元数据  │
│ • Pinecone   │  │ • 节点数据    │  │ • 映射关系    │
│ • Chroma     │  │ • 元数据      │  │ • 配置信息    │
│ • ES         │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

**性能优化**:

**1. 向量索引类型详解**

| 索引类型 | 全称 | 原理 | 优点 | 缺点 | 内存占用 | 查询速度 | 适用场景 |
|---------|------|------|------|------|---------|---------|---------|
| **IVF_FLAT** | Inverted File with Flat quantization | 将向量空间划分为多个聚类中心（nlist），查询时只搜索最近的几个聚类 | • 召回率高<br>• 实现简单<br>• 精度好 | • 内存占用大<br>• 速度中等 | 高 (100%) | ⭐⭐⭐ | 中等规模、精度优先 |
| **HNSW** | Hierarchical Navigable Small World | 构建多层图结构（类似跳表），通过图的导航快速找到最近邻 | • 查询速度极快<br>• 召回率高<br>• 支持实时更新 | • 内存占用最大<br>• 构建时间长 | 最高 (150%+) | ⭐⭐⭐⭐⭐ | 大规模、实时性要求高 |
| **IVF_PQ** | Inverted File with Product Quantization | 先聚类再量化，将向量压缩为更短的编码（如8位），大幅减少内存 | • 内存占用极小<br>• 适合超大规模 | • 召回率较低<br>• 有精度损失 | 低 (10-30%) | ⭐⭐⭐⭐ | 超大规模、成本敏感 |
| **IVF_SQ8** | Inverted File with Scalar Quantization | 使用8位标量量化，将向量从32位压缩到8位 | • 内存占用小<br>• 速度快 | • 精度有损失 | 中 (25%) | ⭐⭐⭐⭐ | 平衡方案 |
| **FLAT** | Flat Index | 暴力搜索，遍历所有向量 | • 精度最高<br>• 实现简单 | • 速度最慢<br>• 内存大 | 高 (100%) | ⭐ | 小规模、高精度 |

**索引类型选择建议**:

```python
# 根据数据规模和需求选择索引类型
def select_index_type(num_vectors, latency_requirement, memory_budget):
    """
    num_vectors: 向量数量
    latency_requirement: 延迟要求 ('low', 'medium', 'high')
    memory_budget: 内存预算 ('low', 'medium', 'high')
    """

    if num_vectors < 100000:
        # 小规模，优先精度
        return "FLAT"

    elif num_vectors < 1000000:
        # 中等规模
        if latency_requirement == "high":
            return "HNSW"
        else:
            return "IVF_FLAT"

    else:
        # 大规模
        if memory_budget == "low":
            return "IVF_PQ"
        elif latency_requirement == "high":
            return "HNSW"
        else:
            return "IVF_SQ8"
```

**性能对比示例**:

```python
# 测试环境: 100万 1024维向量, 16GB 内存

# IVF_FLAT
索引大小: 4.2 GB
查询延迟: 15-30 ms (nprobe=16)
召回率: 98%
适用: 精度优先，内存充足

# HNSW
索引大小: 6.5 GB
查询延迟: 2-5 ms
召回率: 99%
适用: 速度优先，内存充足

# IVF_PQ
索引大小: 0.4 GB (压缩32倍)
查询延迟: 8-15 ms
召回率: 90-95%
适用: 成本优先，内存有限

# IVF_SQ8
索引大小: 1.1 GB (压缩4倍)
查询延迟: 10-20 ms
召回率: 95-97%
适用: 平衡方案
```

**索引构建示例**:

```python
from pymilvus import Collection, utility
from pymilvus.client.types import IndexType

# IVF_FLAT 索引
collection.create_index(
    field_name="embedding",
    index_params={
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}  # 聚类中心数量
    }
)

# HNSW 索引
collection.create_index(
    field_name="embedding",
    index_params={
        "metric_type": "COSINE",
        "index_type": "HNSW",
        "params": {
            "M": 16,        # 每个节点的连接数
            "efConstruction": 256  # 构建时的搜索范围
        }
    }
)

# IVF_PQ 索引
collection.create_index(
    field_name="embedding",
    index_params={
        "metric_type": "COSINE",
        "index_type": "IVF_PQ",
        "params": {
            "nlist": 1024,   # 聚类中心数量
            "m": 8,          # 子向量数量
            "nbits": 8       # 每个子向量的位数
        }
    }
)
```

**2. 分区策略**

```python
# 按知识库分区
partition_name = f"kb_{knowledge_base_id}"

# 按时间分区
partition_name = f"docs_{year}_{month}"

# 好处:
# 1. 减少搜索范围，提升速度
# 2. 便于数据管理和清理
# 3. 支持多租户隔离

# 示例：查询时指定分区
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param={"nprobe": 16},
    partition_names=["kb_001"]  # 只搜索知识库001
)
```

**3. 缓存机制**

```python
# 查询结果缓存
from functools import lru_cache

@lru_cache(maxsize=10000)
def cached_search(query_hash, top_k):
    return vector_store.search(query_hash, top_k)

# 向量缓存
embedding_cache = {}
def get_cached_embedding(text):
    if text not in embedding_cache:
        embedding_cache[text] = model.encode(text)
    return embedding_cache[text]

# 好处:
# - 减少重复计算
# - 降低延迟
# - 节省成本
```

**4. 备份策略**

```python
# 定期备份
import schedule
import datetime

def backup_collection():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"/backups/collection_{timestamp}"

    # 导出数据
    utility.backup_collection(collection, backup_path)

    # 清理旧备份（保留最近7天）
    clean_old_backups(days=7)

# 每天凌晨2点备份
schedule.every().day.at("02:00").do(backup_collection)
```

**5. 混合检索优化**

```python
# 向量检索 + 关键词检索
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever

# 配置
vector_retriever = index.as_retriever(
    similarity_top_k=20,
    vector_store_query_mode="hybrid"  # 混合模式
)

bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=20
)

# 融合检索
hybrid_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=15,
    mode="reciprocal_rerank"
)
```

### 2.4 查询阶段 (Query)

> **实现重点**: 查询阶段关注“召回、融合、重排、生成”的在线链路稳定性。

**目标**: 根据用户问题检索相关文档并生成准确答案

**核心任务**:

```
用户查询 → 查询预处理 → 检索 → 重排序 → 生成 → 返回答案
```

**查询预处理流水线**:

在进入检索之前，对用户查询进行预处理是提高检索质量的关键步骤：

```
┌─────────────────────────────────────────────────────┐
│        查询预处理流水线 (Query Preprocessing)        │
└─────────────────────────────────────────────────────┘

原始查询
    ↓
┌──────────────┐
│ 1. 查询清洗   │  ← 必做
│  (Cleaning)  │
└──────────────┘
    ↓
┌──────────────┐
│ 2. 查询扩展   │  ← 可选
│ (Expansion)  │
└──────────────┘
    ↓
┌──────────────┐
│ 3. 查询改写   │  ← 可选
│  (Rewriting) │
└──────────────┘
    ↓
处理后查询 → 检索器
```

**1) 查询清洗 (必做)**

**目标**: 把"脏输入"变成可检索输入

**常见操作**:
```python
import re

def clean_query(query):
    """查询清洗示例"""

    # 1. 去噪：去除多余空格和特殊符号
    query = " ".join(query.split())
    query = re.sub(r'[^\w\s\u4e00-\u9fff?.]', ' ', query)

    # 2. 拼写纠错
    query = correct_spelling(query)

    # 3. 大小写归一
    query = query.lower()

    # 4. 时间/数字标准化
    query = normalize_numbers(query)  # "3天前" → "三天前"
    query = normalize_dates(query)    # "2024.1.1" → "2024年1月1日"

    # 5. 敏感词与无效词处理
    query = remove_sensitive_words(query)

    return query

# 示例
raw_query = "  怎么  请假？？？  "
cleaned = clean_query(raw_query)  # "怎么请假"
```

**价值**:
- 提高召回稳定性
- 减少误检
- 统一查询格式

**2) 查询扩展 (可选)**

**目标**: 增加查询的覆盖面，提高召回率

**常见操作**:
```python
from llama_index.core.indices.query.query_transform import QueryExpansion

def expand_query(query):
    """查询扩展示例"""

    # 方法1: 同义词扩展
    synonyms = {
        "请假": ["休假", "放假", "假期"],
        "工资": ["薪资", "薪酬", "待遇"]
    }
    expanded = add_synonyms(query, synonyms)

    # 方法2: 上下位词扩展
    # "水果" → ["苹果", "香蕉", "橙子"]

    # 方法3: 多语言扩展（中英文）
    # "人工智能" → ["AI", "Artificial Intelligence"]

    # 方法4: 相关词扩展
    # "Python" → ["Python", "编程", "开发", "代码"]

    return expanded

# 示例
query = "怎么请假？"
expanded = expand_query(query)
# ["怎么请假", "如何休假", "怎么放假"]
```

**使用场景**:
- 检索召回率不足时
- 专业术语多的领域
- 多语言混合场景

**风险**:
- 扩太多会引入噪声
- 精度可能下降
- 需要A/B测试验证效果

**3) 查询改写 (可选)**

**目标**: 把用户自然语言改成"更适合检索"的表达

**常见操作**:
```python
from llama_index.core.indices.query.query_transform import HyDEQueryTransform

def rewrite_query(query):
    """查询改写示例"""

    # 方法1: 口语转书面
    # "咋整" → "如何处理"
    # "啥时候" → "什么时间"

    # 方法2: 补全省略条件
    # "怎么请假" → "员工请假流程和条件是什么"

    # 方法3: 拆分复杂问题为子查询
    complex_query = "对比一下阿里和腾讯的财务情况和发展前景"
    sub_queries = [
        "阿里巴巴最新财务数据",
        "腾讯最新财务数据",
        "阿里巴巴发展战略和前景",
        "腾讯发展战略和前景"
    ]

    # 方法4: 多跳问题改写
    # "马斯克的公司股价" →
    # ["马斯克是谁", "马斯克的公司有哪些", "这些公司的股价"]

    return rewritten_query

# HyDE 改写（最常用）
hyde = HyDEQueryTransform(include_original=True)
# 原查询: "如何提高检索质量？"
# HyDE生成: "提高检索质量的方法包括优化切片策略、
#          使用混合检索、添加重排序、调整相似度阈值等..."
```

**价值**:
- 对复杂问题效果明显
- 提高检索命中率
- 支持多跳推理

**使用场景**:
- 用户查询表达不清晰
- 需要多步推理的问题
- 口语化输入较多

**推荐处理顺序**:

```
1. 查询清洗 (必做)
   ↓
2. 查询扩展 (可选，召回不足时启用)
   ↓
3. 查询改写 (可选，复杂问题场景启用)
   ↓
4. 检索
```

**实战建议**:
```python
def query_preprocessing_pipeline(query, config):
    """查询预处理流水线"""

    # 1. 清洗（必做）
    cleaned_query = clean_query(query)

    # 2. 扩展（可选）
    if config.get("enable_expansion"):
        expanded_queries = expand_query(cleaned_query)
    else:
        expanded_queries = [cleaned_query]

    # 3. 改写（可选）
    if config.get("enable_rewrite"):
        rewritten_queries = [rewrite_query(q) for q in expanded_queries]
    else:
        rewritten_queries = expanded_queries

    return rewritten_queries

# 实战配置示例
config = {
    "enable_expansion": False,  # 初期关闭，通过A/B测试验证后开启
    "enable_rewrite": True      # 复杂问题场景建议开启
}

queries = query_preprocessing_pipeline(user_query, config)
```

**A/B 测试建议**:

| 配置 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 仅清洗 | 简单问答、高精度需求 | 精度高、速度快 | 召回可能不足 |
| 清洗+改写 | 复杂问题、口语化输入 | 召回好、理解强 | 成本高、可能过度 |
| 清洗+扩展 | 专业术语、多语言 | 覆盖广 | 可能引入噪声 |
| 全部开启 | 极端复杂场景 | 效果最好 | 成本最高 |

**建议**:
1. 先从"仅清洗"开始
2. 通过评估发现召回不足时，逐步开启扩展和改写
3. 每次新增处理步骤都要做 A/B 评估
4. 监控指标：context_recall, answer_relevancy

**核心组件**:

```
┌────────────────────────────────────────────────────────┐
│              查询阶段核心组件                           │
└────────────────────────────────────────────────────────┘

用户查询
    ↓
┌──────────────┐
│  查询路由器   │  ← 决定使用哪个检索器
│  (Router)    │
└──────────────┘
    ↓
┌──────────────┐
│  检索器       │  ← 从索引中检索相关节点
│ (Retriever)  │
└──────────────┘
    ↓
┌──────────────┐
│ 节点后处理器  │  ← 过滤、重排序、增强节点
│ (Postprocessor)│
└──────────────┘
    ↓
┌──────────────┐
│ 响应合成器   │  ← 将节点合成为最终答案
│ (Response    │
│  Synthesizer)│
└──────────────┘
    ↓
最终答案
```

1. **检索器 (Retriever)**
   - **作用**: 从索引中检索相关节点
   - **主要类型**:

   | 检索器类型 | 说明 | 使用场景 |
   |-----------|------|---------|
   | `VectorIndexRetriever` | 向量检索 | 语义相似度检索 |
   | `KeywordTableRetriever` | 关键词检索 | 精确匹配 |
   | `BM25Retriever` | BM25 算法 | 传统信息检索 |
   | `QueryFusionRetriever` | 混合检索 | 结合多种检索方式 |

   - **配置示例**:
     ```python
     # 基础检索器
     retriever = index.as_retriever(
         similarity_top_k=10,
         vector_store_query_mode="default"
     )
     
     # 混合检索器
     from llama_index.core.retrievers import QueryFusionRetriever
     
     fusion_retriever = QueryFusionRetriever(
         retrievers=[vector_retriever, keyword_retriever],
         similarity_top_k=10,
         mode="reciprocal_rerank"
     )
     ```

   - **Top K 设置与相似性打分**:

     **基本概念**:
     - **Top K**: 从向量数据库中检索的最相似文档数量
     - **相似性打分 (Similarity Score)**: 衡量查询与文档之间相似程度的数值
     - **常用相似度度量**:
       - 余弦相似度 (Cosine Similarity): [-1, 1]，1表示完全相同
       - 欧几里得距离 (L2 Distance): [0, +∞)，0表示完全相同
       - 点积 (Dot Product): (-∞, +∞)，值越大越相似

     **Top K 的核心矛盾**:
     ```
     ┌─────────────────────────────────────────────────┐
     │          Top K 设置的核心矛盾                    │
     └─────────────────────────────────────────────────┘
     
     K 太小 (例如 K=2)
         ↓
     优点: 精度高、噪声少、速度快
         ↓
     缺点: 召回不足、可能错过重要信息
         ↓
     示例: 查询"Python异常处理"
           → 只返回2个文档，可能漏掉try-except的详细用法
     
     K 太大 (例如 K=50)
         ↓
     优点: 召回全面、信息完整
         ↓
     缺点: 噪声多、精度下降、成本高、可能超出上下文窗口
         ↓
     示例: 查询"Python异常处理"
           → 返回50个文档，包含大量无关内容，模型难以聚焦
     ```

     **常见取值与适用场景**:

     | Top K 值 | 适用场景 | 优点 | 缺点 | 推荐配置 |
     |---------|---------|------|------|---------|
     | **2-3** | 生产环境、简单问答 | 速度快、成本低、精度高 | 召回可能不足 | 适合明确的单跳问题 |
     | **5-10** | 通用RAG系统 | 平衡精度与召回 | - | 最常用的默认值 |
     | **10-20** | 复杂查询、多跳推理 | 召回全面 | 噪声增加 | 需要配合重排序 |
     | **20-50** | 研究场景、评估阶段 | 召回最大化 | 噪声多、成本高 | 仅用于测试和调优 |

     **动态 Top K 策略**:

     ```python
     def dynamic_top_k(query, retriever, config):
         """根据查询复杂度动态调整 Top K"""
     
         # 1. 简单查询 → 小 K
         if is_simple_query(query):
             # 特征: 单跳、明确、关键词清晰
             return config.get("simple_k", 3)
     
         # 2. 中等复杂度 → 中等 K
         elif is_medium_query(query):
             # 特征: 可能需要多个文档、有条件判断
             return config.get("medium_k", 8)
     
         # 3. 复杂查询 → 大 K
         else:
             # 特征: 多跳推理、对比分析、需要上下文
             return config.get("complex_k", 15)
     
     def is_simple_query(query):
         """判断是否为简单查询"""
         # 特征1: 查询长度短
         if len(query.split()) < 5:
             return True
     
         # 特征2: 包含明确关键词
         explicit_patterns = ["是什么", "定义", "列表", "有多少"]
         if any(pattern in query for pattern in explicit_patterns):
             return True
     
         # 特征3: 单实体查询
         if count_entities(query) == 1:
             return True
     
         return False
     
     def is_medium_query(query):
         """判断是否为中等复杂度查询"""
         # 特征1: 包含条件词
         conditional_words = ["如何", "为什么", "区别", "比较"]
         if any(word in query for word in conditional_words):
             return True
     
         # 特征2: 多实体查询
         if 2 <= count_entities(query) <= 3:
             return True
     
         return False
     ```

     **相似度阈值设置**:

     ```python
     from llama_index.core.postprocessor import SimilarityPostprocessor
     
     # 方案1: 硬阈值过滤
     postprocessor = SimilarityPostprocessor(
         similarity_cutoff=0.7  # 只保留相似度 > 0.7 的结果
     )
     
     # 方案2: 动态阈值
     class DynamicSimilarityPostprocessor:
         def __init__(self, min_threshold=0.5, max_threshold=0.8):
             self.min_threshold = min_threshold
             self.max_threshold = max_threshold
     
         def postprocess_nodes(self, nodes):
             if not nodes:
                 return nodes
     
             # 根据最高分动态调整阈值
             max_score = max(node.score for node in nodes)
             dynamic_threshold = max(
                 self.min_threshold,
                 max_score - 0.2  # 保留分数差距在0.2以内的
             )
     
             return [n for n in nodes if n.score >= dynamic_threshold]
     
     # 方案3: 混合策略 (Top K + 阈值)
     retriever = index.as_retriever(
         similarity_top_k=20  # 先取20个
     )
     
     postprocessor = SimilarityPostprocessor(
         similarity_cutoff=0.65  # 再过滤到相似度 > 0.65 的
     )
     
     query_engine = index.as_query_engine(
         retriever=retriever,
         node_postprocessors=[postprocessor]
     )
     # 最终返回: 可能是 5-15 个文档 (取决于实际相似度分布)
     ```

     **推荐配置策略**:

     **1. 保守策略 (高精度优先)**
     ```python
     # 适用场景: 客服机器人、FAQ系统
     config = {
         "top_k": 3,
         "similarity_cutoff": 0.75,
         "enable_rerank": False  # K很小，不需要重排序
     }
     ```

     **2. 均衡策略 (推荐默认)**
     ```python
     # 适用场景: 通用知识库、企业文档检索
     config = {
         "top_k": 10,
         "similarity_cutoff": 0.65,
         "enable_rerank": True,  # 建议开启重排序
         "rerank_top_n": 5       # 重排序后保留5个
     }
     ```

     **3. 激进策略 (高召回优先)**
     ```python
     # 适用场景: 研究分析、复杂推理、多跳问题
     config = {
         "top_k": 20,
         "similarity_cutoff": 0.55,
         "enable_rerank": True,
         "rerank_top_n": 8,
         "enable_expansion": True  # 启用查询扩展
     }
     ```

     **4. 自适应策略 (推荐生产环境)**
     ```python
     def adaptive_retrieval(query, index):
         """自适应检索策略"""
     
         # Step 1: 分析查询复杂度
         complexity = analyze_query_complexity(query)
     
         # Step 2: 根据复杂度选择配置
         if complexity == "simple":
             top_k = 3
             cutoff = 0.75
         elif complexity == "medium":
             top_k = 8
             cutoff = 0.68
         else:  # complex
             top_k = 15
             cutoff = 0.60
     
         # Step 3: 执行检索
         retriever = index.as_retriever(similarity_top_k=top_k)
         nodes = retriever.retrieve(query)
     
         # Step 4: 动态过滤
         filtered_nodes = [
             n for n in nodes
             if n.score >= cutoff
         ]
     
         # Step 5: 如果结果太少，降低阈值重新检索
         if len(filtered_nodes) < 2:
             filtered_nodes = [
                 n for n in nodes
                 if n.score >= cutoff - 0.1
             ]
     
         return filtered_nodes
     ```

     **如何确定最优 Top K**:

     ```python
     # 方法1: 网格搜索 + 离线评测（框架无关伪代码）
     def find_optimal_top_k(eval_dataset, k_candidates=[3, 5, 10, 15, 20]):
         """通过统一评测集找到最优 Top K"""
      
         results = {}
         for k in k_candidates:
             retriever = build_retriever(top_k=k)
      
             # evaluate_retrieval 可由任意评测框架实现
             scores = evaluate_retrieval(
                 retriever=retriever,
                 dataset=eval_dataset,
                 metrics=["context_recall", "context_precision"]
             )
      
             recall = scores["context_recall"]
             precision = scores["context_precision"]
             f1 = 2 * (recall * precision) / max(recall + precision, 1e-9)
      
             results[k] = {"recall": recall, "precision": precision, "f1": f1}
      
         best_k = max(results.items(), key=lambda x: x[1]["f1"])[0]
         return best_k, results
      
     # 方法2: A/B测试
     def ab_test_top_k(queries, k_a=5, k_b=10):
         """A/B测试不同 Top K 的线上效果"""
         import random
      
         results = {"A": [], "B": []}
         for query in queries:
             group = random.choice(["A", "B"])
             k = k_a if group == "A" else k_b
             response = online_query(query, top_k=k)
             feedback = collect_user_feedback(response)
             results[group].append(feedback)
      
         return analyze_ab_results(results)
     ```

     **最佳实践总结**:

     1. **从默认值开始**: 先用 Top K=10 + 相似度阈值 0.65
     2. **监控指标**: 持续跟踪 context_recall 和 context_precision
     3. **动态调整**: 根据查询复杂度自适应调整 K 值
     4. **配合重排序**: K > 10 时务必使用重排序器
     5. **设置下限**: 确保至少返回 2-3 个结果
     6. **定期评估**: 每月用统一评测集（自动指标+人工抽检）重新评估最优 K 值

     **实战建议**:

     ```python
     # 生产环境推荐配置
     class ProductionRetriever:
         def __init__(self, index):
             self.index = index
             self.default_k = 10
             self.min_k = 2
             self.max_k = 20
             self.default_cutoff = 0.65
     
         def retrieve(self, query):
             # 1. 分析查询复杂度
             complexity = self.analyze_complexity(query)
     
             # 2. 确定初始 K
             k = self.determine_k(complexity)
     
             # 3. 检索
             retriever = self.index.as_retriever(similarity_top_k=k)
             nodes = retriever.retrieve(query)
     
             # 4. 动态过滤
             filtered = [n for n in nodes if n.score >= self.default_cutoff]
     
             # 5. 结果太少时降级
             if len(filtered) < self.min_k:
                 filtered = nodes[:self.min_k]  # 至少返回 min_k 个
     
             return filtered
     
         def analyze_complexity(self, query):
             # 实现复杂度分析逻辑
             pass
     
         def determine_k(self, complexity):
             k_map = {
                 "simple": 3,
                 "medium": 10,
                 "complex": 15
             }
             return k_map.get(complexity, self.default_k)
     ```

2. **查询路由器 (Query Router)**
   - **作用**: 根据查询内容选择合适的检索器或索引
   - **类型**:
     - `RouterQueryEngine`: 路由查询引擎
     - `ToolRetrieverRouter`: 工具检索路由
   - **决策依据**:
     - 查询意图识别
     - 关键词匹配
     - 语义分类
   - **示例**:
     ```python
     from llama_index.core.query_engine import RouterQueryEngine
     from llama_index.core.selectors import LLMSingleSelector
     
     # 创建路由查询引擎
     query_engine = RouterQueryEngine(
         selector=LLMSingleSelector.from_defaults(),
         query_engine_tools=[
             Tool(
                 query_engine=summary_engine,
                 metadata=ToolMetadata(
                     name="summary",
                     description="适用于总结类问题"
                 )
             ),
             Tool(
                 query_engine=vector_engine,
                 metadata=ToolMetadata(
                     name="vector",
                     description="适用于事实查询"
                 )
             )
         ]
     )
     ```

3. **节点后处理器 (Node Postprocessor)**
   - **作用**: 对检索到的节点进行过滤、重排序、增强
   - **常用类型**:

   | 后处理器 | 功能 | 使用场景 |
   |---------|------|---------|
   | `SimilarityPostprocessor` | 相似度过滤 | 去除低相关结果 |
   | `CohereRerank` | 重排序 | 提升检索质量 |
   | `LongContextReorder` | 长上下文重排序 | 优化上下文窗口 |
   | `MetadataReplacementPostProcessor` | 元数据替换 | 窗口检索 |
   | `SentenceEmbeddingOptimizer` | 句子优化 | 提升相关性 |

   - **后处理器分类**:

     **1) 过滤类 (Filtering)** - 直接移除不符合条件的节点

     ```python
     # 相似度过滤
     from llama_index.core.postprocessor import SimilarityPostprocessor

     similarity_filter = SimilarityPostprocessor(
         similarity_cutoff=0.7  # 移除相似度 < 0.7 的节点
     )

     # 关键词过滤
     from llama_index.core.postprocessor import KeywordNodePostprocessor

     keyword_filter = KeywordNodePostprocessor(
         required_keywords=["Python"],      # 必须包含的关键词
         exclude_keywords=["deprecated"]    # 排除的关键词
     )

     # 元数据过滤
     from llama_index.core.postprocessor import FixedRecencyPostprocessor

     recency_filter = FixedRecencyPostprocessor(
         top_k=5,  # 只保留最新的5个节点
         date_key="date"  # 根据元数据中的date字段排序
     )

     # 使用场景：
     # - 质量控制：移除低相关性结果
     # - 时效性：只保留最新文档
     # - 权限控制：过滤无权限访问的文档
     ```

     **2) 转换类 (Transformation)** - 修改检索到的节点内容而非移除

     ```python
     # 元数据替换 - 句子窗口检索的核心
     from llama_index.core.postprocessor import MetadataReplacementPostProcessor

     # 场景：检索时用小切片，生成时用完整窗口
     window_postprocessor = MetadataReplacementPostProcessor(
         target_metadata_key="window"  # 用window字段的值替换节点文本
     )

     """
     工作原理：

     索引阶段：
     ┌────────────────────────────────────────┐
     │ 原始文档: "Python是高级编程语言..."    │
     └────────────────────────────────────────┘
              ↓ 句子窗口切片
     ┌────────────────────────────────────────┐
     │ Node 1:                                │
     │ - text: "Python是高级编程语言"         │  ← 小切片用于检索
     │ - metadata:                            │
     │   window: "Python是高级编程语言。它    │  ← 大窗口用于生成
     │          简洁易读，支持多种编程范式。" │
     └────────────────────────────────────────┘

     检索阶段：
     查询: "Python是什么？"
              ↓ 向量检索（用小切片匹配）
     匹配到 Node 1 (相似度: 0.92)

     后处理阶段：
     ┌────────────────────────────────────────┐
     │ MetadataReplacementPostProcessor       │
     │ - 读取 node.metadata["window"]         │
     │ - 替换 node.text = window内容          │
     └────────────────────────────────────────┘
              ↓
     ┌────────────────────────────────────────┐
     │ 发送给LLM的完整上下文：                │
     │ "Python是高级编程语言。它简洁易读，    │
     │  支持多种编程范式。"                   │
     └────────────────────────────────────────┘
     """

     # 实战示例：结合句子窗口检索
     from llama_index.core.node_parser import SentenceWindowNodeParser

     # 1. 创建窗口切片器
     node_parser = SentenceWindowNodeParser.from_defaults(
         window_size=3,           # 前后各3个句子作为窗口
         window_metadata_key="window",
         original_text_metadata_key="original_text"
     )

     # 2. 构建索引（用小切片）
     nodes = node_parser.get_nodes_from_documents(documents)
     index = VectorStoreIndex(nodes)

     # 3. 查询时替换为窗口
     query_engine = index.as_query_engine(
         similarity_top_k=5,
         node_postprocessors=[window_postprocessor]
     )

     # 好处：
     # - 检索精准：小切片语义清晰，向量更准确
     # - 生成完整：大窗口提供充分上下文，回答更全面
     # - 平衡精度与完整性
     ```

     **3) 重排类 (Reranking)** - 解决top_k取值问题，先多取结果再按规则重新排序

     ```python
     # 为什么需要重排序？
     """
     问题：向量检索的局限性

     查询: "Python异常处理最佳实践"
     Top 5 向量检索结果：
     1. Python异常处理语法 (0.89)  ✓ 相关
     2. Java异常处理最佳实践 (0.85) ✗ 错误语言
     3. Python文件操作 (0.82)      ✗ 不相关
     4. Python异常类型 (0.81)      ✓ 相关
     5. Python基础教程 (0.78)      ✗ 太泛

     问题：向量检索只看语义相似度，可能引入：
     - 跨语言混淆（Python vs Java）
     - 主题漂移（异常处理 vs 文件操作）
     - 层级混乱（具体语法 vs 基础教程）
     """

     # 解决方案1：LLM重排序（最准确）
     from llama_index.postprocessor.cohere_rerank import CohereRerank

     llm_rerank = CohereRerank(
         api_key="your-cohere-api-key",
         top_n=5  # 从检索结果中重排后保留5个
     )

     # 工作原理：
     # 1. 检索 top_k=20 个候选
     # 2. Cohere Rerank API 分析每个候选与查询的相关性
     # 3. 返回相关性最高的 top_n=5 个

     # 解决方案2：交叉编码器重排序（高精度）
     from llama_index.postprocessor.sentence_transformer_rerank import (
         SentenceTransformerRerank
     )

     cross_encoder = SentenceTransformerRerank(
         model="cross-encoder/ms-marco-MiniLM-L-6-v2",
         top_n=5
     )

     # 解决方案3：长上下文优化重排序（解决"中间迷失"问题）
     from llama_index.core.postprocessor import LongContextReorder

     long_context_reorder = LongContextReorder()

     """
     长上下文重排序原理：

     问题：模型对长上下文的开头和结尾关注度高，中间容易被忽略

     检索结果（按相似度排序）：
     [Doc1(0.95), Doc2(0.92), Doc3(0.88), Doc4(0.85), Doc5(0.80)]
              ↓ LongContextReorder
     重排后（交替放置）：
     [Doc1(0.95), Doc5(0.80), Doc2(0.92), Doc4(0.85), Doc3(0.88)]
      ↑ 最相关      ↑ 次低相关  ↑ 次相关     ↑ 最低相关   ↑ 中等相关

     策略：把重要文档放在开头和结尾，确保被关注
     """

     # 解决方案4：元数据感知重排序
     from llama_index.core.postprocessor import (
         PrevNextNodePostprocessor
     )

     # 上下文扩展（检索相邻节点）
     context_expansion = PrevNextNodePostprocessor(
         docstore=index.docstore,
         num_nodes=2,  # 前后各取2个节点
         mode="previous"  # 或 "next", "both"
     )

     # 完整重排序流水线
     rerank_pipeline = [
         # 1. 先取较多候选
         # similarity_top_k=20

         # 2. 过滤低质量结果
         SimilarityPostprocessor(similarity_cutoff=0.65),

         # 3. LLM精准重排
         llm_rerank,  # top_n=8

         # 4. 优化长上下文位置
         long_context_reorder,

         # 5. 扩展上下文（可选）
         context_expansion
     ]

     query_engine = index.as_query_engine(
         similarity_top_k=20,
         node_postprocessors=rerank_pipeline
     )

     # 效果对比
     """
     无重排序：
     - Top 5 准确率: 60%
     - 用户满意度: 3.2/5

     有重排序：
     - Top 5 准确率: 85%
     - 用户满意度: 4.5/5
     """
     ```

     **后处理器组合策略**:

     ```python
     # 策略1：轻量级（速度快）
     lightweight_postprocessors = [
         SimilarityPostprocessor(similarity_cutoff=0.7),
         LongContextReorder()
     ]
     # 适用：实时聊天、简单问答

     # 策略2：均衡型（推荐）
     balanced_postprocessors = [
         SimilarityPostprocessor(similarity_cutoff=0.65),
         MetadataReplacementPostProcessor(target_metadata_key="window"),
         CohereRerank(top_n=5),
         LongContextReorder()
     ]
     # 适用：企业知识库、技术文档检索

     # 策略3：高精度（质量优先）
     high_quality_postprocessors = [
         SimilarityPostprocessor(similarity_cutoff=0.6),
         CohereRerank(top_n=10),
         PrevNextNodePostprocessor(docstore=docstore, num_nodes=1),
         LongContextReorder()
     ]
     # 适用：专业领域、复杂推理

     # 选择建议：
     """
     ┌─────────────────────────────────────────────┐
     │        后处理器选择决策树                   │
     └─────────────────────────────────────────────┘

     是否需要高精度？
         ├─ 否 → 轻量级策略
         └─ 是
             ↓
     是否有时效性要求？
         ├─ 是 → 添加 FixedRecencyPostprocessor
         └─ 否
             ↓
     是否使用句子窗口切片？
         ├─ 是 → 添加 MetadataReplacementPostProcessor
         └─ 否
             ↓
     是否有重排序API？
         ├─ 是 → 添加 CohereRerank
         └─ 否 → 使用 LongContextReorder 替代
             ↓
     检索结果 > 5个？
         └─ 是 → 添加 LongContextReorder
     """
     ```

   - **使用示例**:
     ```python
     from llama_index.core.postprocessor import (
         SimilarityPostprocessor,
         LongContextReorder
     )
     from llama_index.postprocessor.cohere_rerank import CohereRerank
     
     # 组合多个后处理器
     postprocessors = [
         SimilarityPostprocessor(similarity_cutoff=0.7),
         CohereRerank(top_n=5),
         LongContextReorder()
     ]
     
     # 集成到查询引擎
     query_engine = index.as_query_engine(
         similarity_top_k=20,
         node_postprocessors=postprocessors
     )
     ```

4. **响应合成器 (Response Synthesizer)**
   - **作用**: 将检索到的节点合成为最终答案
   - **响应模式**:

   | 模式 | 说明 | 适用场景 | 特点 |
   |------|------|---------|------|
   | `compact` | 紧凑模式 | 通用问答 | 合并所有节点后生成 |
   | `refine` | 迭代优化 | 需要深度分析 | 逐步完善答案 |
   | `tree_summarize` | 层级总结 | 长文档总结 | 分层总结后合并 |
   | `simple_summarize` | 简单总结 | 快速概览 | 简单拼接后总结 |
   | `no_text` | 只检索不生成 | 测试检索 | 仅返回节点 |

   - **配置示例**:
     ```python
     from llama_index.core.response_synthesizers import (
         get_response_synthesizer
     )
     
     # 创建响应合成器
     response_synthesizer = get_response_synthesizer(
         response_mode="compact",
         use_async=True
     )
     
     # 集成到查询引擎
     query_engine = index.as_query_engine(
         response_synthesizer=response_synthesizer
     )
     ```

5. **查询引擎 (Query Engine)**
   - **作用**: 整合上述所有组件的统一接口
   - **主要类型**:
     - `RetrieverQueryEngine`: 标准查询引擎
     - `RouterQueryEngine`: 路由查询引擎
     - `TransformQueryEngine`: 查询转换引擎
     - `MultiStepQueryEngine`: 多步查询引擎
   - **完整示例**:
     ```python
     # 标准查询引擎
     query_engine = RetrieverQueryEngine(
         retriever=retriever,
         response_synthesizer=response_synthesizer,
         node_postprocessors=postprocessors
     )
     
     # 查询转换引擎 (HyDE)
     from llama_index.core.query_engine import TransformQueryEngine
     from llama_index.core.indices.query.query_transform import HyDEQueryTransform
     
     hyde_transform = HyDEQueryTransform(include_original=True)
     hyde_engine = TransformQueryEngine(
         query_engine=query_engine,
         query_transform=hyde_transform
     )
     ```

**详细流程**:

```python
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine

# 1. 查询预处理
def preprocess_query(query):
    # 查询清洗
    query = query.strip()

    # 查询扩展（可选）
    expanded_queries = expand_query(query)

    # 查询改写（可选）
    rewritten_query = rewrite_query(query)

    return rewritten_query

# 2. 检索阶段
retriever = index.as_retriever(
    similarity_top_k=10,              # 检索 top 10
    vector_store_query_mode="default" # 检索模式
)

# 执行检索
query = "什么是 RAG？"
retrieved_nodes = retriever.retrieve(query)

print(f"检索到 {len(retrieved_nodes)} 个相关片段")
for i, node in enumerate(retrieved_nodes[:3], 1):
    print(f"\n{i}. 相似度: {node.score:.3f}")
    print(f"   内容: {node.text[:100]}...")

# 3. 后处理阶段
postprocessor = SimilarityPostprocessor(
    similarity_cutoff=0.7  # 相似度阈值
)

filtered_nodes = postprocessor.postprocess_nodes(retrieved_nodes)
print(f"\n过滤后剩余 {len(filtered_nodes)} 个片段")

# 4. 生成阶段
query_engine = index.as_query_engine(
    similarity_top_k=5,
    node_postprocessors=[postprocessor],
    response_mode="compact"  # 响应模式
)

response = query_engine.query(query)

# 5. 结果处理
def process_response(response):
    # 提取答案
    answer = response.response

    # 提取来源
    sources = []
    for node in response.source_nodes:
        sources.append({
            "text": node.text[:200],
            "score": node.score,
            "metadata": node.metadata
        })

    # 格式化输出
    result = {
        "answer": answer,
        "sources": sources,
        "confidence": calculate_confidence(sources)
    }

    return result

# 使用
result = process_response(response)
print(f"\n答案: {result['answer']}")
print(f"\n引用来源:")
for i, source in enumerate(result['sources'], 1):
    print(f"{i}. {source['metadata']['source']} (相似度: {source['score']:.3f})")
```

**查询优化策略**:

```python
# 1. 混合检索
from llama_index.core.retrievers import QueryFusionRetriever

vector_retriever = index.as_retriever(similarity_top_k=10)
keyword_retriever = KeywordTableRetriever(...)

hybrid_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, keyword_retriever],
    similarity_top_k=10,
    mode="reciprocal_rerank"
)

# 2. 查询改写 (HyDE)
from llama_index.core.indices.query.query_transform import HyDEQueryTransform

hyde = HyDEQueryTransform(include_original=True)
hyde_engine = TransformQueryEngine(
    query_engine=index.as_query_engine(),
    query_transform=hyde
)

# 3. 重排序
from llama_index.postprocessor.cohere_rerank import CohereRerank

reranker = CohereRerank(top_n=5)
query_engine = index.as_query_engine(
    similarity_top_k=20,
    node_postprocessors=[reranker]
)

# 4. 多轮对话
from llama_index.core.memory import ChatMemoryBuffer

memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
chat_engine = index.as_chat_engine(
    chat_mode="context",
    memory=memory,
    verbose=True
)
```

**响应模式**:

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `compact` | 紧凑模式，合并所有片段 | 通用问答 |
| `refine` | 迭代优化，逐步完善答案 | 需要深度分析 |
| `tree_summarize` | 层级总结 | 长文档总结 |
| `simple_summarize` | 简单总结 | 快速概览 |
| `no_text` | 只检索不生成 | 测试检索效果 |

### 2.5 评估阶段 (Evaluate)

> **实现重点**: 评估阶段关注“指标闭环 + 用例回归 + 线上验证”。

**目标**: 量化评估 RAG 系统的检索和生成质量，指导优化方向

**核心任务**:
```
准备评测集 → 执行评估 → 分析结果 → 优化迭代
```

**核心组件**:

```
┌──────────────────────────────────────────────────┐
│          评估阶段核心组件                         │
└──────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  评测数据集   │───→│  评估指标     │───→│  评估报告     │
│ (Dataset)    │    │ (Metrics)    │    │ (Report)     │
└──────────────┘    └──────────────┘    └──────────────┘
       ↓                   ↓                   ↓
   标准化数据         量化指标            分析建议
```

1. **评测数据集 (Dataset)**
   - **作用**: 提供标准化的评测样本
   - **必需字段**:

   | 字段 | 类型 | 说明 | 必需性 |
   |------|------|------|--------|
   | `question` | str | 用户问题 | ✅ 必需 |
   | `answer` | str | 系统生成的答案 | ✅ 必需 |
   | `contexts` | List[str] | 检索到的上下文 | ✅ 必需 |
   | `ground_truth` | str | 标准答案 | ⚠️ 推荐 |

   - **数据集构建**:
     ```python
     from datasets import Dataset
     
     # 评测数据集示例
     eval_dataset = Dataset.from_dict({
         "question": ["什么是 RAG?", "如何优化检索?"],
         "answer": ["RAG 是...", "可以通过..."],
         "contexts": [["相关文档1"], ["相关文档2"]],
         "ground_truth": ["RAG 是检索增强生成...", "优化方法包括..."]
     })
     ```

2. **评估指标 (Metrics)**
   - **作用**: 量化评估 RAG 系统的性能
   - **主要指标分类**:

   **检索阶段指标**:

   | 指标 | 说明 | 公式 | 目标值 |
   |------|------|------|--------|
   | `context_precision` | 检索精准率 | 相关文档占比 | > 0.7 |
   | `context_recall` | 检索召回率 | 相关内容覆盖度 | > 0.8 |

   **生成阶段指标**:

   | 指标 | 说明 | 评估维度 | 目标值 |
   |------|------|---------|--------|
   | `faithfulness` | 忠实度 | 答案是否基于上下文 | > 0.85 |
   | `answer_correctness` | 正确性 | 事实准确性 | > 0.75 |
   | `answer_relevancy` | 相关性 | 是否切题 | > 0.8 |
   | `semantic_similarity` | 语义相似度 | 与标准答案的相似度 | > 0.75 |

   - **指标使用**:
     ```python
     from ragas.metrics import (
         context_precision,
         context_recall,
         faithfulness,
         answer_correctness,
         answer_relevancy
     )
     
     # 选择评估指标
     metrics = [
         context_precision,
         context_recall,
         faithfulness,
         answer_correctness,
         answer_relevancy
     ]
     ```

3. **评估执行器 (Evaluator)**
   - **作用**: 执行评估并生成结果
   - **核心函数**: `evaluate()`
   - **参数配置**:
     ```python
     from ragas import evaluate
     
     result = evaluate(
         dataset=eval_dataset,          # 评测数据集
         metrics=metrics,               # 评估指标
         llm=llm,                       # LLM 模型
         embeddings=embeddings,         # Embedding 模型
         raise_exceptions=False,        # 遇错是否中断
         column_map=None                # 字段映射
     )
     ```

4. **评估报告 (Report)**
   - **作用**: 分析评估结果并提供优化建议
   - **内容**:
     - 整体分数统计（均值、中位数、标准差）
     - 各指标详细分数
     - 低分样本识别
     - 优化建议生成
   - **报告生成**:
     ```python
     # 转换为 DataFrame
     df = result.to_pandas()
     
     # 统计分析
     print("=== 评估结果概览 ===")
     print(df.mean(numeric_only=True))
     
     # 识别低分样本
     low_score_samples = df[
         (df['faithfulness'] < 0.7) |
         (df['answer_relevancy'] < 0.7)
     ]
     
     # 生成优化建议
     def generate_suggestions(df):
         suggestions = []
         if df['context_precision'].mean() < 0.7:
             suggestions.append("提高检索精准率: 增加相似度阈值")
         if df['faithfulness'].mean() < 0.8:
             suggestions.append("提升忠实度: 优化 Prompt 模板")
         return suggestions
     ```

5. **评估流水线 (Pipeline)**
   - **作用**: 自动化评估流程
   - **最佳实践**:
     ```python
     def evaluation_pipeline(rag_system, test_data):
         # Step 1: 准备评测集
         dataset = prepare_dataset(test_data)
     
         # Step 2: 执行评估
         result = evaluate(dataset, metrics=[...])
     
         # Step 3: 分析结果
         df = result.to_pandas()
         analysis = analyze_results(df)
     
         # Step 4: 生成建议
         suggestions = generate_suggestions(df)
     
         # Step 5: 保存报告
         save_report(analysis, suggestions)
     
         return {
             "scores": df.mean(),
             "analysis": analysis,
             "suggestions": suggestions
         }
     ```

**详细流程**:

```python
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    context_precision,      # 检索精准率
    context_recall,         # 检索召回率
    faithfulness,           # 忠实度
    answer_correctness,     # 答案正确性
    answer_relevancy        # 答案相关性
)

# 1. 准备评测数据集
test_data = {
    "question": [
        "什么是 RAG？",
        "RAG 的优势是什么？",
        "如何优化检索效果？"
    ],
    "answer": [
        "RAG 是检索增强生成技术...",
        "RAG 的优势包括时效性、准确性...",
        "可以通过优化切片策略..."
    ],
    "ground_truth": [
        "RAG (Retrieval-Augmented Generation) 是...",
        "主要优势：知识时效性、降低幻觉...",
        "优化方向：切片策略、检索策略..."
    ],
    "contexts": [
        ["RAG 是一种将检索和生成结合的技术..."],
        ["RAG 系统的主要优势包括..."],
        ["检索优化可以从以下几个方面入手..."]
    ]
}

dataset = Dataset.from_dict(test_data)

# 2. 执行评估
result = evaluate(
    dataset=dataset,
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_correctness,
        answer_relevancy
    ],
    llm=llm,
    embeddings=embeddings,
    raise_exceptions=False  # 遇到错误继续执行
)

# 3. 分析结果
import pandas as pd

df = result.to_pandas()

print("=== 评估结果概览 ===")
print(df.mean(numeric_only=True))

print("\n=== 各指标详情 ===")
for metric in ['context_precision', 'faithfulness', 'answer_relevancy']:
    print(f"\n{metric}:")
    print(f"  平均值: {df[metric].mean():.3f}")
    print(f"  中位数: {df[metric].median():.3f}")
    print(f"  标准差: {df[metric].std():.3f}")
    print(f"  最小值: {df[metric].min():.3f}")
    print(f"  最大值: {df[metric].max():.3f}")

# 4. 识别低分样本
low_score_samples = df[
    (df['context_precision'] < 0.6) |
    (df['faithfulness'] < 0.7) |
    (df['answer_relevancy'] < 0.7)
]

print(f"\n发现 {len(low_score_samples)} 个低分样本，需要优化")

# 5. 生成优化建议
def generate_optimization_suggestions(df):
    suggestions = []

    if df['context_precision'].mean() < 0.7:
        suggestions.append("检索精准率偏低，建议:")
        suggestions.append("  - 提高相似度阈值")
        suggestions.append("  - 优化切片策略")
        suggestions.append("  - 添加重排序")

    if df['context_recall'].mean() < 0.7:
        suggestions.append("检索召回率偏低，建议:")
        suggestions.append("  - 增加 top_k")
        suggestions.append("  - 扩大切片大小")
        suggestions.append("  - 使用查询扩展")

    if df['faithfulness'].mean() < 0.8:
        suggestions.append("忠实度偏低，建议:")
        suggestions.append("  - 优化 Prompt 模板")
        suggestions.append("  - 增加上下文窗口")
        suggestions.append("  - 过滤低质量片段")

    return "\n".join(suggestions)

print("\n=== 优化建议 ===")
print(generate_optimization_suggestions(df))
```

**评估指标详解**:

```
┌─────────────────────────────────────────────────┐
│          RAG 评估指标体系                        │
└─────────────────────────────────────────────────┘

检索阶段 (Retrieval)
├── context_precision (检索精准率)
│   问题: 检索结果中有多少是相关的？
│   目标: > 0.7
│   优化: 提高阈值、重排序
│
└── context_recall (检索召回率)
    问题: 相关内容被检索到了多少？
    目标: > 0.8
    优化: 增加 top_k、查询扩展

生成阶段 (Generation)
├── faithfulness (忠实度)
│   问题: 答案是否基于检索内容？
│   目标: > 0.85
│   优化: Prompt 模板、上下文质量
│
├── answer_correctness (正确性)
│   问题: 答案事实是否准确？
│   目标: > 0.75
│   优化: 检索质量、生成模型
│
└── answer_relevancy (相关性)
    问题: 答案是否切题？
    目标: > 0.8
    优化: Prompt 模板、查询理解
```

**评估最佳实践**:

```python
# 1. 分层评测集
evaluation_sets = {
    "smoke": {
        "size": 20,
        "purpose": "PR 前快速验证",
        "frequency": "每次提交"
    },
    "regression": {
        "size": 100,
        "purpose": "回归测试",
        "frequency": "每日构建"
    },
    "release": {
        "size": 500,
        "purpose": "版本发布前",
        "frequency": "发布前"
    }
}

# 2. 自动化评估流水线
def automated_evaluation_pipeline():
    # Step 1: 运行评测
    result = evaluate(dataset, metrics=[...])

    # Step 2: 检查阈值
    if result['faithfulness'].mean() < 0.8:
        alert("忠实度低于阈值！")

    # Step 3: 保存结果
    save_result(result, version=git_commit_id)

    # Step 4: 生成报告
    generate_report(result)

    # Step 5: 对比历史
    compare_with_baseline(result)

    return result

# 3. A/B 测试
def ab_test(strategy_a, strategy_b, test_set):
    results_a = evaluate_with_strategy(strategy_a, test_set)
    results_b = evaluate_with_strategy(strategy_b, test_set)

    comparison = {
        "strategy_a_avg": results_a.mean(),
        "strategy_b_avg": results_b.mean(),
        "improvement": results_b.mean() - results_a.mean()
    }

    return comparison
```

### 2.6 完整工作流程示例

```python
# RAG 系统完整工作流程
class RAGSystem:
    def __init__(self):
        self.documents = []
        self.index = None
        self.query_engine = None

    # 1. 加载阶段
    def load_documents(self, data_path):
        print("=== 阶段 1: 加载文档 ===")
        self.documents = SimpleDirectoryReader(data_path).load_data()
        print(f"加载了 {len(self.documents)} 个文档")

        # 数据清洗
        self.documents = [self._clean_doc(doc) for doc in self.documents]
        print("文档清洗完成")

    # 2. 索引阶段
    def build_index(self):
        print("\n=== 阶段 2: 构建索引 ===")

        # 切片
        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = splitter.get_nodes_from_documents(self.documents)
        print(f"生成 {len(nodes)} 个节点")

        # 向量化并构建索引
        self.index = VectorStoreIndex(nodes, show_progress=True)
        print("索引构建完成")

    # 3. 存储阶段
    def save_index(self, persist_dir):
        print("\n=== 阶段 3: 存储索引 ===")
        self.index.storage_context.persist(persist_dir)
        print(f"索引已保存到 {persist_dir}")

    # 4. 查询阶段
    def query(self, question):
        print(f"\n=== 阶段 4: 查询 ===")
        print(f"问题: {question}")

        # 创建查询引擎
        if not self.query_engine:
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                node_postprocessors=[
                    SimilarityPostprocessor(similarity_cutoff=0.7)
                ]
            )

        # 执行查询
        response = self.query_engine.query(question)

        print(f"答案: {response.response}")
        print(f"引用来源数: {len(response.source_nodes)}")

        return response

    # 5. 评估阶段
    def evaluate(self, test_dataset):
        print("\n=== 阶段 5: 评估 ===")

        result = evaluate(
            dataset=test_dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy
            ]
        )

        df = result.to_pandas()
        print("\n评估结果:")
        print(df.mean(numeric_only=True))

        return result

    def _clean_doc(self, doc):
        # 文档清洗逻辑
        doc.text = " ".join(doc.text.split())
        return doc

# 使用示例
rag = RAGSystem()

# 1. 加载
rag.load_documents("./data")

# 2. 索引
rag.build_index()

# 3. 存储
rag.save_index("./storage")

# 4. 查询
response = rag.query("什么是 RAG？")

# 5. 评估
rag.evaluate(test_dataset)
```

### 2.7 主流程总结

| 阶段 | 核心任务 | 关键技术 | 质量指标 |
|------|---------|---------|---------|
| **加载** | 数据 → 文档 | 文件解析、编码处理 | 文档完整性 |
| **索引** | 文档 → 节点 → 向量 | 切片策略、Embedding | 切片质量 |
| **存储** | 持久化索引 | 向量库、分区策略 | 存储效率 |
| **查询** | 检索 + 生成 | 混合检索、重排序 | 响应质量 |
| **评估** | 质量量化 | 自动指标、人工评测、A/B 测试 | 系统性能 |

**最佳实践建议**:

1. **加载阶段**: 支持多种格式，统一编码，保留元数据
2. **索引阶段**: 根据内容类型选择切片策略，平衡大小和语义
3. **存储阶段**: 选择合适的向量库，设计分区策略，定期备份
4. **查询阶段**: 混合检索优于单一检索，重排序提升质量
5. **评估阶段**: 建立评测集，自动化评估，持续优化

---

## 3. 核心组件详解

### 2.1 文档处理

#### 2.1.1 文档加载器 (Document Loaders)

**常用加载器:**

| 加载器 | 适用场景 | 特点 |
|--------|----------|------|
| `SimpleDirectoryReader` | 通用文件目录 | 支持多种格式,自动识别 |
| `SmartPDFLoader` | PDF 文档 | 保留格式,提取表格 |
| `WebPageLoader` | 网页内容 | 支持 JS 渲染 |
| `DatabaseLoader` | 数据库 | SQL 查询转文档 |

**示例代码:**

```python
from llama_index.core import SimpleDirectoryReader

# 基础用法
documents = SimpleDirectoryReader("./data").load_data()

# 自定义加载器
from llama_index.core.readers.base import BaseReader

class MyCustomLoader(BaseReader):
    def load_data(self, file, extra_info=None):
        # 自定义加载逻辑
        text = self._parse_file(file)
        return [Document(text=text, metadata=extra_info or {})]
```

#### 2.1.2 文档切片策略 (Chunking Strategies)

**切片策略对比:**

| 策略 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| **TokenTextSplitter** | 按 token 数硬切分 | 大小可控 | 可能切断语义 | 需要严格控制长度 |
| **SentenceSplitter** | 按句子边界切分 | 语义完整 | 长句处理困难 | 通用文本 |
| **SentenceWindowNodeParser** | 句子+窗口 | 保留上下文 | 需要后处理 | 精准检索+上下文 |
| **SemanticSplitterNodeParser** | 语义变化点切分 | 主题完整 | 依赖 embedding 质量 | 主题跳跃明显 |
| **MarkdownNodeParser** | 按标题层级 | 结构清晰 | 仅适用 Markdown | 技术文档 |

**切片参数调优指南:**

```python
from llama_index.core.node_parser import SentenceSplitter

# 基础参数
splitter = SentenceSplitter(
    chunk_size=512,        # 切片大小 (tokens)
    chunk_overlap=50,      # 重叠部分 (tokens)
    paragraph_separator="\n\n"
)

# 调优建议:
# 1. chunk_size:
#    - 过小: 语义不完整,检索命中率低
#    - 过大: 噪声多,上下文窗口浪费
#    - 推荐: 256-1024 之间,根据文档类型调整

# 2. chunk_overlap:
#    - 通常设置为 chunk_size 的 10-20%
#    - 确保跨切片的语义连续性

# 3. 窗口模式 (SentenceWindowNodeParser)
from llama_index.core.node_parser import SentenceWindowNodeParser

window_parser = SentenceWindowNodeParser(
    window_size=3,         # 前后各 3 句
    window_metadata_key="window"
)
```

### 2.2 多格式文档处理方案

> **生产级实践**: 针对不同文件格式（PDF、Word、Markdown等）的最佳处理策略

不同文件格式有不同的结构和特点，需要针对性的处理方案才能最大化检索效果。本节详细介绍各种格式的处理最佳实践。

#### 2.2.1 PDF 文档处理

这一节按 **RAGFlow 源码**来理解 PDF 处理，不再只讲“某个库怎么抽文本”，而是看完整工程链路如何落地。

**核心思想：解析器与分块策略解耦**

- 分块方法（General/Paper/Manual/...）负责 chunk 形态
- PDF 解析器负责 OCR、版面、表格、图片抽取
- 解析器可切换：`DeepDOC`、`Plain Text`、`MinerU`、`PaddleOCR`、`Docling`、`TCADP`、以及自定义视觉模型

DeepDOC = OCR + 布局理解 + 表格/图片处理 + 可追溯位置信息 的一体化 PDF 解析流程

这也是 RAGFlow 在工程上最实用的一点：同一套下游索引/检索流程，可替换上游 PDF 解析引擎。

**RAGFlow 的 PDF 处理主链路**

```text
上传 PDF
  -> queue_tasks() 按页切任务（或整本）
  -> task_executor.build_chunks() 调用 chunker.chunk()
  -> rag/app/naive.py::chunk() 根据 layout_recognize 分流解析器
  -> 解析产出 sections / tables（附位置）
  -> tokenize_chunks / tokenize_table 生成最终 chunk
  -> embedding + 入库
```

**步骤 1：任务切分（Task Service）**

- PDF 会先计算页数，再按 `task_page_size` 切任务。
- 默认 `DeepDOC` 是小批量分页处理（默认约 12 页）；`paper` 更大（默认约 22 页）。
- 若不是 `DeepDOC`（如 MinerU/PaddleOCR/Plain Text）通常改为整本任务，减少跨任务状态问题。

**步骤 2：解析器分流（naive.chunk）**

`parser_config.layout_recognize` 是关键开关：

| `layout_recognize` 配置 | 实际路径 | 适用场景 |
|---|---|---|
| `DeepDOC` | `by_deepdoc -> RAGFlowPdfParser` | 默认通用方案，OCR+布局+表格一体 |
| `Plain Text` | `by_plaintext -> PlainParser` | 纯文本、追求速度 |
| `MinerU` 或 `xxx@MinerU` | `by_mineru -> LLMBundle(OCR)` | 外部 MinerU 服务解析 |
| `PaddleOCR` 或 `xxx@PaddleOCR` | `by_paddleocr -> LLMBundle(OCR)` | 外部 PaddleOCR-VL 服务解析 |
| `Docling` | `by_docling` | 文档工程化解析实验方案 |
| `TCADP` | `by_tcadp` | 腾讯云解析链路 |
| 其他视觉模型名 | `VisionParser` | 逐页图像+VLM 描述 |

> 小技巧：`normalize_layout_recognizer()` 支持 `模型名@paddleocr` / `模型名@mineru` 的写法，便于在 UI 里同时指定“解析器类型 + 模型名”。

**步骤 3：DeepDOC 默认解析内部做了什么**

`RAGFlowPdfParser.__call__()` 主流程：

1. `__images__`：将页面渲染为图像，并提取字符候选  
2. `_layouts_rec`：版面检测（标题、正文、表格、图等）  
3. `_table_transformer_job`：表格结构识别（TSR），含表格自动旋转与重 OCR  
4. `_text_merge + _concat_downward + _filter_forpages`：跨行/跨页文本拼接与清理  
5. `_extract_table_figure`：抽取表格/图片区域（可裁图、可带位置）  
6. 输出文本块与表格/图片块，统一进入后续 chunk 化

其中表格自动旋转由 `TABLE_AUTO_ROTATE` 控制，默认开启。对扫描角度不正的表格比较关键。

**步骤 3.1：`__images__`（页图与字符候选准备）**

这一阶段的职责是“把每页变成可计算对象”，并准备 OCR 所需上下文：

1. 页面渲染：使用 `pdfplumber` 将页面转成位图。  
2. 文本层候选：读取 `dedupe_chars().chars`，保留 PDF 原生字符与坐标。  
3. 目录信息：尝试提取 `outline`，供后续结构辅助。  
4. 并发调度：逐页触发 `__ocr`，支持多设备并发。  
5. 自适应重试：如果框太少，会增大 `zoomin` 再跑一轮。

关键点：`__images__` 不直接完成最终文本识别，它负责“准备和调度”。

**步骤 3.1 补充：`pdfplumber` 如何抽表，RAGFlow 又是怎么做的**

按“先讲通用，再讲源码差异”来答：

1. `pdfplumber` 通用抽表入口  
- 常用是 `page.extract_table()` / `page.extract_tables()`，可配 `table_settings`。  
- 本质是“先找网格，再把单元格内文本回填”。

2. `pdfplumber` 常见抽表模式（工程叫法）  
- `lattice`（线框型）：依赖表格边框线，适合有清晰横竖线的报表。  
- `stream`（文本对齐型）：按文本对齐/间距推断列边界，适合无边框表格。  
- 对应到 `pdfplumber` 参数通常是 `vertical_strategy/horizontal_strategy` 选择 `lines` 或 `text`（也可混合）。

3. RAGFlow 主链路并不是直接切 `lattice/stream`  
- DeepDOC 主链路里，`pdfplumber` 主要用于页面渲染（`to_image`）和文本层字符候选（`dedupe_chars().chars`）。  
- 表格结构恢复走 `_table_transformer_job` + `TableStructureRecognizer`（TSR）+ OCR 融合，并支持表格自动旋转与重 OCR。  
- 最终由 `construct_table(...)` 产出 HTML（`<table>...</table>`）或行描述文本（`list[str]`）。

4. RAGFlow 里哪里真的用了 `extract_tables()`  
- 在 `rag/app/resume.py` 的简历解析分支里，`page.extract_tables()` 作为补充抽表逻辑。  
- 但这不是 DeepDOC 通用 PDF 主干的默认表格方案。

5. `pdfplumber` 和 OCR 到底怎么配合
- 第一步：`pdfplumber` 提供两份“底稿”  
  - 页图（给 OCR 检测/识别用）  
  - `dedupe_chars().chars` 字符与坐标（PDF 文本层）  
- 第二步：OCR 先做 `detect` 产出文本框（不是直接全量识别）。  
- 第三步：按坐标把 `dedupe_chars` 的字符塞进检测框：  
  - 框内能拼出文本 -> 直接用文本层结果；  
  - 框内拼不出文本 -> 再对该框裁图做 `recognize_batch` 补识别。  
- 结论：融合粒度是“框级别”，不是“整页文本二选一”。

6. 一个直观例子（detect vs recognize）
- 假设某页有 4 个文本区域（3 段正文 + 1 个扫描表格）。
- `detect` 阶段先返回 4 个框坐标（B1/B2/B3/B4），此时还不知道框里具体文字。
- 系统先用 PDF 文本层字符去填这 4 个框：
  - B1/B2/B3 能从 `dedupe_chars` 拼出文本 -> 直接采用；
  - B4（扫描表格）拼不出文本 -> 再对 B4 做 `recognize_batch` 识别。
- 所以“不是直接全量识别”的意思是：先定位，再只识别缺口框，减少误识别和重复计算。

一句话总结：`pdfplumber` 偏“规则工程抽表”，RAGFlow DeepDOC 偏“OCR+布局+TSR 的鲁棒重建”，后者对扫描件、旋转表格更稳。

**步骤 3.2：`_layouts_rec`（版面语义分类）**

这一阶段把 OCR 框变成带语义的版面块：

1. 调用布局识别器，对框做 `title/text/table/figure/...` 分类。  
2. 同步页内坐标到全局累计坐标（跨页拼接时可直接排序）。  
3. 输出 `self.page_layout + self.boxes` 的结构化版面结果。

关键点：后面是否走表格/图片抽取，取决于这里打的 `layout_type`。

**步骤 3.3：`_table_transformer_job`（表格结构识别与纠偏）**

这一阶段专门处理表格：

1. 先从版面块里定位表格区域并裁图。  
2. 对表格尝试 0/90/180/270 方向评估，选最佳角度。  
3. 跑 TSR（表格结构识别），得到行/列/表头/跨单元格信息。  
4. 若发生旋转，会对旋转后表格重做 OCR，并映射回页面坐标。

关键点：这是 DeepDOC 处理“扫描表格、旋转表格”质量差异的核心步骤。

**步骤 3.4：`_text_merge + _concat_downward + _filter_forpages`（文本整理）**

这一阶段做阅读顺序和文本清洗：

1. `_text_merge`：同布局、同列、相邻框横向合并。  
2. `_concat_downward`：按阅读顺序串联跨行内容。  
3. `_filter_forpages`：清理页眉页脚噪声、重复碎片、无效短块。

关键点：这一步决定最终 chunk 的语义连贯性。

**步骤 3.5：`_extract_table_figure`（图表裁图与内容抽取）**

这一阶段把表格和图片变成可入库对象：

1. 将 `layout_type=table/figure` 的框从正文框里分离。  
2. 处理 caption 归属（表注/图注挂到最近目标）。  
3. 对目标区域裁图，保留位置坐标。  
4. 表格额外输出结构化文本（HTML 或自然语言行列描述）。

关键点：输出不仅有文本，还有图像与位置信息，便于引用和多模态检索。

- 文本输出：“2024年Q1华东区销售额为 1,250 万元...”
  - 图像输出：该表格区域的裁剪图（image）
  - 位置信息：page=12, x0=120, x1=520, top=230, bottom=410

**步骤 3.6：`__call__` 返回值（进入 chunk 化前的标准产物）**

`RAGFlowPdfParser.__call__()` 默认返回一个二元组：`(sections, tbls)`。

1. `sections`（文本主结果）  
- 类型：`str`（不是 `list[dict]`）。  
- 内容：清洗拼接后的正文文本。  
- 特征：文本内嵌位置标签（`@@{page}\t{x0}\t{x1}\t{top}\t{bottom}##`）。

2. `tbls`（图表结果）  
- 类型：`list`。  
- 每项结构：`(img, content)`。  
- `img`：裁剪后的图像（PIL Image）。  
- `content`：表格/图片的文本内容，可能是 `str`（如 HTML）或 `list[str]`（自然语言行列描述/图注）。

如果你需要字段化调试结果（而不是 `sections` 字符串），应使用 `parse_into_bboxes()`，其返回 `list[dict]`，常见字段有：

 1. text
     块内文本内容。普通段落是正文；表格块可能是表格文本/HTML；图片块可能是图注文本。
  2. page_number
     页码（1-based）。表示这个块主要落在哪一页。
  3. x0, x1, top, bottom
     块的边界框坐标。
     x0/x1 是左右边界；top/bottom 是上下边界。
     注意：在这个解析器里，top/bottom常是“跨页累计Y坐标”（用于全局排序），不完全等同于单页局部
     坐标。
  4. layout_type
     版面类型标签，比如 text、title、table、figure、table caption、figure caption 等。
  5. layoutno
     版面块编号（同页内的布局区域ID）。常用于判断哪些行属于同一块/同一表格区域。
  6. position_tag
     位置编码字符串，形如：@@3\t12.0\t530.5\t100.2\t120.8## 或跨页 @@3-4\t...##。
     本质是“页码+坐标”的可序列化标签，后续可反解析。
  7. image
     按该块坐标裁出来的图像（通常是 PIL.Image），用于可视化、溯源、VLM。
  8. positions
     position_tag 的结构化版本，通常是 [[page, left, right, top, bottom], ...]。
     跨页块会有多段位置。

上层 `naive.chunk()` 的接入方式：

1. 文本路径：`sections -> naive_merge -> tokenize_chunks(...)`  
2. 图表路径：`tbls -> tokenize_table(...)`

然后统一进入 embedding 与索引阶段。

**步骤 4：位置标签与裁图机制（可解释性关键）**

RAGFlow 在文本里注入位置标签，格式类似：

```text
@@{page}\t{x0}\t{x1}\t{top}\t{bottom}##
```

然后在 chunk 阶段：
- `pdf_parser.crop(...)` 可按标签回裁原图（用于引用展示）
- `pdf_parser.remove_tag(...)` 去除标签，只保留可检索文本

这套机制让“检索内容”与“原文证据位置”一一对应，便于前端高亮和溯源。

**步骤 5：统一 chunk 化与入库**

- 文本走 `tokenize_chunks(...)`
- 表格/图片走 `tokenize_table(...)`，并打上 `doc_type_kwd=table/image`
- 若配置了 `image_context_size/table_context_size`，会用 `append_context2table_image4pdf(...)` 给图表补邻近上下文

最终所有 chunk 进入同一 embedding/索引流程，但保留了类型与位置元数据，便于检索与展示分流。

**和“只做文本抽取”的区别**

RAGFlow 的重点不是“把 PDF 文字抠出来”，而是：

1. 解析器可替换（本地/远程/云服务）  
2. 文本、表格、图片统一入索引但保留类型  
3. 位置标签驱动可视化溯源  
4. 多页任务切分与复用机制降低重算成本  

这也是生产环境中更稳定的一种 PDF RAG 架构。

**实战配置建议（RAGFlow 语境）**

1. 默认优先 `DeepDOC`，稳定后再按场景切 `MinerU/PaddleOCR`。  
2. 对扫描件和复杂表格，保留 `TABLE_AUTO_ROTATE=true`。  
3. 为图表问答开启 `image_context_size`，并结合视觉增强能力。  
4. 纯文本法规/制度类文档可考虑 `Plain Text` 提升吞吐。  
5. 任何解析器都要保留页码/坐标元数据，保证引用可追溯。  

#### 2.2.2 Word 文档处理

这一节按 **RAGFlow 源码**看 DOCX 处理，不用泛化方案。

**RAGFlow 的 Word 处理主链路**

```text
上传 DOCX
  -> rag/app/naive.py::chunk() 识别 .docx 分支
  -> Docx().__call__() 解析成 sections[(text, image, table)]
  -> naive_merge_docx() 生成 chunks（text/image/table）
  -> （可选）vision_figure_parser_docx_wrapper_naive 图像描述增强
  -> doc_tokenize_chunks_with_images() 标准化字段
  -> task_executor 上传图片到对象存储并写入 img_id
  -> embedding + 索引入库
```

**步骤 1：预处理（可选）**

1. 若开启 `parser_config.analyze_hyperlink=true`，会先用 `extract_links_from_docx(binary)` 抽取超链接。  
2. 每个链接会抓取 HTML（`extract_html`）并递归走同一套 `chunk()`。  
3. 根任务还会尝试 `extract_embed_file(binary)`，把嵌入文件（如内嵌附件）递归分块。

**步骤 2：`Docx().__call__` 解析细节**

`Docx` 基于 `python-docx`，按 `document.body` 的真实顺序遍历段落和表格，核心行为如下：

1. **段落**  
- 普通段落：清洗文本后入 `lines`。  
- `Caption` 样式：优先和前一个图片块绑定，保留“图+图注”关系。

2. **图片**  
- 从段落 XML 的 `pic:pic -> a:blip/@r:embed` 找关系 ID。  
- 读取二进制后封装成 `LazyDocxImage`（延迟加载，减少内存峰值）。

3. **分页标记**  
- 识别 `lastRenderedPageBreak`/`w:br type=\"page\"`，维护 `pn` 用于 `from_page/to_page` 过滤。

4. **表格**  
- 表格被转成 HTML 字符串。  
- 通过 `__get_nearest_title()` 反向找最近标题链路，写入 `<caption>Table Location: ...</caption>`，增强语义与可追溯性。

最终输出是三元组列表：`[(text, image, table), ...]`。

**步骤 3：`naive_merge_docx` 分块策略**

1. `_build_cks`：把 `sections` 转成 `ck_type in {text,image,table}` 的中间块。  
2. `_add_context`：若配置了 `table_context_size/image_context_size`，给表格/图片块补上下文句子。  
3. `_merge_cks`：只合并文本块，图片/表格块保持独立，避免媒体块被吞并。

**步骤 4：图像语义增强（可选）**

- `vision_figure_parser_docx_wrapper_naive` 会在租户有 `IMAGE2TEXT` 模型时触发。  
- 对图片 chunk 调用视觉模型生成描述，并把描述追加到该 chunk 的 `text`。  
- 若有上下文，会用“带上下文的图像描述 prompt”。

这一步能显著提升“图说了什么”类问题的召回。

**步骤 5：标准化字段与入库**

1. `doc_tokenize_chunks_with_images` 会把块转换成检索文档：  
- `content_with_weight`（正文）  
- `doc_type_kwd`（`text`/`table`/`image`）  
- `image`（若存在）

2. 在 `task_executor` 中：  
- 若 chunk 含 `image`，调用 `image2id` 转 JPEG 后写入 `STORAGE_IMPL`（默认 MINIO，可配 S3/OSS/Azure/GCS）。  
- 索引文档只保留 `img_id`，不直接存原图二进制。

**和 PDF 路径的关键差异**

1. DOCX 默认没有 PDF 那套精细坐标标签（`@@...##`）和页面 bbox。  
2. DOCX 更强调“结构顺序 + 媒体绑定 + 标题语义补全”。  
3. 图像最终同样走统一对象存储与 `img_id` 检索引用机制。

**实战建议（RAGFlow 语境）**

1. 知识库里 DOCX 较多时，建议开启 `analyze_hyperlink`，能吃到文档中的外链知识。  
2. 对报告/手册类文档，建议设置 `image_context_size > 0`，提升图表问答效果。  
3. 表格密集文档建议保留默认表格 HTML 输出，后续检索和展示更稳定。  
4. 若只关注速度可关闭视觉增强；若关注图表问答则开启 `IMAGE2TEXT` 增强。

#### 2.2.3 Markdown 文档处理

这一节按 **RAGFlow 源码**看 Markdown 处理（`rag/app/naive.py` + `deepdoc/parser/markdown_parser.py`）。

**RAGFlow 的 Markdown 处理主链路**

```text
上传 md/markdown/mdx
  -> MarkdownParser.extract_tables_and_remainder() 抽表
  -> MarkdownElementExtractor.extract_elements() 分段
  -> （可选）图片链接加载与 section_images 聚合
  -> （可选）IMAGE2TEXT 给图片段补描述
  -> （可选）提取超链接并递归抓取 URL 内容
  -> 按 chunk_token_num + overlapped_percent 合并
  -> tokenize_chunks / tokenize_chunks_with_images + tokenize_table
```

**步骤 1：结构解析**

1. 先抽表：支持 Markdown table 和 HTML `<table>`，表格可单独输出。  
2. 再分段：按标题、代码块、列表、引用、普通段落等元素切分。  
3. 若配置了自定义分隔符（如 `` `---` ``），优先按分隔符切段。

**步骤 2：图片与视觉增强（可选）**

1. 解析每个 section 的图片 URL（本地或远程），聚合为 `section_images`。  
2. 若租户配置了 `IMAGE2TEXT` 模型，则对图像生成描述并追加到对应 section 文本。  
3. 这一步是“文本增强”，最终仍走统一 chunk 与索引流程。

**步骤 3：超链接递归（可选）**

- 当开启 `parser_config.hyperlink_urls` / `analyze_hyperlink` 时，会把 Markdown 中链接提取出来，抓取 HTML 后递归调用 `chunk()`，把外链内容也纳入知识库。

**步骤 4：chunk 与入库**

1. 表格走 `tokenize_table`。  
2. 正文按 `chunk_token_num` 和 `overlapped_percent` 合并。  
3. 有图像则走 `tokenize_chunks_with_images`，无图像走 `tokenize_chunks`。  
4. 统一进入 embedding 与索引；图片会在后续任务阶段持久化为 `img_id`。

**实战建议（RAGFlow 语境）**

1. 技术文档建议保留标题/代码块切分，不要只按 token 硬切。  
2. 图多的知识库建议启用 `IMAGE2TEXT`，提升“图示说明类”查询效果。  
3. 开启超链接递归时，建议限制抓取白名单，避免引入噪声网页。  
4. `overlapped_percent` 建议小幅开启，兼顾召回与去重成本。

#### 2.2.4 表格类文件处理（CSV/XLS/XLSX）

这一节单独讲表格文件，因为在企业知识库里它通常是高价值信息最密集、也最容易丢语义的一类数据。

**RAGFlow 表格文件主链路**

```text
上传 csv/xls/xlsx
  -> naive.chunk() 命中表格分支
  -> 默认 ExcelParser（或 TCADP Parser）
  -> 产出 sections/tables
  -> tokenize_table 或 tokenize_chunks
  -> embedding + 索引入库
```

**默认路径：`ExcelParser`**

1. 自动识别 CSV/Excel（二进制头判断，不只看扩展名）。  
2. 兼容多引擎读取失败回退（`openpyxl -> pandas`）。  
3. 可输出两种形态：  
- 行文本形态：`列名:值; 列名:值`（便于文本检索）。  
- HTML 表格形态（`html4excel`）（便于结构展示与表格问答）。

**可选路径：`TCADP Parser`**

当 `layout_recognize == "TCADP Parser"` 时启用，适合复杂表格/扫描表格场景，产物直接按表格 chunk 入库。

**一句话总括（按解析路径统一入库）**

RAGFlow 表格入库的“具体格式”按路径是固定可追溯的，不是泛化的“任意结构化”：

1. `general` 解析器 + `csv/xlsx` + `html4excel=false`：`ExcelParser.__call__` 产出 `列头：值; 列头：值` 的行文本（可附 sheet 名）。  
2. `general` 解析器 + `csv/xlsx` + `html4excel=true`：`ExcelParser.html` 产出 `<table><tr><th>...` 的 HTML 字符串。  
3. `table` 解析器（`rag/app/table.py`）：每行转成多行 Key-Value 文本 `- 字段: 值`；若是 Infinity/OceanBase，还会额外写 `chunk_data` JSON 保留原始列值。  
4. 文档内表格（PDF/Docx 路径）：通常产出 HTML 表格字符串（`<table>...`）；若上游给的是 `list[str]` 表行描述，则 `tokenize_table` 会按批次用 `;`/`；` 拼接后入库。  

无论哪条路径，最终都统一写入 `content_with_weight` 作为检索主文本，并打 `doc_type_kwd=table` 进入同一 embedding/索引流程。

**生产建议（表格专项）**

1. 若业务偏“精确字段问答”，优先保留 HTML 表格形态。  
2. 若业务偏“概念检索/模糊匹配”，行文本形态更稳。  
3. 表格密集库建议配合 `table` parser 或提高 `table_context_size`。  
4. 重点监控“列头是否保留、跨行是否错位、空值是否污染检索”。

**面试补充：表格识别方法总结（与本节的关系）**

很多同学会把“CSV/XLS/XLSX 解析”和“表格识别”混在一起。严格说，这是两类问题：

1. `CSV/XLS/XLSX` 是原生结构化数据，核心是“解析与保真”，通常不需要先做表格检测。  
2. 扫描件/图片/PDF 表格才需要“检测 + 结构重建”。

**表格识别任务拆解（通用）**

1. 表格检测（Table Detection）：先找到表格整体区域。  
2. 结构识别（Structure Recognition）：再恢复行/列/单元格关系（含合并单元格）。

**常见技术路线（面试可答）**

| 路线 | 核心思路 | 代表方案 | 适用场景 |
|---|---|---|---|
| 传统图像规则法 | 形态学 + 连通域 + 线段/交点分析 | OpenCV 规则流水线 | 线框清晰、模板稳定 |
| PDF 工程抽取法 | 用文本层与几何对齐恢复表结构 | `pdfplumber`（`lattice/stream`） | 文本层质量好的 PDF |
| 深度学习法 | 检测/分割/实例分割重建表结构 | TableNet、CascadeTabNet、DeepDeSRT、SPLERGE 等 | 扫描件、复杂版式、弱线表 |

**落地取舍（RAGFlow 语境）**

1. 对 `CSV/XLS/XLSX`：优先走 `ExcelParser` / `table` parser，保留列头与行语义（HTML 或行文本入库）。  
2. 对 PDF 表格：优先可解释的工程抽取（文本层 + 几何）；抽不稳再引入模型方案。  
3. 对扫描/拍照表格：直接按 OCR + 深度学习结构识别路线处理，再统一转成 HTML/KV/行描述入库。

一句话：`2.2.4` 关注“原生表格文件如何高保真入库”，而表格识别方法是其上游补充能力，主要用于非原生表格输入。

#### 2.2.5 其他格式处理（非表格）

这一节按 RAGFlow 的真实分支说明，不再使用通用“读文件示例”。

**A. 纯文本与代码文件（`.txt/.py/.js/.java/...`）**

- 统一走 `TxtParser`。  
- 按 `delimiter` 和 `chunk_token_num` 切分。  
- 代码文件本质按文本处理，不额外做 AST 语义拆分。

**B. HTML（`.htm/.html`）**

- 走 `HtmlParser`：移除 `script/style/comment`，按块级标签提取。  
- 支持标题标签映射（如 `h1/h2`）并保留表格内容。  
- 再按 token 上限切块。

**C. JSON（`.json/.jsonl/.ldjson`）**

- 走 `JsonParser`。  
- 自动判断 JSON vs JSONL。  
- 按结构递归切分，保证块大小不超过阈值，同时尽量保留层级结构。

**D. 老式 Word（`.doc`）**

- `naive.chunk` 里用 `tika` 作为兼容方案。  
- 若环境无 tika 或解析失败，会返回错误/空内容，不建议作为主路径。

**E. 专用多媒体解析器（非 naive）**

这部分由 `parser_id` 选择，不完全依赖扩展名：

1. `picture`：图片 OCR +（可选）视觉模型描述；视频走 `IMAGE2TEXT` 生成摘要。  
2. `audio`：走 `SPEECH2TEXT` 转写后入索引。  
3. `email`：解析邮件头/正文（text+html）并递归处理附件。  
4. `presentation`：PPT/PDF 页面级解析，每页可带图像与位置字段。

**常见格式与 RAGFlow 路径速查**

| 输入格式/类型 | 主要入口 | 关键能力 | 常见输出类型 |
|---|---|---|---|
| `md/markdown/mdx` | `naive.chunk -> MarkdownParser` | 抽表、分段、图像增强、链接递归 | `text/table/image` |
| `txt + 代码` | `naive.chunk -> TxtParser` | 分隔符切分 + token 控制 | `text` |
| `html` | `naive.chunk -> HtmlParser` | DOM 清洗 + 块级抽取 | `text/table` |
| `json/jsonl` | `naive.chunk -> JsonParser` | 结构化递归切分 | `text` |
| 图片/视频 | `picture.chunk` | OCR + CV 描述 | `image/video` |
| 音频 | `audio.chunk` | 语音转文本 | `text` |
| 邮件 | `email.chunk` | 正文+附件递归 | `text + 附件子块` |

#### 2.2.6 混合格式处理策略

企业知识库里“多格式统一处理”在 RAGFlow 里是两层路由：

```text
第一层：task_executor.FACTORY（按 parser_id 选 chunker）
  general -> rag/app/naive.py
  paper/book/manual/laws/presentation/table/qa/...
  picture/audio/email/tag

第二层：chunker 内部再按扩展名与 parser_config 分流
  例如 naive.chunk 内部继续分 .pdf/.docx/.md/.xlsx/.txt/.html/.json...
```

**为什么这样设计**

1. `parser_id` 负责“业务模式”（General/Paper/Manual/...）。  
2. 扩展名分流负责“文件格式解析细节”。  
3. 结果统一进同一索引写入链路，降低系统复杂度。

**统一产物与入库约束**

无论上游格式如何，最终 chunk 都会收敛到统一字段体系（常见）：

1. `content_with_weight`：检索主文本。  
2. `doc_type_kwd`：`text/table/image/video` 等类型标记。  
3. `page_num_int/top_int/position_int`：可选位置字段。  
4. `img_id`：媒体对象引用 ID（真正图片在对象存储，不直接进索引）。

**生产级配置建议（RAGFlow）**

1. 文本为主库：`parser_id=general`，按扩展名自动分流即可。  
2. 论文/手册类：优先 `paper/manual`，提升结构切分质量。  
3. 多图文档：开启 `IMAGE2TEXT`，并设置 `image_context_size`。  
4. 表格密集库：Excel 开 `html4excel` 或选 `table` parser 做行级索引。  
5. 混合库强烈建议保留 `doc_type_kwd + img_id + position`，便于检索后展示分流和证据溯源。

### 2.3 向量化与存储

这一节按 RAGFlow 源码看“向量怎么生成、存到哪、字段长什么样”。

**RAGFlow 向量化与存储主链路**

```text
chunker.chunk() 产出 chunks
  -> task_executor.embedding() 批量向量化
  -> init_kb() 创建/检查索引（按向量维度）
  -> insert_chunks() 批量写入 Doc Engine
  -> 媒体对象写入 STORAGE_IMPL，索引中仅存 img_id
```

#### 2.3.1 向量生成（`task_executor.embedding`）

**什么是向量模型（Embedding Model）？**

- 定义：把文本编码为稠密向量的模型，用于语义相似度检索。  
- 输入：query 或 chunk 文本。  
- 输出：固定维度向量（如 768/1024/1536/4096）。  
- 位置：RAG 的第一阶段召回核心组件（先召回候选，再可选 rerank 精排）。  

**向量模型的原理（bi-encoder）**

- 基本形式：`q_vec = f(q)`，`d_vec = f(d)`，`score = cos(q_vec, d_vec)`。  
- 查询 q 编码成向量 q_vec，把文档 d 也编码成向量 d_vec，用余弦相似度比较两个向量方向，得到相关性分数
- 特点：query/doc 分开编码，文档向量可离线预计算，在线检索速度快。  
- 工程意义：支持 ANN（如 HNSW/IVF） 向量索引，适合大规模知识库“高召回、低延迟”场景。  

**它和 Rerank 模型的关系**

- 向量模型负责“粗召回”：尽量把正确答案捞进 topN。  
- Rerank 负责“精排序”：对候选做更细粒度相关性判断，提升 topK 质量。  
- 常见两阶段：`Embedding Recall -> Rerank -> 生成`。  

**Qwen3 Embedding 实现与原理（源码 + 论文）**

1. 模型规格与能力  
- 模型档位：`Qwen3-Embedding-0.6B/4B/8B`；向量维度：`1024/2560/4096`；支持 MRL（可截断维度）。  
- 原理动机：同一架构下提供不同成本/效果档，便于线上按延迟与精度分层部署。  

2. 输入构造（任务感知）  
- 实现：查询侧拼接指令（如 `Instruct: {task}\nQuery:{query}`），文档侧通常不加指令。  
- 原理：论文把相关性定义为 `score(q,d|I)`，`I` 用于显式注入任务语义，因此 query 侧 instruction 是关键。  

3. 编码与池化（向量从哪里来）  
- 实现：`AutoModel + AutoTokenizer(left padding)` 前向后取 `last_hidden_state`，再做 `last_token_pool`。  
- 原理：论文描述 embedding 来自序列末端（[EOS]/最后有效 token）隐藏状态；工程实现与此一致。  

4. 相似度计算  
- 实现：向量做 `L2 normalize` 后，用点积或余弦计算相似度。  
- 原理：归一化后点积与余弦等价，便于统一向量检索打分与索引实现。  

5. 训练目标（为什么向量可用于召回）  
- 原理：Embedding 训练不是“只算余弦”，而是改进 InfoNCE：正样本 + 硬负样本 + batch 内负样本联合优化。
- 余弦只是相似度函数，真正训练目标是“在正负样本集合上的对比学习排序”  
- 论文还使用误负样本掩码 `m_ij`，降低假负例干扰，提升召回鲁棒性。  

6. 数据与训练流程（为什么效果提升）  
- 原理：多阶段训练是核心增益来源：  
  - 弱监督阶段：大规模合成数据（约 `150M` 对）  
  - 监督阶段：标注数据 + 高质量合成数据（约 `7M + 12M`）  
- 论文消融显示：去掉弱监督阶段或去掉模型合并，性能都会下降。  

7. 数据合成策略（泛化来源）  
- 原理：合成时显式控制任务类型、语言、长度、难度、persona 等维度。  
- 工程意义：让训练分布更接近真实检索流量，降低线上 domain gap。  

8. 模型合并与推理配置（落地建议）  
- 原理：SFT 后用 SLERP 合并多个 checkpoint，提升跨任务/跨分布稳定性。  
- 实现建议：常用 `fp16 + flash_attention_2 + 合理 max_length(如 8192) + batch`；再按业务做维度截断 A/B（如 1024 vs 2560）。  

**RAGFlow 在本阶段做的事（实现视角）**

1. 入口与调用时机  
- 主流程是：`build_chunks -> embedding(...) -> insert_chunks(...)`。  
- `embedding` 在 `do_handle_task()` 中被调用，失败会直接报错并终止任务。  

2. 向量输入文本选择（先问句，后正文）  
- 每个 chunk 先取 `question_kwd`（多行拼接）；没有则取 `content_with_weight`。  
- 标题来自 `docnm_kwd`（默认 `"Title"`），后面用于标题向量融合。  

3. 预处理与长度控制  
- 编码前会清理表格标签噪声（如 `<table>/<tr>/<td>/<th>/<caption>`）。  
- 空文本会兜底成 `"None"`，避免 embedding 接口收到空字符串。  
- 批量编码时会执行 `truncate(text, mdl.max_length - 10)`，留出安全余量。  

4. 编码执行策略（吞吐与稳定）  
- 标题只编码一次，再 `tile` 到每个 chunk，减少重复计算。  
- 内容按 `settings.EMBEDDING_BATCH_SIZE` 分批编码。  
- 通过 `embed_limiter` 控制并发，单批 `batch_encode` 带 `timeout(60)`。  
- 进度回调按批次推进（约 `0.7 -> 0.9` 区间）。  

5. 向量融合与字段写回  
- 若标题向量和内容向量维度一致，则按  
  `v = title_w * title_vec + (1-title_w) * content_vec` 融合。  
- `title_w` 来自 `parser_config.filename_embd_weight`，默认 `0.1`。  
- 最终写回动态字段 `q_{dim}_vec`（如 `q_1024_vec`），并返回 `token_count` 与 `vector_size`。  

6. 后续入库与可靠性（紧邻本阶段）  
- 紧接着走 `insert_chunks` 分批入库（`DOC_BULK_SIZE`）。  
- 若任务取消或任务记录异常，会停止并做清理（含已写入 chunk 的回滚删除）。  
- 入库成功后才更新文档 chunk 数与 token 消耗统计。  

#### 2.3.2 索引与存储层（Doc Engine + Object Storage）

1. 检索索引存储（Doc Engine）  
- 由 `settings.DOC_ENGINE` 决定（Elasticsearch/OpenSearch/Infinity/OceanBase 等）。  
- 创建索引时会带上向量维度和 parser 信息：`create_idx(index_name, kb_id, vector_size, parser_id)`。  

2. 媒体对象存储（STORAGE_IMPL）  
- 图片不直接进检索索引，先上传对象存储（默认 MINIO，可配 S3/OSS/Azure/GCS）。  
- 索引文档里只保留 `img_id` 引用。

3. 批量写入  
- `insert_chunks()` 分批写入，失败会回滚删除已写入 chunk，保证一致性。

#### 2.3.3 入库后的关键字段（检索面）

| 字段 | 含义 | 备注 |
|---|---|---|
| `content_with_weight` | 主检索文本 | 召回与生成都依赖 |
| `content_ltks/content_sm_ltks` | 分词字段 | 词项检索用 |
| `q_{dim}_vec` | 向量字段 | dense 检索列 |
| `doc_type_kwd` | 类型标识 | `text/table/image/video` |
| `img_id` | 媒体引用 | 对象存储键，不是原图 |
| `position_int/page_num_int/top_int` | 位置元数据 | 溯源与高亮 |
| `important_kwd/question_kwd` | 扩展语义字段 | 自动关键词/问题生成可填充 |

### 2.4 检索策略(RAGFlow)

这一节按 RAGFlow `rag/nlp/search.py::Dealer` 来看真实检索流程。

**RAGFlow 检索主链路**

```text
问题 -> FulltextQueryer.question()
    -> 混合召回（词项 + 向量 + weighted_sum）
    -> （可选）rerank模型重排
    -> 阈值过滤 + 分页
    -> （可选）children聚合 / TOC增强 / KG增强
```

#### 2.4.1 第一阶段召回：词项 + 向量混合

**面试回答版（按源码主链路）**

1. 入口参数与召回窗口  
- 第一阶段在 `Dealer.retrieval()` 内构建 `req`，核心参数是：`question/topk/similarity/kb_ids/doc_ids`。  
- 这里先用较大的 `RERANK_LIMIT` 做候选召回（不是最终分页大小），保证后续重排有足够候选。  

2. 词项召回构建（BM25/倒排侧）  
- `FulltextQueryer.question(question, min_match=0.3)` 生成 `MatchTextExpr`。  
- 内部做查询清洗、分词、词权重、同义词扩展，并按字段权重匹配（如 `title_tks/important_kwd/question_tks/content_ltks`）。  

3. 向量召回构建（Dense 侧）  
- `get_vector()` 调 `emb_mdl.encode_queries(question)` 生成查询向量。  
- 构造 `MatchDenseExpr(q_{dim}_vec, cosine, topk, {"similarity": 阈值})`。  

4. 双路融合执行（DocEngine 层）  
- 两路表达式通过 `FusionExpr("weighted_sum")` 融合后一次检索。  
- 当前源码默认权重为 `text:vector = 0.05:0.95`（召回阶段明显偏向向量语义）。  

5. 空结果兜底策略  
- 若首轮 `total == 0`：  
  - 若指定了 `doc_id` 过滤：退化为过滤条件查询；  
  - 否则放宽召回：`min_match 0.3 -> 0.1`，并把向量相似度阈值放宽到 `0.17` 再查一次。  

6. 第一阶段产物（交给重排）  
- 输出 `SearchResult`，包含 `ids/total/query_vector/field(_score)/keywords/highlight/aggregation`。  
- 这批候选进入 `2.4.2` 的重排与阈值过滤，不直接作为最终返回。  

#### 2.4.2 第二阶段重排：本地重排或模型重排

**什么是 Rerank 模型（重排模型）？**

- 定义：在“第一阶段召回”之后，对候选文档做更细粒度相关性判断并重新排序的模型。  
- 输入：`query + 候选文档列表`（通常是召回得到的 topN）。  
- 输出：每个候选的相关性分数（常见是 `0~1`），再按分数降序得到新的 topK。  
- 位置：RAG 里通常是“召回后、生成前”的关键质量闸门。  

**它和向量召回的区别**

- 向量召回（bi-encoder）偏“高召回、低成本”：query/doc 各自编码后算相似度。  
- Rerank（cross-encoder/生成式）偏“高精度、较高成本”：联合看 query 与 doc 再打分。  
- 实践上常用“先粗召回（几十条）-> 再重排（留前几条）”来平衡效果与成本。  

**原理深度对比（面试可直接复述）**

1. 计算函数不同（最本质）  
- 向量召回：`q_vec = f(q)`，`d_vec = f(d)`，`score = sim(q_vec, d_vec)`。  
  先“各自编码”，再做相似度，属于**独立表示 -> 后匹配**。  
- Rerank：`score = g(q, d)`。  
  query 与 doc 一起输入模型联合建模，属于**联合表示 -> 直接判别相关性**。  

2. 交互时机不同（为什么 rerank 更准）  
- 向量召回：交互发生在向量空间，token 级细节交互较弱。  
- Rerank：交互发生在输入序列内部（token 级），能显式建模否定、数值、实体关系、跨句约束。  
- 典型收益场景：  
  - `不支持` vs `支持` 这类否定语义  
  - `5mg` vs `50mg` 这类数字/单位  
  - 同名实体消歧（产品名、缩写、专有词）  

3. 信息压缩路径不同  
- 向量召回要把整段文本压到固定维度（如 1024/2048/4096），存在信息瓶颈。  
- Rerank 直接看原文本（或较长上下文）做判别，丢失信息更少。  

4. 复杂度与系统角色不同  
- 向量召回：可借助 ANN 索引做大规模近邻搜索，适合百万/千万级文档“粗召回”。  
- Rerank：通常对召回候选逐条打分，成本明显更高，适合“精排”而非全库首轮检索。  
- 工程分工：  
  - 召回负责 `Recall@K`（把正确答案尽量捞进候选）  
  - 重排负责 `Precision@TopK`（把最相关排到前面）  

5. 训练目标与分数语义不同  
- 向量召回（bi-encoder）常用对比学习：拉近正样本、推远负样本。  
- Rerank（cross-encoder/生成式）常直接学习“相关/不相关”判别。  
- 生成式 rerank（如 yes/no）常把最终分数映射到 `0~1`，便于阈值过滤与融合。  

6. 常见失败模式不同  
- 向量召回：语义相近但事实错误（数字、时态、否定、版本号）容易混入。  
- Rerank：若首轮候选里没有真阳性，重排无法“凭空召回”；另外受截断长度与推理成本约束。  

**Qwen3 Rerank 实现（生成式 yes/no 打分）**

1. 构造输入模板  
- 将 `Instruct + Query + Document` 组装成统一提示词，让模型回答“是否相关（yes/no）”。  

2. 代码里确实就是这样做前向打分  

   `Qwen3-Embedding/examples/qwen3_reranker_transformers.py` 中的核心代码：

   ```python
   batch_scores = self.lm(**inputs).logits[:, -1, :]
   true_vector = batch_scores[:, self.token_true_id]
   false_vector = batch_scores[:, self.token_false_id]
   batch_scores = torch.stack([false_vector, true_vector], dim=1)
   batch_scores = torch.nn.functional.log_softmax(batch_scores, dim=1)
   scores = batch_scores[:, 1].exp().tolist()
   ```

   `Qwen3-Embedding/README.md` 里也有同样的示例实现：

   ```python
   batch_scores = model(**inputs).logits[:, -1, :]
   ```

3. `model(**inputs).logits` 到底是什么  
- 对一批 `query + document` 输入做一次前向传播，不让模型长文本生成，只拿“下一 token 预测分布”。  
- 输出 `logits` 的形状通常是 `[batch, seq_len, vocab_size]`。  
  - `batch`：这一批一起算了多少组 `(query, doc)`。  
  - `seq_len`：每组输入被分词后有多少个 token。  
  - `vocab_size`：词表大小，也就是模型对“下一个 token 可以是什么”会给多少个候选 token 打分。  

4. 为什么取 `logits[:, -1, :]`  
- `:` 表示保留这一维的全部内容。  
- `-1` 表示“最后一个位置”。  
- 所以 `logits[:, -1, :]` 的意思是：
  - 对 batch 中每个样本，
  - 只取该样本最后一个输入位置，
  - 查看这个位置之后“下一个 token”在整个词表上的打分。  
- 取完以后，张量形状从 `[batch, seq_len, vocab_size]` 变成 `[batch, vocab_size]`。  

5. 为什么“最后一个位置”刚好能用来做 rerank  
- 输入被拼成：
  - system 指令：只能回答 `yes/no`
  - user 内容：`Instruct + Query + Document`
  - assistant 开头
- 到这里为止，模型还没真正生成答案。  
- 此时看“下一个 token 应该是什么”，其实就是在问模型：
  - 现在最应该输出 `yes`，还是 `no`？  
- 也就是说，这里不是让模型生成一整段解释，而是把 rerank 任务压缩成一个单步判别题。  

6. 只取 `yes/no` 两个 token 分数  
- `self.token_true_id` 对应 token `"yes"`。  
- `self.token_false_id` 对应 token `"no"`。  
- 代码：

  ```python
  true_vector = batch_scores[:, self.token_true_id]
  false_vector = batch_scores[:, self.token_false_id]
  ```

- 含义：从整个词表的打分里，只把 `"yes"` 和 `"no"` 这两个 token 的分数抠出来。  
- 这一步相当于把“相关性排序”转换成“yes/no 二分类判别”。  

7. 为什么后面要 `stack + log_softmax + exp`  
- 先把 `[logit_no, logit_yes]` 拼成一个二分类向量：

  ```python
  batch_scores = torch.stack([false_vector, true_vector], dim=1)
  ```

- 然后做 softmax 归一化，得到二者的相对概率。  
- 最终保留 `"yes"` 的概率作为相关性分数：

  ```python
  scores = batch_scores[:, 1].exp().tolist()
  ```

- 公式可理解为：
  `score = exp(logit_yes) / (exp(logit_yes) + exp(logit_no))`
- `score` 范围在 `0~1`，越大表示模型越倾向判断“这个 doc 与 query 相关”。  

8. 一个很小的直觉例子  
- 若某条样本最后一步打分里：
  - `logit_yes = 3.0`
  - `logit_no = 1.0`
- 那模型更倾向输出 `yes`，归一化后相关性分会比较高。  
- 若反过来：
  - `logit_yes = 0.5`
  - `logit_no = 2.0`
- 那模型更倾向输出 `no`，相关性分就比较低。  

9. 一句话总结  
- 向量召回是在比“query 向量像不像 doc 向量”。  
- Qwen3 这类生成式 rerank 是把 `query + doc` 一起喂进模型，然后直接看模型下一步更想输出 `yes` 还是 `no`，用这个倾向当作相关性分数。  

1. 若配置 `rerank_mdl`  
- 走 `rerank_by_model()`：  
  token 相似度 + rerank 模型相似度 + rank_feature 分。  

2. 若未配置 `rerank_mdl`  
- Infinity 引擎：直接使用底层 `_score`。  
- ES/OpenSearch：走本地 `rerank()`（token + vector 混合相似度）。

3. 权重控制  
- 接口参数 `vector_similarity_weight` 控制 token/vector 融合占比。  
- 代码里 token 权重是 `1 - vector_similarity_weight`。

#### 2.4.3 过滤、分页、返回结构

1. 相似度阈值  
- 用 `similarity_threshold` 做后过滤。  
- 特殊处理：若 `vector_similarity_weight <= 0`，阈值会降到 `0`（避免纯词项检索被误过滤）。

2. 分页机制  
- 先按较大的 `RERANK_LIMIT` 检索重排，再分页切片返回，保证分页稳定性。

3. 返回字段（核心）  
- `similarity/vector_similarity/term_similarity`  
- `content_with_weight`  
- `image_id`  
- `positions`  
- `doc_type_kwd`  
- `vector`（接口层通常会移除后返回前端）

#### 2.4.4 检索增强能力（可开关）

1. `rank_feature` 标签增强  
- 来自 `label_question()`，把标签相关性和 pagerank 合并进总分。  

2. `retrieval_by_children`  
- 子块命中后可聚合回母块（`mom_id`），提升上下文完整性。  

3. `retrieval_by_toc`  
- 基于目录结构二次补召回，适合长文档章节问答。  

4. `use_kg`  
- 可叠加 KG 检索结果到 chunk 列表首位。

#### 2.4.5 生产参数建议（RAGFlow）

1. 默认从 `vector_similarity_weight=0.3` 起步，逐步 A/B 调整。  
2. `similarity_threshold` 建议先低后高（如 `0.1~0.25` 区间试验）。  
3. 高频专有词场景可提升 token 权重；长自然语言问题可提升向量权重。  
4. 有预算优先上 rerank 模型，再调阈值，通常收益更稳定。  
5. 开启 `children` 聚合和 `toc` 增强前，先确认 chunk 的层级/目录字段质量。

#### 2.4.6 Dify Hybrid（对比视角）

结合 `dify-1.9.2` 源码（`api/core/rag/datasource/retrieval_service.py`、`api/core/rag/rerank/*`），Dify 的 Hybrid 可细化为：

1. 召回阶段（并发双路）  
- `RetrievalMethod.HYBRID_SEARCH` 会并发执行两路：  
  向量检索（`embedding_search`）+ 全文检索（`full_text_index_search`）
- 两路都使用同一个 `top_k` 作为各自召回上限。  
- 这一阶段不做“0.7/0.3”配比；配比发生在后续 `weighted_score` 重排。

2. 候选合并与去重  
- 两路结果先合并，再做 `_deduplicate_documents()`。  
- 对 Dify 内部文档按 `doc_id` 去重；若重复则保留分数更高的那条，而不是固定“保留向量路”。
- 若分数相等，不会替换（代码是严格 `<` 才替换），因此会保留先进入列表的那条；由于两路是并发写入，先后不保证固定为向量路或全文路。

3. 重排阶段（`reranking_mode` 二选一）  
- `weighted_score`：  
  `final = vector_weight * vector_score + keyword_weight * keyword_score`。  
  其中 `keyword_score` 来自候选集上的关键词相似度计算，`vector_score` 优先使用已有分数/或向量余弦。  
  默认常见值是 `0.7:0.3`（语义:关键词，来自前端 `DEFAULT_WEIGHTED_SCORE.other`）；  
- `reranking_model`：  
  调用外部/托管 rerank 模型返回相关性分，再排序。

4. 阈值过滤（`score_threshold`）  
- 向量召回阶段可先按阈值过滤一次（传给向量检索接口）。  
- 重排阶段还会再次按 `score_threshold` 过滤最终分数（weighted 或 rerank model）。

5. TopK 生效点
- 召回阶段：两路各取 `top_k`，合并前上限约 `2*top_k`。  

- 重排阶段：`DataPostProcessor.invoke(..., top_n=top_k)` 会在有重排 runner 时截断到前 `top_k`。  

- 实践建议：Hybrid 场景建议开启有效重排配置（`weighted_score` 或 `reranking_model`），这样最终条数与排序更可控。

  

在 Dify 1.9.2 里，hybrid_search 不是跨引擎混检，而是单引擎双路召回：

同一个向量后端同时做语义向量检索和全文检索，再合并去重并重排，所以单知识库不能直接配置成Elasticsearch + Milvus 并行。

若后端是Milvus，Hybrid 实际是 Milvus dense +Milvus sparse(BM25)；

这里要注意，Milvus 的文本检索并不只是标量过滤，它有 BM25 稀疏索引和打分，filter 只是附加约束。

Elasticsearch 的优势在于多字段加权和复杂DSL（如 multi_match、boost、bool 组合），但 Dify 默认 ES 适配实现较轻，只用了基础单字段 match



#### 2.4.7 QAnything Hybrid（对比视角）

QAnything 的混合检索可概括为：`ES(BM25) + Milvus(向量)` 先召回，再用 rerank 统一打分，最后做“两层过滤”。

1. 双路召回  
- 一路走 Milvus 向量检索（语义召回）。  
- 一路走 Elasticsearch 全文检索（BM25，关键词/专有词精确召回）。

2. 为什么不能直接合并分数  
- 向量相似度分数与 BM25 分数不在同一量纲，数值不可直接比较。  
- 直接用原始分数融合，容易出现“某一路天然占优”的偏置。

3. rerank 统一分数  
- 把两路候选合并后交给 rerank 模型重排。  
- 重排后分数统一到 `0~1` 区间，再做后续筛选和截断。

4. TopK 规则（QAnything 实际行为）  
- `TopK` 在 **两个阶段都生效**：召回阶段 + 最终返回阶段。  
- Milvus 路取 `k=top_k`，ES 路也取 `k=top_k`。  这是召回阶段的上限控制。  
- 两路合并去重后，候选上限通常接近 `2*top_k`（去重后会更少）。  
- rerank + 两层过滤后，最终再执行 `source_documents = source_documents[:top_k]`，只返回前 `top_k`。  
  这是最终返回阶段的上限控制。  
- 默认 `top_k=30`，接口限制 `top_k<=100`。

5. 第一层过滤：绝对阈值（0.28）  
- 常用规则：保留 `score >= 0.28` 的候选，先过滤低相关结果。  
- 这个 `0.28` 是实践经验值，本质是精确率/召回率折中点；可按业务再做离线标注和线上 A/B 微调。

6. 第二层过滤：相对差异阈值（常见 50%）  
- 以最高分候选为基准（`top_score = saved_docs[0].metadata['score']`），对后续候选逐个计算：  
  `relative_difference = (top_score - current_score) / top_score`  
- 判断规则：  
  `if relative_difference > 0.5: break`，否则保留该候选并继续。  
- 直观例子：若最高分是 `0.80`，当前候选是 `0.36`，则  
  `(0.80 - 0.36) / 0.80 = 0.55`，大于 `0.5`，在此处截断。  
- 触发前提：该逻辑在 `rerank` 开启且候选数 `>1` 时执行，且在第一层 `0.28` 阈值过滤之后执行。  
- 源码参考：`03_rag_and_retrieval/qanything_case_study/qanything_kernel/core/local_doc_qa.py` 中约 `523-546` 行（`saved_docs` 与 `relative_difference` 逻辑）。

### 2.5 后处理与优化（框架无关）

> 面试一句话：后处理不是“锦上添花”，而是把“召回结果”变成“可用答案证据”的质量闸门。

#### 2.5.1 查询侧优化（进入召回前）

1. 查询清洗：去噪、拼写修正、术语标准化（中英文缩写统一）。  
2. 查询改写：同义改写、指代消解、补全上下文。  
3. 查询扩展：Multi-Query / HyDE / 子问题分解，提升召回覆盖率。  
4. 路由分流：按 query 类型动态走 BM25 优先、向量优先或混合检索。  

#### 2.5.2 召回后第一层过滤（轻量规则）

1. 相似度阈值：过滤低相关候选（绝对阈值）。  
2. 相对阈值：与最高分做差异过滤（防止长尾噪声混入）。  
3. 元数据过滤：按来源、时间、权限、文档类型做二次筛选。  
4. 去重与聚合：同 `doc_id/chunk_id` 去重，必要时做父子块聚合。  

#### 2.5.3 第二层精排（Rerank）

1. 核心做法：先粗召回 `topN`，再用 reranker 精排取 `topK`。  
2. 常见模型：Cross-Encoder（BGE/Jina 等）或生成式 rerank（Qwen3 yes/no）。  
3. 目标：提升 `Precision@TopK`，特别是数字、否定、专有词场景。  
4. 注意：rerank 不能“凭空召回”，首轮 recall 不够会限制上限。  

#### 2.5.4 上下文整理（给生成模型前）

1. 去冗余：MMR/相似片段去重，避免重复证据挤占上下文。  
2. 顺序重排：按章节或语义顺序重排（LongContext Reorder 思路）。  
3. 邻域扩展：命中块补前后窗口，增强答案完整性。  
4. 父子回填：子块命中后回填父块，减少“只答半句”。  

#### 2.5.5 答案侧后处理（生成后）

1. 证据绑定：答案句子绑定来源 chunk 与页码/坐标。  
2. 低置信度兜底：证据不足时拒答或要求补充问题。  
3. 结构化输出：统一 JSON/模板格式，便于前端与审计。  
4. 安全合规：敏感词、越权信息、PII 脱敏过滤。  

#### 2.5.6 评估与调参闭环（生产必做）

1. 离线指标：`Recall@K`、`MRR`、`NDCG`、Answer-F1、引用命中率。  
2. 在线指标：首答命中、用户追问率、人工纠错率、响应时延。  
3. 调参顺序建议：先召回覆盖，再重排，再阈值，再上下文组织。  

#### 2.5.7 主流框架/系统落地速记（不是只有 LlamaIndex）

1. LlamaIndex  
- `NodePostprocessor` 链：`SimilarityPostprocessor`、`LongContextReorder`、`CohereRerank` 等。  

2. LangChain  
- `Retriever + DocumentCompressor + Reranker` 组合（如 ContextualCompressionRetriever）。  

3. Haystack  
- Pipeline 串联 `Retriever -> Ranker -> Reader/Generator`，组件化替换方便。  

4. Dify  
- Hybrid 双路召回后，走 `weighted_score` 或 `reranking_model`，再做阈值与 topK 截断。  

5. RAGFlow  
- 混合召回后走本地/模型重排，叠加 similarity 阈值、children 聚合、TOC/KG 增强。  

6. QAnything  
- ES + Milvus 双路召回，rerank 统一分数，再做两层过滤（绝对阈值 + 相对差异阈值）。  

### 2.6 查询增强

#### 2.6.1 HyDE (Hypothetical Document Embeddings)

```python
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine

# HyDE 查询改写
hyde = HyDEQueryTransform(
    include_original=True,  # 保留原始查询
    llm=llm
)

# 包装查询引擎
hyde_engine = TransformQueryEngine(
    query_engine=index.as_query_engine(),
    query_transform=hyde
)

# 使用
response = hyde_engine.query("员工请假要提前多久申请?")
```

#### 2.6.2 查询扩展 (Query Expansion)

```python
from llama_index.core.indices.query.query_transform import QueryExpansion

# 查询扩展
expansion = QueryExpansion(
    llm=llm,
    expand_to_n=3  # 扩展为 3 个相关查询
)

# 使用
expanded_queries = expansion.expand(query)
```

### 2.7 Prompt 工程

#### 2.7.1 自定义 Prompt 模板

```python
from llama_index.core import PromptTemplate

# 问答模板
qa_template = PromptTemplate(
    """你是一个专业的助手。请根据以下上下文回答问题。

上下文:
{context_str}

问题: {query_str}

要求:
1. 只使用上下文中的信息回答
2. 如果上下文中没有相关信息,请明确说明
3. 回答要简洁、准确
4. 分点列出关键信息

答案:"""
)

# 使用模板
query_engine = index.as_query_engine(
    text_qa_template=qa_template
)
```

#### 2.7.2 不同场景的模板

```python
# 总结模板
summary_template = PromptTemplate(
    """请总结以下内容的要点:

{context_str}

总结要求:
1. 提炼 3-5 个核心要点
2. 每个要点不超过 50 字
3. 保持逻辑清晰

总结:"""
)

# 对比模板
compare_template = PromptTemplate(
    """请对比以下内容的异同:

{context_str}

对比维度:
1. 主要功能
2. 适用场景
3. 优缺点

对比分析:"""
)
```

---

## 4. RAGAS 评估体系

> **详细内容请参考**: [`ragas工程实践指南.md`](./ragas工程实践指南.md)

### 4.1 核心评估指标

RAGAS 评估分为两个阶段：

**检索阶段指标**:
- `context_precision`: 检索精准率（检索结果中相关文档的占比）
- `context_recall`: 检索召回率（标准答案所需信息被覆盖的比例）

**生成阶段指标**:
- `faithfulness`: 忠实度（答案是否基于检索内容）
- `answer_correctness`: 答案正确性（事实准确性）
- `answer_relevancy`: 答案相关性（是否切题）
- `semantic_similarity`: 语义相似度（与标准答案的接近程度）

### 4.2 评估流程

```
建立评测集 → 分阶段评估 → 结果分析 → 优化迭代
```

**推荐评测集**:

- Smoke Set (20条): PR前快速验证
- Regression Set (100条): 每日构建
- Release Set (500条): 版本发布前

---

## 5. 混合检索策略

### 5.1 混合检索原理

根据 `03_rag_and_retrieval/qanything_case_study/docs/混合检索实现原理详解.md`,混合检索结合了向量检索和全文检索的优势:

```
向量检索 (Dense)          全文检索 (Sparse)
     ↓                          ↓
语义理解能力强            精确匹配能力强
概念相似性匹配            关键词精确匹配
同义词效果好              专有名词、数字
     ↓                          ↓
     └──────────┬───────────────┘
                ↓
          结果融合与去重
                ↓
          重排序与过滤
                ↓
          最终检索结果
```

### 5.2 优势对比

| 检索类型 | 擅长场景 | 不擅长场景 | 示例 |
|----------|----------|------------|------|
| **向量检索** | 概念查询、同义词 | 精确匹配、专有名词 | "提高效率" → "优化性能" |
| **全文检索** | 精确匹配、专有名词 | 同义词、概念理解 | "Python 3.8" → 精确匹配 |
| **混合检索** | 综合场景 | - | 结合两者优势 |

### 5.3 实现示例

```python
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever

# 向量检索器
vector_retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=10,
    vector_store_query_mode="default"
)

# BM25 检索器
bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=10
)

# 混合检索器 (倒数重排序融合)
hybrid_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=10,
    num_queries=1,
    mode="reciprocal_rerank",  # 使用倒数重排序
    alpha=0.5  # 向量检索权重
)

# 使用
nodes = hybrid_retriever.retrieve("如何使用 Python 3.8?")
```

### 5.4 融合策略详解

混合检索的核心问题：**如何融合 BM25 和向量检索的结果？**

有两种主流策略：**RRF（倒数排名融合）** 和 **加权融合**

#### 5.4.1 RRF (Reciprocal Rank Fusion) - 基于排名的融合

**核心原理**：只看排名位置，不看原始分数大小

```python
"""
RRF 公式：
score(doc) = Σ (1 / (k + rank(doc)))

其中：
- k: 平滑常数（通常取 60）
- rank(doc): 文档在某个检索器中的排名（从1开始）
"""

# 示例：两个检索器的结果
vector_results = [
    {"doc_id": "A", "rank": 1, "score": 0.95},
    {"doc_id": "B", "rank": 2, "score": 0.88},
    {"doc_id": "C", "rank": 3, "score": 0.82},
]

bm25_results = [
    {"doc_id": "B", "rank": 1, "score": 25.3},
    {"doc_id": "D", "rank": 2, "score": 18.7},
    {"doc_id": "A", "rank": 3, "score": 15.2},
]

# RRF 计算（k=60）
def rrf_fusion(vector_results, bm25_results, k=60):
    scores = {}

    # 向量检索贡献
    for result in vector_results:
        doc_id = result["doc_id"]
        rank = result["rank"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    # BM25 检索贡献
    for result in bm25_results:
        doc_id = result["doc_id"]
        rank = result["rank"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    # 按分数排序
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs

# 结果
final_ranking = rrf_fusion(vector_results, bm25_results)
"""
计算过程：
文档 A: 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323
文档 B: 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325  ← 最高
文档 C: 1/(60+3) + 0         = 0.0159 + 0      = 0.0159
文档 D: 0         + 1/(60+2) = 0      + 0.0161 = 0.0161

最终排序: B > A > D > C
"""
```

**LlamaIndex 实现**：

```python
from llama_index.core.retrievers import QueryFusionRetriever

# RRF 模式
rrf_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=10,
    mode="reciprocal_rerank",  # RRF 模式
    num_queries=1
    # 注意：alpha 参数在 RRF 模式下不起作用（因为只用排名，不用分数）
)

# 注意：mode="reciprocal_rerank" 就是 RRF
```

**RRF 优缺点**：

| 维度 | 说明 |
|------|------|
| **优点** | ✅ **稳定性强**：不依赖分数的绝对大小，只看相对排名<br>✅ **抗噪性好**：异常高分不会过度影响结果<br>✅ **几乎不用调参**：k=60 是经验值，适用于大多数场景<br>✅ **跨检索器友好**：不同检索器的分数范围差异不影响结果 |
| **缺点** | ❌ **信息损失**：忽略了原始分数的强弱信息<br>❌ **个性化空间小**：无法根据业务调整权重<br>❌ **平局处理**：相同排名的文档无法区分 |
| **适用场景** | • 通用场景、冷启动<br>• 不确定哪种检索器更重要<br>• 不同检索器分数范围差异大 |

#### 5.4.2 加权融合 (Weighted Fusion) - 基于分数的融合

**核心原理**：直接融合分数，但需要先归一化

```python
"""
加权融合公式：
score(doc) = α × normalize(vector_score) + (1-α) × normalize(bm25_score)

其中：
- α: 向量检索权重 (0-1)
- normalize(): 分数归一化函数
"""

# 问题：BM25 分数和向量分数不可比！
vector_score = 0.95   # 范围 [0, 1]
bm25_score = 25.3     # 范围 [0, +∞)

# 解决方案：分数归一化
def normalize_scores(scores, method="minmax"):
    """分数归一化"""
    import numpy as np

    scores = np.array(scores)

    if method == "minmax":
        # Min-Max 归一化：[0, 1]
        return (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)

    elif method == "zscore":
        # Z-Score 标准化
        return (scores - scores.mean()) / (scores.std() + 1e-9)

    elif method == "softmax":
        # Softmax 归一化：和为1
        exp_scores = np.exp(scores - scores.max())
        return exp_scores / exp_scores.sum()

# 加权融合实现
def weighted_fusion(vector_results, bm25_results, alpha=0.7, normalize_method="minmax"):
    """
    加权融合
    alpha: 向量检索权重（0-1），bm25权重 = 1-alpha
    """

    # 1. 提取分数
    vector_scores = {r["doc_id"]: r["score"] for r in vector_results}
    bm25_scores = {r["doc_id"]: r["score"] for r in bm25_results}

    # 2. 归一化
    if normalize_method == "minmax":
        # 向量分数归一化
        v_scores = list(vector_scores.values())
        v_normalized = normalize_scores(v_scores, "minmax")
        for i, doc_id in enumerate(vector_scores.keys()):
            vector_scores[doc_id] = v_normalized[i]

        # BM25分数归一化
        b_scores = list(bm25_scores.values())
        b_normalized = normalize_scores(b_scores, "minmax")
        for i, doc_id in enumerate(bm25_scores.keys()):
            bm25_scores[doc_id] = b_normalized[i]

    # 3. 加权融合
    all_docs = set(vector_scores.keys()) | set(bm25_scores.keys())
    final_scores = {}

    for doc_id in all_docs:
        v_score = vector_scores.get(doc_id, 0)
        b_score = bm25_scores.get(doc_id, 0)

        # 加权求和
        final_scores[doc_id] = alpha * v_score + (1 - alpha) * b_score

    # 4. 排序
    sorted_docs = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs
```

**LlamaIndex 实现**：

```python
from llama_index.core.retrievers import QueryFusionRetriever

# 加权融合模式
weighted_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=10,
    mode="distillation",  # 加权融合模式
    alpha=0.7,  # 向量检索权重 70%，BM25权重 30%
    num_queries=1
)

# 注意：
# - mode="distillation" 或 "simple" 使用加权融合
# - alpha 参数控制向量检索权重
# - LlamaIndex 会自动处理分数归一化
```

**加权融合优缺点**：

| 维度 | 说明 |
|------|------|
| **优点** | ✅ **可控性强**：可以根据业务需求精细调整权重<br>✅ **利用分数信息**：保留了分数的强弱差异<br>✅ **个性化空间大**：不同场景可以使用不同的 alpha<br>✅ **可解释性好**：权重有明确的业务含义 |
| **缺点** | ❌ **依赖归一化**：归一化方法不当会严重影响结果<br>❌ **需要调参**：alpha 需要根据数据分布调整<br>❌ **数据敏感性**：数据分布变化可能导致权重失效<br>❌ **跨检索器敏感**：不同检索器分数范围差异大时难以处理 |
| **适用场景** | • 明确知道哪种检索器更重要<br>• 需要精细控制检索行为<br>• 数据分布相对稳定 |

#### 5.4.3 两种策略对比与选择

| 对比维度 | RRF (倒数排名融合) | 加权融合 |
|---------|-------------------|---------|
| **融合对象** | 排名（rank） | 分数（score） |
| **是否需要归一化** | ❌ 不需要 | ✅ 必须需要 |
| **调参难度** | 低（k=60 通用） | 高（alpha 需调优） |
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **可控性** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **信息利用率** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **跨检索器兼容性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **推荐场景** | 通用、冷启动 | 专业领域、精细控制 |

**决策树：选择哪种融合策略？**

```python
def choose_fusion_strategy(context):
    """选择融合策略"""

    # 1. 是否知道哪种检索器更重要？
    if not context.get("know_retriever_importance"):
        return "RRF"  # 不知道 → 用 RRF

    # 2. 数据分布是否稳定？
    if not context.get("stable_distribution"):
        return "RRF"  # 不稳定 → 用 RRF

    # 3. 是否需要精细控制？
    if context.get("need_fine_control"):
        return "Weighted"  # 需要 → 加权融合

    # 4. 是否有领域专家知识？
    if context.get("domain_expert_knowledge"):
        return "Weighted"  # 有 → 加权融合

    # 5. 默认
    return "RRF"

# 场景示例
scenarios = {
    "通用企业知识库": {
        "know_retriever_importance": False,
        "recommendation": "RRF"
    },

    "医疗问答（精确词重要）": {
        "know_retriever_importance": True,  # BM25更重要
        "need_fine_control": True,
        "recommendation": "Weighted (alpha=0.3)"  # BM25权重70%
    },

    "技术文档检索（语义重要）": {
        "know_retriever_importance": True,  # 向量更重要
        "need_fine_control": True,
        "recommendation": "Weighted (alpha=0.8)"  # 向量权重80%
    },

    "电商搜索（均衡）": {
        "know_retriever_importance": False,
        "recommendation": "RRF"
    }
}
```

#### 5.4.4 权重设置最佳实践

**1. RRF 的 k 值设置**

```python
# k 值的影响
"""
k 值越小：排名靠前的文档优势越大
k 值越大：排名差异的影响被削弱

经验值：k=60 是学术界和工业界的通用选择
"""

# 不同 k 值对比示例
"""
文档 A: rank 1 in vector, rank 5 in BM25
文档 B: rank 3 in vector, rank 1 in BM25

k= 10: A=0.1083, B=0.1333, Winner=B
k= 30: A=0.0583, B=0.0625, Winner=B
k= 60: A=0.0323, B=0.0325, Winner=B  ← 推荐
k=100: A=0.0198, B=0.0198, Winner=A  (几乎相同)
"""

# 建议：
# - k=60: 通用场景（推荐）
# - k=40: 强调排名靠前的文档
# - k=80: 削弱排名差异，更均衡
```

**2. 加权融合的 alpha 值设置**

```python
# alpha 值的影响
"""
alpha: 向量检索权重
1-alpha: BM25 检索权重

alpha 越大：语义匹配越重要
alpha 越小：关键词匹配越重要
"""

# 不同场景的推荐 alpha 值
ALPHA_RECOMMENDATIONS = {
    # 场景1: 语义理解重要（概念查询、同义词多）
    "概念查询": {
        "alpha": 0.8,  # 向量 80%, BM25 20%
        "example": "如何提高系统性能？",
        "reason": "需要理解'提高'='优化'等语义"
    },

    # 场景2: 精确词重要（专有名词、版本号）
    "精确查询": {
        "alpha": 0.3,  # 向量 30%, BM25 70%
        "example": "Python 3.8 安装教程",
        "reason": "必须精确匹配'3.8'"
    },

    # 场景3: 均衡场景
    "通用查询": {
        "alpha": 0.5,  # 向量 50%, BM25 50%
        "example": "Python 异常处理",
        "reason": "语义和关键词同等重要"
    },

    # 场景4: 专业术语（医疗、法律）
    "专业领域": {
        "alpha": 0.4,  # 向量 40%, BM25 60%
        "example": "高血压治疗方案",
        "reason": "专业术语必须精确匹配"
    },

    # 场景5: 代码搜索
    "代码检索": {
        "alpha": 0.6,  # 向量 60%, BM25 40%
        "example": "如何实现快速排序？",
        "reason": "代码语义和关键词都需要"
    }
}

# 动态 alpha
def dynamic_alpha(query):
    """根据查询特征动态调整 alpha"""

    # 1. 检测是否包含版本号、数字
    if re.search(r'\d+\.\d+|\d{4}', query):
        return 0.3  # 精确匹配重要

    # 2. 检测是否是概念性查询
    concept_words = ["如何", "什么是", "原理", "为什么"]
    if any(word in query for word in concept_words):
        return 0.7  # 语义理解重要

    # 3. 检测是否包含专业术语
    if contains_technical_terms(query):
        return 0.4  # 精确词重要

    # 4. 默认均衡
    return 0.5
```

**3. 实战配置模板**

```python
# 模板1: RRF 通用配置（推荐起步）
rrf_config = {
    "mode": "reciprocal_rerank",
    "k": 60,
    "vector_top_k": 20,
    "bm25_top_k": 10,
    "final_top_k": 15
}

# 模板2: 加权融合 - 语义优先
semantic_priority_config = {
    "mode": "distillation",
    "alpha": 0.8,  # 向量 80%
    "normalize": "minmax",
    "vector_top_k": 15,
    "bm25_top_k": 5,
    "final_top_k": 10
}

# 模板3: 加权融合 - 精确词优先
keyword_priority_config = {
    "mode": "distillation",
    "alpha": 0.3,  # BM25 70%
    "normalize": "minmax",
    "vector_top_k": 5,
    "bm25_top_k": 15,
    "final_top_k": 10
}

# 模板4: 自适应混合（生产推荐）
adaptive_config = {
    "mode": "adaptive",  # 根据查询自动选择
    "rrf_k": 60,
    "default_alpha": 0.5,
    "dynamic_alpha": True,
    "vector_top_k": 20,
    "bm25_top_k": 10,
    "final_top_k": 15
}
```

#### 5.4.5 实战建议

**新手起步**:
```python
# 1. 先用 RRF，不用调参
retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    mode="reciprocal_rerank",  # RRF
    similarity_top_k=15
)
```

**进阶优化**:
```python
# 2. 评估 RRF 效果
scores = evaluate_retrieval(retriever, test_set)

# 3. 如果效果不理想，尝试加权融合
# 3.1 分析查询类型分布
query_types = analyze_query_types(test_queries)

# 3.2 根据分布选择 alpha
if query_types["concept"] > 0.6:
    alpha = 0.7  # 语义重要
elif query_types["exact"] > 0.6:
    alpha = 0.3  # 精确词重要
else:
    alpha = 0.5  # 均衡

# 3.3 使用加权融合
retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    mode="distillation",
    alpha=alpha,
    similarity_top_k=15
)
```

**生产部署**:
```python
# 4. 实现自适应策略
class AdaptiveHybridRetriever:
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query):
        # 分析查询特征
        query_type = self.classify_query(query)

        # 选择策略
        if query_type == "ambiguous":
            # 不确定 → RRF
            return self.rrf_retrieve(query)
        else:
            # 确定 → 加权融合
            alpha = self.get_alpha(query_type)
            return self.weighted_retrieve(query, alpha)

    def classify_query(self, query):
        """查询分类"""
        if re.search(r'\d+\.\d+', query):
            return "exact"
        elif any(w in query for w in ["如何", "为什么"]):
            return "concept"
        else:
            return "ambiguous"

    def get_alpha(self, query_type):
        """获取 alpha"""
        return {
            "exact": 0.3,
            "concept": 0.7,
            "ambiguous": 0.5
        }.get(query_type, 0.5)
```

**总结**:
- 🚀 **冷启动**: 用 RRF (k=60)
- 🎯 **有明确偏好**: 用加权融合，alpha 根据场景调整
- 🔄 **复杂场景**: 实现自适应策略
- 📊 **持续优化**: 用 RAGAS 评估，A/B 测试验证

### 5.5 混合检索最佳实践

```python
# 实践建议
BEST_PRACTICES = {
    "检索数量": {
        "vector_top_k": 20,    # 向量检索可以多一些
        "bm25_top_k": 10,      # 全文检索通常较少
        "final_top_k": 15      # 最终返回数量
    },

    "权重配置": {
        "vector_weight": 0.7,   # 向量检索权重
        "keyword_weight": 0.3   # 关键词权重
    },

    "去重策略": {
        "method": "doc_id",     # 按文档 ID 去重
        "priority": "vector"    # 向量检索优先
    },

    "性能优化": {
        "parallel": True,       # 并行检索
        "cache": True,          # 启用缓存
        "timeout": 5.0          # 超时设置
    }
}
```

---

## 6. 工程化最佳实践

### 6.1 系统架构设计

```
┌─────────────────────────────────────────────────────┐
│              生产级 RAG 系统架构                     │
└─────────────────────────────────────────────────────┘

                    负载均衡
                        ↓
    ┌───────────────────┴───────────────────┐
    ↓                                       ↓
┌─────────┐                             ┌─────────┐
│ API 网关 │                             │ API 网关 │
└─────────┘                             └─────────┘
    ↓                                       ↓
┌──────────────────────────────────────────────────┐
│              应用服务层                           │
│  • 请求验证                                       │
│  • 查询预处理                                     │
│  • 结果后处理                                     │
└──────────────────────────────────────────────────┘
    ↓                    ↓                    ↓
┌──────────┐       ┌──────────┐        ┌──────────┐
│ 检索服务  │       │ 生成服务  │        │ 评估服务  │
└──────────┘       └──────────┘        └──────────┘
    ↓                    ↓                    ↓
┌──────────┐       ┌──────────┐        ┌──────────┐
│ Milvus   │       │ LLM API  │        │ 监控系统  │
│ ES       │       │          │        │ 日志系统  │
│ Redis    │       │          │        │          │
└──────────┘       └──────────┘        └──────────┘
```

### 6.2 性能优化清单

#### 6.2.1 检索优化

```python
# 1. 向量检索优化
retriever = index.as_retriever(
    similarity_top_k=5,           # 控制 top_k
    vector_store_query_mode="mmr", # 使用 MMR
    show_progress=False           # 关闭进度条
)

# 2. 缓存策略
from llama_index.core import StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore

# 文档缓存
docstore = SimpleDocumentStore()
storage_context = StorageContext.from_defaults(docstore=docstore)

# 查询缓存
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_retrieve(query_hash):
    return retriever.retrieve(query)
```

#### 6.2.2 生成优化

```python
# 1. Prompt 长度控制
def truncate_context(context, max_tokens=4000):
    """截断上下文到指定长度"""
    tokens = tokenizer.encode(context)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        return tokenizer.decode(tokens)
    return context

# 2. 批量处理
def batch_process(queries, batch_size=10):
    """批量处理查询"""
    results = []
    for i in range(0, len(queries), batch_size):
        batch = queries[i:i+batch_size]
        batch_results = process_batch(batch)
        results.extend(batch_results)
    return results
```

#### 

### 6.4 成本优化

#### 6.4.1 Token 优化

1. 智能切片  按段落切分

2. 动态 top_k  根据查询复杂度动态调整 top_k

#### 6.4.2 模型选择策略

根据查询复杂度选择模型

简单问题用小模型

中等复杂度用中等模型

复杂问题用大模型

---

## 7. 学习路径与资源

### 7.2 本仓库资源索引

```
03_rag_and_retrieval/llamaindex_and_ragas/
├── docs/                              # 文档目录
│   ├── RAG系统学习指南.md             # 本文档 (总览)
│   ├── llamaindex学习文档.md          # LlamaIndex 详细指南
│   └── ragas工程实践指南.md           # RAGAS 评估指南
│
├── code/                              # 代码目录
│   ├── llamaindex/                    # LlamaIndex 示例
│   │   ├── llamaindex_01_quickstart.ipynb
│   │   ├── llamaindex_03_node_basics.ipynb
│   │   ├── llamaindex_04_custom_loader.ipynb
│   │   ├── llamaindex_05_chunking_strategies.ipynb
│   │   ├── llamaindex_06_similarity_postprocessor.py
│   │   ├── llamaindex_07_prompt_template.ipynb
│   │   ├── llamaindex_08_hyde_query_transform.ipynb
│   │   ├── llamaindex_09_text2sql_demo.ipynb
│   │   └── llamaindex_10_es_hybrid_retrieval.ipynb
│   │
│   └── ragas/                         # RAGAS 评估示例
│       ├── ragas_smoke_test.py
│       ├── ragas_answer_quality_demo.py
│       ├── ragas_retrieval_metrics_demo.py
│       ├── ragas_full_metrics_demo.py
│       ├── ragas_chinese_prompt_tuning.py
│       └── ragas_chinese_prompts.py
│
└── 03_rag_and_retrieval/qanything_case_study/                  # QAnything 实战项目
    └── docs/
        ├── 混合检索实现原理详解.md
        └── 重排序两层过滤策略详解.md
```

### 7.3 外部学习资源

#### 7.3.1 官方文档

- **LlamaIndex**: https://docs.llamaindex.ai/
- **RAGAS**: https://docs.ragas.io/
- **Milvus**: https://milvus.io/docs
- **Elasticsearch**: https://www.elastic.co/guide/

#### 7.3.2 推荐论文

1. **RAG 基础**
   - Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*  
     https://arxiv.org/abs/2005.11401
   - Karpukhin et al. (2020), *Dense Passage Retrieval for Open-Domain Question Answering*  
     https://arxiv.org/abs/2004.04906

2. **检索 + 推理交错**
   - Trivedi et al. (2022), *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions (IRCoT)*  
     https://arxiv.org/abs/2212.10509
   - Khattab et al. (2022), *Demonstrate-Search-Predict: Composing retrieval and language models for knowledge-intensive NLP (DSP)*  
     https://arxiv.org/abs/2212.14024

3. **工具调用 / Agent 能力**
   - Yao et al. (2022), *ReAct: Synergizing Reasoning and Acting in Language Models*  
     https://arxiv.org/abs/2210.03629
   - Schick et al. (2023), *Toolformer: Language Models Can Teach Themselves to Use Tools*  
     https://arxiv.org/abs/2302.04761
   - Karpas et al. (2022), *MRKL Systems: A modular, neuro-symbolic architecture that combines large language models, external knowledge sources and discrete reasoning*  
     https://arxiv.org/abs/2205.00445

4. **Self-Reflective / Agentic RAG**
   - Asai et al. (2023), *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*  
     https://arxiv.org/abs/2310.11511

#### 7.3.3 开源项目

1. **QAnything**: https://github.com/netease-youdao/QAnything
2. **RAGFlow**: https://github.com/infiniflow/ragflow
3. **Dify**: https://github.com/langgenius/dify

### 7.4 实践项目建议

#### 7.4.2 进阶项目: 企业知识库

```python
# 项目目标
"""
搭建一个企业级知识库系统:
1. 多租户支持
2. 权限管理
3. 混合检索
4. 实时更新
5. 监控告警
"""
# 技术栈
tech_stack = {
    "框架": "LlamaIndex + FastAPI",
    "向量库": "Milvus",
    "全文检索": "Elasticsearch",
    "LLM": "私有化部署大模型",
    "缓存": "Redis",
    "监控": "Prometheus + Grafana"
}
# 系统要求
system_requirements = {
    "并发": "> 100 QPS",
    "延迟": "p95 < 1s",
    "可用性": "> 99.9%",
    "数据量": "> 100万文档"
}
```

---

## 8. RAG vs 微调选择指南

### 8.1 核心判断标准

在选择 RAG 还是微调时，遵循以下核心原则：

```
┌─────────────────────────────────────────────────────┐
│         RAG vs 微调 选择决策树                      │
└─────────────────────────────────────────────────────┘

                    你的需求是什么？
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
   改知识/内容                          改行为/风格
        ↓                                  ↓
   使用 RAG ✓                          使用微调 ✓
        ↓                                  ↓
   特点:                               特点:
   • 知识更新频繁                       • 固定的输出风格
   • 需要引用来源                       • 特定格式要求
   • 降低幻觉                           • 决策流程
   • 快速迭代                           • 领域深度理解
```

### 8.2 详细对比分析

| 维度 | RAG | 微调 |
|------|-----|------|
| **核心目标** | 改变知识内容 | 改变行为模式 |
| **适用场景** | • 知识频繁更新<br>• 需要引用来源<br>• 降低幻觉<br>• 快速迭代 | • 固定输出风格<br>• 特定格式要求<br>• 决策流程<br>• 领域深度理解 |
| **知识更新** | ✅ 实时更新知识库 | ❌ 需要重新训练 |
| **成本** | 💰 低（维护知识库） | 💰💰💰 高（训练+推理） |
| **响应速度** | ⚡⚡ 稍慢（检索+生成） | ⚡⚡⚡ 快（直接生成） |
| **可解释性** | ✅ 可引用来源 | ❌ 黑盒输出 |
| **准确性** | 📊 依赖检索质量 | 📊 依赖训练数据 |
| **适用领域** | 🌐 通用知识问答 | 🎯 垂直领域专家 |

### 8.3 典型场景分析

#### 场景 1: 企业知识库客服 → **RAG**

```python
需求分析:
- ✅ 知识频繁更新（产品、政策变化）
- ✅ 需要引用来源（可追溯）
- ✅ 降低幻觉（准确性要求高）
- ✅ 快速迭代（业务变化快）

推荐方案: RAG
理由: 知识更新频繁，需要可追溯的答案
```

**示例:**
```
用户: "最新的请假制度是什么？"
RAG: "根据《员工手册 v2.3》（2024年3月更新），事假需要提前3天申请..."
      ↑ 引用来源，可追溯
```

#### 场景 2: 医疗诊断助手 → **微调**

```python
需求分析:
- ✅ 固定的诊断流程
- ✅ 专业的医学术语
- ✅ 严谨的决策逻辑
- ✅ 深度医学知识
推荐方案: 微调 + RAG（混合）
理由: 需要专业的诊断行为，同时需要最新的医学文献
```

**示例:**
```
输入: 患者症状描述
微调模型: 按照标准的诊断流程，自动进行症状分析、鉴别诊断
          ↑ 固定的决策行为
```

#### 场景 3: 法律文书生成 → **微调**

```python
需求分析:
- ✅ 固定的文书格式
- ✅ 严谨的法律术语
- ✅ 规范的行文风格
- ✅ 决策流程（法条引用逻辑）

推荐方案: 微调
理由: 输出格式和风格是固定的，不需要频繁更新
```

**示例:**
```
输入: 案件信息
微调模型: 自动生成符合法律规范的起诉书、答辩状等
          ↑ 固定的格式和风格
```

#### 场景 4: 技术文档问答 → **RAG**

```python
需求分析:
- ✅ 技术文档频繁更新
- ✅ 需要精确的代码示例
- ✅ 可追溯的文档来源
- ✅ 降低幻觉（代码准确性）

推荐方案: RAG
理由: 技术文档更新频繁，需要引用官方文档
```

**示例:**
```
用户: "Python 3.12 的新特性有哪些？"
RAG: "根据 Python 3.12 官方文档，主要新特性包括：
      1. 改进的错误消息（PEP 678）
      2. ...（引用官方文档）"
      ↑ 引用官方文档，可追溯
```

#### 场景 5: 个性化写作助手 → **微调**

```python
需求分析:
- ✅ 特定的写作风格
- ✅ 固定的语言习惯
- ✅ 个性化的表达方式
- ❌ 不需要频繁更新知识

推荐方案: 微调
理由: 学习用户的写作风格，生成符合个人习惯的内容
```

**示例:**
```
输入: "写一篇关于 AI 的文章"
微调模型: 按照用户习惯的文风、句式、用词生成文章
          ↑ 学习到的个性化风格
```

#### 场景 6: 电商产品推荐 → **RAG + 微调**

```python
需求分析:
- ✅ 产品信息频繁更新（RAG）
- ✅ 推荐策略固定（微调）
- ✅ 用户偏好学习（微调）
- ✅ 实时库存查询（RAG）

推荐方案: RAG + 微调
理由: 结合实时产品信息和个性化推荐策略
```

### 8.4 组合使用策略

在许多实际场景中，**RAG + 微调** 的组合效果最佳：

```
┌─────────────────────────────────────────────────────┐
│           RAG + 微调 组合架构                       │
└─────────────────────────────────────────────────────┘

                    用户查询
                        ↓
    ┌───────────────────┴──────────────────┐
    ↓                                       ↓
┌──────────┐                          ┌──────────┐
│ 微调模型  │                          │   RAG    │
│          │                          │          │
│ 作用:    │                          │ 作用:    │
│ • 理解意图│←───────知识补充─────────│ • 检索知识│
│ • 风格控制│                          │ • 更新事实│
│ • 决策流程│                          │ • 引用来源│
└──────────┘                          └──────────┘
    ↓                                       ↓
    └───────────────────┬───────────────────┘
                        ↓
                最终回答 (风格 + 知识)
```

**组合策略示例:**

```python
# 场景: 医疗咨询助手

# 1. 微调部分（行为）
class MedicalAssistant:
    """
    微调目标:
    - 学习标准的问诊流程
    - 掌握医学术语和表达方式
    - 理解诊断决策逻辑
    """

    def get_diagnosis_flow(self, symptoms):
        # 微调模型执行标准的问诊流程
        return self.fine_tuned_model(symptoms)

# 2. RAG 部分（知识）
class MedicalKnowledgeBase:
    """
    RAG 目标:
    - 提供最新的医学文献
    - 药物相互作用查询
    - 最新诊疗指南
    """

    def retrieve_medical_knowledge(self, query):
        # RAG 检索最新医学知识
        return self.rag_system.retrieve(query)

# 3. 组合使用
def medical_consultation(user_query):
    # Step 1: 微调模型理解意图并确定流程
    intent = fine_tuned_model.understand_intent(user_query)

    # Step 2: RAG 检索相关医学知识
    knowledge = rag_system.retrieve(intent.keywords)

    # Step 3: 微调模型基于知识生成专业回答
    response = fine_tuned_model.generate(
        intent=intent,
        knowledge=knowledge,
        style="professional_medical"  # 微调学到的风格
    )

    return response
```

### 8.5 决策流程图

```
开始决策
    ↓
问题 1: 知识是否需要频繁更新？
    ├─ 是 → 倾向 RAG
    └─ 否 → 继续
        ↓
    问题 2: 是否需要引用来源？
        ├─ 是 → 倾向 RAG
        └─ 否 → 继续
            ↓
        问题 3: 是否有固定的输出格式/风格？
            ├─ 是 → 倾向微调
            └─ 否 → 继续
                ↓
            问题 4: 是否需要深度领域理解？
                ├─ 是 → 倾向微调
                └─ 否 → 继续
                    ↓
                问题 5: 预算是否充足？
                    ├─ 是 → 考虑 RAG + 微调
                    └─ 否 → 优先 RAG
                        ↓
                    最终决策
```

### 8.6 成本效益分析

#### RAG 成本结构

```python
RAG_COSTS = {
    "初期投入": {
        "向量库搭建": "中",
        "知识库整理": "中-高",
        "Embedding 模型": "低"
    },
    "持续成本": {
        "知识库维护": "低-中",
        "向量存储": "中",
        "检索+生成": "按使用量计费"
    },
    "优势": [
        "知识更新成本低",
        "无需重新训练",
        "可解释性强"
    ]
}
```

#### 微调成本结构

```python
FINETUNING_COSTS = {
    "初期投入": {
        "数据准备": "高",
        "训练成本": "高",
        "验证测试": "中-高"
    },
    "持续成本": {
        "模型维护": "中",
        "知识更新": "高（需重新训练）",
        "推理成本": "固定"
    },
    "优势": [
        "响应速度快",
        "领域深度理解",
        "风格一致性好"
    ]
}
```

### 8.8 总结

**核心决策原则:**

> **改知识（且经常更新）→ RAG**
> **改行为（风格、格式、流程、决策习惯）→ 微调**
> **既需要专业知识，又需要专业行为 → RAG + 微调**

---

## 9. Agentic RAG - 智能体增强检索

### 9.1 为什么需要 Agentic RAG

普通 RAG 非常适合回答“从知识库里找到一段相关内容，再总结出来”的问题，但一旦任务变复杂，它会很快碰到上限。

**普通 RAG 的典型局限**:

- **一次检索不够**：复杂问题往往需要分几步补证据，而不是只查一次 `top_k`
- **无法主动发现缺口**：检索结果不完整时，普通 RAG 通常不会继续追问“我还缺什么信息”
- **难以处理异构数据源**：知识库、SQL、API、Web 搜索、代码执行往往要一起用
- **固定流程不够灵活**：对比分析、趋势判断、跨文档归纳、实时数据查询通常无法用固定流水线高质量解决

**一个直观例子**:

- 问题：`分析公司过去 3 年销售趋势并预测明年`
- 普通 RAG：可能只会检索几份销售报告，然后直接生成答案
- Agentic RAG：会先判断还需要哪些证据，再决定是否继续检索市场报告、调用数据库、调用预测 API，最后再综合回答

所以，`Agentic RAG` 出现的原因不是“普通 RAG 失效了”，而是为了处理那些**需要多步求证、多源取数、动态决策**的复杂任务。

### 9.2 什么是 Agentic RAG

> **Agentic RAG 是一种 RAG 架构范式：让 LLM 以智能体方式围绕“获取证据并验证证据”动态决策，而不是只执行预先写死的一次检索流程。**

**更准确地说**:

- 它不是一个单独算法
- 它也不是某个框架专属名词
- 它是一种把 `检索、工具调用、结果校验、再次检索、停止回答` 放入**Agent 执行循环**中的系统设计方式

**一句话定义**:

> **Agentic RAG = Retrieval-Augmented Generation + 基于中间结果动态决策的 Agent Loop**

**判断一个系统是否接近 Agentic RAG，重点看 4 点**:

1. **目标驱动**：系统会先围绕用户目标判断缺什么证据
2. **动态决策**：模型会根据当前结果决定下一步动作
3. **检索在循环中**：检索不是一次性动作，可以被反复触发
4. **证据导向收敛**：证据够了就停止，不够就补查或换工具

### 9.3 它不是什么：和普通 RAG / Workflow / Tool Calling / Multi-Agent 的区别

这部分非常关键。很多系统“看起来像 Agentic RAG”，但严格来说并不是。

#### 9.3.1 和普通 RAG 的区别

| 维度 | 普通 RAG | Agentic RAG |
|------|---------|------------|
| **控制方式** | 开发者预定义流程 | 模型基于中间证据动态决策 |
| **检索次数** | 单次或固定次数 | 可多轮、多跳、按需补充 |
| **任务处理** | 被动回答 | 主动补足缺失信息 |
| **典型形式** | `检索 -> 生成` | `规划 -> 检索/工具 -> 校验 -> 再检索 -> 回答` |

**关键分界线**:

- 普通 RAG：程序决定下一步
- Agentic RAG：模型根据证据决定下一步

#### 9.3.2 和 Workflow 的区别

`Workflow` 指的是开发者把流程提前编排好，例如：

`查询改写 -> 混合检索 -> rerank -> 摘要 -> 最终答案`

如果系统只是沿着这条固定链路运行，即使步骤很多，也更接近 **Workflow RAG**，不一定是 Agentic RAG。

**简单判断**:

- **固定编排**：更像 Workflow
- **动态编排**：更像 Agentic RAG

#### 9.3.3 和 Tool Calling 的区别

仅仅“支持工具调用”并不等于 Agentic RAG。

例如：

- 固定先调用一次 SQL，再调用一次 API，再回答
- 这属于工具编排，不一定属于 Agentic RAG

只有当模型会根据中间结果判断：

- 要不要调用工具
- 调哪个工具
- 什么时候继续查
- 什么时候停止

这种围绕证据动态决策的行为，才更接近 Agentic RAG。

#### 9.3.4 和 Multi-Agent 的区别

`Multi-Agent` 说的是系统组织方式，`Agentic RAG` 说的是检索增强任务的决策范式。

- Multi-Agent 可以用来实现 Agentic RAG
- 但 Multi-Agent 本身不等于 Agentic RAG
- 一个单 Agent + 检索工具，也可以是轻量版 Agentic RAG

所以：

- **Multi-Agent 是实现手段**
- **Agentic RAG 是问题求解方式**

### 9.4 Agentic RAG 的核心执行闭环

一个典型的 Agentic RAG 不应该被理解成“更多模块”，而应该被理解成“围绕证据收敛的执行闭环”。

```
用户目标
   ↓
理解任务 / 判断缺口
   ↓
制定下一步动作
   ↓
检索知识库 / 调用工具 / 改写查询
   ↓
评估证据是否足够
   ├─ 不足：继续检索或换工具
   └─ 足够：生成最终答案并给出引用
```

这个闭环的关键不是每一轮都要很复杂，而是系统能够反复回答下面两个问题：

1. 我现在已经知道了什么？
2. 为了完成任务，我还缺什么？

只要系统真的围绕这两个问题动态行动，它就已经具备了 Agentic RAG 的核心特征。

### 9.5 Agentic RAG 的核心能力拆解

如果说 `9.4` 讲的是 Agentic RAG 的**执行闭环**，那么这一节讲的是支撑这个闭环的**能力抽象层**。

这里重点回答的不是“系统里有几个模块”，也不是“必须采用哪种架构”，而是：

> **一个 Agentic RAG 系统，至少要具备哪些关键能力，才有可能围绕证据动态行动。**

也就是说，`Planner-Executor`、`Graph / Workflow`、`Master / Subagent` 这些都属于**实现方式**；而本节要说的是，在这些实现方式背后，系统本质上需要会什么。

| 能力 | 要解决的核心问题 | 典型表现 | 后续常见实现 |
|------|------------------|----------|-------------|
| 任务理解与路由 | 这个问题到底需不需要进入多步检索闭环 | 判断复杂度、识别信息缺口、选择下一步策略 | Router、Planner |
| 证据获取 | 去哪里拿证据、怎么拿证据 | 检索知识库、改写查询、调用 SQL / API / Web 工具 | Retriever、Tool Calling |
| 状态管理 | 系统如何记住自己已经做过什么 | 保存目标、历史动作、证据、中间结论、预算 | State、Memory、Graph State |
| 结果校验 | 当前证据够不够支撑回答 | 检查完整性、一致性、引用充分性，决定是否补查 | Critic、Reflection |
| 答案合成与引用 | 如何把证据组织成可交付结果 | 生成最终答案、附带引用、标注不确定性 | Answer Node、Report Generator |

#### 9.5.1 任务理解与路由能力

这是 Agentic RAG 的起点。系统需要先判断：当前问题究竟是一个可以直接回答的问题，还是一个必须进入多步检索、工具调用和补充验证的问题。

这类能力通常包括：

- 理解用户目标，而不是只看表面关键词
- 判断任务是简单问答，还是复杂分析 / 多步求证
- 识别当前信息缺口
- 决定下一步走普通 RAG、工具调用，还是进入更完整的 Agent 闭环

没有这层能力，系统就很容易出现两种问题：

- 简单问题被过度复杂化，导致成本和延迟上升
- 复杂问题却被当成一次性检索处理，导致答案不完整

#### 9.5.2 证据获取能力

Agentic RAG 和普通 RAG 的一个核心差别，就是它不会把“检索”固定死成单次 Top-K 查询，而是把“获取证据”当成一个可持续调整的动作。

这类能力通常包括：

- 面向知识库做语义检索、关键词检索、混合检索
- 根据中间结果改写查询
- 分步检索、多跳检索
- 调用结构化数据源，例如 SQL
- 调用外部 API、Web Search、业务系统等工具补充证据

所以从能力层看，检索和工具调用本质上都在解决同一个问题：

> **如何持续获取完成任务所需的外部证据。**

#### 9.5.3 状态管理能力

一旦系统进入多步闭环，就不能只靠“当前这一轮 prompt”工作，而必须显式维护状态。

这类能力通常包括：

- 保存当前任务目标和子任务进度
- 记录已经检索过的证据
- 记录工具调用历史和中间结果
- 记录预算、重试次数、失败原因、停止条件
- 避免重复检索和重复调用

状态管理的价值在于：让系统不是“每一步都重新开始想”，而是能够基于已有上下文持续推进。

#### 9.5.4 结果校验能力

Agentic RAG 不是“查到点东西就立刻生成答案”，而是要有能力判断：

- 当前证据是否足够
- 证据之间是否一致
- 是否还存在遗漏、冲突或明显空洞
- 是否需要继续检索、换一种工具，或者回退重试

这就是为什么很多 Agentic RAG 系统里会出现 `Critic`、`Reflection`、`Verifier` 之类的角色或节点。

它们不一定必须是独立 agent，但这类**校验能力**本身通常是必要的，尤其是在报告生成、多文档分析、研究型任务里。

#### 9.5.5 答案合成与引用能力

即使前面的检索和校验都做得不错，如果最后不能把证据组织成清晰、可追溯的结果，整个系统的价值仍然有限。

这类能力通常包括：

- 基于累积证据生成最终答案
- 保留并组织引用来源
- 区分“证据支持的事实”和“模型基于证据的推断”
- 在证据不足时明确说明不确定性和边界

对于企业级场景来说，这层能力非常重要，因为用户最终要消费的不是“检索过程”，而是一个**可解释、可引用、可交付**的结果。

#### 9.5.6 小结：这一节为什么重要

这一节的目的，是把 Agentic RAG 从“某种具体架构”提升到“能力视角”去理解。

- `9.4` 解决的是：它如何运行
- `9.5` 解决的是：它需要具备什么能力
- `9.6` 解决的是：这些能力可以如何落成具体实现

这样读者在后面看到 `Planner-Executor`、`Graph / Workflow`、`Master / Subagent` 时，就不会把它们误解成 Agentic RAG 的定义本身，而会理解成：**它们只是实现这些能力的不同组织方式。**

### 9.6 常见实现方式

理解了上一节的能力抽象层之后，下一步要问的就是：

> **这些能力在工程上通常如何被组织起来？**

这就是本节要讨论的“实现方式”。

需要注意的是，下面这些并不是互斥的标准答案，而是几种常见的组织模式。很多真实系统往往会把它们组合使用，例如：

- 用 `Router` 决定哪些请求进入 Agentic RAG
- 在 Agentic RAG 内部采用 `Planner-Executor`
- 再用 `Graph / Workflow` 管理状态、重试、超时和分支控制

所以本节更适合从“**能力如何落地**”的角度去理解，而不是把每一种实现方式当成彼此完全替代的独立路线。

#### 9.6.1 单 Agent + 检索工具

这是最轻量的 Agentic RAG 形态：把知识库检索、SQL、API、Web Search 等能力封装成工具，再由一个 Agent 决定何时调用、调用哪个工具。

它的优点是实现快、成本低、适合从普通 RAG 平滑升级；局限是随着任务复杂度上升，系统容易出现重复检索、行为不稳定和调试困难的问题。

#### 9.6.2 Planner-Executor

`Planner-Executor` 是一种很经典的 Agentic RAG 组织方式：先由 `Planner` 生成多步计划，再由 `Executor` 按计划执行，必要时再重规划。

它可以看作对传统 `ReAct` 的一种改进。`ReAct` 更像边走边想，每执行一步都再让模型决定下一步；`Planner-Executor` 则先给出全局路线，再进入执行阶段。

两者最关键的区别只有 3 点：

- **规划粒度不同**：`ReAct` 偏局部决策，`Planner-Executor` 先做全局拆解
- **执行成本不同**：`ReAct` 往往每一步都要重新调用主模型，`Planner-Executor` 可以把大模型集中用在规划和重规划上
- **流程组织不同**：`Planner-Executor` 通常是 `Plan -> Execute -> Re-plan`，更适合多步任务

进一步的变体也都沿着这个思路演化：

- **ReWOO**：在计划里显式引用前序结果，减少重复推理
- **LLMCompiler**：把任务编排成 DAG，支持并行执行无依赖步骤

**一句话总结**:

> `ReAct` 更像边走边想，`Plan-and-Execute` 更像先画路线图，再按路线执行，必要时再修正路线。

#### 9.6.2.1 典型执行流程

`Planner-Executor` 的标准流程可以概括为：

```text
用户问题
  -> Planner 生成计划
  -> Executor 按步骤执行
  -> 判断当前结果是否足够
  -> 不足则回到 Planner 重规划
  -> 生成最终答案
```

这个流程的重点有 3 个：

- 先用 `Planner` 给出全局方向，而不是每一步都临时决策
- `Executor` 只负责执行当前步骤，减少职责混杂
- 当执行结果不理想时，允许局部重规划，而不是整条链路重来

#### 9.6.2.2 适用场景

`Planner-Executor` 适合那些“不能一次检索解决、又需要明确步骤”的任务，例如：

- 多步分析任务
- 报告生成任务
- 多文档对比分析
- 跨知识库与数据库的复合查询
- 需要“先分解、再求证、再汇总”的复杂问答

典型例子：

- “分析过去三年的销售趋势并给出判断”
- “对比三份技术方案的优劣”
- “查询某产品实时库存，并结合历史销售判断补货风险”

这类任务通常有 3 个共同点：

- 一次检索不够
- 需要多类证据
- 需要中间步骤和阶段性汇总

#### 9.6.2.3 工程实现要点

如果要把它做成稳定系统，工程上至少要控制好下面几点：

- **计划格式结构化**：不要只返回自然语言大段文字，最好返回 steps、tool、expected_output 这类结构
- **每一步都要有状态**：包括待执行、执行中、成功、失败、重试次数
- **失败时支持重规划**：某一步拿不到证据时，不能只能报错退出
- **限制迭代次数**：避免 Planner 和 Executor 来回打转
- **保留证据链**：每一步产出的文档、SQL 结果、API 响应都要能回溯
- **有降级策略**：复杂流程失败后，必要时退回普通 RAG 或返回部分结果

一个常见的职责分工是：

- `Planner` 输出结构化 plan
- `Executor` 只消费 plan，不随意扩展职责
- `Evaluator/Critic` 负责判断是否需要重新规划

#### 9.6.2.4 一个最小示例

前面讲的是流程、适用任务和工程约束，下面用 LangGraph 官方 `plan-and-execute.ipynb` 对应的实现思路，看一个最小工程化例子。

**概念**

这个 notebook 把 `Planner-Executor` 拆成几个很清楚的 graph 节点：

- `planner`
  - 根据用户问题生成 `plan: List[str]`
- `agent_executor`
  - 用 `create_react_agent(...)` 创建一个执行代理
  - 它不是总控，只负责执行当前步骤
- `execute_step`
  - 取出当前第一步并执行
  - 把结果写入 `past_steps`
- `replan_step`
  - 根据当前进度决定“结束”还是“生成新计划”
- `should_end`
  - 判断流程是否结束

整体流程就是：

```text
输入问题
  -> planner 生成完整计划
  -> execute_step 执行当前步骤
  -> replan_step 判断是否继续
  -> should_end 决定结束或进入下一轮
```

这个例子说明了一件很重要的事：

- `Planner-Executor` 并不意味着执行器本身不能是一个 agent
- 在这个 notebook 里，执行器本身就是一个 `ReAct agent`
- 只是它不负责全局规划，只负责把当前步骤执行掉

所以它展示的是一个很标准的结构：

> **Planner 负责全局拆解，Execution Agent 负责局部执行，Replanner 负责根据中间结果决定是否继续**

**代码实现**

notebook 先准备一个最简单的工具集，这里只放一个搜索工具：

```python
from langchain_community.tools.tavily_search import TavilySearchResults

tools = [TavilySearchResults(max_results=3)]
```

然后用 `create_react_agent(...)` 创建执行器：

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4-turbo-preview")
prompt = "You are a helpful assistant."
agent_executor = create_react_agent(llm, tools, prompt=prompt)
```

接着用 `PlanExecute` 定义状态：

```python
class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
```

字段含义很直接：

- `input`：用户原始问题
- `plan`：当前剩余计划
- `past_steps`：已经完成的步骤及其结果
- `response`：最终答案

接着通过结构化输出约束 `Planner`：

```python
class Plan(BaseModel):
    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

planner = planner_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(Plan)
```

这意味着 `Planner` 不是输出自由文本，而是输出“有顺序的步骤列表”。

`Replanner` 也一样，只允许两种输出：

```python
class Response(BaseModel):
    response: str
class Act(BaseModel):
    action: Union[Response, Plan]

replanner = replanner_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(Act)
```

因此它每轮只做两件事：

- 直接给最终答案
- 返回一个更新后的计划

这个 notebook 最核心的是 4 个函数：

- `plan_step(state)`：读取输入，调用 `planner`，返回 `plan`
- `execute_step(state)`：取当前第一步，调用 `agent_executor` 执行，并写入 `past_steps`
- `replan_step(state)`：判断是直接返回答案，还是生成新计划
- `should_end(state)`：如果已有 `response` 则结束，否则继续执行

最后用 `StateGraph` 把这些节点连成闭环：

```python
workflow = StateGraph(PlanExecute)

workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end, ["agent", END])

app = workflow.compile()
```

对应的运行顺序就是：

```text
START
  -> planner
  -> agent
  -> replan
     -> END
     or
     -> agent
```

#### 9.6.2.5 经典论文

- Wang et al. (2023), *Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models*  
  https://arxiv.org/abs/2305.04091
  - 核心内容：提出 `Plan-and-Solve` 提示方法，先让模型给出计划，再按计划逐步推理，目标是减少零样本 CoT 中常见的漏步问题。
  - 对本节的启发：它说明“先规划、后执行”本身就是一种有效的推理组织方式，是 Planner-Executor 思路最直接的论文基础。
- Sun et al. (2023), *PEARL: Prompting Large Language Models to Plan and Execute Actions Over Long Documents*  
  https://arxiv.org/abs/2305.14564
  - 核心内容：针对长文档问答，提出 `action mining -> plan formulation -> plan execution` 三阶段框架，把复杂问题拆成一系列可执行动作，再逐步在长文档中完成。
  - 对本节的启发：它把 Planner-Executor 明确落到了“长文档推理”场景里，说明规划不仅能拆任务，还能帮助控制长上下文中的执行路径。
- Shen et al. (2023), *HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face*  
  https://arxiv.org/abs/2303.17580
  - 核心内容：把 LLM 作为总控，让它先规划任务，再从外部模型库中挑选合适的模型执行子任务，最后汇总结果。
  - 对本节的启发：虽然它是更广义的多工具/多模型编排系统，但其核心流程同样是“规划 -> 选择执行器 -> 执行 -> 汇总”，可以看作 Planner-Executor 在工具生态上的扩展。

#### 9.6.3 Master / Subagent

这是把 Agentic RAG 做成“多角色协作”的实现方式：不是让一个 Agent 包办所有事情，而是由一个总控负责理解目标、拆分任务、分派执行、汇总证据，再把不同子任务交给更专门的 `Subagent`。

做法：

- `Master Agent` 负责总控：理解用户目标、拆任务、选择子代理、合并中间结果、决定是否继续追问或补查
- `Subagent` 负责专项执行：例如知识库检索、SQL 查询、API 调用、Web 搜索、事实校验、引用整理
- `Master` 不直接做所有细节，而是更像一个调度器和结果集成器

一个典型流程通常是：

```text
用户问题
   ↓
Master Agent 理解任务
   ↓
拆成若干子任务
   ├─ 子任务 A：去知识库检索背景资料
   ├─ 子任务 B：去 SQL / BI 系统拿结构化数据
   ├─ 子任务 C：去外部 API / Web 补充最新信息
   └─ 子任务 D：检查证据是否冲突、引用是否充分
   ↓
Master 汇总结果
   ↓
必要时发起第二轮补查
   ↓
输出最终答案
```

这种模式最适合下面几类场景：

- 问题天然可以拆成多个相对独立的子问题
- 需要同时连接多种异构数据源
- 不同子任务的执行逻辑差异很大，不适合塞进一个通用 Agent prompt
- 某些任务可以并行完成，希望缩短总耗时

从工程视角看，`Subagent` 不一定非得是“完全自治的智能体”，它更常见的真实形态是：

- 一个带专用提示词的轻量 Agent
- 一个封装好的工具调用器
- 一个固定职责的工作流节点

也就是说，`Master / Subagent` 的重点不在“角色名字多”，而在于：

> **是否真的把复杂任务拆成了若干职责清晰、可独立执行、可汇总证据的单元。**

优点：

- 适合多数据源、可并行的复杂任务
- 职责边界清晰时，可维护性和可扩展性都很好
- 各个 `Subagent` 可以按领域独立优化，例如分别强化检索、SQL 生成、网页归纳、证据校验

缺点：

- 最容易过度设计，小任务也可能被拆得过碎
- `Master` 的调度逻辑如果不稳，整体行为会比单 Agent 更难预测
- 状态同步、证据归并、结果一致性、去重与冲突处理都更难

落地时最容易踩的坑有 3 类：

1. 子代理划分按“技术组件”拆得太细，导致通信成本高于实际收益。
2. 每个子代理都保留自己的上下文和结论，但没有统一的证据格式，最后很难汇总。
3. `Master` 只汇总结论、不汇总证据，最终答案看起来完整，但引用链断裂。

所以一个更稳妥的工程原则是：

- `Master` 主要维护全局状态：原始问题、任务计划、子任务结果、证据池、预算和停止条件
- `Subagent` 只对自己负责的局部目标输出结构化结果
- 所有子任务尽量返回统一格式，例如 `result + evidence + citation + confidence`

如果把它放到 RAG 场景里，可以把子代理粗略分成这几类：

- `Retriever Subagent`：负责知识库检索、查询改写、召回和 rerank
- `Structured Data Subagent`：负责 SQL / 表格 / BI 数据查询
- `External Info Subagent`：负责 API 或 Web 信息补充
- `Critic / Verifier Subagent`：负责检查证据充分性、一致性和引用质量
- `Writer Subagent`：负责把最终证据整理成回答、报告或摘要

#### 9.6.3.1 经典论文

- Wu et al. (2023), *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation*  
  https://arxiv.org/abs/2308.08155
- Li et al. (2023), *CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society*  
  https://arxiv.org/abs/2303.17760
- Hong et al. (2023), *MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework*  
  https://arxiv.org/abs/2308.00352

#### 9.6.4 Graph / Workflow Agent

做法：

- 用状态机或图定义节点
- 节点可能是：路由、检索、工具调用、校验、补查、回答
- 哪条边被走，由条件或模型判断

优点：

- 工程上最稳
- 易于加预算、超时、重试、降级
- 适合生产环境

缺点：

- 架构复杂度更高
- 前期设计成本更大

#### 9.6.5 Reflection / Critic 闭环

做法：

- 先得到初步答案
- 再由 `Critic` 判断证据是否充分
- 不够则自动生成补充查询继续检索

优点：

- 能明显提升复杂任务质量
- 特别适合报告、分析、研究型任务

缺点：

- 成本和延迟上升明显

**结论**:

- 学习和原型阶段：优先从 `单 Agent + 检索工具` 开始
- 中等复杂度：`Planner-Executor`
- 生产环境：`Graph / Workflow Agent`
- 超复杂场景：再考虑 `Master / Subagent`

### 9.7 一套最小可行实现（MVP）

如果你要真正动手做一个最小可行版 Agentic RAG，不需要一开始就上多 Agent。下面这套最小结构已经足够。

**MVP 最少需要 6 个部分**:

1. 一个 `Retriever Tool`
2. 一个 `Tool Registry`
3. 一个 `Agent Loop`
4. 一个 `State`
5. 一套 `Stop Criteria`
6. 一个 `Answer with Citations`

**最小执行逻辑**:

```python
class AgentState:
    def __init__(self, query: str):
        self.query = query
        self.evidence = []
        self.history = []
        self.iterations = 0


class AgenticRAGMVP:
    def __init__(self, agent, retriever_tool, tools, max_iterations=5):
        self.agent = agent
        self.retriever_tool = retriever_tool
        self.tools = tools
        self.max_iterations = max_iterations

    def run(self, query: str):
        state = AgentState(query)

        while state.iterations < self.max_iterations:
            action = self.agent.decide(
                query=state.query,
                evidence=state.evidence,
                history=state.history,
            )

            if action["type"] == "retrieve":
                docs = self.retriever_tool(action["query"])
                state.evidence.extend(docs)
                state.history.append(action)

            elif action["type"] == "tool":
                result = self.tools[action["tool_name"]](**action["args"])
                state.evidence.append(result)
                state.history.append(action)

            elif action["type"] == "final_answer":
                return self.agent.answer(
                    query=state.query,
                    evidence=state.evidence,
                    with_citations=True,
                )

            state.iterations += 1

        return self.agent.answer(
            query=state.query,
            evidence=state.evidence,
            with_citations=True,
        )
```

这个版本虽然简单，但已经具备了 Agentic RAG 最关键的能力：

- 检索在循环中
- 模型能决定下一步动作
- 有最大迭代次数
- 最终答案基于累积证据生成

### 9.8 典型架构模式

下面是工程里最常见的几种架构模式。

#### 9.8.1 单 Agent 架构

```
用户问题
   ↓
单个 Agent
   ↓
RAG / SQL / API / Web Tools
   ↓
最终答案
```

适合：原型验证、轻量应用、单一业务团队。

#### 9.8.2 普通 RAG + Agentic RAG 混合路由

```
用户问题
   ↓
Router
 ├─ 简单问题 -> 普通 RAG
 └─ 复杂问题 -> Agentic RAG
```

适合：线上大部分请求简单，只有少数请求复杂的场景。  
这是最推荐的生产方案之一，因为能兼顾成本和质量。

#### 9.8.3 Master / Subagent

```
用户问题
   ↓
Master Agent
 ├─ Retriever Subagent
 ├─ SQL Subagent
 ├─ API Subagent
 ├─ Web Subagent
 └─ Critic Subagent
   ↓
汇总答案
```

适合：问题天然可拆分、可并行、多数据源、多角色协同的场景。

#### 9.8.4 Graph / State Machine

```
Router -> Planner -> Retrieve -> Critic
                     ↑         ↓
                     └-- Retry ┘
```

适合：对超时、预算、审计、可观测性要求高的生产系统。

### 9.9 适用场景与不适用场景

| 场景 | 是否推荐 Agentic RAG | 原因 |
|------|---------------------|------|
| 简单 FAQ | 不推荐 | 固定检索已经足够 |
| 企业知识库问答 | 视情况而定 | 简单问答可用普通 RAG，复杂问答可升级 |
| 多文档对比分析 | 推荐 | 需要拆任务和聚合证据 |
| 实时库存 + 历史销售查询 | 推荐 | 往往需要知识库 + SQL/API |
| 趋势分析 / 报告生成 | 推荐 | 需要多步求证与校验 |
| 高并发、低延迟、低预算接口 | 谨慎使用 | 成本和响应时间压力大 |

**不适用或不必优先使用的情况**:

- 大多数请求都是简单事实问答
- 业务只有一个知识库，没有外部工具需求
- 团队还没有把普通 RAG 做稳定
- 对延迟极其敏感，且没有复杂任务需求

### 9.10 工程落地难点与最佳实践

Agentic RAG 的难点通常不在“能不能跑起来”，而在“能不能稳定、可控、可观测地跑起来”。

#### 9.10.1 成本控制

建议：

- 限制最大迭代次数
- 限制单工具最大调用次数
- 只让复杂请求进入 Agentic RAG
- 优先对高价值任务使用 Reflection

#### 9.10.2 延迟与超时

建议：

- 给每轮执行设置超时
- 为关键工具设置降级策略
- 超时后回退到普通 RAG 或返回部分结果

#### 9.10.3 工具安全

建议：

- SQL 只开放白名单操作
- API 工具做参数校验
- Web 搜索结果进入答案前做引用约束
- 代码执行工具必须有严格沙箱

#### 9.10.4 状态与可观测性

建议：

- 记录每轮动作、输入、输出、耗时、花费
- 记录为什么继续、为什么停止
- 把最终答案和证据链一起保存，便于回放与排查

#### 9.10.5 引用与一致性

建议：

- 最终答案必须区分“证据事实”和“模型推断”
- 多个 subagent 返回结果时统一归并引用
- 引用找不到来源时不要输出强结论

#### 9.10.6 错误处理与降级

建议：

- 检索失败时尝试改写查询重试
- 工具失败时允许切换备选工具
- 多轮失败后降级到普通 RAG
- 无足够证据时明确说明不确定性

### 9.11 选型建议：什么时候用普通 RAG，什么时候升级 Agentic RAG

可以按照下面的思路做选型。

| 问题特征 | 推荐方案 |
|---------|---------|
| 简单事实查询 | 普通 RAG |
| 固定知识库问答 | 普通 RAG |
| 需要多步推理 | Agentic RAG |
| 需要调用外部工具 | Agentic RAG |
| 需要多源数据聚合 | Agentic RAG |
| 高实时、低预算、低延迟 | 优先普通 RAG |
| 大部分请求简单，少数请求复杂 | 路由式混合架构 |

**推荐升级路径**:

1. 先把普通 RAG 做稳定
2. 再增加查询改写、混合检索、rerank
3. 再做问题路由，把复杂请求送进 Agentic RAG
4. 最后再考虑 Reflection、Graph、Master/Subagent

也就是说，工程上最务实的路线通常不是“全面改成 Agentic RAG”，而是：

> **普通 RAG 为主，复杂任务再升级到 Agentic RAG**

### 9.12 总结

`Agentic RAG` 的核心，不是“系统里出现了几个 Agent”，而是：

> **模型会围绕证据获取和证据验证动态决定下一步动作**

你可以用下面这句口诀来帮助判断：

> **固定流程做检索 = 普通 RAG**
> **模型决定如何继续检索 = Agentic RAG**

**最后记住 3 点**:

1. Agentic RAG 是一种架构范式，不是单一算法
2. Multi-Agent、Tool Calling、Workflow 都可以参与实现，但都不等于定义本身
3. 最推荐的工程策略通常是：`普通 RAG 处理大多数问题，Agentic RAG 处理复杂问题`

---

## 附录

### A. 常见问题 FAQ

**Q1: RAG 和微调如何选择?**

A:
- **RAG**: 知识频繁更新、需要引用来源、成本敏感
- **微调**: 需要特定风格、领域深度理解、长期使用
- **组合**: 微调领域理解能力 + RAG 提供最新知识

**Q2: 如何评估 RAG 系统的好坏?**

A: 从三个维度评估:
1. **检索质量**: context_precision, context_recall
2. **生成质量**: faithfulness, answer_correctness
3. **系统性能**: 延迟、吞吐量、成本

**Q3: 如何处理大规模知识库?**

A:
1. 使用分布式向量库 (Milvus 集群)
2. 分区管理 (按主题/时间分区)
3. 分级存储 (热数据 + 冷数据)
4. 异步索引更新

**Q4: 如何降低 RAG 系统成本?**

A:
1. **模型选择**: 根据问题复杂度动态选择模型
2. **缓存策略**: 缓存热门查询和 embedding
3. **批处理**: 合并相似请求
4. **Token 优化**: 智能切片和上下文压缩

### B. 工具推荐

| 类别 | 工具 | 用途 |
|------|------|------|
| **开发框架** | LlamaIndex, LangChain | RAG 系统开发 |
| **向量数据库** | Milvus, Pinecone, Chroma | 向量存储与检索 |
| **全文检索** | Elasticsearch, Meilisearch | 关键词检索 |
| **评估工具** | RAGAS, TruLens | 质量评估 |
| **监控** | Prometheus, Grafana | 系统监控 |
| **部署** | Docker, Kubernetes | 容器化部署 |

### C. 参考资料

1. LlamaIndex 官方文档: https://docs.llamaindex.ai/
2. RAGAS 官方文档: https://docs.ragas.io/
3. Agentic RAG 相关经典论文:
   - RAG: https://arxiv.org/abs/2005.11401
   - DPR: https://arxiv.org/abs/2004.04906
   - ReAct: https://arxiv.org/abs/2210.03629
   - IRCoT: https://arxiv.org/abs/2212.10509
   - DSP: https://arxiv.org/abs/2212.14024
   - MRKL: https://arxiv.org/abs/2205.00445
   - Toolformer: https://arxiv.org/abs/2302.04761
   - Self-RAG: https://arxiv.org/abs/2310.11511
4. 本仓库文档:
   - `03_rag_and_retrieval/llamaindex_and_ragas/docs/llamaindex学习文档.md`
   - `03_rag_and_retrieval/llamaindex_and_ragas/docs/ragas工程实践指南.md`
   - `03_rag_and_retrieval/qanything_case_study/docs/混合检索实现原理详解.md`

---

**最后更新**: 2026-03-07
**维护者**: AI Training Team
**反馈**: 如有问题或建议,请提交 Issue
