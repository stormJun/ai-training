"""RAG 工作流基础示例。

这个脚本演示一个比“检索 + 生成”更完整的 RAG 工作流：
1. 文档加载与向量化
2. 问题路由
3. 检索结果评分
4. 答案生成
5. 幻觉检查与答案质量评分
6. 必要时回退到 Web 搜索
"""

from __future__ import annotations

import json
import operator
import os
import re
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_nomic.embeddings import NomicEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


def load_environment() -> None:
    """读取当前目录或工作流目录下的环境变量。"""
    if not load_dotenv():
        load_dotenv(Path("02_workflows/.env"))


def require_dashscope_key() -> None:
    """确保当前环境中存在 DASHSCOPE_API_KEY。"""
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("Missing DASHSCOPE_API_KEY. Set env var or fill 02_workflows/.env")


load_environment()
require_dashscope_key()


llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
)
llm_json_mode = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
    format="json",
)


langfuse_handler = None
try:
    from langfuse.callback import CallbackHandler

    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        langfuse_handler = CallbackHandler()
        print("Langfuse enabled")
    else:
        print("Langfuse disabled: set LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY to enable")
except Exception as exc:
    print(f"Langfuse disabled: {exc}")

callbacks = [langfuse_handler] if langfuse_handler else []
run_config = {"callbacks": callbacks} if callbacks else {}


if os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "langgraph-rag-demo"
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def invoke_llm(messages):
    """按需携带 tracing 配置调用普通模型。"""
    if callbacks:
        return llm.invoke(messages, config=run_config)
    return llm.invoke(messages)


def invoke_llm_json(messages):
    """按需携带 tracing 配置调用 JSON 模式模型。"""
    if callbacks:
        return llm_json_mode.invoke(messages, config=run_config)
    return llm_json_mode.invoke(messages)


def parse_json(content: str):
    """尽量鲁棒地解析模型返回的 JSON。"""
    content = (content or "").strip()
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def format_docs(docs):
    """把文档列表拼接成单个上下文字符串。"""
    return "\n\n".join(doc.page_content for doc in docs)


urls = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
]

docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=1000,
    chunk_overlap=200,
)
doc_splits = text_splitter.split_documents(docs_list)

vectorstore = SKLearnVectorStore.from_documents(
    documents=doc_splits,
    embedding=NomicEmbeddings(model="nomic-embed-text-v1.5", inference_mode="local"),
)
retriever = vectorstore.as_retriever(k=3)


router_instructions = """You are an expert at routing a user question to a vectorstore or web search.

The vectorstore contains documents related to agents, prompt engineering, and adversarial attacks.

Use the vectorstore for questions on these topics. For all else, and especially for current events, use web-search.

Return ONLY valid JSON with a single key, datasource, that is 'websearch' or 'vectorstore'. Do not output any other text."""


doc_grader_instructions = """You are a grader assessing relevance of a retrieved document to a user question.

If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant."""


doc_grader_prompt = """Here is the retrieved document: \n\n {document} \n\n Here is the user question: \n\n {question}. 

This carefully and objectively assess whether the document contains at least some information that is relevant to the question.

Return ONLY valid JSON with single key, binary_score, that is 'yes' or 'no'. Do not output any other text."""


rag_prompt = """You are an assistant for question-answering tasks.

Here is the context to use to answer the question:

{context}

Think carefully about the above context.

Now, review the user question:

{question}

Provide an answer to this questions using only the above context.

Use three sentences maximum and keep the answer concise.

Answer:"""


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


hallucination_grader_prompt = """FACTS: \n\n {documents} \n\n STUDENT ANSWER: {generation}.

Return ONLY valid JSON with two keys: binary_score ('yes' or 'no') and explanation (string). Do not output any other text."""


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


answer_grader_prompt = """QUESTION: \n\n {question} \n\n STUDENT ANSWER: {generation}.

Return ONLY valid JSON with two keys: binary_score ('yes' or 'no') and explanation (string). Do not output any other text."""


if not os.getenv("TAVILY_API_KEY"):
    web_search_tool = None
    print("TAVILY_API_KEY not set: web search disabled.")
else:
    web_search_tool = TavilySearchResults(k=3)


class GraphState(TypedDict):
    """RAG 工作流状态。"""

    question: str
    generation: str
    web_search: str
    max_retries: int
    loop_step: Annotated[int, operator.add]
    documents: list[Document]


def retrieve(state: GraphState):
    """从向量存储中检索相关文档。"""
    print("---RETRIEVE---")
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents}


def generate(state: GraphState):
    """基于检索文档和问题生成回答。"""
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    loop_step = state.get("loop_step", 0)

    docs_txt = format_docs(documents)
    rag_prompt_formatted = rag_prompt.format(context=docs_txt, question=question)
    generation = invoke_llm([HumanMessage(content=rag_prompt_formatted)])
    return {"generation": generation, "loop_step": loop_step + 1}


