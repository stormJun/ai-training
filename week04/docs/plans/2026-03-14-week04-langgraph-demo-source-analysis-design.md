# week04-langgraph-demo 源码解析设计文档

**日期：** 2026-03-14

**目标：** 在 `week04/docs` 下补充一篇面向进阶读者的源码解析文档，系统说明 `week04-langgraph-demo` 如何通过 `HostAgent + Subagent` 组合实现路由、分发、聚合，以及 `direct/remote` 两种运行模式的统一编排。

## 背景

`week04-langgraph-demo` 已经具备可运行的 README，但缺少一篇从源码结构、状态流转、调用链和扩展点角度展开的技术文档。现有 `week04/docs` 中已有 LangGraph 相关理论说明，因此新增文档应更聚焦项目本身，而不是重复通用概念。

## 目标读者

- 已掌握 `StateGraph` 的基本使用方式
- 希望理解 demo 的多代理拆分思路与代码组织
- 需要对照源码快速建立整体心智模型的进阶读者

## 文档边界

### 包含内容

- `HostAgent`、`StockAgent`、`AnalysisAgent` 的职责划分
- 三张 `StateGraph` 各自的状态设计与节点职责
- 一次查询从入口到最终答案的完整执行链
- `direct` 与 `remote` 两种模式如何接入同一套 Host Graph
- `store.py`、`models.py`、`apps/*.py`、`run_all.py` 在整体架构中的位置
- 当前 demo 的简化点与可扩展方向

### 不包含内容

- LangGraph Pregel 运行时或 channel 机制底层源码分析
- A2A 协议的完整实现细节
- 通用股票分析方法论或真实投研策略

## 结构设计

1. 项目定位与核心问题
2. 架构总览
3. 为什么拆成 Host / Subagent
4. 三张 StateGraph 的状态与节点职责
5. 一次请求的完整执行链
6. `direct` / `remote` 两种执行路径对照
7. 共享基础设施：`store`、`models`、FastAPI、`run_all`
8. 当前简化点与后续扩展方向

## 呈现方式

- 使用一张 Mermaid 架构图概览模块关系
- 使用两条文本化流程分别说明 `direct` 与 `remote` 路径
- 关键分析段落直接绑定具体源码文件路径
- 解释重点放在“为什么这样设计”与“状态如何流转”

## 写作原则

- 以项目源码为主线，而非按文件逐一注释
- 适度引用必要代码片段，但避免把文档写成逐行讲解
- 对复杂点给出抽象总结，再回落到具体实现
- 结尾明确指出 demo 与真实多智能体系统之间的差距

## 验收标准

- 读者能解释三类 agent 的职责边界
- 读者能说明 `HostGraph` 如何切换本地调用与远程调用
- 读者能定位共享数据模型和静态数据仓库的作用
- 文档能作为 `week04-langgraph-demo` 的源码导读入口
