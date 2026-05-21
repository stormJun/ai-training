# %%

# 依赖安装说明：
# - 在本仓库里建议跳过本 cell，直接用 `cd 02_workflows && uv sync --locked` 安装（稳定可复现）。
# - 如果你在临时环境（如 Colab）运行，再用 `%pip install` 安装依赖。
# 1. LangChain 核心框架：提供 Prompt 管理、Chain、Agent 等基础组件
# %pip install --quiet langchain

# 2. LangChain 社区版：集成第三方开源模型、数据库、工具 API（扩展核心库兼容性）
# %pip install --quiet langchain_community

# 3. Token 计数库（OpenAI 开源）：计算文本 Token 数，避免超出模型上下文窗口
# %pip install --quiet tiktoken

# 4. LangChain + Nomic AI 集成：对接 Nomic 的 Embedding 模型和向量数据库
# %pip install --quiet langchain-nomic

# 5. Nomic 本地运行依赖：安装本地 Embedding/向量存储所需的额外依赖（无需云端服务）
# %pip install --quiet "nomic[local]"

# 6. LangChain + Ollama 集成：调用本地 Ollama 部署的大模型（如 Llama 3、Qwen）
# %pip install --quiet langchain-ollama

# 7. 机器学习库：提供数据预处理、检索结果重排序、文本分类等算法支持
# %pip install --quiet scikit-learn

# 8. LangChain 工作流库：用图结构实现复杂多轮逻辑（如 Agent 状态流转、分支循环）
# %pip install --quiet langgraph

# 9. Tavily 搜索引擎 SDK：AI 专用实时检索工具，供 Agent 获取最新信息
# %pip install --quiet tavily-python

# 10. HTML 解析库（BeautifulSoup4）：爬取网页后提取结构化文本/表格
# %pip install --quiet bs4

# 11. LangChain 观测分析工具：跟踪链执行、调试 Prompt、监控 Token 消耗和性能
# %pip install --quiet langfuse

pass

# %%
# （可选）在临时环境安装：%pip install langchain-nomic

# %%
### LLM配置 - 使用通义千问模型
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi

# 读取环境变量：优先当前目录的 .env；如果你从仓库根目录运行，再尝试 02_workflows/.env
if not load_dotenv():
    load_dotenv(Path("02_workflows/.env"))

if not os.getenv("DASHSCOPE_API_KEY"):
    raise RuntimeError("Missing DASHSCOPE_API_KEY. Set env var or fill 02_workflows/.env")

llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True
)
llm_json_mode = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
    format="json"
)

# Langfuse（可选）：开源可自建的 tracing/观测平台。
# 1) 先自建/使用 Langfuse，然后配置环境变量：
#    LANGFUSE_PUBLIC_KEY=...
#    LANGFUSE_SECRET_KEY=...
#    LANGFUSE_HOST=http://localhost:3000   # 自建时常见；云端可不配
# 2) 未配置则自动禁用，不影响 notebook 正常运行。
langfuse_handler = None
try:
    from langfuse.callback import CallbackHandler

    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        langfuse_handler = CallbackHandler()
        print("Langfuse enabled")
    else:
        print("Langfuse disabled: set LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY to enable")
except Exception as e:
    print(f"Langfuse disabled: {e}")

callbacks = [langfuse_handler] if langfuse_handler else []
run_config = {"callbacks": callbacks} if callbacks else {}


def invoke_llm(messages):
    if callbacks:
        return llm.invoke(messages, config=run_config)
    return llm.invoke(messages)


def invoke_llm_json(messages):
    if callbacks:
        return llm_json_mode.invoke(messages, config=run_config)
    return llm_json_mode.invoke(messages)

# %%
# 使用 LangSmith 追踪
import os

# 没有 LANGSMITH_API_KEY 时开启 tracing 会导致 401（不影响核心流程，但会污染输出）。
if os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "langgraph-rag-demo"
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# %%
# 向量存储 - 文档加载、分割和向量化
# 导入必要的库用于文档处理和向量存储
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 递归字符文本分割器
from langchain_community.document_loaders import WebBaseLoader  # 网页文档加载器
from langchain_community.vectorstores import SKLearnVectorStore  # 基于SKLearn的向量存储
from langchain_nomic.embeddings import NomicEmbeddings  # Nomic嵌入模型

# 定义要加载的网页URL列表，包含关于AI代理、提示工程和对抗攻击的文章
urls = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",  # AI代理相关文章
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",  # 提示工程文章
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",  # LLM对抗攻击文章
]

