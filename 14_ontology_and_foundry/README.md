# Ontology and Foundry

本目录用于记录 Ontology 与 Palantir Foundry 相关学习内容。

目录路径：

`/Users/songxijun/workspace/otherProject/ai-training/14_ontology_and_foundry`

## Palantir Foundry Ontology 学习入口

说明：

Palantir Foundry 的 Ontology 更接近产品化的企业语义层与操作层设计，不是主要靠学术论文定义的概念。理解它，优先看官方文档和白皮书。

### 推荐阅读

1. Ontology Overview
- 作用：建立最基础的概念框架。
- 重点：`objects`、`properties`、`links`、`actions`、`functions`、`interfaces`
- 链接：https://www.palantir.com/docs/foundry/ontology/overview

2. The Ontology System
- 作用：理解 Foundry 为什么把 ontology 设计成“系统”而不只是语义模型。
- 重点：把 `data + logic + action + security` 统一到企业决策模型里。
- 链接：https://www.palantir.com/docs/foundry/architecture-center/ontology-system

3. Core Concepts
- 作用：把概念落实到对象模型。
- 重点：`object type`、`property`、`link type`、`action type`
- 链接：https://www.palantir.com/docs/foundry/ontology/core-concepts

4. Why Create an Ontology?
- 作用：理解 Palantir 为什么强调 ontology，而不只强调 data platform。
- 重点：可解释性、规模化连接、决策沉淀、运营闭环。
- 链接：https://www.palantir.com/docs/foundry/ontology/why-ontology

5. Object Permissioning
- 作用：理解 Foundry Ontology 与普通知识图谱的重要差异。
- 重点：对象级权限、安全控制、按业务对象治理访问。
- 链接：https://www.palantir.com/docs/foundry/object-permissioning/overview

6. Ontology-aware Applications
- 作用：理解 ontology 如何直接驱动应用层。
- 重点：对象视图、工作流、操作闭环，而不只是“查询数据”。
- 链接：https://www.palantir.com/docs/foundry/ontology/applications

7. Foundry 平台白皮书
- 作用：从平台整体角度看 ontology 在 Foundry 里的位置。
- 链接：
  - https://www.palantir.com/assets/xrfr7uokpv1b/mhoyY4c8vdVlJhulDStk2/a7340768109c8e8d79d00b4cb99d8e70/Whitepaper_-_Foundry_2022.pdf
  - https://www.palantir.com/assets/xrfr7uokpv1b/7BxLPkTqJU9QhLTQCjJMo6/eed1457949dc2d1cd6b6e71936c0aa9c/Enabling_Interoperability_and_Embracing_Openness_with_Foundry.pdf

## 建议阅读顺序

`Overview -> Core Concepts -> The Ontology System -> Why Create an Ontology? -> Object Permissioning -> Ontology-aware Applications`

## 一句话理解

Palantir Foundry Ontology 不是传统意义上“只表达知识”的 ontology，也不是普通 semantic layer；它更像是把企业对象、关系、权限、业务动作和应用工作流绑定在一起的 operational ontology。
