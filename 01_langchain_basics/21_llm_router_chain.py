# -*- coding: utf-8 -*-
# Converted from p24-LLMRouterChain.ipynb

# %%
##  一个售前和售后的 langchain  LLMRouterChain 模版

from langchain.chains.router import MultiPromptChain
from langchain_community.llms import Tongyi
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import (
    LLMRouterChain,
    RouterOutputParser
)
from langchain.chains.router.multi_prompt_prompt import (
    MULTI_PROMPT_ROUTER_TEMPLATE
)

# 售前咨询模板
presales_prompt_tpl = PromptTemplate.from_template(
    '你是一位专业的售前顾问，擅长产品介绍、方案推荐和商务咨询。'
    '你需要热情、专业地回答客户的产品咨询、价格询问、功能介绍等售前问题。'
    '请使用中文帮我解答下列售前咨询问题：\n{input}'
)

# 售后服务模板
aftersales_prompt_tpl = PromptTemplate.from_template(
    '你是一位耐心的售后服务专员，擅长解决客户的使用问题、技术支持和投诉处理。'
    '你需要耐心、细致地帮助客户解决产品使用中遇到的问题，提供技术支持和服务指导。'
    '请使用中文帮我解答下列售后服务问题：\n{input}'
)

# 创建模板信息列表
prompt_infos = [
    {
        'name': 'presales',
        'description': '用于处理售前咨询，包括产品介绍、价格询问、功能说明、方案推荐等',
        'prompt_template': presales_prompt_tpl,
    },
    {
        'name': 'aftersales',
        'description': '用于处理售后服务，包括使用问题、技术支持、故障排除、投诉处理等',
        'prompt_template': aftersales_prompt_tpl,
    },
]

llm = Tongyi(
    temperature=0.1,
)

# 生成键为模板名称、值为Chain的字典
destination_chains = {}
for p_info in prompt_infos:
    name = p_info['name']
    prompt = p_info['prompt_template']
    chain = LLMChain(llm=llm, prompt=prompt)
    destination_chains[name] = chain

# 将模板名称和模板描述通过MULTI_PROMPT_ROUTER_TEMPLATE生成模板
destinations = [f'{p["name"]}: {p["description"]}'
                for p in prompt_infos]
destinations_str = "\n".join(destinations)

router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
    destinations=destinations_str
)
router_prompt = PromptTemplate(
    template=router_template,
    input_variables=['input'],
    output_parser=RouterOutputParser(),
)
router_chain = LLMRouterChain.from_llm(llm, router_prompt)

# 这里创建了一个default_chain
# 为了防止提的问题类型并没有包含在prompt_infos中
default_chain = ConversationChain(llm=llm, output_key='text')
chain = MultiPromptChain(
    router_chain=router_chain,
    destination_chains=destination_chains,
    default_chain=default_chain,
    verbose=True,
)

# 测试售前咨询问题
print("=== 售前咨询测试 ===")
print(chain.run("你们的产品有什么功能？价格是多少？"))

print("\n=== 售后服务测试 ===")
print(chain.run("我的产品出现故障了，无法正常启动，该怎么办？"))

print("\n=== 其他问题测试 ===")
print(chain.run("今天天气怎么样？"))

# %%
# 整合链的语法