# 加载文档
# 使用WebBaseLoader为每个URL加载网页内容，返回文档列表的列表
docs = [WebBaseLoader(url).load() for url in urls]
# 将嵌套的文档列表展平为单一的文档列表
docs_list = [item for sublist in docs for item in sublist]

# 分割文档
# 创建递归字符文本分割器，使用tiktoken编码器来准确计算token数量
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=1000,  # 每个文档块的最大大小为1000个token
    chunk_overlap=200  # 相邻文档块之间重叠200个token，确保上下文连续性
)
# 将所有文档分割成较小的文档块，便于检索和处理
doc_splits = text_splitter.split_documents(docs_list)

# 添加到向量数据库
# 使用分割后的文档创建向量存储，将文档转换为向量表示
vectorstore = SKLearnVectorStore.from_documents(
    documents=doc_splits,  # 输入分割后的文档
    embedding=NomicEmbeddings(model="nomic-embed-text-v1.5", inference_mode="local"),  # 使用Nomic嵌入模型，本地推理模式
)

# 创建检索器
# 将向量存储转换为检索器，设置返回最相关的3个文档
retriever = vectorstore.as_retriever(k=3)

# %%
### Router - 路由模块
import json  # 用于JSON数据处理
import re
from langchain_core.messages import HumanMessage, SystemMessage  # 导入消息类型

def parse_json(content: str):
    """Best-effort JSON parser for LLM outputs.

    Tongyi / other chat models may prepend explanations or whitespace.
    This helper tries strict json.loads first, then extracts the first {...} block.
    """
    content = (content or "").strip()
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))

# 提示词定义
# 定义路由的系统指令，用于决定问题应该路由到向量存储还是网络搜索
router_instructions = """You are an expert at routing a user question to a vectorstore or web search.

The vectorstore contains documents related to agents, prompt engineering, and adversarial attacks.

Use the vectorstore for questions on these topics. For all else, and especially for current events, use web-search.

Return ONLY valid JSON with a single key, datasource, that is 'websearch' or 'vectorstore'. Do not output any other text."""

# 测试路由功能
# 测试1：体育赛事问题 - 应该路由到网络搜索（时事相关）
test_web_search = invoke_llm_json(
    [SystemMessage(content=router_instructions)]  # 系统消息包含路由指令
    + [
        HumanMessage(
            content="Who is favored to win the NFC Championship game in the 2024 season?"  # 询问2024赛季NFC冠军赛的热门球队
        )
    ]
)

# 测试2：最新模型发布问题 - 应该路由到网络搜索（时事相关）
test_web_search_2 = invoke_llm_json(
    [SystemMessage(content=router_instructions)]  # 系统消息包含路由指令
    + [HumanMessage(content="What are the models released today for llama3.2?")]  # 询问今天发布的llama3.2模型
)

# 测试3：代理记忆类型问题 - 应该路由到向量存储（与已有文档相关）
test_vector_store = invoke_llm_json(
    [SystemMessage(content=router_instructions)]  # 系统消息包含路由指令
    + [HumanMessage(content="What are the types of agent memory?")]  # 询问代理记忆的类型
)

# 打印所有测试结果，展示路由器的决策
print(
    parse_json(test_web_search.content),      # 解析第一个测试的JSON响应
    parse_json(test_web_search_2.content),   # 解析第二个测试的JSON响应
    parse_json(test_vector_store.content),   # 解析第三个测试的JSON响应
)

# %%
### Retrieval Grader - 检索评分器模块

# 文档评分器指令
# 定义文档评分器的系统指令，用于评估检索到的文档与用户问题的相关性
doc_grader_instructions = """You are a grader assessing relevance of a retrieved document to a user question.

If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant."""

# 评分器提示词模板
# 定义具体的评分提示词，包含文档内容和用户问题
doc_grader_prompt = """Here is the retrieved document: \n\n {document} \n\n Here is the user question: \n\n {question}. 

This carefully and objectively assess whether the document contains at least some information that is relevant to the question.

Return ONLY valid JSON with single key, binary_score, that is 'yes' or 'no'. Do not output any other text."""

