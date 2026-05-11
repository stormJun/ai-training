# Token 管理最佳实践

> **适用场景**: 大规模 RAG 系统（知识库节点 > 60 万）需要重点关注 Token 管理，小型系统可适度关注

## 1. 概述

### 1.1 为什么需要 Token 管理

在 RAG 系统中，Token 管理是确保系统稳定性和响应质量的关键环节：

```
┌──────────────────────────────────────────────┐
│         Token 管理的核心目标                  │
└──────────────────────────────────────────────┘

1. 避免超限错误
   ├─ 超过模型上下文窗口导致 API 报错
   ├─ 文档被截断，信息不完整
   └─ 历史对话丢失，上下文断裂

2. 优化成本
   ├─ Token 使用直接影响 API 调用成本
   ├─ 减少不必要的 Token 消耗
   └─ 提高资源利用率

3. 保证质量
   ├─ 确保关键信息不被截断
   ├─ 平衡上下文长度和检索精度
   └─ 维持对话连贯性

4. 提升性能
   ├─ 减少 API 调用次数
   ├─ 降低响应延迟
   └─ 提高吞吐量
```

### 1.2 Token 管理的适用场景

| 知识库规模 | Token 管理重要性 | 建议策略 |
|-----------|----------------|---------|
| **< 10 万节点** | ⭐⭐ 低 | 基础检查即可 |
| **10-60 万节点** | ⭐⭐⭐ 中等 | 启用日志监控 |
| **> 60 万节点** | ⭐⭐⭐⭐⭐ 高 | 完整 Token 管理 |
| **生产环境** | ⭐⭐⭐⭐ 高 | 全量日志 + 告警 |

## 2. 核心概念

### 2.1 Token 窗口大小计算

**核心公式**:

```
总窗口 = 模型窗口 - 输出预留 - 安全边界 - 各固定部分
```

**详细公式**:

```python
limited_token_nums = (
    token_window          # 模型总窗口（如 4096, 8192, 128k）
    - max_token           # 输出预留（生成答案的 token 数）
    - offcut_token        # 安全边界（默认 50）
    - query_token_num     # 查询 token 数
    - history_token_num   # 历史对话 token 数
    - template_token_num  # 提示模板 token 数
    - reference_field_token_num  # 参考字段 token 数
)
```

**示例计算**:

```python
# 假设使用 GPT-3.5-turbo (4096 窗口)
token_window = 4096
max_token = 1024           # 输出预留 1024 tokens
offcut_token = 50          # 安全边界 50 tokens
query_token_num = 20       # 用户查询 20 tokens
history_token_num = 200    # 历史对话 200 tokens
template_token_num = 100   # 提示模板 100 tokens
reference_field_token_num = 30  # 参考字段 30 tokens

limited_token_nums = 4096 - 1024 - 50 - 20 - 200 - 100 - 30
                    = 2672 tokens

# 结论：可用于检索文档的 token 数为 2672
```

### 2.2 各组成部分详解

```
┌──────────────────────────────────────────────┐
│       Token 窗口组成部分                      │
└──────────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  模型总窗口 (token_window)             │  4096 / 8192 / 128k
│  ├─ GPT-3.5-turbo: 4096 / 16k          │
│  ├─ GPT-4: 8192 / 32k                  │
│  └─ GPT-4-turbo: 128k                  │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  输出预留 (max_token)                  │  512 - 4096
│  ├─ 简单问答: 512                      │
│  ├─ 复杂问答: 1024                     │
│  └─ 长文本生成: 2048-4096              │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  安全边界 (offcut_token)               │  50 - 100
│  ├─ 防止边界误差                       │
│  ├─ 应对特殊字符                       │
│  └─ 保守估计余量                       │
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  固定部分 (各固定组件)                 │
│  ├─ 查询 (query_token_num)             │  10 - 100
│  ├─ 历史对话 (history_token_num)       │  0 - 1000+
│  ├─ 提示模板 (template_token_num)      │  50 - 500
│  └─ 参考字段 (reference_field_token_num)│  0 - 100
└────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│  可用于文档的 Token (limited_token_nums)│  剩余空间
│  ├─ 检索文档内容                       │
│  ├─ 上下文信息                         │
│  └─ 知识库内容                         │
└────────────────────────────────────────┘
```