def grade_documents(state: GraphState):
    """判断检索文档是否与问题相关。"""
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]

    filtered_docs = []
    web_search = "No"

    for document in documents:
        prompt = doc_grader_prompt.format(
            document=document.page_content,
            question=question,
        )
        result = invoke_llm_json(
            [SystemMessage(content=doc_grader_instructions)]
            + [HumanMessage(content=prompt)]
        )
        grade = parse_json(result.content)["binary_score"]

        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(document)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            web_search = "Yes"

    if web_search == "Yes" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); continue without web search---")
        web_search = "No"

    return {"documents": filtered_docs, "web_search": web_search}


def run_web_search(state: GraphState):
    """使用 Tavily 进行网络搜索，并把结果附加到文档列表中。"""
    print("---WEB SEARCH---")
    question = state["question"]
    documents = state.get("documents", [])

    docs = web_search_tool.invoke({"query": question})
    web_results = "\n".join(doc["content"] for doc in docs)
    documents.append(Document(page_content=web_results))
    return {"documents": documents}


def route_question(state: GraphState):
    """决定当前问题应该走向量检索还是 Web 搜索。"""
    print("---ROUTE QUESTION---")
    route_result = invoke_llm_json(
        [SystemMessage(content=router_instructions)]
        + [HumanMessage(content=state["question"])]
    )
    source = parse_json(route_result.content)["datasource"]

    if source == "websearch" and web_search_tool is None:
        print("---WEB SEARCH DISABLED (missing TAVILY_API_KEY); fallback to vectorstore---")
        source = "vectorstore"

    if source == "websearch":
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "websearch"

    print("---ROUTE QUESTION TO RAG---")
    return "vectorstore"


def decide_to_generate(state: GraphState):
    """决定是否直接生成答案，还是先补充 Web 搜索。"""
    print("---ASSESS GRADED DOCUMENTS---")
    if state["web_search"] == "Yes":
        print("---DECISION: NOT ALL DOCUMENTS ARE RELEVANT TO QUESTION, INCLUDE WEB SEARCH---")
        return "websearch"

    print("---DECISION: GENERATE---")
    return "generate"


def grade_generation_v_documents_and_question(state: GraphState):
    """检查答案是否基于文档，且是否真正回答了问题。"""
    print("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    max_retries = state.get("max_retries", 3)

    hallucination_prompt = hallucination_grader_prompt.format(
        documents=format_docs(documents),
        generation=generation.content,
    )
    result = invoke_llm_json(
        [SystemMessage(content=hallucination_grader_instructions)]
        + [HumanMessage(content=hallucination_prompt)]
    )
    grade = parse_json(result.content)["binary_score"]

    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        print("---GRADE GENERATION vs QUESTION---")

        answer_prompt = answer_grader_prompt.format(
            question=question,
            generation=generation.content,
        )
        result = invoke_llm_json(
            [SystemMessage(content=answer_grader_instructions)]
            + [HumanMessage(content=answer_prompt)]
        )
        grade = parse_json(result.content)["binary_score"]

        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        if state["loop_step"] <= max_retries:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
        print("---DECISION: MAX RETRIES REACHED---")
        return "max retries"

    if state["loop_step"] <= max_retries:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"

    print("---DECISION: MAX RETRIES REACHED---")
    return "max retries"


workflow = StateGraph(GraphState)
workflow.add_node("websearch", run_web_search)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)

workflow.set_conditional_entry_point(
    route_question,
    {
        "websearch": "websearch",
        "vectorstore": "retrieve",
    },
)
workflow.add_edge("websearch", "generate")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "websearch": "websearch",
        "generate": "generate",
    },
)
workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "websearch",
        "max retries": END,
    },
)

graph = workflow.compile()


def show_graph() -> None:
    """在支持的环境里显示流程图，不支持时回退到 Mermaid 文本。"""
    try:
        from IPython.display import Image, display

        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception as exc:
        print(f"Skip mermaid PNG render: {exc}")
        print(graph.get_graph().draw_mermaid())


def run_vectorstore_demo() -> None:
    """运行一个适合走向量库的示例问题。"""
    inputs = {"question": "What are the types of agent memory?", "max_retries": 3}
    for event in graph.stream(inputs, config=run_config, stream_mode="values"):
        print(event)


def run_current_events_demo() -> None:
    """运行一个偏实时信息的问题。"""
    if not os.getenv("TAVILY_API_KEY"):
        print("Skip: missing TAVILY_API_KEY")
        return

    inputs = {
        "question": "What are the models released today for llama3.2?",
        "max_retries": 3,
    }
    for event in graph.stream(inputs, config=run_config, stream_mode="values"):
        print(event)


def main() -> None:
    show_graph()
    run_vectorstore_demo()
    run_current_events_demo()


if __name__ == "__main__":
    main()
