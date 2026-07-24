<!-- Converted from p36-tool.ipynb -->

## 内置工具

https://python.langchain.ac.cn/docs/integrations/tools/


```python
!pip install -qU duckduckgo-search langchain-community ddgs
```

```python
from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()

search.invoke("苹果公司的创始人 ?")

```

输出：

```text
'2025年7月22日 — 1976年4月，史蒂夫·賈伯斯、史蒂夫·沃茲尼亞克和羅納德·韋恩創立了蘋果公司，目的是為了研發和銷售沃茲尼亞克Apple I個人電腦，但韋恩12天後就放棄了自己的股份。 2025年7月13日 — 1976年，沃茲尼克與史蒂夫·賈伯斯合夥創立蘋果電腦公司，並在1970年代末研發出第一代和第二代蘋果電腦。 二代電腦一經發售即風靡全美，成為1970-80年代之交銷量最佳的個人電 ... 2024年10月8日 — 乔布斯 的离世引发了全球科技从业者的哀悼。他不仅是苹果公司的创始人，还是一位卓越的创新者，其对产品设计、创业和企业管理的见解深刻影响了科技界。 美国 司 法部称 苹 果 公 司 是非法垄断企业，并基于有着上百年历史 的 《谢尔曼法》对这家 公 司 提起诉讼。 《华尔街日报》请反垄断律师分析了 司 法部 的 法律论据，以及 苹 果 公 司 可能如何反击。 Spotify于2019年3月向欧洲监管机构提出了针对 苹 果 的 反托拉斯投诉。 “ 苹 果 公 司 已向App Store引入新增规则，目 的 是限制选择并扼杀 创 新，以牺牲用户体验为代价。 ” 公 司 创 始 人 兼首席执行官Daniel Ek当时表示。'
```

```python
# 溯源

from langchain_community.tools import DuckDuckGoSearchResults

search = DuckDuckGoSearchResults(output_format="list")

search.invoke("苹果公司的创始人 ?")
```

输出：

```text
[{'snippet': '2025年7月22日 — 1976年4月，史蒂夫·賈伯斯、史蒂夫·沃茲尼亞克和羅納德·韋恩創立了蘋果公司，目的是為了研發和銷售沃茲尼亞克Apple I個人電腦，但韋恩12天後就放棄了自己的股份。',
  'title': '蘋果公司- 維基百科，自由的百科全書',
  'link': 'https://zh.wikipedia.org/zh-hk/蘋果公司'},
 {'snippet': '2025年7月13日 — 1976年，沃茲尼克與史蒂夫·賈伯斯合夥創立蘋果電腦公司，並在1970年代末研發出第一代和第二代蘋果電腦。 二代電腦一經發售即風靡全美，成為1970-80年代之交銷量最佳的個人電 ...',
  'title': '史蒂夫·沃茲尼克',
  'link': 'https://zh.wikipedia.org/zh-hk/史蒂夫·沃兹尼亚克'},
 {'snippet': '在他生活 的 年代裡，喬布斯被認為是電腦業界與娛樂業界 的 標誌性人物，同時 人 們也把他視作 mac 、 iPod 、 iPhone 、 iPad 等知名數碼產品 的 締造者。 他亦曾七次登上《時代雜誌》封面，被認為是当时全球最為成功 的 商人之一。',
  'title': '史蒂夫·乔布斯 - 维基百科，自由的百科全书',
  'link': 'https://zh.wikipedia.org/wiki/史蒂夫·乔布斯'},
 {'snippet': '2024年10月8日 — 乔布斯 的离世引发了全球科技从业者的哀悼。他不仅是苹果公司的创始人，还是一位卓越的创新者，其对产品设计、创业和企业管理的见解深刻影响了科技界。',
  'title': '离世13周年，重温乔布斯的100条思考',
  'link': 'https://finance.sina.com.cn/stock/stockzmt/2024-10-08/doc-incrvssy7197443.shtml'}]
```

```python
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
```

输出：

```text
my_search_tool
通过搜索引擎查询
{'query': {'title': 'Query', 'type': 'string'}}

问题: 苹果公司的创始人是谁？


[1m> Entering new AgentExecutor chain...[0m
[32;1m[1;3m我应该使用搜索工具来查找苹果公司的创始人是谁。
Action: my_search_tool
Action Input: "苹果公司的创始人是谁"[0m[36;1m[1;3m['2025年7月13日 — 1976年，沃茲尼克與史蒂夫·賈伯斯合夥創立蘋果電腦公司，並在1970年代末研發出第一代和第二代蘋果電腦。 二代電腦一經發售即風靡全美，成為1970-80年代之交銷量最佳的個人電 ...', '1 day ago · 네이버 동영상 검색 은 네이버의 동영상 검색 서비스이다. 2005년 12월 네이버 동영상 검색 오픈 베타 서비스가 시작되었다.', '1 日前 — 1976年4月1日，乔布斯、沃兹和罗纳德·杰拉尔德·韦恩（Ronald Gerald Wayne）在乔布斯父母的车库里创立合伙企业“ 苹果 电脑 公司 ” 。韦恩是乔布斯在雅达利的同事，在合伙企业期间为 ...', '2025年2月17日 — 十年前 蘋果 前 創始人 喬布斯（Steve Jobs）結束了他傳奇的一生。隨後，庫克（Tim Cook）接過了 蘋果 的大旗，至今也已十年之久。而這十年間，眾人對庫克的評價是褒貶不一的，庫克也 ...'][0m[32;1m[1;3m根据搜索结果，苹果公司的创始人是史蒂夫·乔布斯（Steve Jobs）。
Final Answer: 史蒂夫·乔布斯（Steve Jobs）是苹果公司的创始人。[0m

[1m> Finished chain.[0m
答案: 史蒂夫·乔布斯（Steve Jobs）是苹果公司的创始人。
--------------------------------------------------
```
