# RAGFlow Parent-Child 文档设计详解

## 概述

RAGFlow 中的 Parent-Child 文档设计是一种分层文档索引与检索策略，旨在解决传统 RAG 系统中"碎片化检索"导致上下文缺失的问题。通过建立父子层级关系，系统能够在保持检索精度的同时，为 LLM 提供更完整的语义上下文。

## 核心问题与解决方案

### 传统 RAG 的痛点

| 问题 | 描述 | 影响 |
|------|------|------|
| 上下文缺失 | 文档被切分成小块，丢失整体语义 | LLM 无法理解完整背景 |
| 召回与精度矛盾 | 大块召回率高但精度低，小块反之 | 难以平衡 |
| 语义边界模糊 | 机械切分可能打断关键语义 | 检索结果不相关 |

### Parent-Child 的解决思路

```
┌─────────────────────────────────────────────────────┐
│                    检索流程                          │
├─────────────────────────────────────────────────────┤
│  用户查询 ──► 子块精确匹配 ──► 关联父块 ──► 返回完整上下文 │
└─────────────────────────────────────────────────────┘
```

**核心优势：**
- **子块（Child Chunk）**：负责精确匹配，确保检索精度
- **父块（Parent Chunk）**：提供完整上下文，保证语义完整性

---

## 一、数据结构设计

### 1.1 数据库 Schema

RAGFlow 使用 Infinity 向量数据库存储文档块，关键字段定义如下：

```json
{
    "id": {"type": "varchar", "default": ""},
    "doc_id": {"type": "varchar", "default": ""},
    "kb_id": {"type": "varchar", "default": ""},
    "mom_id": {"type": "varchar", "default": ""},   // 核心字段：父块ID
    "content": {"type": "varchar", "default": ""},
    "content_ltks": {"type": "varchar", "default": ""},
    "content_with_weight": {"type": "varchar", "default": ""},
    "important_keywords": {"type": "varchar", "default": ""},
    "questions": {"type": "varchar", "default": ""},
    "position_int": {"type": "varchar", "default": ""},
    "create_time": {"type": "varchar", "default": ""},
    "create_timestamp_flt": {"type": "float", "default": 0.0}
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | varchar | 块的唯一标识符 |
| `doc_id` | varchar | 所属文档ID |
| `kb_id` | varchar | 所属知识库ID |
| `mom_id` | varchar | **父块ID**，为空表示顶层块 |
| `content` | varchar | 块的文本内容 |
| `content_ltks` | varchar | 分词后的内容（用于检索） |
| `content_with_weight` | varchar | 带权重的内容 |
| `important_keywords` | varchar | 关键词列表 |
| `questions` | varchar | 问题列表（用于问答对） |

### 1.2 Python 模型定义

```python
from pydantic import BaseModel, Field
from typing import List

class Chunk(BaseModel):
    """文档块模型"""
    id: str = ""
    content: str = ""
    document_id: str = ""
    docnm_kwd: str = ""
    important_keywords: list = Field(default_factory=list)
    questions: list = Field(default_factory=list)
    question_tks: str = ""
    image_id: str = ""
    available: bool = True
    positions: list[list[int]] = Field(default_factory=list)
```

### 1.3 层级关系示意

```
文档 (Document)
├── 父块 A (Parent Chunk, mom_id = "")
│   ├── 子块 A1 (Child Chunk, mom_id = "parent_A_id")
│   ├── 子块 A2 (Child Chunk, mom_id = "parent_A_id")
│   └── 子块 A3 (Child Chunk, mom_id = "parent_A_id")
├── 父块 B (Parent Chunk, mom_id = "")
│   ├── 子块 B1 (Child Chunk, mom_id = "parent_B_id")
│   └── 子块 B2 (Child Chunk, mom_id = "parent_B_id")
└── 父块 C (Parent Chunk, mom_id = "")
    └── 子块 C1 (Child Chunk, mom_id = "parent_C_id")
