# 工作流编排

这一阶段是 `02_langgraph_basics` 里最核心的一段内容。

如果前面的 `01_intro` 主要解决的是：

- LangGraph 是什么
- 状态、节点、边怎么理解

那么这一阶段解决的是：

> 当图开始变复杂之后，怎样把它做成真正可用的工作流。

这里的内容会从工作流基础，一路走到：

- 人机协同
- 记忆机制
- RAG 工作流
- 快照与恢复
- Studio 调试

---

## 建议阅读顺序

1. [tutorials/01_workflow_foundations/README.md](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/01_workflow_foundations/README.md)
   先建立整体心智模型，理解为什么工作流需要编排、路由和结构化控制。

2. `tutorials/02_human_in_the_loop/04_人机协同_HITL.md` / `04_人机协同_HITL.py`
   看最基础的人机协同例子，理解审批节点、条件路由和人工介入。

3. [tutorials/03_memory/README.md](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/03_memory/README.md)
   再看短期记忆、长期记忆、Redis、窗口记忆和 Mem0。

4. [tutorials/04_rag_workflows/README.md](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/04_rag_workflows/README.md)
   把检索、路由、评分、生成和回退做成一张完整工作流图。

5. [tutorials/05_snapshot_and_recovery/README.md](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/05_snapshot_and_recovery/README.md)
   理解 `checkpointer`、状态历史、检查点恢复和容错流程。

6. [tutorials/06_studio_and_debugging/README.md](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/06_studio_and_debugging/README.md)
   最后看本地 API、Studio 和工作流调试入口。

---

## 这一阶段真正要掌握什么

- 工作流不是单次函数调用，而是状态驱动的执行过程
- 节点之间不只是顺序连接，还会涉及条件路由、重试、回退和人工介入
- 一旦开始做真实 Agent 系统，记忆、RAG、快照和调试能力都不再是可选项

你可以把这一阶段理解成：

> 从“会写一个图”，进入“会组织一套可运行、可调试、可恢复的图”。

---

## 阅读建议

这一阶段里的很多示例都带有运行依赖，例如：

- `DASHSCOPE_API_KEY`
- Redis
- `mem0`
- `TAVILY_API_KEY`
- `langgraph-cli`

所以更推荐的阅读方式是：

1. 先读 `.md`
2. 再看同名 `.py`
3. 最后再决定要不要把对应环境完整跑起来

这样不会因为环境问题打断理解主线。

---

## 参考资料

- `references/12_参考论文_2510.11967v1.pdf`
- `references/13_智能客服系统架构设计.pdf`

这些材料更适合在你已经看完主线示例之后，再拿来做补充阅读。

---

## 小结

如果你能顺着这一阶段走完，应该会建立起这样一套认识：

- LangGraph 不只是“搭 Agent”
- 更重要的是“把 Agent 做成工作流系统”

而这一点，正是后面服务化、多智能体和协议扩展的基础。  