## 3. Token 计算方法

### 3.1 基础 Token 计算函数

```python
import tiktoken

def num_tokens(text: str, model: str = 'gpt-3.5-turbo-0613') -> int:
    """
    计算文本的 token 数量

    Args:
        text: 输入文本
        model: 模型名称

    Returns:
        token 数量
    """
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text, disallowed_special=()))
```

### 3.2 消息 Token 计算（OpenAI API 格式）

```python
def num_tokens_from_messages(messages, tokenizer, use_cl100k_base=True):
    """
    计算 OpenAI API 消息格式的 token 数

    Args:
        messages: 消息列表，格式 [{"role": "user", "content": "..."}]
        tokenizer: tiktoken 编码器
        use_cl100k_base: 是否使用 cl100k_base 编码（GPT-4/GPT-3.5-turbo）

    Returns:
        token 数量（含 10-20% 余量）
    """
    total_tokens = 0

    for message in messages:
        if isinstance(message, dict):
            for key, value in message.items():
                total_tokens += 3  # role 的开销（key 的开销）

                if isinstance(value, str):
                    tokens = tokenizer.encode(value, disallowed_special=())
                    total_tokens += len(tokens)

        elif isinstance(message, str):
            tokens = tokenizer.encode(message, disallowed_special=())
            total_tokens += len(tokens)

    # 添加安全余量
    if use_cl100k_base:
        total_tokens *= 1.2  # cl100k_base 编码额外 20% 余量
    else:
        total_tokens *= 1.1  # 普通编码 10% 余量

    return int(total_tokens)
```

**为什么需要 1.1-1.2 倍系数？**

```
1. 编码差异
   - 不同编码器（tokenizer）实现可能略有差异
   - 特殊字符处理方式不同

2. 动态变化
   - 某些 token 在不同上下文中可能被拆分
   - 格式化字符（换行、空格）的编码可能变化

3. 安全边界
   - 保守估计，避免边界情况超限
   - 应对未预见的 token 增长
```

### 3.3 文档 Token 计算

```python
def num_tokens_from_docs(docs, tokenizer, use_cl100k_base=True):
    """
    计算文档列表的 token 数

    Args:
        docs: 文档列表（LangChain Document 对象）
        tokenizer: tiktoken 编码器
        use_cl100k_base: 是否使用 cl100k_base 编码

    Returns:
        token 数量（含余量）
    """
    total_tokens = 0

    for doc in docs:
        # 提取文档内容
        tokens = tokenizer.encode(doc.page_content, disallowed_special=())
        total_tokens += len(tokens)

    # 添加安全余量
    if use_cl100k_base:
        total_tokens *= 1.2
    else:
        total_tokens *= 1.1

    return int(total_tokens)
```

### 3.4 专用 Token 计算

```python
# Embedding Token 计算
def num_tokens_embed(text: str) -> int:
    """计算用于 embedding 的 token 数"""
    return num_tokens(text, model='gpt-3.5-turbo-0613')

# Rerank Token 计算
def num_tokens_rerank(text: str) -> int:
    """计算用于 rerank 的 token 数"""
    return num_tokens(text, model='gpt-3.5-turbo-0613')
```

## 4. Token 检查机制

### 4.1 完整的 Token 检查流程