# 测试检索评分器功能
question = "What is Chain of thought prompting?"  # 测试问题：什么是思维链提示
docs = retriever.invoke(question)  # 使用检索器根据问题检索相关文档
doc_txt = docs[1].page_content  # 获取第二个文档的页面内容用于测试
# 格式化评分提示词，将实际的文档内容和问题填入模板
doc_grader_prompt_formatted = doc_grader_prompt.format(
    document=doc_txt, question=question
)
# 调用LLM进行文档相关性评分
result = invoke_llm_json(
    [SystemMessage(content=doc_grader_instructions)]  # 系统消息包含评分指令
    + [HumanMessage(content=doc_grader_prompt_formatted)]  # 用户消息包含格式化的评分提示
)
# 解析并返回JSON格式的评分结果
parse_json(result.content)

# %%
### Generate - 生成器模块

# 提示词模板
# 定义RAG（检索增强生成）的提示词模板，用于基于检索到的上下文回答问题
rag_prompt = """You are an assistant for question-answering tasks. 

Here is the context to use to answer the question:

{context} 

Think carefully about the above context. 

Now, review the user question:

{question}

Provide an answer to this questions using only the above context. 

Use three sentences maximum and keep the answer concise.

Answer:"""


# 后处理函数
# 定义文档格式化函数，将多个文档合并为单一的上下文字符串
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)  # 用双换行符连接所有文档的页面内容


# 测试生成功能
docs = retriever.invoke(question)  # 使用检索器根据问题检索相关文档
docs_txt = format_docs(docs)  # 将检索到的文档格式化为文本字符串
# 格式化RAG提示词，将上下文和问题填入模板
rag_prompt_formatted = rag_prompt.format(context=docs_txt, question=question)
# 调用LLM生成基于上下文的答案
generation = invoke_llm([HumanMessage(content=rag_prompt_formatted)])
# 打印生成的答案内容
print(generation.content)

# %%
### Hallucination Grader - 幻觉评分器模块

# 幻觉评分器指令
# 定义幻觉评分器的系统指令，用于检查生成的答案是否基于提供的事实，避免产生虚假信息
hallucination_grader_instructions = """

You are a teacher grading a quiz. 

You will be given FACTS and a STUDENT ANSWER. 

Here is the grade criteria to follow:

(1) Ensure the STUDENT ANSWER is grounded in the FACTS. 

(2) Ensure the STUDENT ANSWER does not contain "hallucinated" information outside the scope of the FACTS.

Score:

A score of yes means that the student's answer meets all of the criteria. This is the highest (best) score. 

A score of no means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 

Avoid simply stating the correct answer at the outset."""

# 评分器提示词模板
# 定义具体的幻觉检测提示词，包含事实文档和学生答案的占位符
hallucination_grader_prompt = """FACTS: \n\n {documents} \n\n STUDENT ANSWER: {generation}. 

Return ONLY valid JSON with two keys: binary_score ('yes' or 'no') and explanation (string). Do not output any other text."""

# 使用上面的文档和生成内容进行测试
# 格式化幻觉检测提示词，将实际的文档内容和生成的答案填入模板
hallucination_grader_prompt_formatted = hallucination_grader_prompt.format(
    documents=docs_txt, generation=generation.content  # docs_txt是格式化的文档，generation.content是LLM生成的答案
)
# 调用LLM进行幻觉检测评分
result = invoke_llm_json(
    [SystemMessage(content=hallucination_grader_instructions)]  # 系统消息包含幻觉检测指令
    + [HumanMessage(content=hallucination_grader_prompt_formatted)]  # 用户消息包含格式化的检测提示
)
# 解析并返回JSON格式的评分结果，包含二元评分和解释
parse_json(result.content)

# %%
### Answer Grader - 答案评分器模块

# 答案评分器指令
# 定义答案评分器的系统指令，用于评估学生答案是否有效回答了给定问题
answer_grader_instructions = """You are a teacher grading a quiz. 

You will be given a QUESTION and a STUDENT ANSWER. 

Here is the grade criteria to follow:

(1) The STUDENT ANSWER helps to answer the QUESTION

Score:

A score of yes means that the student's answer meets all of the criteria. This is the highest (best) score. 

The student can receive a score of yes if the answer contains extra information that is not explicitly asked for in the question.

A score of no means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 

Avoid simply stating the correct answer at the outset."""

# 评分器提示词模板
# 定义具体的答案评分提示词，包含问题和学生答案的占位符
answer_grader_prompt = """QUESTION: \n\n {question} \n\n STUDENT ANSWER: {generation}. 

Return ONLY valid JSON with two keys: binary_score ('yes' or 'no') and explanation (string). Do not output any other text."""

