# -*- coding: utf-8 -*-
# Converted from p12-crewAI.ipynb

# %%
# NOTEBOOK_MAGIC: !pip install crewai

# %%
## 需要提前通过export把token注入.

from crewai import Agent, Task, Crew
from langchain.chat_models import ChatOpenAI
import os

# 创建GPT-4o mini语言模型实例
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 创建智能体
researcher = Agent(
    role='市场研究员',
    goal='深入研究市场趋势和竞争对手',
    backstory='你是一位经验丰富的市场研究员,擅长收集和分析市场数据。',
    verbose=True,
    llm=llm
)

strategist = Agent(
    role='商业策略师',
    goal='制定有效的商业策略',
    backstory='你是一位资深商业策略师,擅长制定创新的商业计划。',
    verbose=True,
    llm=llm
)

writer = Agent(
    role='商业计划撰写人',
    goal='撰写清晰、详细的商业计划',
    backstory='你是一位专业的商业计划撰写人,擅长将复杂的信息转化为易于理解的文档。',
    verbose=True,
    llm=llm
)

# 定义任务
task1 = Task(
    description='进行简要市场研究,分析目标市场的主要特征和主要竞争对手。',
    agent=researcher,
    expected_output="一份简洁的市场研究报告,包括市场主要特征和主要竞争对手。"
)

task2 = Task(
    description='基于市场研究结果,制定7天的初步商业策略,包括产品定位和主要营销方向。',
    agent=strategist,
    expected_output="一份7天的初步商业策略计划,包括产品定位和主要营销方向。"
)

task3 = Task(
    description='将研究结果和策略整合成一份简要的7天商业计划概要。',
    agent=writer,
    expected_output="一份简要的7天商业计划概要,包括市场分析要点和主要策略方向。"
)

# 创建Crew
crew = Crew(
    agents=[researcher, strategist, writer],
    tasks=[task1, task2, task3],
    verbose=True
)

# 运行Crew并获取结果
result = crew.kickoff()

print("最终的7天商业计划概要：")
print(result)

# %%
from crewai import Agent, Task, Crew
from langchain.chat_models import ChatOpenAI

# 初始化模型
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 定义 Agent
requirement_parser = Agent(
    role="需求解析专家",
    goal="从需求文档中提取关键测试点",
    backstory="你是一位资深测试专家，擅长从自然语言需求中识别测试场景。",
    verbose=True,
    llm=llm
)

test_case_generator = Agent(
    role="测试用例生成专家",
    goal="生成覆盖正常、边界和异常场景的测试用例",
    backstory="你能够根据测试点生成多维度测试用例，并确保逻辑完整性。",
    verbose=True,
    llm=llm
)

formatter = Agent(
    role="格式转换专家",
    goal="将测试用例转换为Jira或Gherkin格式",
    backstory="你熟悉多种测试用例格式规范，并能自动适配不同团队需求。",
    verbose=True,
    llm=llm
)

validator = Agent(
    role="验证专家",
    goal="验证测试用例的完整性和逻辑一致性",
    backstory="你能够检查测试用例是否覆盖需求，是否存在冲突。",
    verbose=True,
    llm=llm
)

# 定义任务
task1 = Task(
    description="解析以下需求并提取测试点：'用户登录功能需支持手机号/邮箱登录，密码强度校验，登录失败3次锁定账户'",
    agent=requirement_parser,
    expected_output="提取出的测试点列表，包括登录方式、密码强度验证、账户锁定机制等"
)

task2 = Task(
    description="根据测试点生成测试用例（正常流程、边界条件、异常场景）",
    agent=test_case_generator,
    expected_output="完整的测试用例集合，包含正常流程、边界条件和异常场景的测试用例"
)

task3 = Task(
    description="将测试用例转换为Jira格式",
    agent=formatter,
    expected_output="Jira格式的测试用例，包含测试步骤、预期结果、优先级等信息"
)

task4 = Task(
    description="验证测试用例是否覆盖所有需求点，是否存在逻辑冲突",
    agent=validator,
    expected_output="验证报告，说明测试用例覆盖情况和发现的任何问题"
)


# 创建 Crew 并运行 - 修复：verbose 参数改为布尔值
crew = Crew(
    agents=[requirement_parser, test_case_generator, formatter, validator],
    tasks=[task1, task2, task3, task4],
    verbose=True
)

result = crew.kickoff()
print(result)

# %% [markdown]
# 使用工具
# ```bash
# pip install "crewai[tools]"
# ```
#
# ```python
# import os
# from crewai import Agent, Task, Crew
# # Importing crewAI tools
# from crewai_tools import (
#     DirectoryReadTool,
#     FileReadTool,
#     SerperDevTool,
#     WebsiteSearchTool
# )
#
# # Set up API keys
# os.environ["SERPER_API_KEY"] = "Your Key" # serper.dev API key
# os.environ["OPENAI_API_KEY"] = "Your Key"
#
# # Instantiate tools
# docs_tool = DirectoryReadTool(directory='./blog-posts')
# file_tool = FileReadTool()
# search_tool = SerperDevTool()
# web_rag_tool = WebsiteSearchTool()
#
# # Create agents
# researcher = Agent(
#     role='Market Research Analyst',
#     goal='Provide up-to-date market analysis of the AI industry',
#     backstory='An expert analyst with a keen eye for market trends.',
#     tools=[search_tool, web_rag_tool],
#     verbose=True
# )
#
# writer = Agent(
#     role='Content Writer',
#     goal='Craft engaging blog posts about the AI industry',
#     backstory='A skilled writer with a passion for technology.',
#     tools=[docs_tool, file_tool],
#     verbose=True
# )
#
# # Define tasks
# research = Task(
#     description='Research the latest trends in the AI industry and provide a summary.',
#     expected_output='A summary of the top 3 trending developments in the AI industry with a unique perspective on their significance.',
#     agent=researcher
# )
#
# write = Task(
#     description="Write an engaging blog post about the AI industry, based on the research analyst's summary. Draw inspiration from the latest blog posts in the directory.",
#     expected_output='A 4-paragraph blog post formatted in markdown with engaging, informative, and accessible content, avoiding complex jargon.',
#     agent=writer,
#     output_file='blog-posts/new_post.md'  # The final blog post will be saved here
# )
#
# # Assemble a crew with planning enabled
# crew = Crew(
#     agents=[researcher, writer],
#     tasks=[research, write],
#     verbose=True,
#     planning=True,  # Enable planning feature
# )
#
# # Execute tasks
# crew.kickoff()
# ```