```

---

## 二、索引机制

### 2.1 文档处理流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        文档处理流水线                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   原始文档                                                        │
│      │                                                           │
│      ▼                                                           │
│   ┌─────────────┐                                                │
│   │  文档解析    │  ← 支持 PDF、Word、Markdown 等                   │
│   └─────────────┘                                                │
│      │                                                           │
│      ▼                                                           │
│   ┌─────────────┐                                                │
│   │  层级分割    │  ← 根据标题/分隔符建立层级                        │
│   └─────────────┘                                                │
│      │                                                           │
│      ▼                                                           │
│   ┌─────────────┐                                                │
│   │ 父子关系建立  │  ← 设置 mom_id                                 │
│   └─────────────┘                                                │
│      │                                                           │
│      ▼                                                           │
│   ┌─────────────┐                                                │
│   │  向量索引    │  ← Embedding + 存储                            │
│   └─────────────┘                                                │
│      │                                                           │
│      ▼                                                           │
│   向量数据库 (Infinity)                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 分层分割策略

RAGFlow 支持多种分割策略来建立父子关系：

#### 2.2.1 标题层级分割

```python
# 配置示例
{
    "chunk_method": "hierarchical",
    "levels": ["H1", "H2", "H3"],  # 支持的标题层级
    "parent_level": "H2",           # 父块层级
    "child_level": "H3"             # 子块层级
}
```

**效果：**
```markdown
# 第一章 合同总则 (H1 - 父块)
## 1.1 定义与解释 (H2 - 父块)
### 1.1.1 甲方定义 (H3 - 子块)
### 1.1.2 乙方定义 (H3 - 子块)
## 1.2 合同范围 (H2 - 父块)
### 1.2.1 服务内容 (H3 - 子块)
```

#### 2.2.2 自定义分隔符分割

```python
# 配置示例
{
    "chunk_method": "delimiter",
    "parent_delimiters": ["\n\n", "##"],   # 父块分隔符
    "child_delimiters": ["\n", "。", "；"]  # 子块分隔符
}
```

### 2.3 HierarchicalMerger 组件

```python
class HierarchicalMerger:
    """层级合并器：建立树形结构的父子关系"""

    component_name = "HierarchicalMerger"

    async def _invoke(self, **kwargs):
        # 1. 根据层级设置分割文本
        # 2. 建立树形结构的父子关系
        # 3. 将叶子节点作为子块，非叶子节点作为父块
        # 4. 设置每个子块的 mom_id 指向其父块
        pass
```

### 2.4 索引存储优化

```python
# 索引配置
{
    "primary_key": "id",
    "indexes": [
        {"field": "mom_id", "type": "btree"},     # 父子关系索引
        {"field": "doc_id", "type": "btree"},     # 文档索引
        {"field": "kb_id", "type": "btree"},      # 知识库索引
        {"field": "content_ltks", "type": "fulltext"}  # 全文索引
    ]
}
```

---

## 三、检索机制

### 3.1 检索流程详解

```
┌─────────────────────────────────────────────────────────────────┐
│                      Parent-Child 检索流程                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 初始检索                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Query ──► 向量相似度搜索 ──► 返回 Top-K 子块              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 2: 父子关联                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  根据子块的 mom_id ──► 查找对应父块                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 3: 内容合并                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  子块内容 + 父块内容 ──► 合并为完整上下文                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 4: 相似度重计算                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  综合子块和父块相似度 ──► 重新排序                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 5: 返回结果                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  返回合并后的块（包含完整上下文）                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心检索代码

```python
def retrieval_by_children(self, chunks: list[dict], tenant_ids: list[str]):
    """
    基于 Parent-Child 策略的检索实现

    Args:
        chunks: 初始检索返回的子块列表
        tenant_ids: 租户ID列表

    Returns:
        合并父子块后的结果列表
    """
    if not chunks:
        return []

    # Step 1: 将 chunks 分为父块和子块
    mom_chunks = defaultdict(list)  # {mom_id: [child_chunks]}
    i = 0
    while i < len(chunks):
        ck = chunks[i]
        mom_id = ck.get("mom_id")

        # 检查是否有有效的父块ID
        if not isinstance(mom_id, str) or not mom_id.strip():
            i += 1
            continue

        # 将子块按父块ID分组
        mom_chunks[ck["mom_id"]].append(chunks.pop(i))

    # Step 2: 为每组子块查找对应的父块
    for mom_id, child_chunks in mom_chunks.items():
        # 从向量数据库获取父块
        parent_chunk = self.dataStore.get(
            mom_id,
            idx_nms[0],
            [ck["kb_id"] for ck in child_chunks]
        )

        # Step 3: 合并子块内容与父块内容
        merged_chunk = {
            "chunk_id": mom_id,
            # 合并所有子块的 token 信息
            "content_ltks": " ".join([ck["content_ltks"] for ck in child_chunks]),
            # 使用父块的权重内容
            "content_with_weight": parent_chunk["content_with_weight"],
            "doc_id": parent_chunk["doc_id"],
            "docnm_kwt": parent_chunk.get("docnm_kwt", ""),
            "kb_id": parent_chunk["kb_id"],
            # 计算平均相似度
            "similarity": np.mean([ck["similarity"] for ck in child_chunks]),
            # 合并关键词
            "important_keywords": list(set(
                kw for ck in child_chunks
                for kw in ck.get("important_keywords", [])
            )),
            # 合并问题
            "questions": list(set(
                q for ck in child_chunks
                for q in ck.get("questions", [])
            ))
        }

        chunks.append(merged_chunk)

    # Step 4: 按相似度排序返回
    return sorted(chunks, key=lambda x: x["similarity"] * -1)
```