```python
import logging

# 配置日志（必须设置为 INFO 级别才能查看详细 token 信息）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenManager:
    """Token 管理器"""

    def __init__(self, token_window, max_token, offcut_token=50):
        self.token_window = token_window
        self.max_token = max_token
        self.offcut_token = offcut_token
        self.tokenizer = tiktoken.encoding_for_model('gpt-3.5-turbo')

    def calculate_limited_tokens(
        self,
        query: str,
        history: list,
        template: str,
        reference_fields: str = ""
    ):
        """
        计算可用于文档的 token 数

        Args:
            query: 用户查询
            history: 历史对话列表
            template: 提示模板
            reference_fields: 参考字段（如元数据）

        Returns:
            limited_token_nums: 可用于文档的 token 数
            tokens_msg: 详细的 token 计算信息
        """
        # 1. 计算各部分 token 数
        query_token_num = num_tokens(query)
        history_token_num = self.num_tokens_from_messages(history)
        template_token_num = num_tokens(template)
        reference_field_token_num = num_tokens(reference_fields)

        # 2. 计算剩余 token 数
        limited_token_nums = (
            self.token_window
            - self.max_token
            - self.offcut_token
            - query_token_num
            - history_token_num
            - template_token_num
            - reference_field_token_num
        )

        # 3. 记录详细日志（INFO 级别）
        logger.info("=" * 50)
        logger.info(f"Token 窗口计算详情:")
        logger.info(f"  token_window = {self.token_window}")
        logger.info(f"  max_token = {self.max_token}")
        logger.info(f"  offcut_token = {self.offcut_token}")
        logger.info(f"  limited_token_nums = {limited_token_nums}")
        logger.info(f"  query_token_num = {query_token_num}")
        logger.info(f"  history_token_num = {history_token_num}")
        logger.info(f"  template_token_num = {template_token_num}")
        logger.info(f"  reference_field_token_num = {reference_field_token_num}")
        logger.info("=" * 50)

        # 4. 构建 token 信息消息
        tokens_msg = (
            f"总窗口: {self.token_window} - "
            f"输出预留: {self.max_token} - "
            f"安全边界: {self.offcut_token} - "
            f"查询: {query_token_num} - "
            f"历史: {history_token_num} - "
            f"模板: {template_token_num} - "
            f"参考字段: {reference_field_token_num} = "
            f"剩余: {limited_token_nums}"
        )

        return limited_token_nums, tokens_msg

    def check_and_trim_docs(self, docs, limited_token_nums, web_chunk_size=400):
        """
        检查并裁剪文档列表以符合 token 限制

        Args:
            docs: 文档列表
            limited_token_nums: 可用的 token 数
            web_chunk_size: 每个 chunk 的最小 token 数

        Returns:
            trimmed_docs: 裁剪后的文档列表
            total_token_num: 实际使用的 token 数
        """
        trimmed_docs = []
        total_token_num = 0

        for doc in docs:
            doc_token_num = num_tokens(doc.page_content)

            # 检查是否超过限制
            if total_token_num + doc_token_num <= limited_token_nums:
                trimmed_docs.append(doc)
                total_token_num += doc_token_num
                logger.info(f"添加文档: token={doc_token_num}, 累计={total_token_num}")
            else:
                logger.warning(f"文档 token 超限，停止添加: {doc_token_num}")
                break

        # 检查是否所有文档都被移除
        if len(trimmed_docs) == 0:
            logger.error(
                f"剩余 token 不足: {limited_token_nums} < 最小 chunk 大小: {web_chunk_size}"
            )
            raise TokenLimitError(
                f"可用 token 不足 ({limited_token_nums} < {web_chunk_size})，"
                f"请增加总 token 数或减少输出 token 数"
            )

        logger.info(f"最终文档数: {len(trimmed_docs)}, 总 token: {total_token_num}")

        return trimmed_docs, total_token_num


class TokenLimitError(Exception):
    """Token 限制错误"""
    pass
```

### 4.2 历史对话 Token 检查

