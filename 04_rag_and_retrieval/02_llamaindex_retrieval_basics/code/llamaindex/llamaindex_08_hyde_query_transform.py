# -*- coding: utf-8 -*-
# Converted from llamaindex_08_hyde_query_transform.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%
## 问题改写提示词：
query_gen_str = """\
系统角色设定:
你是一个专业的问题改写助手。你的任务是将用户的原始问题扩充为一个更完整、更全面的问题。

规则：
1. 将可能的歧义、相关概念和上下文信息整合到一个完整的问题中
2. 使用括号对歧义概念进行补充说明
3. 添加关键的限定词和修饰语
4. 确保改写后的问题清晰且语义完整
5. 对于模糊概念，在括号中列举主要可能性

原始问题:
{query}

请生成一个综合的改写问题，确保：
- 包含原始问题的核心意图
- 涵盖可能的歧义解释
- 使用清晰的逻辑关系词连接不同方面
- 必要时使用括号补充说明

输出格式：
[综合改写] - 改写后的问题
"""
query_gen_prompt = PromptTemplate(query_gen_str)

# %%
## 将单一查询改写为多步骤查询
query_engine = sentence_index.as_query_engine(streaming=True,similarity_top_k=5)
query_engine = MultiStepQueryEngine(
    query_engine=query_engine,
    query_transform=step_decompose_transform,
    index_summary="公司请假信息"

# %%
# 方法三 ： 用假设文档来增强检索

from llama_index.core.indices.query.query_transform.base import (
    HyDEQueryTransform,
)
from llama_index.core.query_engine import TransformQueryEngine
# run query with HyDE query transform
hyde = HyDEQueryTransform(include_original=True)
query_engine = sentence_index.as_query_engine(streaming=True,similarity_top_k=5)
query_engine = TransformQueryEngine(query_engine, query_transform=hyde)

# %%
# 提取标签进行增强检索
system_message = """你是一个标签提取专家。请从文本中提取结构化信息，并按要求输出标签。
---
【支持的标签类型】
- 人名
- 部门名称
- 职位名称
- 技术领域
- 产品名称
---
【输出要求】
1. 请用 JSON 格式输出，如：[{"key": "部门名称", "value": "教研部"}]
2. 如果某类标签未识别到，则不输出该类
---
待分析文

# %%
LEAVE_ROUTER_INSTRUCTION = """你是一个专业的员工休假政策问题分类器。
请根据用户的提问内容，判断其咨询的休假类型。

请严格根据以下类别进行判断，输出结果只能是下列选项中的一个，不得添加任何解释、标点或额外信息：

- 年休假（用户询问年假天数、何时能休、是否可以拆分、未休补偿等）
- 病假（用户询问病假申请流程、需要什么证明、工资如何发放等）
- 事假（用户询问事假申请、审批流程、是否带薪等）
- 婚假（用户询问婚假天数、有效期、是否包含周末等）
- 产假或陪产假（用户询问产假/陪产假时长、生育津贴、能否延长等）
- 丧假（用户询问丧假天数、适用亲属范围等）
- 法定节假日（用户询问春节、国庆等节假日安排、调休等）
- 其他休假（如育儿假、哺乳假、工伤假等未明确列出的假期类型）
- 非休假问题（用户的问题与请假、休假政策完全无关，例如考勤打卡、薪资、离职等）

示例输出：
年休假
"""

router_agent = Assistants.create(
    model="qwen-plus",  # 推荐使用 qwen-plus：效果均衡，支持长上下文，适合理解复杂语义
    name='休假问题分类器',
    description='负责将员工关于休假政策的咨询自动分类到对应假期类型，用于路由至专业问答模块。',
    instructions=LEAVE_ROUTER_INSTRUCTION
)