from langchain.chains.router import MultiPromptChain
from langchain_community.llms import Tongyi
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import (
    LLMRouterChain,
    RouterOutputParser
)
from langchain.chains.router.multi_prompt_prompt import (
    MULTI_PROMPT_ROUTER_TEMPLATE
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

# 初始化LLM
llm = Tongyi(temperature=0.1)

# 售前咨询链 - 使用新式语法
presales_prompt = PromptTemplate.from_template(
    '你是一位专业的售前顾问，擅长产品介绍、方案推荐和商务咨询。'
    '你需要热情、专业地回答客户的产品咨询、价格询问、功能介绍等售前问题。'
    '请使用中文帮我解答下列售前咨询问题：\n{input}'
)
presales_chain = presales_prompt | llm | StrOutputParser()

# 售后服务链 - 使用新式语法
aftersales_prompt = PromptTemplate.from_template(
    '你是一位耐心的售后服务专员，擅长解决客户的使用问题、技术支持和投诉处理。'
    '你需要耐心、细致地帮助客户解决产品使用中遇到的问题，提供技术支持和服务指导。'
    '请使用中文帮我解答下列售后服务问题：\n{input}'
)
aftersales_chain = aftersales_prompt | llm | StrOutputParser()

# 意图识别链 - 使用新式语法
intent_prompt = PromptTemplate.from_template(
    """请分析以下用户问题的意图，判断是售前咨询还是售后服务：

售前咨询：产品介绍、功能说明、价格询问、方案推荐、购买咨询等
售后服务：使用问题、技术支持、故障排除、投诉处理、维修服务等

用户问题：{input}

请只回答"售前"或"售后"，不要添加其他内容。"""
)
intent_chain = intent_prompt | llm | StrOutputParser()

# 创建路由函数
def route_question(input_dict):
    question = input_dict["input"]
    intent = intent_chain.invoke({"input": question})

    print(f"识别意图: {intent.strip()}")

    if "售前" in intent:
        return presales_chain.invoke({"input": question})
    elif "售后" in intent:
        return aftersales_chain.invoke({"input": question})
    else:
        # 默认处理
        default_prompt = PromptTemplate.from_template(
            "我是一个智能助手，很高兴为您服务。请问有什么可以帮助您的吗？\n问题：{input}"
        )
        default_chain = default_prompt | llm | StrOutputParser()
        return default_chain.invoke({"input": question})

# 创建完整的路由链
router_chain = RunnablePassthrough() | RunnableLambda(route_question)

# 方法二：更简洁的条件路由实现
from langchain_core.runnables import RunnableBranch

# 创建条件判断函数
def is_presales(input_dict):
    intent = intent_chain.invoke(input_dict)
    return "售前" in intent

def is_aftersales(input_dict):
    intent = intent_chain.invoke(input_dict)
    return "售后" in intent

# 使用 RunnableBranch 创建条件路由
branch_chain = RunnableBranch(
    (is_presales, presales_chain),
    (is_aftersales, aftersales_chain),
    # 默认链
    PromptTemplate.from_template("我是智能助手，请问有什么可以帮助您的？\n{input}") | llm | StrOutputParser()
)

# 测试代码
if __name__ == "__main__":
    print("=== 方法一：自定义路由函数 ===")

    # 测试售前问题
    print("\n--- 售前咨询测试 ---")
    result1 = router_chain.invoke({"input": "你们的产品有什么功能？价格是多少？"})
    print(f"回答: {result1}")

    # 测试售后问题
    print("\n--- 售后服务测试 ---")
    result2 = router_chain.invoke({"input": "我的产品出现故障了，无法正常启动，该怎么办？"})
    print(f"回答: {result2}")

    print("\n=== 方法二：RunnableBranch 条件路由 ===")

    # 测试售前问题
    print("\n--- 售前咨询测试 ---")
    result3 = branch_chain.invoke({"input": "我想了解一下你们的服务套餐和收费标准"})
    print(f"回答: {result3}")

    # 测试售后问题
    print("\n--- 售后服务测试 ---")
    result4 = branch_chain.invoke({"input": "产品使用过程中遇到了错误提示，需要技术支持"})
    print(f"回答: {result4}")

# %% [markdown]
# ## EmbeddingRouterChain
#
# 不仅可以使用 LLMRouteChain 来智能选择合适的处理链，还可以采用 EmbeddingRouterChain，该组件通过计算各 Chain 描述与用户问题之间的语义相关性，实现更精准的路由决策。

# %%
# NOTEBOOK_MAGIC: !pip install chromadb

# %%
from langchain_community.vectorstores import Chroma    # # pip install chroma
from langchain_community.embeddings import DashScopeEmbeddings # pip install dashscope
from langchain.chains import LLMRouterChain, MultiPromptChain
from langchain_core.language_models import BaseLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Tongyi  # 或你使用的 LLM
import os

# 1. 定义任务名称与描述
names_and_descriptions = [
    ("physics", ["用于解答物理相关问题，例如力学、电磁学等"]),
    ("math", ["用于解答数学相关问题，例如代数、几何、微积分等"]),
]

# 2. 使用通义千问的 Embedding 模型
embeddings = DashScopeEmbeddings(model="text-embedding-v2")

# 3. 构建向量数据库（用于路由匹配）
descriptions = []
names = []
for name, desc_list in names_and_descriptions:
    for desc in desc_list:
        descriptions.append(desc)
        names.append(name)

# 创建 Chroma 向量库
vectorstore = Chroma(embedding_function=embeddings)
# 批量添加文档
vectorstore.add_texts(texts=descriptions, metadatas=[{"name": name} for name in names])

# 4. 自定义 Embedding 路由链（LangChain 没有直接 from_names_and_descriptions）
def get_relevant_chain_name(question: str) -> str:
    docs = vectorstore.similarity_search(question, k=1)
    return docs[0].metadata["name"]

# 5. 定义各个目标链的 prompt 和 LLM
llm = Tongyi(model_name="qwen-plus", temperature=0.1)  # 可替换为你用的 LLM

physics_prompt = PromptTemplate(
    template="你是一个物理专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)
math_prompt = PromptTemplate(
    template="你是一个数学专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)

destination_chains = {
    "physics": physics_prompt | llm,
    "math": math_prompt | llm,
}

default_chain = PromptTemplate.from_template("请回答以下问题：{input}") | llm

# 6. 定义运行逻辑（模拟 MultiPromptChain）
def run_router_chain(question: str):
    chain_name = get_relevant_chain_name(question)
    print(f"路由到: {chain_name}")
    if chain_name in destination_chains:
        return destination_chains[chain_name].invoke({"input": question})
    else:
        return default_chain.invoke({"input": question})

# 7. 测试
result = run_router_chain("牛顿第一定律是什么？")
print(result)