```python
def check_and_compress_history(
    history: list,
    max_history_tokens: int = 1000,
    model_window: int = 4096,
    safety_margin: int = 256
):
    """
    检查并压缩历史对话以符合 token 限制

    Args:
        history: 历史对话列表 [{"role": "user", "content": "..."}, ...]
        max_history_tokens: 历史对话最大 token 数
        model_window: 模型窗口大小
        safety_margin: 安全边界（从窗口上限预留）

    Returns:
        compressed_history: 压缩后的历史对话
    """
    if not history:
        return []

    tokenizer = tiktoken.encoding_for_model('gpt-3.5-turbo')
    compressed_history = history.copy()

    # 计算当前历史对话的 token 数
    history_tokens = num_tokens_from_messages(compressed_history, tokenizer)

    logger.info(f"历史对话 token 数: {history_tokens}")

    # 如果超过限制，逐步移除最早的对话
    while history_tokens > max_history_tokens or \
          history_tokens > (model_window - safety_margin):

        if len(compressed_history) <= 2:
            logger.warning("历史对话已压缩至最小，仍超限")
            break

        # 移除最早的一轮对话（user + assistant）
        compressed_history = compressed_history[2:]

        # 重新计算 token 数
        history_tokens = num_tokens_from_messages(compressed_history, tokenizer)
        logger.info(f"压缩后历史 token 数: {history_tokens}")

    logger.info(f"最终历史对话轮数: {len(compressed_history) // 2}")

    return compressed_history
```

### 4.3 聚合文档时的 Token 检查

```python
def aggregate_docs_with_token_check(
    first_docs: list,
    second_docs: list,
    limited_token_nums: int
):
    """
    聚合两组文档，并进行 token 检查

    Args:
        first_docs: 第一组文档（优先级高）
        second_docs: 第二组文档（补充）
        limited_token_nums: 可用的 token 数

    Returns:
        aggregated_docs: 聚合后的文档列表
    """
    aggregated_docs = []
    total_tokens = 0

    # 1. 先添加第一组文档
    for doc in first_docs:
        doc_tokens = num_tokens(doc.page_content)

        if total_tokens + doc_tokens <= limited_token_nums:
            aggregated_docs.append(doc)
            total_tokens += doc_tokens
        else:
            logger.warning(f"第一组文档超限，停止添加")
            break

    # 2. 再添加第二组文档（如果有剩余空间）
    if total_tokens < limited_token_nums:
        remaining_tokens = limited_token_nums - total_tokens
        logger.info(f"剩余空间: {remaining_tokens} tokens")

        for doc in second_docs:
            doc_tokens = num_tokens(doc.page_content)

            if total_tokens + doc_tokens <= limited_token_nums:
                aggregated_docs.append(doc)
                total_tokens += doc_tokens
            else:
                logger.warning(f"第二组文档超限，停止添加")
                break

    logger.info(f"聚合完成: {len(aggregated_docs)} 个文档, {total_tokens} tokens")

    return aggregated_docs
```

## 5. 日志记录和调试

### 5.1 日志级别配置

**重要**: 必须将日志级别设置为 `INFO` 才能查看详细的 Token 计算信息！

```python
import logging

# 方式 1: 全局配置
logging.basicConfig(
    level=logging.INFO,  # 必须是 INFO 或 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 方式 2: 针对 Token 管理模块配置
token_logger = logging.getLogger('token_manager')
token_logger.setLevel(logging.INFO)

# 方式 3: 通过配置文件
# logging_config.yaml
version: 1
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
loggers:
  token_manager:
    level: INFO
    handlers: [console]
```

### 5.2 详细日志示例

```python
# 正常情况下的日志输出
"""
==================================================
Token 窗口计算详情:
  token_window = 4096
  max_token = 1024
  offcut_token = 50
  limited_token_nums = 2672
  query_token_num = 20
  history_token_num = 200
  template_token_num = 100
  reference_field_token_num = 30
==================================================
添加文档: token=150, 累计=150
添加文档: token=180, 累计=330
添加文档: token=200, 累计=530
文档 token 超限，停止添加: 2500
最终文档数: 3, 总 token: 530
"""

# Token 不足时的错误日志
"""
ERROR - 剩余 token 不足: 300 < 最小 chunk 大小: 400
ERROR - 可用 token 不足 (300 < 400)，请增加总 token 数或减少输出 token 数
"""
```

### 5.3 Token 监控指标