### 3.3 相似度计算策略

```python
def calculate_combined_similarity(child_chunks: list, parent_chunk: dict) -> float:
    """
    综合计算父子块的相似度

    策略：
    1. 子块相似度：精确匹配的得分
    2. 父块相似度：上下文相关性的得分
    3. 加权平均：平衡精度与召回
    """
    # 子块平均相似度
    child_avg = np.mean([ck["similarity"] for ck in child_chunks])

    # 父块相似度（如果有单独计算）
    parent_sim = parent_chunk.get("similarity", child_avg)

    # 加权组合 (可配置)
    weights = {
        "child_weight": 0.7,   # 子块权重更高，确保精确匹配
        "parent_weight": 0.3   # 父块提供上下文补充
    }

    combined = (
        weights["child_weight"] * child_avg +
        weights["parent_weight"] * parent_sim
    )

    return combined
```

---

## 四、配置与使用

### 4.1 启用 Child Chunk 检索

在知识库配置中开启：

```yaml
# dataset configuration
dataset:
  retrieval_mode: "child_chunk"  # 启用子块检索模式

  child_chunk:
    enabled: true
    delimiters: ["\n", "。", "；", "？", "!"]  # 子块分隔符

  parent_chunk:
    delimiters: ["\n\n", "##", "---"]  # 父块分隔符
```

### 4.2 API 调用示例

```python
from ragflow import RAGFlow

# 初始化客户端
client = RAGFlow(api_key="your_api_key")

# 创建知识库并启用 Parent-Child
dataset = client.create_dataset(
    name="合规手册",
    chunk_method="hierarchical",
    child_chunk_enabled=True
)

# 上传文档
document = dataset.upload_document(
    file_path="compliance_manual.pdf",
    parser_config={
        "parent_delimiters": ["\n\n## "],
        "child_delimiters": ["\n"]
    }
)

# 检索
results = dataset.search(
    query="违约责任如何界定？",
    top_k=5,
    retrieval_mode="child_chunk"  # 使用子块检索
)

for result in results:
    print(f"相似度: {result.similarity}")
    print(f"内容: {result.content}")  # 包含完整上下文
    print(f"文档: {result.document_name}")
    print("-" * 50)
```

---

## 五、实际应用场景

### 5.1 场景一：合规手册查询

**文档结构：**
```markdown
## 第三章 违约责任

### 3.1 违约分类
违约分为重大违约和轻微违约。重大违约包括但不限于：
- 未按约定时间交付
- 交付物质量不符合标准
- 擅自终止合同

### 3.2 违约处罚
- 重大违约：罚款为合同总额的 20%
- 轻微违约：罚款为合同总额的 5%
```

**检索过程：**

```
用户查询: "违约罚款是多少？"

Step 1 - 子块匹配:
  匹配到子块: "重大违约：罚款为合同总额的 20%"
  相似度: 0.92

Step 2 - 关联父块:
  父块内容: "### 3.2 违约处罚\n- 重大违约：罚款...\n- 轻微违约：罚款..."

Step 3 - 返回结果:
  完整上下文: 包含违约分类和处罚标准的完整信息

LLM 回答:
  "根据合规手册第三章，违约处罚标准如下：
   - 重大违约（如未按时交付、质量不达标等）：罚款为合同总额的 20%
   - 轻微违约：罚款为合同总额的 5%"
```

**优势对比：**

| 方案 | 返回内容 | LLM 理解 |
|------|---------|---------|
| 传统检索 | "罚款为合同总额的 20%" | ❓ 不知道是什么类型的违约 |
| Parent-Child | 包含分类和标准的完整上下文 | ✅ 能准确回答不同情况 |

### 5.2 场景二：技术文档查询

**文档结构：**
```markdown
## API 接口规范

### 用户认证接口
#### POST /api/auth/login
请求参数：
- username: 用户名
- password: 密码

返回结果：
- token: 认证令牌
- expires_in: 过期时间

### 数据查询接口
#### GET /api/data/query
请求头：
- Authorization: Bearer {token}

请求参数：
- query: 查询语句
- limit: 返回数量
```

**检索过程：**

```
用户查询: "如何获取认证令牌？"

子块匹配: "token: 认证令牌" (相似度 0.85)
关联父块: 完整的 "用户认证接口" 章节

返回结果: 包含完整的认证接口文档，包括请求方法、参数、返回结果

LLM 能准确回答:
  "获取认证令牌需要调用 POST /api/auth/login 接口，
   传入 username 和 password 参数，返回结果中的 token 字段即为认证令牌。"
```

### 5.3 场景三：法律合同分析