# 测试数据
question = "What are the vision models released today as part of Llama 3.2?"  # 测试问题：今天发布的Llama 3.2视觉模型有哪些？
# 测试答案：包含Llama 3.2视觉模型的详细信息
answer = "The Llama 3.2 models released today include two vision models: Llama 3.2 11B Vision Instruct and Llama 3.2 90B Vision Instruct, which are available on Azure AI Model Catalog via managed compute. These models are part of Meta's first foray into multimodal AI and rival closed models like Anthropic's Claude 3 Haiku and OpenAI's GPT-4o mini in visual reasoning. They replace the older text-only Llama 3.1 models."

# 使用上面的问题和答案进行测试
# 格式化答案评分提示词，将实际的问题和答案填入模板
answer_grader_prompt_formatted = answer_grader_prompt.format(
    question=question, generation=answer  # question是测试问题，answer是要评分的答案
)
# 调用LLM进行答案质量评分
result = invoke_llm_json(
    [SystemMessage(content=answer_grader_instructions)]  # 系统消息包含答案评分指令
    + [HumanMessage(content=answer_grader_prompt_formatted)]  # 用户消息包含格式化的评分提示
)
# 解析并返回JSON格式的评分结果，包含二元评分和解释
parse_json(result.content)

# %%
# 搜索

from langchain_community.tools.tavily_search import TavilySearchResults

import os

# Tavily 需要设置环境变量 TAVILY_API_KEY，否则在调用 web search 时会报错。
if not os.getenv("TAVILY_API_KEY"):
    web_search_tool = None
    print("TAVILY_API_KEY not set: web search disabled (skip current-events test or set the key).")
else:
    web_search_tool = TavilySearchResults(k=3)

# %%
# 状态定义
# 图的 `state` (状态) 模式包含我们想要
# 传递给我们图中每个节点的键
# （可选）在我们图的每个节点中修改

# 导入必要的类型定义库
import operator  # 操作符模块，用于定义累加操作
from typing_extensions import TypedDict  # 类型化字典，提供类型提示
from typing import List, Annotated  # 列表类型和注解类型


class GraphState(TypedDict):
    """
    Graph state is a dictionary that contains information we want to propagate to, and modify in, each graph node.
    图状态是一个字典，包含我们想要传播到图中每个节点并在其中修改的信息。
    """

    question: str  # 用户问题 - 存储用户输入的查询问题
    generation: str  # LLM生成内容 - 存储大语言模型生成的回答
    web_search: str  # 网络搜索决策 - 二元决策，决定是否运行网络搜索
    max_retries: int  # 最大重试次数 - 答案生成的最大重试次数限制
    answers: int  # 答案数量 - 已生成的答案数量计数
    loop_step: Annotated[int, operator.add]  # 循环步骤 - 使用累加操作符跟踪循环迭代次数
    documents: List[str]  # 文档列表 - 存储检索到的相关文档列表

# %%
# 节点定义
# 我们图中的每个节点都只是一个函数，它会
# (1) 将 `state` (状态) 作为输入
# (2) 修改 `state` (状态)
# (3) 将修改后的 `state` (状态) 写入状态模式 (字典) 中

# 导入必要的模块
from langchain_core.documents import Document  # 文档类，用于创建文档对象
from langgraph.graph import END  # 图的结束节点


### Nodes - 节点函数定义
def retrieve(state):
    """
    从向量存储中检索文档
    Retrieve documents from vectorstore

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 添加了新键documents的状态，包含检索到的文档 New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题

    # 将检索到的文档写入状态的documents键中
    documents = retriever.invoke(question)  # 使用检索器根据问题检索相关文档
    return {"documents": documents}  # 返回包含文档的状态更新


def generate(state):
    """
    使用RAG在检索到的文档上生成答案
    Generate answer using RAG on retrieved documents

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 添加了新键generation的状态，包含LLM生成内容 New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取检索到的文档
    loop_step = state.get("loop_step", 0)  # 获取当前循环步骤，默认为0

    # RAG生成过程
    docs_txt = format_docs(documents)  # 格式化文档为文本字符串
    rag_prompt_formatted = rag_prompt.format(context=docs_txt, question=question)  # 格式化RAG提示词
    generation = invoke_llm([HumanMessage(content=rag_prompt_formatted)])  # 调用LLM生成答案
    return {"generation": generation, "loop_step": loop_step + 1}  # 返回生成内容和更新的循环步骤


