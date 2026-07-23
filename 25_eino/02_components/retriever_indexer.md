# Embedding / Retriever / Indexer 组件与 RAG 流水线

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/embedding/`、`retriever/`、`indexer/`
> 核心文件: `interface.go`、`option.go`。
> 本文阐述 RAG 三大核心组件的接口契约、协作关系与 Option 机制。

## 一、概述

RAG(Retrieval-Augmented Generation)是最常见的 LLM 应用模式，它通过"检索相关文档 + 拼入 prompt 让模型基于检索内容回答"，解决模型"知识过时"和"幻觉"问题。

Eino 将 RAG 拆解为三个独立接口，职责分离、可独立替换：

| 组件 | 职责 | 接口方法 | 输入 → 输出 |
|------|------|----------|-------------|
| **Embedding** | 文本向量化 | `EmbedStrings` | `[]string` → `[][]float64` |
| **Indexer** | 文档写入向量库 | `Store` | `[]*schema.Document` → `[]string`(文档ID) |
| **Retriever** | 按查询召回相关文档 | `Retrieve` | `string` → `[]*schema.Document` |

三者协作构成完整 RAG 流水线：
```
【离线构建索引】
Loader → Document → Transformer → Embedding → Indexer.Store → 向量库
                  切分         向量化       持久化

【在线检索问答】
用户问题 → Embedding(query) → Retriever.Retrieve → 召回 Documents → ChatTemplate → ChatModel → 回答
                向量化          向量库相似度搜索              拼prompt
```

实现都在 [eino-ext](https://github.com/cloudwego/eino-ext)，核心仓库仅定义接口。常见实现：
- Embedding: OpenAI、火山方舟、Ollama 等
- Indexer/Retriever: Redis、Elasticsearch、Milvus、Weaviate 等

## 二、接口契约详解

### 2.1 Embedding:文本向量化

`embedding.Embedder` 接口(`interface.go:38`):
```go
type Embedder interface {
	EmbedStrings(ctx context.Context, texts []string, opts ...Option) ([][]float64, error)
}
```

**契约要点:**
- 输入一批文本，输出**同顺序**的向量数组
- 每个文本对应一个向量，维度固定由底层模型决定(如 `text-embedding-ada-002` 是 1536 维)
- **Indexer 和 Retriever 必须使用同一个 Embedder 模型**——维度和语义空间必须一致，否则相似度计算无意义

### 2.2 Indexer:文档入库

`indexer.Indexer` 接口(`interface.go:39`):
```go
type Indexer interface {
	Store(ctx context.Context, docs []*schema.Document, opts ...Option) (ids []string, err error)
}
```

**输入 `schema.Document`**(`schema/document.go`):
```go
type Document struct {
	ID       string              // 可选，用户指定 ID
	Content  string              // 文档文本内容
	MetaData map[string]any      // 元数据，用于过滤
}
```

**契约要点:**
- 批量入库，返回后端分配的文档 ID 列表
- 若用户已填 `doc.ID`，多数实现直接使用该 ID
- 可通过 `WithEmbedding` 选项传入 Embedder，Indexer 自动对文档内容向量化后存储

### 2.3 Retriever:查询召回

`retriever.Retriever` 接口(`interface.go:49`):
```go
type Retriever interface {
	Retrieve(ctx context.Context, query string, opts ...Option) ([]*schema.Document, error)
}
```

**契约要点:**
- 输入查询字符串，输出按相关性排序的文档列表(**最相关在前**)
- 相似度分数放在 `doc.MetaData["score"]` 里，由后端填充
- 可通过 `WithEmbedding` 传入 Embedder，Retriever 自动对查询向量化后搜索
- 支持 `WithTopK` 限制返回数量、`WithScoreThreshold` 过滤低分文档

## 三、Option 机制:通用+实现特定二分法

三个组件都遵循 Eino 标准的 Option 设计:和 ChatModel/Tool 一样，**通用选项 + 实现特定选项**共享同一个 `[]Option` 切片，按类型分派提取。

### 3.1 Embedding Option

```go
// 通用选项
type Options struct {
	Model *string  // 覆盖模型名
}