**应用价值：**
- 保持条款的完整语义
- 关联相关条款和定义
- 避免断章取义的风险

---

## 六、性能优化

### 6.1 索引优化

```python
# 为 mom_id 建立专门的索引
CREATE INDEX idx_mom_id ON chunks(mom_id);

# 复合索引优化常用查询
CREATE INDEX idx_kb_mom ON chunks(kb_id, mom_id);
```

### 6.2 缓存策略

```python
class ParentChunkCache:
    """父块缓存，避免重复查询"""

    def __init__(self, max_size=1000):
        self.cache = LRUCache(max_size)

    def get_parent(self, mom_id: str):
        if mom_id in self.cache:
            return self.cache[mom_id]

        parent = self.dataStore.get(mom_id)
        self.cache[mom_id] = parent
        return parent
```

### 6.3 批量查询优化

```python
def batch_get_parents(child_chunks: list) -> dict:
    """
    批量获取父块，减少数据库查询次数
    """
    # 收集所有唯一的 mom_id
    mom_ids = list(set(ck["mom_id"] for ck in child_chunks if ck.get("mom_id")))

    # 批量查询
    parents = self.dataStore.batch_get(mom_ids)

    return {p["id"]: p for p in parents}
```

---

## 七、最佳实践

### 7.1 分割粒度选择

| 文档类型 | 父块大小 | 子块大小 | 说明 |
|---------|---------|---------|------|
| 技术文档 | 500-1000 tokens | 100-200 tokens | 保持章节完整 |
| 法律合同 | 条款级别 | 段落级别 | 保持条款完整 |
| 新闻文章 | 300-500 tokens | 50-100 tokens | 保持段落完整 |
| 学术论文 | 章节级别 | 段落级别 | 保持论证完整 |

### 7.2 配置建议

```yaml
# 推荐配置
hierarchical_chunking:
  # 父块配置
  parent:
    max_tokens: 800
    overlap: 50
    delimiters: ["\n\n", "##", "###"]

  # 子块配置
  child:
    max_tokens: 150
    overlap: 20
    delimiters: ["\n", "。", "；"]

  # 检索配置
  retrieval:
    top_k_children: 20      # 初始检索子块数量
    top_k_merged: 5         # 合并后返回数量
    min_similarity: 0.6     # 最小相似度阈值
```

### 7.3 避免的坑

1. **过度分割**：子块太小会导致语义丢失
2. **层级过深**：建议只使用父子两层，避免复杂树结构
3. **忽视分隔符**：选择合适的分隔符至关重要
4. **不评估效果**：需要对比传统检索评估效果提升

---

## 八、与其他方案对比

| 特性 | RAGFlow Parent-Child | Small-to-Big | 滑动窗口 |
|------|---------------------|--------------|---------|
| 上下文完整性 | ✅ 优秀 | ✅ 优秀 | ⚠️ 一般 |
| 检索精度 | ✅ 高 | ✅ 高 | ⚠️ 中等 |
| 实现复杂度 | ⚠️ 中等 | ❌ 复杂 | ✅ 简单 |
| 存储开销 | ⚠️ 较高 | ❌ 高 | ✅ 低 |
| 灵活性 | ✅ 高 | ⚠️ 中等 | ❌ 低 |
| 适用场景 | 结构化文档 | 通用 | 简单场景 |

---

## 九、总结

RAGFlow 的 Parent-Child 文档设计通过以下核心机制解决了 RAG 系统的关键问题：

### 核心要点

1. **双层结构设计**
   - 父块：保持语义完整性，提供上下文
   - 子块：精确匹配，确保检索精度

2. **智能索引机制**
   - `mom_id` 字段建立父子关系
   - 支持多种分割策略（标题层级、自定义分隔符）

3. **高效检索流程**
   - 子块检索 → 父块关联 → 内容合并 → 相似度重算

4. **灵活配置选项**
   - 可调整分割粒度
   - 可配置相似度权重
   - 支持多种文档类型

### 适用场景

- ✅ 结构化文档（技术文档、法律合同、合规手册）
- ✅ 需要保持上下文完整性的场景
- ✅ 对检索精度和召回率都有要求的场景

### 局限性

- ⚠️ 增加存储开销（父子块都需要存储）
- ⚠️ 增加检索延迟（需要额外查询父块）
- ⚠️ 需要合理配置分割策略

---

## 参考资料

- RAGFlow 源码：`/rag/nlp/search.py` - `retrieval_by_children` 方法
- RAGFlow 源码：`/rag/flow/hierarchical_merger/` - 层级合并器
- RAGFlow 文档：`/docs/guides/dataset/configure_child_chunking_strategy.md`
- Infinity 数据库映射：`/conf/infinity_mapping.json`
