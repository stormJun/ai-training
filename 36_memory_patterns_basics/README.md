# Agent Memory 学习材料

本目录是合并后的 Agent Memory 专题目录，整合了原 `36_memory_patterns_basics/`、`37_vector_and_faiss_memory/`、`38_knowledge_graph_memory/` 和 `39_redis_memory_and_reliability/`，聚焦对话记忆、向量记忆、知识图谱记忆、Redis 时序记忆，以及工具调用可靠性。

## 开始使用

```bash
cd 36_memory_patterns_basics
uv sync --locked
source .venv/bin/activate
```

环境要求：

- Python 3.11+
- `uv`
- Redis 可选，仅 `p11-redisMEM.py` 需要

## 内容结构

- `p04-shortMEM.py`
  - 短期记忆与线程级会话持久化
- `p06-summaryMEM.py`
  - 摘要记忆与上下文压缩
- `p07-windowMEM.py`
  - 滑动窗口记忆
- `p08-vectorMEM.py`
  - 向量记忆与语义检索
- `p09-faissMEM.py`
  - FAISS 长期记忆
- `p10-KnowledgeTripleMEM.py`
  - 知识图谱记忆
- `p11-redisMEM.py`
  - Redis 时序记忆
- `p13-toolRetry.py`
  - 工具调用重试与降级处理
- `LLM-Memory核心观点-Anthropic与OpenAI.md`
  - Memory 方法论笔记
- `大模型Memory论文导读.md`
  - Memory 论文阅读材料
- `TECH_DOC.md`
  - 本主题的技术总览

## 存储目录

- `faiss_memory_index/`
  - FAISS 示例索引
- `knowledge_graph_storage/`
  - 知识图谱持久化数据
- `docs/`
  - Memory 相关论文与翻译材料

## 已迁移内容

以下内容已从本目录拆出：

- RPA 与 AI 工作流集成：
  - `26_rpa_and_ai_workflow/rpa_and_ai_workflow/`
- 小模型优化：
  - `53_slm_optimization/slm_optimization/`
- CLIP 图像搜索：
  - `54_multimodal_clip_search/multimodal_clip_search/`
- 强化学习：
  - `55_reinforcement_learning/reinforcement_learning/`
- 第三方全栈示例：
  - `third_party_sources/gemini-fullstack-langgraph-quickstart/`
