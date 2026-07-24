# 手动实现的摘要记忆（Summary Memory）

基于 [WeKnora](https://github.com/Tencent/WeKnora) 的精简实现，展示核心压缩逻辑。

## 核心原理

### 两级防线

```
用户消息 → LLM 智能摘要 → 暴力截断兜底
                ↓
           [system] + [summary] + [近期历史] + [当前轮次]
```

### 流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    原始消息序列                              │
│   [sys] [u1] [a1] [u2] [a2] [u3] [a3]                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 定位当前轮次                                        │
│  - 从后往前找最后一个 user 消息                             │
│  - lastUserIdx = 5 (u3 的位置)                              │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 分割消息                                            │
│  history = [u1, a1, u2, a2]  ← 旧历史                       │
│  tail = [u3, a3]             ← 当前轮次（必须完整保留）      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: 贪心保留近期历史                                    │
│  - 预算 = 窗口 × 30% - system - tail - summary预留           │
│  - 从尾部往前保留，越近越重要                                │
│  toConsolidate = [u1, a1]  ← 需要压缩                       │
│  toKeep = [u2, a2]         ← 保留的近期历史                 │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: LLM 摘要 toConsolidate                              │
│  [u1, a1] → "用户问了X，助手回答了Y"                         │
│  失败 → rawArchive() 纯文本兜底                              │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: 组装结果                                            │
│  [sys] + [Memory Summary] + [u2,a2] + [u3,a3]              │
│  总 token ≈ 窗口 × 30%                                      │
└─────────────────────────────────────────────────────────────┘
```

## 核心设计

### 1. 触发条件

```python
def should_consolidate(self, current_tokens: int) -> bool:
    trigger_at = int(self.max_tokens * 0.5)  # 50% 触发
    return current_tokens > trigger_at
```

**为什么是 50% 而不是 100%？**
- 留出安全余量，避免 LLM 被截断
- 预留增长空间给后续对话

### 2. 定位当前轮次

```python
# 从后往前找最后一个 user 消息
for i in range(len(messages) - 1, 0, -1):
    if isinstance(messages[i], HumanMessage):
        last_user_idx = i
        break

# 分割
history = messages[1:last_user_idx]  # 旧历史
tail = messages[last_user_idx:]       # 当前轮次（完整保留）
```

**为什么要完整保留当前轮次？**
- 当前轮次包含正在进行的推理上下文
- LLM 正在处理这个请求，不能打断

### 3. 贪心保留近期历史

```python
# 从尾部往前逐条累加 token
for i in range(len(history) - 1, -1, -1):
    msg_tokens = count_tokens_approximately([msg])
    if tokens + msg_tokens > budget:
        break
    tokens += msg_tokens
    keep_count += 1
```

**为什么是从尾部往前？**
- 越近的对话越重要
- 符合对话的时序性

**特殊处理：Tool 消息组**
```python
if isinstance(msg, ToolMessage):
    # assistant(tool_calls) + tool(results) 必须成组保留
    # 不能拆散，否则 LLM 会找不到对应的 tool call
```

### 4. LLM 摘要

```python
response = self.model.invoke(
    prompt,
    temperature=0.3,  # 低温 → 事实性摘要，不发散
    max_tokens=1000,  # 摘要上限
)
```

**失败兜底：**
```python
except Exception:
    # LLM 失败 → 纯文本转储
    return self._raw_archive(messages)
```

## 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_tokens` | 4000 | 上下文窗口大小 |
| `threshold` | 0.5 | 触发阈值（50%） |
| `target_ratio` | 0.6 | 目标压缩比（窗口 × 50% × 60% = 30%） |
| `summary_reserve` | 500 | 预留给 summary 消息的 token |
| `temperature` | 0.3 | 摘要时使用低温 |
| `max_summary_tokens` | 1000 | 摘要最大 token 数 |

## 代码对比

### WeKnora (Go) vs Python 实现

| 功能 | WeKnora (Go) | Python 实现 |
|------|--------------|-------------|
| Token 估算 | `EstimateMessage()` | `count_tokens_approximately()` |
| 触发判断 | `ShouldConsolidate()` | `should_consolidate()` |
| 分割消息 | `history := messages[1:lastUserIdx]` | `history = messages[1:last_user_idx]` |
| 贪心保留 | `findKeepBoundary()` | `_find_keep_boundary()` |
| LLM 摘要 | `summarizeWithRetry()` | `_summarize_messages()` |
| 兜底处理 | `rawArchive()` | `_raw_archive()` |

## 运行

```bash
cd 09_memory_patterns_basics
source .venv/bin/activate

# 配置 API Key
export DASHSCOPE_API_KEY=your_key

# 运行
python p06-summaryMEM-manual.py
```

## 输出示例

```
============================================================
手动实现的摘要记忆（Summary Memory）
============================================================

配置:
  - 模型: 通义千问
  - 上下文窗口: 4000 tokens
  - 触发阈值: 50% (2000 tokens)
  - 目标压缩: 30% (1200 tokens)

Token 数: 180 - 未超过阈值
Token 数: 360 - 未超过阈值
Token 数: 520 - 未超过阈值
Token 数: 2100 - 超过阈值，触发压缩...

✓ 压缩完成:
  - 压缩了 2 条旧消息
  - 保留了 2 条近期历史
  - 当前轮次 2 条消息完整保留
  - 总消息数: 7 → 6

============================================================
最终统计
============================================================
总消息数: 12
总 Token 数: 1560
✓ 生成了 1 个摘要消息
```

## 与 langmem.SummarizationNode 的对比

| 特性 | langmem.SummarizationNode | 手动实现 |
|------|---------------------------|----------|
| 依赖 | 需要 langmem 库 | 仅需 langchain-core |
| 灵活性 | 较固定 | 完全可控 |
| Tool 消息处理 | 自动处理 | 需要手动处理 |
| 摘要更新策略 | 支持增量更新 | 单次压缩 |
| 适用场景 | 生产环境 | 学习/理解原理 |

## 核心要点

1. **渐进式压缩**：50% 触发 → 压缩到 30% → 留 70% 增长空间
2. **保护当前推理**：当前轮次完整保留
3. **就近保留**：贪心从尾部保留近期历史
4. **原子性**：tool 消息组成组保留，不拆散
5. **优雅降级**：LLM 失败 → 纯文本兜底
6. **成本控制**：低温 + 短输出

## 相关文档

- `p06-summaryMEM.py` - 使用 langmem 库的实现
- `LLM-Memory核心观点-Anthropic与OpenAI.md` - Compaction 理论
- `memory-qa-notes.md` - Memory 问答整理

## 参考资料

- [WeKnora - consolidator.go](https://github.com/Tencent/WeKnora/blob/main/internal/agent/memory/consolidator.go)
- [LangChain - count_tokens_approximately](https://python.langchain.com/docs/modules/model_io/messages/utils)