def grade_documents(state):
    """
    判断检索到的文档是否与问题相关
    如果任何文档不相关，我们将设置标志来运行网络搜索
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will set a flag to run web search

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 过滤掉不相关文档并更新web_search状态 Filtered out irrelevant documents and updated web_search state
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取检索到的文档

    # 对每个文档进行评分
    filtered_docs = []  # 初始化过滤后的文档列表
    web_search = "No"  # 初始化网络搜索标志为"No"
    for d in documents:  # 遍历每个文档
        # 格式化文档评分提示词
        doc_grader_prompt_formatted = doc_grader_prompt.format(
            document=d.page_content, question=question
        )
        # 调用LLM对文档相关性进行评分
        result = invoke_llm_json(
            [SystemMessage(content=doc_grader_instructions)]
            + [HumanMessage(content=doc_grader_prompt_formatted)]
        )
        grade = parse_json(result.content)["binary_score"]  # 解析评分结果
        # 文档相关
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")  # 打印文档相关信息
            filtered_docs.append(d)  # 将相关文档添加到过滤列表
        # 文档不相关
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")  # 打印文档不相关信息
            # 我们不将该文档包含在filtered_docs中
            # 我们设置标志表示要运行网络搜索
            web_search = "Yes"  # 设置网络搜索标志为"Yes"
            continue  # 继续处理下一个文档

    # 如果没有配置 Tavily（TAVILY_API_KEY），则禁用 web_search 分支，避免运行时报错
    if web_search == "Yes" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); continue without web search---")
        web_search = "No"

    return {"documents": filtered_docs, "web_search": web_search}  # 返回过滤后的文档和搜索标志


def web_search(state):
    """
    基于问题进行网络搜索
    Web search based based on the question

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 将网络搜索结果附加到文档中 Appended web results to documents
    """

    print("---WEB SEARCH---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题
    documents = state.get("documents", [])  # 从状态中获取现有文档，默认为空列表

    # 网络搜索
    docs = web_search_tool.invoke({"query": question})  # 使用网络搜索工具搜索问题
    web_results = "\n".join([d["content"] for d in docs])  # 将搜索结果合并为文本
    web_results = Document(page_content=web_results)  # 创建文档对象
    documents.append(web_results)  # 将网络搜索结果添加到文档列表
    return {"documents": documents}  # 返回更新后的文档列表


### Edges - 边函数定义（用于节点间路由）


def route_question(state):
    """
    将问题路由到网络搜索或RAG
    Route question to web search or RAG

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点 Next node to call
    """

    print("---ROUTE QUESTION---")  # 打印当前执行的步骤
    # 调用路由器LLM决定使用哪种数据源
    route_question = invoke_llm_json(
        [SystemMessage(content=router_instructions)]
        + [HumanMessage(content=state["question"])]
    )
    source = parse_json(route_question.content)["datasource"]  # 解析数据源决策
    if source == "websearch" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); fallback to vectorstore---")
        source = "vectorstore"

    if source == "websearch":
        print("---ROUTE QUESTION TO WEB SEARCH---")  # 路由到网络搜索
        return "websearch"
    elif source == "vectorstore":
        print("---ROUTE QUESTION TO RAG---")  # 路由到RAG（向量存储）
        return "vectorstore"


def decide_to_generate(state):
    """
    决定是生成答案还是添加网络搜索
    Determines whether to generate an answer, or add web search

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点的二元决策 Binary decision for next node to call
    """

    print("---ASSESS GRADED DOCUMENTS---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题
    web_search = state["web_search"]  # 从状态中获取网络搜索标志
    filtered_documents = state["documents"]  # 从状态中获取过滤后的文档

    if web_search == "Yes":
        # 所有文档都已被过滤检查相关性
        # 我们将重新生成一个新查询
        print(
            "---DECISION: NOT ALL DOCUMENTS ARE RELEVANT TO QUESTION, INCLUDE WEB SEARCH---"
        )
        return "websearch"  # 返回网络搜索节点
    else:
        # 我们有相关文档，所以生成答案
        print("---DECISION: GENERATE---")
        return "generate"  # 返回生成节点


def grade_generation_v_documents_and_question(state):
    """
    判断生成内容是否基于文档并回答了问题
    Determines whether the generation is grounded in the document and answers question

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点的决策 Decision for next node to call
    """

    print("---CHECK HALLUCINATIONS---")  # 打印当前执行的步骤
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取文档
    generation = state["generation"]  # 从状态中获取生成内容
    max_retries = state.get("max_retries", 3)  # 获取最大重试次数，默认为3

    # 格式化幻觉检测提示词
    hallucination_grader_prompt_formatted = hallucination_grader_prompt.format(
        documents=format_docs(documents), generation=generation.content
    )
    # 调用LLM进行幻觉检测
    result = invoke_llm_json(
        [SystemMessage(content=hallucination_grader_instructions)]
        + [HumanMessage(content=hallucination_grader_prompt_formatted)]
    )
    grade = parse_json(result.content)["binary_score"]  # 解析幻觉检测结果

    # 检查幻觉
    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")  # 生成内容基于文档
        # 检查问题回答质量
        print("---GRADE GENERATION vs QUESTION---")
        # 使用上面的问题和生成内容进行测试
        answer_grader_prompt_formatted = answer_grader_prompt.format(
            question=question, generation=generation.content
        )
        # 调用LLM进行答案质量评分
        result = invoke_llm_json(
            [SystemMessage(content=answer_grader_instructions)]
            + [HumanMessage(content=answer_grader_prompt_formatted)]
        )
        grade = parse_json(result.content)["binary_score"]  # 解析答案质量评分
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")  # 生成内容回答了问题
            return "useful"  # 返回有用标志
        elif state["loop_step"] <= max_retries:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")  # 生成内容未回答问题
            return "not useful"  # 返回无用标志
        else:
            print("---DECISION: MAX RETRIES REACHED---")  # 达到最大重试次数
            return "max retries"  # 返回最大重试标志
    elif state["loop_step"] <= max_retries:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")  # 生成内容未基于文档，重试
        return "not supported"  # 返回不支持标志
    else:
        print("---DECISION: MAX RETRIES REACHED---")  # 达到最大重试次数
        return "max retries"  # 返回最大重试标志

# %%
# 每个边在图中的节点之间进行路由。
# 边函数负责决定工作流的下一步执行哪个节点

# 导入必要的模块
from langchain_core.documents import Document  # 文档类，用于创建文档对象
from langgraph.graph import END  # 图的结束节点


### Nodes - 节点函数定义
def retrieve(state):
    """
    从向量存储中检索文档
    Retrieve documents from vectorstore

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 添加了新键documents的状态，包含检索到的文档 New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE---")  # 打印检索步骤标识
    question = state["question"]  # 从状态中提取用户问题

    # 将检索到的文档写入状态的documents键中
    documents = retriever.invoke(question)  # 调用检索器获取相关文档
    return {"documents": documents}  # 返回包含检索文档的状态更新


