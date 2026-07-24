# 摘要记忆（Summary Memory）示例

## 功能

当 token 数超过阈值时，自动将旧消息压缩成摘要，用 `[Memory Summary]` 替换旧消息，保留：
- 系统提示
- 当前轮次
- 部分近期历史

## 核心组件

### `SummarizationNode`

```python
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately

summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,  # token 计数器
    model=model,                                # 用于生成摘要的模型
    max_tokens=384,                             # token 阈值
    max_summary_tokens=128,                     # 摘要最大 token 数
    output_messages_key="messages",             # 输出消息的 key
)
```

### 工作流程

```
START → summarize → agent → END
```

在 `summarize` 节点：
1. 检测 token 数是否超过阈值（`max_tokens`）
2. 如果是，把旧消息喂给 LLM，生成一段摘要
3. 用一条摘要消息替换旧消息
4. 保留系统提示 + 当前轮次 + 部分近期历史

## 运行

```bash
cd 09_memory_patterns_basics

# 安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate

# 配置 API Key（二选一）
export DASHSCOPE_API_KEY=your_key  # 通义千问
# 或
export OPENAI_API_KEY=your_key      # OpenAI

# 运行
python p06-summaryMEM.py
```

## 依赖版本

```
langgraph==1.2.9
langmem==0.0.30
langchain-core
langchain-openai 或 langchain-community
```

## 适用场景

- 长对话场景
- 需要控制上下文大小
- 保留关键信息，降低 token 成本
- Agent 长任务执行

## 与其他记忆模式的对比

| 记忆模式 | 特点 | 适用场景 |
|---------|------|----------|
| 短期记忆 | 当前会话内，不持久化 | 简单对话 |
| **摘要记忆** | 压缩旧消息，保留关键信息 | 长对话，控制成本 |
| 窗口记忆 | 固定窗口，丢弃旧消息 | 轻量聊天 |
| 向量记忆 | 语义检索，召回相关历史 | 需要精准回忆 |
| Redis 记忆 | 持久化，跨会话 | 生产环境 |

## 相关文档

- `LLM-Memory核心观点-Anthropic与OpenAI.md` - Compaction 理论
- `memory-qa-notes.md` - Memory 问答整理
- `TECH_DOC.md` - 技术文档概览
