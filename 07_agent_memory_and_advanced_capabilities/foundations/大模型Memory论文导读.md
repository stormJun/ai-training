# 大模型 Memory 论文导读

这份文档整理的是和大模型 `memory` 相关、适合入门和建立整体框架的论文。  
重点覆盖：

- memory 为什么需要
- memory 怎么设计
- 长期记忆与外部记忆
- agent memory
- 参数化 / 潜空间记忆
- 工程化长期记忆系统

## 1. 入门先看

### 1.1 A Survey on the Memory Mechanism of Large Language Model based Agents

- 类型：综述
- 作用：适合先建立全局框架，理解记忆为什么需要、怎么设计、怎么评估
- 链接：https://arxiv.org/abs/2404.13501

建议先读这篇，因为它能先把以下问题讲清楚：

- 什么是 LLM agent 的 memory
- memory 在 agent 中扮演什么角色
- memory 的来源、形式、操作和评估方式有哪些

## 2. 长期记忆 / 外部记忆

### 2.1 MemoryBank: Enhancing Large Language Models with Long-Term Memory

- 类型：长期对话记忆
- 作用：很典型的“长期对话记忆”工作
- 重点：强调记忆的存取、更新和遗忘
- 链接：https://arxiv.org/abs/2305.10250

这篇更偏：

- 长期对话
- 用户历史信息积累
- 记忆检索与更新机制

### 2.2 Augmenting Language Models with Long-Term Memory (LongMem)

- 类型：长期记忆架构
- 作用：更偏“给 LLM 增加长期记忆模块”的代表作
- 重点：适合看模型架构设计
- 链接：https://arxiv.org/abs/2306.07174

这篇更偏：

- 模型架构层的 long-term memory
- 如何把额外记忆模块挂到语言模型上

### 2.3 Think-in-Memory: Recalling and Post-thinking Enable LLMs with Long-Term Memory

- 类型：长期记忆 + 推理流程
- 作用：强调“先回忆，再回答，事后再整理记忆”
- 链接：https://arxiv.org/abs/2311.08719

这篇的特点是把 memory 不只当存储层，而是放进完整推理链路里：

- recall
- answer
- post-thinking

## 3. Agent Memory / 行为记忆

### 3.1 Generative Agents: Interactive Simulacra of Human Behavior

- 类型：agent memory 经典论文
- 作用：虽然更偏 agent，但对后续 memory 方向影响非常大
- 重点：`memory stream + reflection + planning`
- 链接：https://arxiv.org/abs/2304.03442

这篇的重要性在于，它把 agent 的行为机制和记忆机制真正串起来了：

- 先积累 memory stream
- 再通过 reflection 抽象高层经验
- 再结合 planning 驱动后续行为

### 3.2 A-MEM: Agentic Memory for LLM Agents

- 类型：agent memory
- 作用：更偏 agent 的记忆组织与管理
- 链接：https://arxiv.org/abs/2502.12110

这篇更适合看：

- agent 场景下 memory 的组织方式
- memory 如何服务多步任务与决策

## 4. 参数化 / 潜空间记忆

### 4.1 MEMORYLLM: Towards Self-Updatable Large Language Models

- 类型：参数化记忆
- 作用：偏“把记忆做进模型内部 / 潜空间”，不是单纯外部检索
- 链接：https://arxiv.org/abs/2402.04624

这篇适合帮助区分两类 memory 思路：

- 外部 memory：单独存、单独取
- 参数化 memory：直接写进模型内部表示

### 4.2 M+: Extending MemoryLLM with Scalable Long-Term Memory

- 类型：参数化长期记忆扩展
- 作用：是 MemoryLLM 这条线的后续扩展
- 链接：https://arxiv.org/abs/2502.00592

这篇更适合接着看：

- 参数化 memory 如何扩展
- 可扩展长期记忆怎么做

## 5. 工程化记忆系统

### 5.1 Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory

- 类型：工程化长期记忆系统
- 作用：更偏工程和 `production-ready` 的长期记忆系统
- 重点：和项目里的 `mem0` 这条线直接相关
- 链接：https://arxiv.org/abs/2504.19413

如果你已经开始关注落地，就可以重点看这篇。它更偏：

- 长期记忆系统如何工程化
- 如何做生产可用的 memory 层
- 如何让 agent 在长期使用中保留用户信息

## 6. 推荐阅读顺序

如果你想快速建立理解，可以按下面顺序读：

1. `A Survey on the Memory Mechanism of Large Language Model based Agents`
2. `Generative Agents: Interactive Simulacra of Human Behavior`
3. `MemoryBank: Enhancing Large Language Models with Long-Term Memory`
4. `Augmenting Language Models with Long-Term Memory (LongMem)`
5. `Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory`

## 7. 一句话区分

- `Generative Agents`：agent memory 的经典起点
- `MemoryBank / Mem0`：更像长期对话记忆系统
- `LongMem / MemoryLLM`：更偏模型架构层的 memory
- `Survey`：适合总览整个方向

## 8. 适合什么人先看哪篇

- 如果你是第一次接触 memory：先看 `Survey`
- 如果你想理解 agent 为什么需要记忆：看 `Generative Agents`
- 如果你想理解长期对话记忆怎么做：看 `MemoryBank`
- 如果你想理解“记忆模块怎么接到模型上”：看 `LongMem`
- 如果你更关心工程落地：看 `Mem0`