def generate(state):
    """
    使用RAG在检索到的文档上生成答案
    Generate answer using RAG on retrieved documents

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 添加了新键generation的状态，包含LLM生成内容 New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")  # 打印生成步骤标识
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取检索到的文档
    loop_step = state.get("loop_step", 0)  # 获取当前循环步数，默认为0

    # RAG生成过程
    docs_txt = format_docs(documents)  # 将文档列表格式化为文本字符串
    rag_prompt_formatted = rag_prompt.format(context=docs_txt, question=question)  # 使用上下文和问题格式化提示词
    generation = invoke_llm([HumanMessage(content=rag_prompt_formatted)])  # 调用LLM生成回答
    return {"generation": generation, "loop_step": loop_step + 1}  # 返回生成结果和递增的循环步数


def grade_documents(state):
    """
    判断检索到的文档是否与问题相关
    如果任何文档不相关，我们将设置标志来运行网络搜索
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will set a flag to run web search

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 过滤掉不相关文档并更新web_search状态 Filtered out irrelevant documents and updated web_search state
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")  # 打印文档相关性检查标识
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取检索到的文档

    # 对每个文档进行评分
    filtered_docs = []  # 初始化过滤后的文档列表
    web_search = "No"  # 初始化网络搜索标志为否
    for d in documents:  # 遍历每个检索到的文档
        # 格式化文档评分提示词
        doc_grader_prompt_formatted = doc_grader_prompt.format(
            document=d.page_content, question=question
        )
        # 调用LLM对文档相关性进行评分
        result = invoke_llm_json(
            [SystemMessage(content=doc_grader_instructions)]
            + [HumanMessage(content=doc_grader_prompt_formatted)]
        )
        grade = parse_json(result.content)["binary_score"]  # 解析评分结果
        # 文档相关
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")  # 打印文档相关信息
            filtered_docs.append(d)  # 将相关文档添加到过滤列表
        # 文档不相关
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")  # 打印文档不相关信息
            # 我们不将该文档包含在filtered_docs中
            # 我们设置标志表示要运行网络搜索
            web_search = "Yes"  # 设置网络搜索标志为是
            continue  # 继续处理下一个文档

    # 如果没有配置 Tavily（TAVILY_API_KEY），则禁用 web_search 分支，避免运行时报错
    if web_search == "Yes" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); continue without web search---")
        web_search = "No"

    return {"documents": filtered_docs, "web_search": web_search}  # 返回过滤后的文档和搜索标志