// 构造通用选项
embedding.WithModel("text-embedding-3-large")
```

提取方式和 ChatModel 完全一致:
```go
// 在实现内提取
common := embedding.GetCommonOptions(nil, opts...)
mine := embedding.GetImplSpecificOptions(&MyOptions{}, opts...)
// common.Model 拿到通用选项，mine.MyParam 拿到实现特定选项
```

### 3.2 Indexer Option

```go
// 通用选项
type Options struct {
	Index       *string       // 指定入库的目标索引
	SubIndexes []string      // 写入多个子分区
	Embedding   embedding.Embedder  // 入库时自动对文档向量化
}

// 构造通用选项
indexer.WithIndex("my-index")
indexer.WithSubIndexes([]string{"partition-a"})
indexer.WithEmbedding(embedder)  // 自动向量化
```

### 3.3 Retriever Option

```go
// 通用选项
type Options struct {
	Index           *string       // 指定搜索的目标索引
	SubIndex        *string       // 指定搜索的子分区
	TopK            *int          // 返回 top K 结果
	ScoreThreshold  *float64      // 分数阈值过滤(低于阈值排除)
	Embedding       embedding.Embedder  // 查询时自动向量化
	DSLInfo         map[string]any  // 后端特定查询表达式
}

// 构造通用选项
retriever.WithTopK(5)
retriever.WithScoreThreshold(0.5)
retriever.WithEmbedding(embedder)
```

### 3.4 实现特定选项

所有组件都支持实现特定选项，方式与 ChatModel 完全相同:
```go
// 实现方定义
func WithMyParam(v string) embedding.Option {
	return embedding.WrapImplSpecificOptFn(func(o *MyOptions) {
		o.MyParam = v
	})
}

// 调用方使用
embedder.EmbedStrings(ctx, texts, embedding.WithModel("model"), WithMyParam("value"))
```

提取:
```go
func (e *MyEmbedder) EmbedStrings(ctx context.Context, texts []string, opts ...embedding.Option) ([][]float64, error) {
	common := embedding.GetCommonOptions(nil, opts...)
	mine := embedding.GetImplSpecificOptions(&MyOptions{Default: "default"}, opts...)
	// ...
}
```

## 四、RAG 完整流水线示例

以下示例演示从离线构建索引到在线问答的完整流程，使用 Redis 向量库 + OpenAI Embedding:

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/embedding"
	"github.com/cloudwego/eino/components/indexer"
	"github.com/cloudwego/eino/components/retriever"
	"github.com/cloudwego/eino/schema"

	// eino-ext 实现
	"github.com/cloudwego/eino-ext/components/model/openai"
	redis "github.com/cloudwego/eino-ext/components/indexer/redis"
)

func main() {
	ctx := context.Background()

	// 1. 构造 Embedder
	emb, err := openai.NewEmbedding(ctx, &openai.EmbeddingConfig{
		APIKey: "your-api-key",
		Model:  "text-embedding-ada-002",
	})
	if err != nil { panic(err) }

	// 2. 构造 Redis Indexer + Retriever
	client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	idx, err := redis.NewIndexer(ctx, &redis.IndexerConfig{
		Client:    client,
		IndexName: "my_docs",
		Embedder:  emb, // 自动向量化
	})
	if err != nil { panic(err) }

	ret, err := redis.NewRetriever(ctx, &redis.RetrieverConfig{
		Client:    client,
		IndexName: "my_docs",
		Embedder:  emb, // 自动向量化查询
		TopK:      5,   // 默认返回 top 5
	})
	if err != nil { panic(err) }

	// ========== 离线:构建索引 ==========
	docs := []*schema.Document{
		{Content: "Eino 是 CloudWeGo 团队开源的 Go 语言 LLM 应用开发框架"},
		{Content: "Eino 提供组件抽象、图编排、ADK 智能体套件三层能力"},
		{Content: "Eino 支持流式输出、中断恢复、回调可观测性等生产级特性"},
	}

	ids, err := idx.Store(ctx, docs,
		indexer.WithEmbedding(emb), // 也可在这里再次指定 Embedder，覆盖构造时的
	)
	if err != nil { panic(err) }
	fmt.Printf("Indexed %d documents, IDs: %v\n", len(ids), ids)

	// ========== 在线:检索问答 ==========
	query := "eino 提供哪些能力"
	recalled, err := ret.Retrieve(ctx, query,
		retriever.WithTopK(3),
		retriever.WithScoreThreshold(0.5),
	)
	if err != nil { panic(err) }

	fmt.Printf("\nRecalled %d documents:\n", len(recalled))
	for i, doc := range recalled {
		fmt.Printf("  %d. %s\n", i+1, doc.Content)
	}

	// 下一步:将 recalled 文档拼入 ChatTemplate，喂给 ChatModel 生成答案
}
```