```python
class TokenMonitor:
    """Token 使用监控"""

    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "token_overflows": 0,
            "avg_token_usage": 0,
            "max_token_usage": 0,
            "history_compressions": 0
        }

    def record_token_usage(self, used_tokens, limited_tokens):
        """记录 token 使用情况"""

        self.metrics["total_queries"] += 1

        usage_ratio = used_tokens / limited_tokens
        self.metrics["avg_token_usage"] = (
            (self.metrics["avg_token_usage"] * (self.metrics["total_queries"] - 1) + usage_ratio)
            / self.metrics["total_queries"]
        )

        if used_tokens > self.metrics["max_token_usage"]:
            self.metrics["max_token_usage"] = used_tokens

        # 记录详细日志
        logger.info(f"Token 使用率: {usage_ratio:.2%} ({used_tokens}/{limited_tokens})")

        # 告警检查
        if usage_ratio > 0.9:
            logger.warning(f"Token 使用率超过 90%: {usage_ratio:.2%}")

        if used_tokens > limited_tokens:
            self.metrics["token_overflows"] += 1
            logger.error(f"Token 溢出: {used_tokens} > {limited_tokens}")

    def get_report(self):
        """获取监控报告"""

        return {
            **self.metrics,
            "overflow_rate": self.metrics["token_overflows"] / max(self.metrics["total_queries"], 1)
        }
```

## 6. 实战案例

### 6.1 案例 1: 基础 RAG 系统 Token 管理

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI

# 1. 初始化
llm = OpenAI(model="gpt-3.5-turbo", max_tokens=1024)
token_manager = TokenManager(
    token_window=4096,
    max_token=1024,
    offcut_token=50
)

# 2. 加载文档
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# 3. 查询时进行 token 管理
def query_with_token_management(query: str, history: list = None):
    """带 token 管理的查询"""

    # 3.1 计算 token 限制
    template = "基于以下上下文回答问题：\n{context}\n\n问题：{query}"
    limited_tokens, tokens_msg = token_manager.calculate_limited_tokens(
        query=query,
        history=history or [],
        template=template
    )

    # 3.2 检索文档
    retriever = index.as_retriever(similarity_top_k=10)
    docs = retriever.retrieve(query)

    # 3.3 检查并裁剪文档
    try:
        trimmed_docs, used_tokens = token_manager.check_and_trim_docs(
            docs, limited_tokens
        )
    except TokenLimitError as e:
        return f"错误: {str(e)}\n\nToken 计算详情: {tokens_msg}"

    # 3.4 生成答案
    context = "\n\n".join([doc.text for doc in trimmed_docs])
    prompt = template.format(context=context, query=query)

    response = llm.complete(prompt)

    return response.text
