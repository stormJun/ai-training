# 技术文档 - Agent Memory 主线

## 概览

`36_memory_patterns_basics` 现已收束为 Agent Memory 专题，目标是把不同层次的记忆机制和常见工程问题放在同一条学习主线上。

```bash
cd 36_memory_patterns_basics
uv sync --locked
source .venv/bin/activate
```

## 主题范围

本目录保留以下内容：

- 短期记忆
- 摘要记忆
- 滑动窗口记忆
- 向量记忆
- FAISS 长期记忆
- 知识图谱记忆
- Redis 时序记忆
- 工具调用重试与降级
- Memory 论文与方法论文档

以下内容已迁出：

- RPA 与 AI 工作流集成：`26_rpa_and_ai_workflow/rpa_and_ai_workflow/`
- 小模型优化：`53_slm_optimization/slm_optimization/`
- CLIP 图像搜索：`54_multimodal_clip_search/multimodal_clip_search/`
- 强化学习：`55_reinforcement_learning/reinforcement_learning/`
- 第三方全栈 quickstart：`third_party_sources/gemini-fullstack-langgraph-quickstart/`

## 技术栈

- LangChain / LangGraph
- `langmem`
- FAISS
- Redis
- NetworkX
- DashScope / OpenAI 兼容模型接口

## 多层记忆结构

### 1. 短期记忆

文件：`p04-shortMEM.py`

关注点：

- 基于线程 ID 的会话隔离
- 对话状态持久化
- 当前进程内的短期上下文保持

### 2. 摘要记忆

文件：`p06-summaryMEM.py`

关注点：

- 长对话压缩
- Token 预算控制
- 保留摘要和最新上下文

### 3. 滑动窗口记忆

文件：`p07-windowMEM.py`

关注点：

- 固定窗口上下文
- 成本可控
- 适合轻量聊天场景

### 4. 向量记忆

文件：`p08-vectorMEM.py`

关注点：

- 将历史信息向量化
- 基于相似度做语义检索
- 在长上下文场景中回忆关键事实

### 5. FAISS 长期记忆

文件：`p09-faissMEM.py`

配套目录：

- `faiss_memory_index/`

关注点：

- 本地向量索引持久化
- 检索增强的长期记忆
- 工程上可复用的记忆存储模式

### 6. 知识图谱记忆

文件：`p10-KnowledgeTripleMEM.py`

配套目录：

- `knowledge_graph_storage/`

关注点：

- 实体与关系抽取
- 图结构查询
- 从对话中构造结构化长期记忆

### 7. Redis 时序记忆

文件：`p11-redisMEM.py`

关注点：

- 时效性记忆
- TTL 过期策略
- 高并发下的外部状态存储

### 8. 工具调用重试

文件：`p13-toolRetry.py`

关注点：

- 失败重试
- 异常分类
- 降级策略
- Memory 写入过程中的可靠性保护

## 文档材料

- `LLM-Memory核心观点-Anthropic与OpenAI.md`
- `大模型Memory论文导读.md`
- `docs/`

这些材料用于补充 Memory 方法论、论文背景和实现思路。

## 学习顺序建议

1. `p04-shortMEM.py`
2. `p06-summaryMEM.py`
3. `p07-windowMEM.py`
4. `p08-vectorMEM.py`
5. `p09-faissMEM.py`
6. `p10-KnowledgeTripleMEM.py`
7. `p11-redisMEM.py`
8. `p13-toolRetry.py`

## 迁移说明

本次目录整理的目标是让 `07` 只承载 memory 主线，避免把多模态检索、小模型优化、强化学习和工作流集成放进同一个主题目录，造成依赖和学习路径混乱。