## 五、RAG 流水线在 Graph/Workflow 中的编排

在编排中，可直接用 `AddRetrieverNode` / `AddIndexerNode` 将组件接入图，无需包装 Lambda:

```go
// Workflow 中的 RAG 示例
wf := compose.NewWorkflow[map[string]any, string]()

// query 从输入来，retrieve 输出 documents
retrieveNode := wf.AddRetrieverNode("retrieve", retriever)
retrieveNode.AddInput(compose.START, compose.FromField("query")) // 从 START 输入取 query 字段

// chat template 节点:拼 prompt
// ...

// chat model 节点:生成回答
// ...

wf.AddEnd("chat", compose.ToField("output"))
```

关键点:
- `AddRetrieverNode` 自动处理输入输出类型转换，输入 `string` → 输出 `[]*schema.Document`
- 若需要在检索后做重排(rerank)，可再加一个 Lambda 或 Transformer 节点
- Indexer 通常离线运行，不放在在线问答 Graph 里

## 六、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **Embedder 不匹配** | Indexer 和 Retriever 使用了不同的 Embedder 模型，维度不一致 | 必须同一个 Embedder 实例，至少模型必须相同 |
| **维度 mismatch panic** | 换了 Embedder 模型但向量库已有旧维度数据 | 删除旧索引重建，向量维度变了必须重建 |
| **WithTopK 不生效** | 把 `retriever.WithTopK` 写在构造 Retriever 时 | `TopK` 是调用时选项，必须在 `Retrieve()` 调用时传 |
| **分数阈值理解错误** | `ScoreThreshold` 是**排除低分**，不是保留高分 | 文档分数 < 阈值会被排除，阈值要设对(如向量余弦相似度范围 [-1,1]，阈值设 0.5 会排除分数 ≤0.5 的) |
| **空结果不报错** | 查询召回零文档是正常语义，不是错误 | 检查 `len(docs) == 0`，业务层处理"没有找到相关内容" |
| **多分区使用错误** | Indexer `WithSubIndexes` 和 Retriever `WithSubIndex` 不匹配 | 入库写了哪些子分区，查询只能选其中一个，不能查不存在的分区 |

## 七、设计要点小结

| 设计点 | 手段 | 收益 |
|--------|------|------|
| **三接口分离** | Embedding / Indexer / Retriever 分开 | 可独立替换实现(换向量库不换 Embedding 模型，反之亦然) |
| **Embedder 注入** | Indexer/Retriever 接受 `WithEmbedding` 选项，不自己持有 | 调用方控制共享同一个 Embedder，保证一致性 |
| **Option 统一范式** | 通用选项 + 实现特定选项双槽结构 | 和 ChatModel/Tool 一致的使用体验，实现可扩展性 |
| **schema.Document** | 统一文档结构，含 ID/Content/MetaData | 上层编排不关心后端存储，可互换不同向量库 |

三个组件协作就是 RAG 的核心骨架：Embedding 提供语义表示，Indexer 负责持久化，Retriever 负责召回。Eino 的接口抽象让你可以灵活组合不同的开源实现，适配你的现有向量库。

## 八、参考

- [RAG 概念介绍](https://www.cloudwego.io/zh/docs/eino/quickstart/rag_tutorial/)
- 组件总览:[README.md](./README.md)
- eino-ext 实现:https://github.com/cloudwego/eino-ext/tree/main/components
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/components/embedding`、`retriever`、`indexer`
