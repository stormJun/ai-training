# -*- coding: utf-8 -*-
# Converted from p36-tool.ipynb

# %% [markdown]
# ## 内置工具
#
# https://python.langchain.ac.cn/docs/integrations/tools/
#

# %%
# NOTEBOOK_MAGIC: !pip install -qU duckduckgo-search langchain-community ddgs

# %%
from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()

search.invoke("苹果公司的创始人 ?")


# %%
# 溯源

from langchain_community.tools import DuckDuckGoSearchResults

search = DuckDuckGoSearchResults(output_format="list")

search.invoke("苹果公司的创始人 ?")

# %%
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# 创建搜索工具
search_wrapper = DuckDuckGoSearchResults(output_format="list")

@tool("my_search_tool")
def search(query: str) -> list[str]:
    """通过搜索引擎查询"""
    result = search_wrapper.invoke(query)
    return [res["snippet"] for res in result]

print(search.name)
print(search.description)
print(search.args)


def create_react_search_agent():
    tools = [search]
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")


    prompt = PromptTemplate.from_template("""
        Answer the following questions as best you can. You have access to the following tools:

        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question

        Begin!

        Question: {input}
        Thought:{agent_scratchpad}""")

    agent = create_react_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True  # 这个很重要！
    )

    return agent_executor

# 使用修复后的 Agent
agent = create_react_search_agent()

# 测试
questions = ["苹果公司的创始人是谁？"]

for question in questions:
    print(f"\n问题: {question}")
    response = agent.invoke({"input": question})
    print(f"答案: {response['output']}")
    print("-" * 50)
