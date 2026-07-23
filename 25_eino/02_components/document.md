# Loader / Parser / Transformer 文档处理

> 源码:`/Users/songxijun/workspace/otherProject/eino/components/document/`、`parser/`
> 核心文件: `interface.go`、`option.go`、`parser/interface.go`
> 本文阐述文档处理三阶段：加载、解析、变换的接口契约与使用。

## 一、概述

在 RAG 流水线中，**原始文档 → 可检索切片**需要三个处理步骤：

| 组件 | 职责 | 输入 → 输出 |
|------|------|-------------|
| **Loader** | 从外部源加载原始字节 | `document.Source`(URI) → `[]*schema.Document` |
| **Parser** | 解析原始字节为结构化文档 | `io.Reader` → `[]*schema.Document` |
| **Transformer** | 对文档做变换（切分、过滤、重排） | `[]*schema.Document` → `[]*schema.Document` |

三者协作构成完整文档处理流水线：
```
原始文档文件
    ↓ Loader 根据 URI 读取字节
    ↓ Parser 解析字节为结构化文档
    ↓ Transformer 切分/清洗/过滤得到最终切片
    ↓ Embedder 向量化 → Indexer 入库
```

实现都在 [eino-ext](https://github.com/cloudwego/eino-ext/components/document)，核心仓库仅定义接口。常见实现：
- Loader: 文件系统、S3、HTTP
- Parser: Text 纯文本、PDF、Markdown
- Transformer: 按字符切分、递归切分、语义切分

## 二、接口契约详解

### 2.1 Loader:从源加载文档

`document.Loader` 接口(`interface.go:43`):
```go
type Loader interface {
	Load(ctx context.Context, src Source, opts ...LoaderOption) ([]*schema.Document, error)
}

// Source 定义文档来源
type Source struct {
	URI string  // 本地路径 / URL
}
```

**契约要点:**
- `URI` 可以是本地文件路径，也可以是远程 URL，Loader 负责识别协议并读取
- 单个源可能产出多个文档（例如 PDF 每页一个文档）
- 必须把 `URI` 填入 `doc.MetaData`，下游需要溯源
- Parser 通常注入在 Loader 内部，Loader 读取字节后调用 Parser

### 2.2 Parser:解析字节为文档

`parser.Parser` 接口(`parser/interface.go:35`):
```go
type Parser interface {
	Parse(ctx context.Context, reader io.Reader, opts ...Option) ([]*schema.Document, error)
}
```

**契约要点:**
- 消费 `io.Reader`，产出 `[]*schema.Document`
- 单个文件可产出多个文档（如 PDF 按页拆分）
- 一般不直接调用，由 Loader 内部调用
- 可通过 `parser.WithExtraMeta` 添加额外元数据到所有文档

**内置 `TextParser`:**
eino 自带纯文本解析器，直接把整个内容当成一个文档：
```go
parser := text.NewParser()  // 开箱即用，不需要额外依赖
```

**ExtParser 扩展解析:**
`ExtParser` 可以根据 URI 后缀自动选解析器:
```go
// ext_parser.go 支持根据后缀分发到不同 parser
parser := parser.NewExtParser(map[string]parser.Parser{
	".txt": text.NewParser(),
	".md":  markdown.NewParser(),
	".pdf": pdf.NewParser(),
})
// 然后 Loader 使用这个 parser 会根据文件扩展名选对解析器
```

### 2.3 Transformer:文档变换

`document.Transformer` 接口(`interface.go:54`):
```go
type Transformer interface {
	Transform(ctx context.Context, src []*schema.Document, opts ...TransformerOption) ([]*schema.Document, error)
}
```

**最常见变换：文本切分**
大文档需要切成小块才能向量化和检索，Transformer 负责切分：
- 按字符数切分，可控制重叠
- 递归切分（按markdown标题/段落切分后再合并）
- 语义切分（基于模型判断断点）

**其他常见变换:**
- 过滤：去掉太短/太长的文档
- 合并：把多个小文档合并
- 重排序：改变文档顺序

**契约要点:**
- 输入输出都是 `[]*schema.Document`，可增可删可修改
- 应当**保留原有元数据**，新增元数据合并进去，不要替换整个 `MetaData`
- 下游 Indexer 需要元数据溯源，所以 `SourceURI` 不能丢

## 三、Option 机制

三个组件都遵循 Eino 标准的"通用选项 + 实现特定选项"模式：

### 3.1 Loader Option

```go
// 通用选项
document.WithParserOptions(opts ...parser.Option)  // 传递给内部 Parser 的选项
```

提取方式：
```go
func (l *MyLoader) Load(ctx context.Context, src Source, opts ...document.LoaderOption) ([]*schema.Document, error) {
	// 提取通用选项
	commonOpts := document.GetLoaderCommonOptions(nil, opts...)
	// 提取实现特定选项
	myOpts := document.GetLoaderImplSpecificOptions(&MyOptions{Default: "foo"}, opts...)
	// ...
}
```

自定义实现特定选项：
```go
func WithMyOption(v string) document.LoaderOption {
	return document.WrapLoaderImplSpecificOptFn(func(o *MyOptions) {
		o.V = v
	})
}
```

### 3.2 Parser Option

```go
// 通用选项
parser.WithURI(uri string)          // 设置源 URI
parser.WithExtraMeta(meta map[string]any)  // 添加额外元数据
```

提取方式和其他组件一样：`parser.GetCommonOptions` + `parser.GetImplSpecificOptions`。

### 3.3 Transformer Option

Transformer 没有预定义通用选项，只有实现特定选项机制：
```go
func WithMyOption(v int) document.TransformerOption {
	return document.WrapTransformerImplSpecificOptFn(func(o *MyOptions) {
		o.V = v
	})
}
```

提取：
```go
func (t *MyTransformer) Transform(ctx context.Context, src []*schema.Document, opts ...document.TransformerOption) ([]*schema.Document, error) {
	myOpts := document.GetTransformerImplSpecificOptions(&MyOptions{Default: 10}, opts...)
	// ...
}
```

## 四、完整示例：文件加载 → 切分 → 入库

```go
package main

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/document"
	"github.com/cloudwego/eino/components/document/parser"
	"github.com/cloudwego/eino/components/document/parser/text"
	"github.com/cloudwego/eino/components/embedding"
	"github.com/cloudwego/eino/components/indexer"
	"github.com/cloudwego/eino/schema"

	// eino-ext 实现
	"github.com/cloudwego/eino-ext/components/document/loader/file"
	"github.com/cloudwego/eino-ext/components/document/transformer/splitter"
	"github.com/cloudwego/eino-ext/components/indexer/redis"
	"github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
	ctx := context.Background()

	// 1. Loader: 从本地文件加载
	l, err := file.NewLoader(file.LoaderConfig{
		Parser: text.NewParser(),  // 纯文本解析
	})
	if err != nil { panic(err) }

	// 加载单个文件
	docs, err := l.Load(ctx, document.Source{URI: "./my_doc.txt"})
	if err != nil { panic(err) }
	fmt.Printf("Loaded %d documents\n", len(docs))  // 通常 1 个文档

	// 2. Transformer: 按字符切分
	tr, err := splitter.NewCharacterTextSplitter(splitter.CharacterTextSplitterConfig{
		ChunkSize:     500,  // 每块 500 字符
		ChunkOverlap:  50,   // 重叠 50 字符
		KeepSeparator: true,
	})
	if err != nil { panic(err) }

	splittedDocs, err := tr.Transform(ctx, docs)
	if err != nil { panic(err) }
	fmt.Printf("Split into %d chunks\n", len(splittedDocs))

	// 3. Embedding + Indexer: 向量化并入 Redis 向量库
	emb, err := openai.NewEmbedding(ctx, &openai.EmbeddingConfig{
		APIKey: "your-key",
		Model:  "text-embedding-ada-002",
	})
	if err != nil { panic(err) }

	idx, err := redis.NewIndexer(ctx, redis.IndexerConfig{
		Client:    redis.NewClient(&redis.Options{Addr: "localhost:6379"}),
		IndexName: "my_docs",
		Embedder:  emb,  // 自动向量化
	})
	if err != nil { panic(err) }

	ids, err := idx.Store(ctx, splittedDocs)
	if err != nil { panic(err) }
	fmt.Printf("Indexed %d chunks, IDs: %v\n", len(ids), ids)
}
```

## 五、在 Graph/Workflow 中编排文档流水线

```go
// Workflow 示例：离线构建索引
wf := compose.NewWorkflow[string, []string]()

// 加载 -> 解析 -> 切分 -> 向量化 -> 入库
loadNode := wf.AddLoaderNode("load", loader)
loadNode.AddInput(compose.START, compose.FromField("uri"))  // 输入 URI

splitNode := wf.AddTransformerNode("split", transformer)
splitNode.AddInput("load")  // 输入就是 load 输出的 []*schema.Document

indexNode := wf.AddIndexerNode("index", indexer)
indexNode.AddInput("split", embedding.WithEmbedding(emb))  // 注入 Embedder

wf.AddEnd("index")
```

关键点：
- `AddLoaderNode` / `AddTransformerNode` / `AddIndexerNode` 都是编排层提供的语法糖，直接接入
- 每个步骤输入输出类型固定，编排层自动处理

## 六、常见坑与排错

| 问题 | 原因 | 解法 |
|------|------|------|
| **切分后文档数量不对** | `ChunkSize` / `ChunkOverlap` 参数设置不对 | 根据你的文档平均长度调整，重叠通常是块大小 10% |
| **Parser 不识别文件格式** | 使用 `ExtParser` 但没对应扩展名的解析器 | 检查文件扩展名，添加对应 parser 到扩展映射 |
| **元数据丢失** | Transformer 新建了 `doc` 没复制原有元数据 | 始终保留原有 `MetaData`，只合并新增字段，不要替换整个 |
| **Loader 返回空文档不报错** | 文件为空是正常情况，返回空切片不是错误 | 业务代码检查 `len(docs) == 0` |
| **PDF 解析需要额外依赖** | PDF 解析依赖第三方库（如 `github.com/yuin/goldmark` 对 markdown，`github.com/ledongthuc/pdf` 对 pdf） | go get 对应依赖，eino-ext 不把这些放进 go.mod 需要你自己引入 |

## 七、设计要点小结

| 设计点 | 手段 | 收益 |
|--------|------|------|
| **三阶段分离** | Loader / Parser / Transformer 分开接口 | 可独立组合替换——换切分算法不换 loader，换存储不换切分 |
| **Parser 注入 Loader** | Loader 内部持有 Parser，对外一个入口 | 使用者 `Load` 一步到位，不需要自己读字节调 parser |
| **ExtParser 按扩展名分发** | 映射后缀 → parser，自动选择 | 多格式混合目录批量加载很方便 |
| **Option 统一模式** | 和其他组件一致的通用+实现特定二分法 | 学习成本低，实现者容易扩展 |
| **保留元数据** | 约定 Transformers 合并不替换元数据 | 溯源信息从加载到入库一直保留 |

文档处理是 RAG 的"第一公里"，质量好坏直接影响检索效果。Eino 把每个步骤拆成独立接口，方便你根据文档类型选择最优实现，也方便替换改进。

## 八、参考

- [RAG 官方教程](https://www.cloudwego.io/zh/docs/eino/quickstart/rag_tutorial/)
- 组件总览:[README.md](./README.md)
- 索引/检索:[retriever_indexer.md](./retriever_indexer.md)
- eino-ext 实现: https://github.com/cloudwego/eino-ext/tree/main/components/document
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/components/document`