```

### 6.2 案例 2: 大规模知识库的 Token 管理

```python
class LargeScaleRAGSystem:
    """大规模 RAG 系统的 Token 管理"""

    def __init__(self, index, llm, token_window=8192):
        self.index = index
        self.llm = llm
        self.token_manager = TokenManager(
            token_window=token_window,
            max_token=2048,  # 大规模系统预留更多输出空间
            offcut_token=100  # 更大的安全边界
        )
        self.monitor = TokenMonitor()

    def query(self, query: str, history: list = None):
        """带完整 token 管理的查询"""

        # 1. 历史对话压缩
        if history:
            history = check_and_compress_history(
                history,
                max_history_tokens=1000,
                model_window=self.token_manager.token_window
            )

        # 2. 计算 token 限制
        template = self._build_prompt_template()
        limited_tokens, tokens_msg = self.token_manager.calculate_limited_tokens(
            query=query,
            history=history or [],
            template=template
        )

        # 3. 多阶段检索
        # 3.1 第一阶段：向量检索
        retriever = self.index.as_retriever(similarity_top_k=20)
        first_docs = retriever.retrieve(query)

        # 3.2 第二阶段：关键词检索（可选）
        # second_docs = keyword_retriever.retrieve(query)

        # 4. Token 检查和文档聚合
        try:
            trimmed_docs, used_tokens = self.token_manager.check_and_trim_docs(
                first_docs, limited_tokens
            )

            # 记录监控指标
            self.monitor.record_token_usage(used_tokens, limited_tokens)

        except TokenLimitError as e:
            self.monitor.metrics["token_overflows"] += 1
            return {
                "answer": f"错误: {str(e)}",
                "tokens_msg": tokens_msg,
                "monitor": self.monitor.get_report()
            }

        # 5. 生成答案
        context = self._format_context(trimmed_docs)
        prompt = template.format(context=context, query=query)

        response = self.llm.complete(prompt)

        return {
            "answer": response.text,
            "used_docs": len(trimmed_docs),
            "used_tokens": used_tokens,
            "limited_tokens": limited_tokens,
            "tokens_msg": tokens_msg,
            "monitor": self.monitor.get_report()
        }

    def _build_prompt_template(self):
        """构建提示模板"""
        return (
            "你是一个专业的问答助手。请基于以下上下文回答用户问题。\n\n"
            "上下文：\n{context}\n\n"
            "问题：{query}\n\n"
            "答案："
        )

    def _format_context(self, docs):
        """格式化上下文"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append(f"[文档 {i}]\n{doc.text}")
        return "\n\n".join(formatted)
```

### 6.3 案例 3: 动态 Token 分配

```python
class DynamicTokenAllocator:
    """动态 Token 分配器"""

    def __init__(self, token_window=8192):
        self.token_window = token_window

    def allocate_tokens(
        self,
        query_complexity: str = "medium",
        history_length: int = 0,
        num_docs: int = 5
    ):
        """
        根据 query 复杂度动态分配 token

        Args:
            query_complexity: 查询复杂度 (simple/medium/complex)
            history_length: 历史对话长度
            num_docs: 期望检索的文档数量

        Returns:
            allocation: token 分配方案
        """
        # 1. 根据复杂度确定输出 token
        output_tokens = {
            "simple": 512,
            "medium": 1024,
            "complex": 2048
        }[query_complexity]

        # 2. 根据历史对话长度分配 token
        history_tokens = min(history_length * 100, 1000)

        # 3. 计算可用于文档的 token
        fixed_tokens = output_tokens + 50 + 100 + 50  # 输出 + 安全 + 模板 + 查询
        doc_tokens = self.token_window - fixed_tokens - history_tokens

        # 4. 计算每个文档的平均 token
        avg_doc_tokens = doc_tokens // num_docs

        allocation = {
            "output_tokens": output_tokens,
            "history_tokens": history_tokens,
            "doc_tokens": doc_tokens,
            "num_docs": num_docs,
            "avg_doc_tokens": avg_doc_tokens,
            "safety_margin": 50,
            "template_tokens": 100,
            "query_tokens": 50
        }

        logger.info(f"Token 分配方案: {allocation}")

        return allocation
```

## 7. 最佳实践

### 7.1 Token 管理清单

```
┌──────────────────────────────────────────────┐
│       Token 管理最佳实践清单                  │
└──────────────────────────────────────────────┘

✅ 必做项
  ├─ 设置日志级别为 INFO
  ├─ 计算 token 窗口时预留足够安全边界
  ├─ 使用 1.1-1.2 倍系数估算 token
  ├─ 对历史对话进行 token 检查和压缩
  └─ 记录详细的 token 使用日志

✅ 推荐项
  ├─ 实现 token 监控和告警
  ├─ 根据知识库规模调整 token 策略
  ├─ 对不同复杂度的查询动态分配 token
  └─ 定期分析 token 使用情况

✅ 避免项
  ├─ 不要忽略 token 超限错误
  ├─ 不要使用过小的安全边界（< 50）
  ├─ 不要在日志级别低于 INFO 时期望看到详细信息
  └─ 不要在小规模系统过度优化 token
```

### 7.2 不同规模的 Token 策略

| 知识库规模 | 输出预留 | 安全边界 | 历史对话 | 文档 Token | 日志级别 |
|-----------|---------|---------|---------|-----------|---------|
| **< 10 万** | 512-1024 | 50 | 不限制 | 自动 | WARNING |
| **10-60 万** | 1024-2048 | 50-100 | 限制 1000 | 检查 | INFO |
| **> 60 万** | 2048+ | 100 | 压缩至 500 | 严格检查 | INFO |
| **生产环境** | 2048+ | 100 | 压缩至 500 | 严格检查 + 监控 | INFO + 告警 |

### 7.3 性能优化建议

```python
# 1. 缓存 token 计算结果
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_num_tokens(text: str) -> int:
    """缓存 token 计算结果"""
    return num_tokens(text)

# 2. 批量计算 token
def batch_num_tokens(texts: list) -> list:
    """批量计算 token，提高效率"""
    tokenizer = tiktoken.encoding_for_model('gpt-3.5-turbo')
    return [len(tokenizer.encode(text)) for text in texts]

# 3. 预估 token（避免频繁计算）
def estimate_tokens(text: str, avg_chars_per_token: int = 4) -> int:
    """快速预估 token 数（基于字符数）"""
    return len(text) // avg_chars_per_token

# 4. 异步 token 检查
import asyncio

async def async_check_tokens(docs, limited_tokens):
    """异步检查 token"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        token_manager.check_and_trim_docs,
        docs,
        limited_tokens
    )
