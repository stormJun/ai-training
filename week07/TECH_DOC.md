# Week 07 技术文档 - AI智能体高级能力构建

## 目录

- [快速入门指南](#快速入门指南)
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
  - [快速运行示例](#快速运行示例)
- [技术架构详解](#技术架构详解)
  - [核心技术栈](#核心技术栈)
  - [内存管理架构](#内存管理架构)
  - [知识存储系统](#知识存储系统)
  - [错误处理机制](#错误处理机制)
- [代码示例说明](#代码示例说明)
  - [短期记忆 (p04-shortMEM.py)](#短期记忆-p04-shortmempy)
  - [摘要记忆 (p06-summaryMEM.py)](#摘要记忆-p06-summarymempy)
  - [滑窗记忆 (p07-windowMEM.py)](#滑窗记忆-p07-windowmempy)
  - [向量记忆 (p08-vectorMEM.py)](#向量记忆-p08-vectormempy)
  - [FAISS长期记忆 (p09-faissMEM.py)](#faiss长期记忆-p09-faissmempy)
  - [知识图谱 (p10-KnowledgeTripleMEM.py)](#知识图谱-p10-knowledgetripplemempy)
  - [时序记忆 (p11-redisMEM.py)](#时序记忆-p11-redismempy)
  - [工具重试 (p13-toolRetry.py)](#工具重试-p13-toolretrypy)
  - [RPA集成 (RPA.py)](#rpa集成-rpapy)
  - [小型模型优化 (p32-SLM.ipynb)](#小型模型优化-p32-slmipynb)
- [独立项目说明](#独立项目说明)
- [最佳实践与注意事项](#最佳实践与注意事项)

---

## 快速入门指南

### 环境要求

- **Python**: 3.11+ (推荐 3.11 或 3.12)
- **包管理器**: uv (超快速的Python包管理器)
- **操作系统**: macOS / Linux / Windows
- **可选服务**:
  - Redis (用于 p11-redisMEM.py)
  - 网络连接 (访问 DashScope/OpenAI API)

### 安装步骤

#### 1. 安装 uv 包管理器

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. 进入项目目录并安装依赖

```bash
cd week07
uv sync --locked
```

#### 3. 激活虚拟环境

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

#### 4. 配置环境变量

创建 `.env` 文件或设置环境变量:

```bash
# DashScope (阿里云通义千问)
export DASHSCOPE_API_KEY="your_api_key_here"

# OpenAI (可选)
export OPENAI_API_KEY="your_api_key_here"

# DeepSeek (可选)
export DEEPSEEK_API_KEY="your_api_key_here"
```

### 快速运行示例

#### 示例 1: 运行短期记忆演示

```bash
python p04-shortMEM.py
```

**预期输出**:
- 带有记忆的对话演示
- 展示线程间的会话持久化
- 工具调用示例 (天气查询)

#### 示例 2: 运行 FAISS 向量记忆

```bash
python p09-faissMEM.py
```

**预期输出**:
- 创建 FAISS 索引
- 4轮对话演示，包含语义记忆检索
- 自动保存索引到 `faiss_memory_index/` 目录

#### 示例 3: 运行知识图谱演示

```bash
python p10-KnowledgeTripleMEM.py
```

**预期输出**:
- 构建知识图谱 (人物-职业-公司关系)
- 路径查询演示
- 保存图谱到 `knowledge_graph_storage/` 目录

---

## 技术架构详解

### 核心技术栈

```
┌─────────────────────────────────────────────────────────┐
│                    应用层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Chat UI  │  │ RPA 集成 │  │ API 服务 │  │  工具   │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 LangGraph 编排层                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  StateGraph: 状态机 + 条件路由 + 节点调度        │  │
│  │  - Checkpointer: 状态持久化                       │  │
│  │  - Conditional Edge: 动态路由                     │  │
│  │  - Tool Node: 工具执行节点                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   LangChain 工具层                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ LLM 调用 │  │  工具绑定│  │ 提示模板 │  │ 消息管理│ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   存储 & 记忆层                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ FAISS 向量  │  │ NetworkX 图 │  │ Redis 缓存  │     │
│  │   索引      │  │   数据库    │  │   (TTL)     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   LLM 服务层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Qwen    │  │  OpenAI  │  │ DeepSeek │              │
│  │(DashScope│  │   GPT    │  │          │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 内存管理架构

Week07 实现了**多层次内存架构**，模拟人类记忆系统：

#### 1. 短期记忆 (Short-Term Memory)

**实现方式**: `InMemorySaver` + Checkpointer

```python
# 架构模式
StateGraph → Agent Node → Checkpointer → Thread Storage
```

**特点**:
- 基于线程 ID 的会话隔离
- 仅在当前会话生命周期内有效
- 序列化为内存对象，进程结束后丢失
- 适合: 单次对话、临时状态存储

**数据流**:
```
用户输入 → 加载线程历史 → LLM 处理 → 保存到检查点 → 下次调用时恢复
```

---

#### 2. 摘要记忆 (Summarization Memory)

**实现方式**: `langmem.SummarizationNode` + Token 预算管理

```python
# 架构模式
消息累积 → Token 计数 → 超限触发 → 摘要节点 → 压缩历史
```

**核心机制**:
- **Token 预算**: 384 tokens (最大上下文)
- **摘要预算**: 128 tokens (摘要长度)
- **触发条件**: 当累积消息超过 max_tokens 时

**工作流程**:
```
[用户消息1, AI回复1, 用户消息2, AI回复2, ...]
           ↓ (累积超过 384 tokens)
[摘要: "用户询问了X, AI回答了Y...", 最新消息...]
           ↓ (保留 128 tokens 摘要 + 最新消息)
继续对话...
```

**适合场景**: 长对话、咨询场景、需保留上下文但限制成本

---

#### 3. 滑窗记忆 (Sliding Window Memory)

**实现方式**: `trim_messages()` + 固定窗口大小

```python
# 架构模式
消息队列 → 窗口检查 → 超出部分截断 → 保留最新 N tokens
```

**策略配置**:
```python
strategy="last"          # 保留最新消息
max_tokens=384           # 窗口大小
start_on="human"         # 从人类消息开始
end_on=["human", "tool"] # 到人类或工具消息结束
```

**示例演示**:
```
窗口大小 = 384 tokens

[消息1, 消息2, 消息3, 消息4, 消息5]  ← 总计 500 tokens
                    ↓ 截断
           [消息3, 消息4, 消息5]     ← 保留 380 tokens
```

**适合场景**: 实时对话、内存受限环境、流式处理

---

#### 4. 向量记忆 (Vector Memory)

**实现方式**: `InMemoryVectorStore` + Embedding + 语义检索

```python
# 架构模式
三节点流程:
1. load_memories → 语义搜索相关记忆
2. agent → LLM 处理 (含检索到的记忆作为上下文)
3. save_memory → 自动保存新记忆
```

**核心组件**:
- **向量存储**: 内存中的向量数据库
- **嵌入模型**: DashScope text-embedding-v3
- **检索策略**: 余弦相似度 Top-K

**数据流**:
```
用户输入
  ↓
查询向量化 (Embedding)
  ↓
相似度搜索 (Cosine Similarity)
  ↓
返回 Top-3 相关记忆
  ↓
注入到 LLM 提示词 (作为上下文)
  ↓
生成回复
  ↓
自动保存新记忆到向量库
```

**工具函数**:
- `save_memory`: 用户主动保存重要信息
- `search_memory`: 主动检索历史记忆

**适合场景**: 知识库问答、个性化对话、长期记忆系统

---

#### 5. FAISS 长期记忆 (Persistent Vector Memory)

**实现方式**: FAISS + 持久化索引 + 用户隔离

```python
# 架构模式
FAISSMemoryManager
  ├── index.faiss      (二进制向量索引)
  ├── index.pkl        (文档元数据)
  └── 索引生命周期管理 (加载/保存/查询)
```

**技术细节**:
- **索引类型**: `IndexFlatIP` (内积索引，用于余弦相似度)
- **向量维度**: 1536 (DashScope embedding 维度)
- **存储格式**:
  - `index.faiss`: FAISS 二进制索引文件
  - `index.pkl`: Pickle 序列化的文档列表
- **用户隔离**: 每条记忆带 `user_id` 元数据

**核心类方法**:
```python
class FAISSMemoryManager:
    def add_memory(user_id, text) → None
        # 1. 文本向量化
        # 2. 添加到 FAISS 索引
        # 3. 保存元数据
        # 4. 持久化到磁盘

    def search_memory(user_id, query, k=5) → List[str]
        # 1. 查询向量化
        # 2. FAISS 相似度搜索
        # 3. 过滤用户 ID
        # 4. 返回 Top-K 结果

    def get_statistics() → Dict
        # 返回索引统计 (向量数、用户数等)
```

**演示场景**:
```
第1轮: 用户保存 "我喜欢吃北京烤鸭"
第2轮: 用户保存 "我的工作是软件工程师"
第3轮: Agent 询问 "你喜欢吃什么?"
        ↓ 自动检索到 "我喜欢吃北京烤鸭"
        回答: "你之前提到喜欢吃北京烤鸭..."
```

**适合场景**: 个人知识库、企业知识管理、多租户 SaaS

---

#### 6. 知识图谱记忆 (Knowledge Graph Memory)

**实现方式**: NetworkX MultiDiGraph + 三元组存储

**核心数据结构**:
```python
# 1. 知识节点
KnowledgeNode:
    - id: UUID
    - label: "张三"
    - type: "Person"
    - properties: {"age": 30, "city": "北京"}

# 2. 知识关系
KnowledgeRelation:
    - source_id: UUID
    - target_id: UUID
    - relation_type: "WORKS_AT"
    - properties: {"since": "2020"}
    - weight: 0.9

# 3. 知识三元组
KnowledgeTriple:
    - subject: "张三"
    - predicate: "工作于"
    - object: "阿里巴巴"
```

**存储架构**:
```
knowledge_graph_storage/
├── graph_data.json          # 人类可读的 JSON
│   ├── nodes: [...]
│   ├── relations: [...]
│   └── triples: [...]
│
├── graph_index.pkl          # 快速查找索引
│   ├── node_label_index    # 标签 → 节点 ID
│   ├── node_type_index     # 类型 → 节点列表
│   └── user_index          # 用户 → 图谱隔离
│
└── networkx_graph.pkl       # NetworkX 图对象
    └── MultiDiGraph         # 支持多种图算法
```

**高级查询能力**:

1. **路径查询** (Shortest Path):
```python
find_path("张三", "阿里巴巴")
# 返回: ["张三" → "李四" → "阿里巴巴"]
```

2. **关系类型路径** (Relation-Type Path):
```python
find_relation_path("张三", "阿里巴巴", "WORKS_AT")
# 返回: 所有通过 "WORKS_AT" 关系的路径
```

3. **多跳关系遍历** (BFS Traversal):
```python
traverse_relations("张三", max_depth=3)
# 返回: 3跳内所有可达节点和关系
```

**LangGraph 集成**:
```python
# 提供 8 个工具函数
1. add_knowledge_node        # 添加实体
2. add_knowledge_relation    # 添加关系
3. search_nodes_by_label     # 按标签搜索
4. search_nodes_by_type      # 按类型搜索
5. search_relations          # 搜索关系
6. find_path                 # 路径查找
7. traverse_relations        # 关系遍历
8. add_triple                # 添加三元组
```

**演示场景**:
```
构建图谱:
  张三 --[WORKS_AT]--> 阿里巴巴
  李四 --[WORKS_AT]--> 阿里巴巴
  张三 --[COLLEAGUE]--> 李四

查询:
  Q: "张三和阿里巴巴的关系?"
  A: "张三在阿里巴巴工作"

  Q: "通过同事关系找到共同雇主?"
  A: "张三的同事李四也在阿里巴巴工作"
```

**适合场景**:
- 社交网络分析
- 企业组织架构
- 知识图谱问答
- 推荐系统

---

#### 7. 时序记忆 (Temporal Memory with TTL)

**实现方式**: Redis + Time-To-Live (过期机制)

```python
# 架构模式
Redis List
  ├── Key: f"chat_history:{user_id}"
  ├── Value: [消息1, 消息2, ...]
  └── TTL: 8 秒 (演示值，生产可设置小时/天)
```

**核心机制**:
- **自动过期**: 消息在 N 秒后自动删除
- **模拟遗忘**: 类似人类记忆的衰减
- **隐私保护**: 敏感对话自动清除

**Redis 操作**:
```python
# 1. 保存消息 (带 TTL)
redis.rpush(f"chat_history:{user_id}", json.dumps(msg))
redis.expire(f"chat_history:{user_id}", ttl_seconds)

# 2. 检索历史
messages = redis.lrange(f"chat_history:{user_id}", 0, -1)

# 3. 检查 TTL
remaining = redis.ttl(f"chat_history:{user_id}")
if remaining == -2:
    print("消息已过期")
```

**演示流程**:
```
t=0s:  保存 "你好"                  → TTL=8s
t=2s:  保存 "今天天气如何?"         → TTL=8s (重置)
t=5s:  查询历史 → ["你好", "今天天气如何?"]
t=10s: 查询历史 → [] (已过期)
```

**适合场景**:
- 临时会话 (客服对话)
- 隐私敏感应用 (医疗咨询)
- 缓存管理 (热数据淘汰)

---

### 知识存储系统

#### 存储层级对比

| 存储类型 | 持久化 | 语义检索 | 结构化查询 | 自动过期 | 适用场景 |
|---------|--------|---------|-----------|---------|---------|
| **InMemorySaver** | ✗ | ✗ | ✗ | ✗ | 单次会话 |
| **Summarization** | ✗ | ✗ | ✗ | ✗ | 长对话压缩 |
| **Sliding Window** | ✗ | ✗ | ✗ | ✓ (隐式) | 实时流式 |
| **InMemory Vector** | ✗ | ✓ | ✗ | ✗ | 原型开发 |
| **FAISS** | ✓ | ✓ | ✗ | ✗ | 生产级语义搜索 |
| **Knowledge Graph** | ✓ | ✗ | ✓ | ✗ | 关系推理 |
| **Redis TTL** | ✓ | ✗ | ✗ | ✓ | 临时缓存 |

#### 组合使用建议

**场景1: 智能客服系统**
```
短期记忆 (当前会话)
  + FAISS (知识库检索)
  + Redis TTL (会话缓存)
```

**场景2: 企业知识管理**
```
FAISS (文档向量检索)
  + Knowledge Graph (组织架构 + 业务流程)
  + Summarization (会议纪要压缩)
```

**场景3: 个人助手**
```
FAISS (个人知识库)
  + Knowledge Graph (人际关系)
  + Redis TTL (临时提醒)
```

---

### 错误处理机制

#### 自定义异常体系

```python
# 异常继承树
Exception
  └── MemoryWriteError           # 内存写入错误
  └── NetworkTimeoutError        # 网络超时错误
  └── ResourceUnavailableError   # 资源不可用错误
```

#### 重试策略 (Retry Policy)

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3          # 最大重试次数
    initial_delay: float = 1.0     # 初始延迟 (秒)
    backoff_factor: float = 2.0    # 退避因子 (指数增长)
    max_delay: float = 10.0        # 最大延迟
```

**指数退避算法**:
```
尝试次数 | 延迟时间
--------|----------
1       | 1s
2       | 2s  (1 × 2)
3       | 4s  (2 × 2)
4       | 8s  (4 × 2)
5       | 10s (达到 max_delay 上限)
```

#### LangGraph 集成

```python
# 节点重试配置
graph.add_node(
    "unreliable_storage",
    memory_storage_node,
    retry=RetryPolicy(max_attempts=5)  # LangGraph 原生支持
)

# 条件路由 (错误处理)
def should_retry(state):
    if state["error_count"] < 3:
        return "retry"
    else:
        return "error_handler"

graph.add_conditional_edges(
    "storage_node",
    should_retry,
    {
        "retry": "storage_node",        # 重试
        "error_handler": "fallback_node"  # 降级处理
    }
)
```

#### 演示场景

```python
# 模拟 60% 失败率的不可靠存储
class MemoryStorage:
    def save(self, data):
        if random.random() < 0.6:
            raise MemoryWriteError("Storage temporarily unavailable")
        return "Success"

# 测试结果
场景1 (0% 失败率):   ✓ 成功
场景2 (40% 失败率):  ✓ 重试后成功
场景3 (90% 失败率):  ✗ 超过重试上限，进入错误处理
场景4 (无效数据):    ✗ 立即失败，不重试
```

---

## 代码示例说明

### 短期记忆 (p04-shortMEM.py)

**功能**: 基于线程 ID 的会话持久化

**核心代码**:
```python
from langgraph.checkpoint.memory import MemorySaver

# 创建内存保存器
memory = MemorySaver()

# 构建图
graph = StateGraph(State)
graph.add_node("agent", call_model)
graph.set_entry_point("agent")
graph = graph.compile(checkpointer=memory)  # 注入检查点

# 使用线程 ID 隔离会话
config1 = {"configurable": {"thread_id": "session_1"}}
config2 = {"configurable": {"thread_id": "session_2"}}

graph.invoke({"messages": [HumanMessage("你好")]}, config1)
graph.invoke({"messages": [HumanMessage("再见")]}, config1)  # 记住上文
graph.invoke({"messages": [HumanMessage("你好")]}, config2)  # 独立会话
```

**关键点**:
- `MemorySaver`: 内存中的检查点存储
- `thread_id`: 会话隔离的唯一标识
- 每次调用自动加载历史状态

**文件位置**: p04-shortMEM.py:45-67

---

### 摘要记忆 (p06-summaryMEM.py)

**功能**: Token 超限时自动摘要压缩

**核心代码**:
```python
from langmem import SummarizationNode

# 创建摘要节点
summarizer = SummarizationNode(
    model=ChatOpenAI(model="gpt-4"),
    max_tokens=384,      # 上下文预算
    summary_tokens=128   # 摘要长度
)

# 在处理前自动摘要
summarizer.pre_model_hook(state)  # 检查并压缩历史
```

**工作流程**:
```python
# 状态定义
class State(TypedDict):
    messages: Annotated[list, add_messages]
    context: str  # 存储摘要内容

# 摘要触发逻辑
if count_tokens(state["messages"]) > 384:
    summary = summarizer.summarize(state["messages"])
    state["messages"] = [SystemMessage(summary)] + recent_messages
```

**文件位置**: p06-summaryMEM.py:18-35

---

### 滑窗记忆 (p07-windowMEM.py)

**功能**: 固定窗口大小的消息截断

**核心代码**:
```python
from langchain_core.messages import trim_messages

# 定义窗口策略
trimmer = trim_messages(
    strategy="last",              # 保留最新消息
    token_counter=len,            # Token 计数函数
    max_tokens=384,               # 窗口大小
    start_on="human",             # 从人类消息开始
    end_on=["human", "tool"],     # 到人类或工具消息结束
    include_system=True           # 始终保留系统消息
)

# 在每次调用前截断
def call_model(state: State):
    trimmed = trimmer.invoke(state["messages"])
    response = model.invoke(trimmed)
    return {"messages": [response]}
```

**演示场景**:
```python
# 模拟 5 轮对话
for i in range(5):
    graph.invoke({"messages": [HumanMessage(f"第{i+1}条消息")]})
    # 自动保留最新 384 tokens
```

**文件位置**: p07-windowMEM.py:28-56

---

### 向量记忆 (p08-vectorMEM.py)

**功能**: 语义检索 + 自动记忆存储

**核心架构**:
```python
# 1. 定义三节点图
graph = StateGraph(State)
graph.add_node("load_memories", load_memories_node)  # 检索
graph.add_node("agent", agent_node)                  # 处理
graph.add_node("save_memory", save_memory_node)      # 保存

# 2. 条件路由
def route_after_agent(state):
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END

graph.add_conditional_edges("agent", route_after_agent)
```

**检索节点**:
```python
async def load_memories_node(state: State):
    query = state["messages"][-1].content
    # 语义搜索相关记忆
    memories = await vector_store.asimilarity_search(query, k=3)
    # 注入到消息历史
    memory_msg = SystemMessage(f"相关记忆: {memories}")
    return {"messages": [memory_msg]}
```

**保存节点**:
```python
async def save_memory_node(state: State):
    # 自动提取并保存新记忆
    last_msg = state["messages"][-1].content
    await vector_store.aadd_texts([last_msg])
    return {}
```

**工具函数**:
```python
# 用户主动保存
@tool
async def save_memory(content: str):
    await vector_store.aadd_texts([content], metadatas=[{"user_id": "..."}])

# 用户主动检索
@tool
async def search_memory(query: str):
    results = await vector_store.asimilarity_search(query, k=5)
    return results
```

**文件位置**: p08-vectorMEM.py:45-189

---

### FAISS长期记忆 (p09-faissMEM.py)

**功能**: 持久化向量索引 + 生产级检索

**管理器类**:
```python
class FAISSMemoryManager:
    def __init__(self, index_dir: str = "./faiss_memory_index"):
        self.index_dir = Path(index_dir)
        self.index = None
        self.documents = []
        self.dimension = 1536  # DashScope embedding 维度

        # 启动时加载索引
        self.load_index()

        # 程序退出时自动保存
        atexit.register(self.save_index)

    def add_memory(self, user_id: str, text: str):
        # 1. 生成向量
        vector = self._get_embedding(text)

        # 2. 添加到索引
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(np.array([vector]))

        # 3. 保存元数据
        self.documents.append({
            "user_id": user_id,
            "text": text,
            "timestamp": datetime.now()
        })

        # 4. 持久化
        self.save_index()

    def search_memory(self, user_id: str, query: str, k: int = 5):
        query_vector = self._get_embedding(query)

        # FAISS 相似度搜索
        distances, indices = self.index.search(
            np.array([query_vector]), k * 3  # 过滤前多取一些
        )

        # 过滤用户 ID
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            doc = self.documents[idx]
            if doc["user_id"] == user_id:
                results.append(doc["text"])
                if len(results) >= k:
                    break

        return results
```

**持久化逻辑**:
```python
def save_index(self):
    self.index_dir.mkdir(exist_ok=True)

    # 保存 FAISS 索引
    faiss.write_index(
        self.index,
        str(self.index_dir / "index.faiss")
    )

    # 保存文档元数据
    with open(self.index_dir / "index.pkl", "wb") as f:
        pickle.dump(self.documents, f)

def load_index(self):
    index_file = self.index_dir / "index.faiss"
    if index_file.exists():
        self.index = faiss.read_index(str(index_file))
        with open(self.index_dir / "index.pkl", "rb") as f:
            self.documents = pickle.load(f)
```

**演示场景**:
```python
# 第1轮: 存储个人信息
memory_manager.add_memory("user123", "我喜欢吃北京烤鸭")

# 第3轮: 自动检索
results = memory_manager.search_memory("user123", "你喜欢吃什么", k=3)
# 返回: ["我喜欢吃北京烤鸭"]
```

**文件位置**: p09-faissMEM.py:50-250

---

### 知识图谱 (p10-KnowledgeTripleMEM.py)

**功能**: 实体-关系-实体存储 + 图算法查询

**核心数据结构**:
```python
@dataclass
class KnowledgeNode:
    id: str
    label: str                    # "张三"
    type: str                     # "Person"
    properties: Dict = field(default_factory=dict)

@dataclass
class KnowledgeRelation:
    source_id: str
    target_id: str
    relation_type: str            # "WORKS_AT"
    properties: Dict = field(default_factory=dict)
    weight: float = 1.0

@dataclass
class KnowledgeTriple:
    subject: str                  # "张三"
    predicate: str                # "工作于"
    object: str                   # "阿里巴巴"
```

**图管理器**:
```python
class KnowledgeGraphManager:
    def __init__(self):
        self.graph = nx.MultiDiGraph()  # 多重有向图
        self.node_label_index = {}      # 标签索引
        self.node_type_index = {}       # 类型索引

    def add_node(self, label: str, node_type: str, properties: dict):
        node = KnowledgeNode(
            id=str(uuid.uuid4()),
            label=label,
            type=node_type,
            properties=properties
        )
        self.graph.add_node(node.id, **asdict(node))

        # 更新索引
        self.node_label_index[label] = node.id
        self.node_type_index.setdefault(node_type, []).append(node.id)

        return node.id

    def add_relation(self, source_label: str, target_label: str,
                     relation_type: str):
        source_id = self.node_label_index[source_label]
        target_id = self.node_label_index[target_label]

        self.graph.add_edge(
            source_id, target_id,
            relation_type=relation_type
        )
```

**高级查询**:
```python
# 1. 最短路径
def find_path(self, source_label: str, target_label: str):
    source_id = self.node_label_index[source_label]
    target_id = self.node_label_index[target_label]

    path_ids = nx.shortest_path(self.graph, source_id, target_id)
    # 转换为标签路径
    return [self.graph.nodes[nid]["label"] for nid in path_ids]

# 2. 关系遍历
def traverse_relations(self, start_label: str, max_depth: int = 2):
    start_id = self.node_label_index[start_label]
    visited = set()
    results = []

    def bfs(node_id, depth):
        if depth > max_depth or node_id in visited:
            return
        visited.add(node_id)

        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            results.append({
                "from": self.graph.nodes[node_id]["label"],
                "to": self.graph.nodes[neighbor]["label"],
                "relation": edge_data[0]["relation_type"]
            })
            bfs(neighbor, depth + 1)

    bfs(start_id, 0)
    return results
```

**持久化**:
```python
def save_to_file(self, directory: str = "./knowledge_graph_storage"):
    # 1. JSON 格式 (人类可读)
    with open(f"{directory}/graph_data.json", "w") as f:
        json.dump({
            "nodes": [self.graph.nodes[n] for n in self.graph.nodes],
            "relations": list(self.graph.edges(data=True))
        }, f, ensure_ascii=False, indent=2)

    # 2. Pickle 索引 (快速加载)
    with open(f"{directory}/graph_index.pkl", "wb") as f:
        pickle.dump({
            "label_index": self.node_label_index,
            "type_index": self.node_type_index
        }, f)

    # 3. NetworkX 图对象
    nx.write_gpickle(self.graph, f"{directory}/networkx_graph.pkl")
```

**LangGraph 工具集成**:
```python
@tool
def add_knowledge_node(label: str, node_type: str, user_id: str):
    """添加知识节点 (实体)"""
    return kg_manager.add_node(label, node_type, {})

@tool
def find_path(source: str, target: str):
    """查找两个实体之间的路径"""
    return kg_manager.find_path(source, target)
```

**文件位置**: p10-KnowledgeTripleMEM.py:60-800

---

### 时序记忆 (p11-redisMEM.py)

**功能**: Redis TTL 实现自动遗忘

**核心逻辑**:
```python
import redis

class RedisMemoryManager:
    def __init__(self, ttl_seconds: int = 8):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        self.ttl = ttl_seconds

    def save_message(self, user_id: str, message: dict):
        key = f"chat_history:{user_id}"

        # 1. 添加消息到列表
        self.redis_client.rpush(key, json.dumps(message))

        # 2. 设置/重置 TTL
        self.redis_client.expire(key, self.ttl)

        print(f"消息已保存，将在 {self.ttl} 秒后过期")

    def get_history(self, user_id: str):
        key = f"chat_history:{user_id}"

        # 检查 TTL
        ttl_remaining = self.redis_client.ttl(key)
        if ttl_remaining == -2:
            print("消息已过期")
            return []

        # 获取所有消息
        messages = self.redis_client.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages]

    def check_ttl(self, user_id: str):
        key = f"chat_history:{user_id}"
        ttl = self.redis_client.ttl(key)

        if ttl == -2:
            return "消息已过期删除"
        elif ttl == -1:
            return "消息永久存储 (无 TTL)"
        else:
            return f"剩余 {ttl} 秒"
```

**演示场景**:
```python
# 时间线演示
manager = RedisMemoryManager(ttl_seconds=8)

# t=0s
manager.save_message("user1", {"role": "user", "content": "你好"})

# t=2s
manager.save_message("user1", {"role": "ai", "content": "你好!"})
print(manager.check_ttl("user1"))  # "剩余 6 秒"

# t=5s
history = manager.get_history("user1")  # 仍然可用

# t=10s
history = manager.get_history("user1")  # 返回 [] (已过期)
```

**文件位置**: p11-redisMEM.py:25-120

---

### 工具重试 (p13-toolRetry.py)

**功能**: 指数退避 + 错误恢复

**异常定义**:
```python
class MemoryWriteError(Exception):
    """内存写入失败"""
    pass

class NetworkTimeoutError(Exception):
    """网络超时"""
    pass

class ResourceUnavailableError(Exception):
    """资源不可用"""
    pass
```

**重试策略**:
```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 10.0

    def get_delay(self, attempt: int) -> float:
        """计算当前重试的延迟时间"""
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)
```

**模拟不可靠存储**:
```python
class MemoryStorage:
    def __init__(self, failure_rate: float = 0.6):
        self.failure_rate = failure_rate
        self.attempt_count = 0

    def save(self, data: dict) -> str:
        self.attempt_count += 1

        # 模拟失败
        if random.random() < self.failure_rate:
            raise MemoryWriteError(
                f"存储暂时不可用 (尝试 {self.attempt_count})"
            )

        return f"成功保存 (尝试 {self.attempt_count} 次)"
```

**重试装饰器**:
```python
def retry_with_backoff(policy: RetryPolicy):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except (MemoryWriteError, NetworkTimeoutError) as e:
                    last_exception = e

                    if attempt == policy.max_attempts:
                        raise

                    delay = policy.get_delay(attempt)
                    print(f"重试 {attempt}/{policy.max_attempts}, "
                          f"等待 {delay}s...")
                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator

# 使用示例
@retry_with_backoff(RetryPolicy(max_attempts=5))
def save_memory(storage, data):
    return storage.save(data)
```

**LangGraph 集成**:
```python
# 定义带重试的节点
async def storage_node(state: State):
    try:
        result = await save_with_retry(state["data"])
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 添加到图
graph.add_node(
    "storage",
    storage_node,
    retry=RetryPolicy(max_attempts=5)  # LangGraph 原生支持
)

# 错误路由
def route_after_storage(state):
    if state["status"] == "error":
        return "error_handler"
    return END

graph.add_conditional_edges("storage", route_after_storage)
```

**测试场景**:
```python
# 场景1: 0% 失败率 → 立即成功
storage = MemoryStorage(failure_rate=0.0)
result = save_memory(storage, {"test": "data"})
# 输出: "成功保存 (尝试 1 次)"

# 场景2: 40% 失败率 → 重试后成功
storage = MemoryStorage(failure_rate=0.4)
result = save_memory(storage, {"test": "data"})
# 输出: "重试 1/5, 等待 1.0s..."
#       "成功保存 (尝试 2 次)"

# 场景3: 90% 失败率 → 超过重试上限
storage = MemoryStorage(failure_rate=0.9)
try:
    result = save_memory(storage, {"test": "data"})
except MemoryWriteError:
    print("所有重试均失败，进入降级处理")
```

**文件位置**: p13-toolRetry.py:30-280

---

### RPA集成 (RPA.py)

**功能**: 连接 RPA 软件 (影刀/ClickBot) 与 Dify AI 工作流

**核心代码**:
```python
def execute_dify_workflow(user_input: str, user_id: str = "default"):
    """
    调用 Dify 工作流 API

    参数:
        user_input: 用户输入文本
        user_id: 用户唯一标识
    """
    url = "https://api.dify.ai/v1/workflows/run"

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {"query": user_input},
        "response_mode": "blocking",  # 同步模式
        "user": user_id
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()

        # 解析工作流输出
        if data["data"]["status"] == "succeeded":
            outputs = data["data"]["outputs"]
            return outputs.get("result", "无输出")
        else:
            return f"工作流执行失败: {data['data']['error']}"

    else:
        return f"API 调用失败: {response.status_code}"

# RPA 集成示例 (需要影刀 xbot 包)
try:
    from xbot import web  # 影刀 RPA SDK

    def rpa_workflow_bridge():
        # 1. RPA 获取网页输入
        input_text = web.get_element_text("//input[@id='user_query']")

        # 2. 调用 AI 工作流
        ai_result = execute_dify_workflow(input_text)

        # 3. RPA 填充结果
        web.input_text("//textarea[@id='result']", ai_result)
        web.click("//button[@id='submit']")

except ImportError:
    print("xbot 包未安装，仅演示 API 调用")
```

**使用场景**:
- 自动化表单填写 (RPA 获取 → AI 处理 → RPA 填充)
- 批量数据处理 (Excel → AI 分析 → 输出报告)
- 业务流程自动化 (订单审核、发票识别等)

**文件位置**: RPA.py:15-85

---

### 小型模型优化 (p32-SLM.ipynb)

**功能**: 模型压缩技术 (量化/剪枝/蒸馏)

#### 1. 量化 (Quantization)

```python
import torch
from transformers import AutoModelForCausalLM

# 加载模型
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-1.8B")

# FP32 → INT8 量化
quantized_model = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},  # 量化所有线性层
    dtype=torch.qint8
)

# 模型大小对比
original_size = os.path.getsize("original_model.pth") / (1024**3)  # GB
quantized_size = os.path.getsize("quantized_model.pth") / (1024**3)

print(f"原始模型: {original_size:.2f} GB")
print(f"量化模型: {quantized_size:.2f} GB")
print(f"压缩比: {original_size / quantized_size:.2f}x")
```

**预期结果**:
```
原始模型: 7.2 GB (FP32)
量化模型: 1.9 GB (INT8)
压缩比: 3.8x
精度损失: < 1%
```

---

#### 2. 剪枝 (Pruning)

```python
import torch.nn.utils.prune as prune

# 对模型进行结构化剪枝
for name, module in model.named_modules():
    if isinstance(module, torch.nn.Linear):
        # 剪枝 30% 的权重
        prune.l1_unstructured(module, name='weight', amount=0.3)

        # 移除剪枝重参数化 (永久应用)
        prune.remove(module, 'weight')

# 统计稀疏度
def calculate_sparsity(model):
    total_params = 0
    zero_params = 0

    for param in model.parameters():
        total_params += param.numel()
        zero_params += (param == 0).sum().item()

    return zero_params / total_params

print(f"模型稀疏度: {calculate_sparsity(model) * 100:.2f}%")
```

---

#### 3. 知识蒸馏 (Knowledge Distillation)

```python
# 教师模型 (大模型)
teacher_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-7B")

# 学生模型 (小模型)
student_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-1.8B")

# 蒸馏损失函数
def distillation_loss(student_logits, teacher_logits, temperature=2.0):
    """
    KL 散度损失 + 软标签
    """
    soft_targets = F.softmax(teacher_logits / temperature, dim=-1)
    soft_prob = F.log_softmax(student_logits / temperature, dim=-1)

    return F.kl_div(soft_prob, soft_targets, reduction='batchmean') * (temperature ** 2)

# 训练循环
for batch in dataloader:
    # 教师模型推理 (不更新梯度)
    with torch.no_grad():
        teacher_outputs = teacher_model(batch["input_ids"])

    # 学生模型训练
    student_outputs = student_model(batch["input_ids"])

    # 计算蒸馏损失
    loss = distillation_loss(
        student_outputs.logits,
        teacher_outputs.logits
    )

    loss.backward()
    optimizer.step()
```

**效果对比**:
```
模型          | 参数量 | 推理速度 | 准确率
-------------|--------|---------|-------
Qwen-7B      | 7B     | 100 ms  | 95%
Qwen-1.8B    | 1.8B   | 25 ms   | 88% (直接训练)
Qwen-1.8B-KD | 1.8B   | 25 ms   | 92% (蒸馏后)
```

**文件位置**: p32-SLM.ipynb (Jupyter 笔记本)

---

## 独立项目说明

### 1. gemini-fullstack-langgraph-quickstart

**项目类型**: 全栈 Agentic RAG 应用

**技术栈**:
- **前端**: TypeScript + React + Vite
- **后端**: Python + LangGraph + FastAPI
- **AI 能力**: 工具调用、RAG 检索、流式输出

**目录结构**:
```
gemini-fullstack-langgraph-quickstart/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   ├── hooks/         # React Hooks
│   │   └── App.tsx
│   └── package.json
│
├── backend/               # Python 后端
│   ├── agent/
│   │   ├── graph.py      # LangGraph 定义
│   │   └── tools.py      # 工具函数
│   ├── api/
│   │   └── routes.py     # FastAPI 路由
│   └── main.py
│
├── docker-compose.yml     # 容器编排
└── README.md
```

**核心功能**:
```python
# backend/agent/graph.py
from langgraph.graph import StateGraph

def create_research_agent():
    graph = StateGraph(AgentState)

    # 节点定义
    graph.add_node("retrieve", retrieval_node)      # RAG 检索
    graph.add_node("generate", generation_node)     # 内容生成
    graph.add_node("validate", validation_node)     # 答案验证

    # 流程定义
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_conditional_edges(
        "generate",
        should_validate,
        {
            "validate": "validate",
            "end": END
        }
    )

    return graph.compile()
```

**启动方式**:
```bash
# Docker 启动 (推荐)
docker-compose up

# 手动启动
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

**访问地址**:
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000

---

### 2. qlearn (Q-Learning 强化学习)

**项目类型**: 强化学习 Agent 演示

**文件说明**:
```
qlearn/
├── qlearn-1.py          # 基础 Q-Learning 实现
├── qlearn-2.py          # 经验回放 (Experience Replay)
├── qlearn-3.py          # Double Q-Learning
├── qlearn-4.py          # CartPole 环境训练
└── cartpole_model.pth   # 训练好的模型
```

**核心算法** (qlearn-1.py):
```python
import numpy as np

class QLearningAgent:
    def __init__(self, state_size, action_size):
        self.q_table = np.zeros((state_size, action_size))
        self.learning_rate = 0.1
        self.discount_factor = 0.99
        self.epsilon = 1.0  # 探索率

    def choose_action(self, state):
        # Epsilon-Greedy 策略
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)  # 探索
        else:
            return np.argmax(self.q_table[state])       # 利用

    def update(self, state, action, reward, next_state):
        # Q-Learning 更新公式
        current_q = self.q_table[state, action]
        max_next_q = np.max(self.q_table[next_state])

        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )

        self.q_table[state, action] = new_q

    def decay_epsilon(self, decay_rate=0.995):
        self.epsilon = max(0.01, self.epsilon * decay_rate)
```

**训练示例** (qlearn-4.py):
```python
import gym

env = gym.make('CartPole-v1')
agent = QLearningAgent(state_size=..., action_size=2)

for episode in range(1000):
    state = env.reset()
    total_reward = 0

    while True:
        action = agent.choose_action(state)
        next_state, reward, done, _ = env.step(action)

        agent.update(state, action, reward, next_state)

        state = next_state
        total_reward += reward

        if done:
            break

    agent.decay_epsilon()
    print(f"Episode {episode}: Reward = {total_reward}")

# 保存模型
torch.save(agent.q_table, "cartpole_model.pth")
```

---

### 3. p25-CLIP (图像搜索)

**项目类型**: 多模态 AI (文本 → 图像检索)

**技术栈**:
- **模型**: OpenAI CLIP
- **向量库**: Milvus
- **数据集**: ImageNet 子集

**目录结构**:
```
p25-CLIP/
├── clip_encoder.py      # CLIP 模型封装
├── milvus_client.py     # Milvus 连接
├── image_search.py      # 搜索引擎
├── preprocess.py        # 图像预处理
└── test_images/         # 测试图片
    ├── animals/
    ├── vehicles/
    └── food/
```

**核心实现**:
```python
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

class CLIPImageSearch:
    def __init__(self):
        # 加载 CLIP 模型
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        # 连接 Milvus
        self.milvus_client = MilvusClient(host="localhost", port=19530)

    def index_images(self, image_folder):
        """批量索引图片"""
        for img_path in glob.glob(f"{image_folder}/**/*.jpg"):
            # 1. 加载图片
            image = Image.open(img_path)

            # 2. 提取图像特征
            inputs = self.processor(images=image, return_tensors="pt")
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)

            # 3. 存入 Milvus
            self.milvus_client.insert(
                collection_name="images",
                data={
                    "embedding": image_features.numpy(),
                    "path": img_path
                }
            )

    def search_by_text(self, text_query, top_k=5):
        """文本查询图片"""
        # 1. 文本向量化
        inputs = self.processor(text=[text_query], return_tensors="pt")
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)

        # 2. 向量检索
        results = self.milvus_client.search(
            collection_name="images",
            query_vectors=text_features.numpy(),
            limit=top_k
        )

        # 3. 返回图片路径
        return [result["path"] for result in results]

# 使用示例
searcher = CLIPImageSearch()

# 索引图片库
searcher.index_images("./test_images")

# 文本搜索
results = searcher.search_by_text("a photo of a cat", top_k=3)
# 返回: ["./test_images/animals/cat_001.jpg", ...]
```

**支持的查询类型**:
- **对象查询**: "a photo of a dog"
- **场景查询**: "sunset over the ocean"
- **风格查询**: "impressionist painting"
- **颜色查询**: "red sports car"

---

## 最佳实践与注意事项

### 1. 内存管理选择指南

**决策树**:
```
是否需要持久化?
  ├─ 否 → 是否需要语义检索?
  │      ├─ 否 → 会话很长吗?
  │      │      ├─ 是 → Summarization / Sliding Window
  │      │      └─ 否 → Short-Term (InMemorySaver)
  │      └─ 是 → InMemory Vector Store
  │
  └─ 是 → 需要结构化查询吗?
         ├─ 是 → Knowledge Graph
         ├─ 否 → 需要自动过期吗?
         │      ├─ 是 → Redis TTL
         │      └─ 否 → FAISS Vector Store
```

### 2. 性能优化建议

#### FAISS 索引优化
```python
# 生产环境推荐配置
# 1. 使用 IVF (倒排索引) 加速大规模检索
import faiss

dimension = 1536
nlist = 100  # 聚类中心数量

quantizer = faiss.IndexFlatIP(dimension)
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

# 2. 训练索引 (需要 > 10K 样本)
index.train(training_vectors)

# 3. 查询时设置探测数量
index.nprobe = 10  # 权衡速度和精度
```

#### 向量缓存策略
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text: str):
    """缓存常见查询的向量"""
    return embedding_model.embed(text)
```

### 3. 安全性注意事项

#### 用户隔离
```python
# ✓ 正确: 严格过滤用户 ID
def search_memory(user_id: str, query: str):
    results = vector_store.search(query)
    return [r for r in results if r.metadata["user_id"] == user_id]

# ✗ 错误: 未过滤用户
def search_memory(query: str):
    return vector_store.search(query)  # 可能泄露其他用户数据
```

#### API 密钥管理
```python
# ✓ 使用环境变量
import os
api_key = os.getenv("DASHSCOPE_API_KEY")

# ✗ 硬编码在代码中
api_key = "sk-abc123..."  # 危险!
```

### 4. 错误处理最佳实践

#### 多层防御
```python
async def robust_memory_save(data):
    try:
        # 第1层: 主存储 (FAISS)
        await faiss_manager.add_memory(data)

    except FAISSError as e:
        logger.error(f"FAISS 失败: {e}")

        try:
            # 第2层: 降级到 Redis
            await redis_manager.save(data)

        except RedisError as e2:
            logger.critical(f"Redis 降级失败: {e2}")

            # 第3层: 本地文件备份
            with open("backup.jsonl", "a") as f:
                f.write(json.dumps(data) + "\n")
```

### 5. 监控与日志

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 记录关键指标
def log_memory_operation(operation: str, user_id: str, success: bool):
    logger.info(
        f"Memory Operation | "
        f"Op={operation} | "
        f"User={user_id} | "
        f"Success={success} | "
        f"Timestamp={datetime.now().isoformat()}"
    )
```

### 6. 测试策略

```python
import pytest

class TestFAISSMemory:
    @pytest.fixture
    def memory_manager(self):
        # 使用临时目录
        return FAISSMemoryManager(index_dir="./test_index")

    def test_add_and_search(self, memory_manager):
        # 添加记忆
        memory_manager.add_memory("user1", "我喜欢Python")

        # 搜索验证
        results = memory_manager.search_memory("user1", "编程语言")
        assert "Python" in results[0]

    def test_user_isolation(self, memory_manager):
        memory_manager.add_memory("user1", "私密信息1")
        memory_manager.add_memory("user2", "私密信息2")

        # 验证隔离
        results = memory_manager.search_memory("user1", "私密")
        assert "私密信息2" not in str(results)

    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        # 清理测试数据
        shutil.rmtree("./test_index", ignore_errors=True)
```

### 7. 部署建议

#### Docker 配置
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 设置环境变量
ENV DASHSCOPE_API_KEY=""
ENV REDIS_HOST="redis"
ENV FAISS_INDEX_DIR="/data/faiss_index"

# 启动应用
CMD ["python", "main.py"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
    volumes:
      - ./data:/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

---

## 总结

Week 07 提供了构建**企业级 AI Agent** 的完整技术栈:

1. **内存层次**: 从短期到长期，从无结构到结构化
2. **持久化策略**: FAISS / NetworkX / Redis 多种选择
3. **错误恢复**: 重试机制 + 降级方案
4. **集成能力**: RPA / API / 全栈应用
5. **性能优化**: 量化 / 剪枝 / 蒸馏

**学习路径建议**:
```
第1天: 基础概念 (p04, p06, p07)
第2天: 向量存储 (p08, p09)
第3天: 知识图谱 (p10)
第4天: 时序记忆 + 重试 (p11, p13)
第5天: 独立项目实战 (gemini-fullstack 或 CLIP)
```

---

**文档版本**: v1.0
**最后更新**: 2025-12-15
**维护者**: AI Engineering Training Team