def web_search(state):
    """
    基于问题进行网络搜索
    Web search based based on the question

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        state (dict): 将网络搜索结果附加到文档中 Appended web results to documents
    """

    print("---WEB SEARCH---")  # 打印网络搜索步骤标识
    question = state["question"]  # 从状态中获取用户问题
    documents = state.get("documents", [])  # 从状态中获取现有文档，默认为空列表

    # 网络搜索
    docs = web_search_tool.invoke({"query": question})  # 使用网络搜索工具执行搜索
    web_results = "\n".join([d["content"] for d in docs])  # 将搜索结果内容合并为字符串
    web_results = Document(page_content=web_results)  # 创建包含搜索结果的文档对象
    documents.append(web_results)  # 将网络搜索结果添加到现有文档列表
    return {"documents": documents}  # 返回更新后的文档列表


### Edges - 边函数定义（控制节点间的路由逻辑）


def route_question(state):
    """
    将问题路由到网络搜索或RAG
    Route question to web search or RAG

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点名称 Next node to call
    """

    print("---ROUTE QUESTION---")  # 打印问题路由步骤标识
    # 使用路由器LLM决定数据源
    route_question = invoke_llm_json(
        [SystemMessage(content=router_instructions)]
        + [HumanMessage(content=state["question"])]
    )
    source = parse_json(route_question.content)["datasource"]  # 解析路由决策结果
    if source == "websearch" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); fallback to vectorstore---")
        source = "vectorstore"

    if source == "websearch":
        print("---ROUTE QUESTION TO WEB SEARCH---")  # 路由到网络搜索
        return "websearch"  # 返回网络搜索节点名
    elif source == "vectorstore":
        print("---ROUTE QUESTION TO RAG---")  # 路由到RAG检索
        return "vectorstore"  # 返回向量存储节点名


def decide_to_generate(state):
    """
    决定是生成答案还是添加网络搜索
    Determines whether to generate an answer, or add web search

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点的二元决策 Binary decision for next node to call
    """

    print("---ASSESS GRADED DOCUMENTS---")  # 打印文档评估步骤标识
    question = state["question"]  # 从状态中获取用户问题
    web_search = state["web_search"]  # 从状态中获取网络搜索标志
    filtered_documents = state["documents"]  # 从状态中获取过滤后的文档

    if web_search == "Yes":
        # 所有文档都已被过滤检查相关性
        # 我们将重新生成一个新查询
        print(
            "---DECISION: NOT ALL DOCUMENTS ARE RELEVANT TO QUESTION, INCLUDE WEB SEARCH---"
        )
        return "websearch"  # 返回网络搜索节点
    else:
        # 我们有相关文档，所以生成答案
        print("---DECISION: GENERATE---")  # 决定生成答案
        return "generate"  # 返回生成节点


def grade_generation_v_documents_and_question(state):
    """
    判断生成内容是否基于文档并回答了问题
    Determines whether the generation is grounded in the document and answers question

    Args:
        state (dict): 当前图状态 The current graph state

    Returns:
        str: 要调用的下一个节点的决策 Decision for next node to call
    """

    print("---CHECK HALLUCINATIONS---")  # 打印幻觉检查步骤标识
    question = state["question"]  # 从状态中获取用户问题
    documents = state["documents"]  # 从状态中获取文档
    generation = state["generation"]  # 从状态中获取生成内容
    max_retries = state.get("max_retries", 3)  # 获取最大重试次数，默认为3

    # 格式化幻觉检测提示词
    hallucination_grader_prompt_formatted = hallucination_grader_prompt.format(
        documents=format_docs(documents), generation=generation.content
    )
    # 调用LLM进行幻觉检测
    result = invoke_llm_json(
        [SystemMessage(content=hallucination_grader_instructions)]
        + [HumanMessage(content=hallucination_grader_prompt_formatted)]
    )
    grade = parse_json(result.content)["binary_score"]  # 解析幻觉检测结果

    # 检查幻觉
    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")  # 生成内容基于文档
        # 检查问题回答质量
        print("---GRADE GENERATION vs QUESTION---")  # 评估生成内容与问题的匹配度
        # 使用上面的问题和生成内容进行测试
        answer_grader_prompt_formatted = answer_grader_prompt.format(
            question=question, generation=generation.content
        )
        # 调用LLM进行答案质量评分
        result = invoke_llm_json(
            [SystemMessage(content=answer_grader_instructions)]
            + [HumanMessage(content=answer_grader_prompt_formatted)]
        )
        grade = parse_json(result.content)["binary_score"]  # 解析答案质量评分
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")  # 生成内容回答了问题
            return "useful"  # 返回有用标志，结束流程
        elif state["loop_step"] <= max_retries:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")  # 生成内容未回答问题
            return "not useful"  # 返回无用标志，需要网络搜索
        else:
            print("---DECISION: MAX RETRIES REACHED---")  # 达到最大重试次数
            return "max retries"  # 返回最大重试标志，结束流程
    elif state["loop_step"] <= max_retries:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")  # 生成内容未基于文档，重试
        return "not supported"  # 返回不支持标志，重新生成
    else:
        print("---DECISION: MAX RETRIES REACHED---")  # 达到最大重试次数
        return "max retries"  # 返回最大重试标志，结束流程