```

## 8. 常见问题

### Q1: 为什么我的日志看不到详细的 token 信息？

**A**: 必须将日志级别设置为 `INFO` 或 `DEBUG`。

```python
# ❌ 错误：日志级别太高
logging.basicConfig(level=logging.WARNING)

# ✅ 正确：设置为 INFO
logging.basicConfig(level=logging.INFO)
```

### Q2: Token 计算不准确怎么办？

**A**: 使用 1.1-1.2 倍系数，并增加安全边界。

```python
# 添加 20% 余量
actual_tokens = calculated_tokens * 1.2

# 增加安全边界
offcut_token = 100  # 默认 50，建议增加到 100
```

### Q3: 如何处理 token 超限？

**A**: 实现降级策略。

```python
def handle_token_overflow(limited_tokens, docs):
    """处理 token 超限"""

    # 策略 1: 减少文档数量
    if limited_tokens < 100:
        return []

    # 策略 2: 使用文档摘要
    summarized_docs = summarize_docs(docs, max_tokens=limited_tokens)

    # 策略 3: 提示用户调整参数
    if len(summarized_docs) == 0:
        raise TokenLimitError(
            "可用 token 不足，请增加总 token 数或减少输出 token 数"
        )

    return summarized_docs
```

### Q4: 小规模 RAG 系统需要关注 token 吗？

**A**: 知识库节点 < 60 万时，基础检查即可，无需过度优化。

```python
if num_nodes < 600000:
    # 简单策略
    token_manager = TokenManager(
        token_window=4096,
        max_token=1024,
        offcut_token=50
    )
else:
    # 严格策略
    token_manager = TokenManager(
        token_window=8192,
        max_token=2048,
        offcut_token=100
    )
```

## 9. 参考资料

### 9.1 相关代码实现

- **QAnything Token 管理**: `13_rag_and_retrieval/17_qanything_case_study/qanything_case_study/qanything_kernel/core/local_doc_qa.py`
- **Token 计算工具**: `13_rag_and_retrieval/17_qanything_case_study/qanything_case_study/qanything_kernel/utils/general_utils.py`
- **LLM Token 计算**: `13_rag_and_retrieval/17_qanything_case_study/qanything_case_study/qanything_kernel/connector/llm/llm_for_openai_api.py`

### 9.2 推荐阅读

- [OpenAI Token 限制文档](https://platform.openai.com/docs/guides/tokens)
- [Tiktoken 官方文档](https://github.com/openai/tiktoken)
- [LlamaIndex Token 管理](https://docs.llamaindex.ai/en/stable/module_guides/deploying/production_rag/#token-management)

### 9.3 工具推荐

- **tiktoken**: OpenAI 官方 token 计算库
- **langchain**: 提供 token 计算和管理工具
- **llama-index**: 内置 token 管理功能

---

**总结**: Token 管理是大规模 RAG 系统的关键环节，但对于小型系统（< 60 万节点）可以适度简化。关键是要设置正确的日志级别（INFO）、预留足够的安全边界，并实现完善的检查机制。