# %%
# 控制流 - 构建和配置LangGraph工作流

# 导入必要的模块
from langgraph.graph import StateGraph  # 状态图类，用于构建工作流图
from IPython.display import Image, display  # 用于显示图像的模块

# 创建状态图工作流，使用之前定义的GraphState作为状态模式
workflow = StateGraph(GraphState)

# 定义节点 - 将函数添加为图中的节点
workflow.add_node("websearch", web_search)  # 添加网络搜索节点
workflow.add_node("retrieve", retrieve)  # 添加文档检索节点
workflow.add_node("grade_documents", grade_documents)  # 添加文档评分节点
workflow.add_node("generate", generate)  # 添加答案生成节点

# 构建图结构
# 设置条件入口点 - 根据问题类型决定起始节点
workflow.set_conditional_entry_point(
    route_question,  # 路由函数，决定使用哪个数据源
    {
        "websearch": "websearch",    # 如果路由结果是"websearch"，跳转到网络搜索节点
        "vectorstore": "retrieve",   # 如果路由结果是"vectorstore"，跳转到检索节点
    },
)

# 添加固定边 - 定义节点间的直接连接
workflow.add_edge("websearch", "generate")  # 网络搜索后直接跳转到生成节点
workflow.add_edge("retrieve", "grade_documents")  # 检索后跳转到文档评分节点

# 添加条件边 - 根据函数返回值决定下一个节点
workflow.add_conditional_edges(
    "grade_documents",  # 从文档评分节点出发
    decide_to_generate,  # 决策函数，判断是否可以生成答案
    {
        "websearch": "websearch",  # 如果需要网络搜索，跳转到网络搜索节点
        "generate": "generate",    # 如果可以生成答案，跳转到生成节点
    },
)

# 添加生成节点的条件边 - 评估生成质量并决定下一步
workflow.add_conditional_edges(
    "generate",  # 从生成节点出发
    grade_generation_v_documents_and_question,  # 评估函数，检查生成质量
    {
        "not supported": "generate",    # 如果生成内容不基于文档，重新生成
        "useful": END,                  # 如果生成内容有用，结束流程
        "not useful": "websearch",      # 如果生成内容无用，进行网络搜索
        "max retries": END,             # 如果达到最大重试次数，结束流程
    },
)

# 编译工作流图
graph = workflow.compile()  # 将工作流编译为可执行的图

# 显示工作流图的可视化表示
# Mermaid PNG 渲染默认会请求 https://mermaid.ink（有时会失败）。失败时退化为输出 Mermaid 文本。
try:
    display(Image(graph.get_graph().draw_mermaid_png()))  # 生成并显示Mermaid格式的流程图
except Exception as e:
    print(f"Skip mermaid PNG render: {e}")
    print(graph.get_graph().draw_mermaid())

# %%
inputs = {"question": "What are the types of agent memory?", "max_retries": 3}
for event in graph.stream(inputs, config=run_config, stream_mode="values"):
    print(event)

# %%
# Test on current events
# 需要 Tavily 才能跑通（否则会在 web_search 节点调用时报错）
import os

if not os.getenv("TAVILY_API_KEY"):
    print("Skip: missing TAVILY_API_KEY")
else:
    inputs = {
        "question": "What are the models released today for llama3.2?",
        "max_retries": 3,
    }
    for event in graph.stream(inputs, config=run_config, stream_mode="values"):
        print(event)
