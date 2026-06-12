# -*- coding: utf-8 -*-
# Converted from llamaindex_01_quickstart.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%
# 使用 OpenAI API 密钥设置一个名为 OPENAI_API_KEY 的环境变量。安装 Python 库
# NOTEBOOK_MAGIC: !pip install llama-index
# NOTEBOOK_MAGIC: !pip install llama-index-core

# NOTEBOOK_MAGIC: !pip install llama-index-llms-openai-like

# NOTEBOOK_MAGIC: !pip install llama-index-llms-dashscope
# NOTEBOOK_MAGIC: !pip install llama-index-embeddings-dashscope

# %%
# from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# documents = SimpleDirectoryReader("data").load_data()
# index = VectorStoreIndex.from_documents(documents)
# query_engine = index.as_query_engine()
# response = query_engine.query("怎么休事假？")
# print(response)

# 配置通义千问大模型和文本向量模型
import os
from llama_index.core import Settings
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels

Settings.llm = OpenAILike(
    model="qwen-plus",
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    is_chat_model=True
)

Settings.embed_model = DashScopeEmbedding(
    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
    embed_batch_size=6,
    embed_input_length=8192
)

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("怎么休事假？")
print(response)

# %% [markdown]
# # 思考： 为什么要用框架？
#
#
# **数据层**
# - 如何支持多种数据源（如本地文件、云存储、数据库、API）的统一接入？
# - 多种文件类型（PDF、DOCX、CSV、PPT）能否被自动识别并正确解析？
# - 面对编码错误、损坏文件或加密文档，解析过程是否具备容错能力？
# - 目录路径“data”写死，是否支持通过配置动态指定？
# - 是否支持递归读取子目录以及按规则排除特定文件或文件夹？
# - 用户能否自定义文件解析逻辑，例如为特定格式注册自己的解析器？
#
# >  说明：LlamaIndex 提供 `SimpleDirectoryReader` 支持常见格式、递归读取、文件过滤（`required_exts`、`exclude_hidden`），并可通过继承 `BaseReader` 实现自定义解析器。
#
# ---
#
# **索引层**
# - 向量存储后端（如 FAISS、Chroma、Pinecone、Weaviate、Milvus）是否可灵活切换？
# - 文档切分策略是否可配置，例如按固定长度、语义边界或段落分割？
# - 是否支持元数据（如来源路径、作者、时间）嵌入索引以用于过滤？
# - 索引能否持久化保存，避免每次重复构建？
# - 新增文档时是否支持增量索引更新而非全量重建？
# - 是否可以组合使用向量检索与关键词检索实现混合搜索？
#
# >  说明：LlamaIndex 支持多种 `VectorStore` 集成、`NodeParser`（如 `SentenceSplitter`）可配置切分、支持元数据过滤、索引持久化（`storage_context.persist()`）、增量添加文档、以及通过 `AutoMergingRetriever` 或 `BM25Retriever + VectorIndexRetriever` 实现混合检索。
#
# ---
#
# **查询层**
# - 查询是否支持流式输出，以便前端实时展示生成内容？
# - 是否能结合对话历史实现多轮问答和上下文理解？
# - 不同类型的问题是否可以路由到不同的查询引擎（如规则引擎 vs 向量检索）？
# - 是否具备意图识别能力，判断用户问题是政策咨询、流程操作还是其他类别？
# - 如何处理模糊或歧义查询，是否支持查询重写或澄清提问？
#
# >  说明：支持流式响应（`StreamingResponse`）、`ChatEngine` 支持对话历史、可通过 `Tool` 或自定义 `RouterQueryEngine` 实现路由、支持 `SubQuestionQueryEngine` 进行查询分解与重写。
#
# ---
#
# **输出层**
# - 返回的 `response` 对象是否能转换为标准 JSON 格式以便 API 集成？
# - 是否可以在答案中附带引用来源、原始文本片段和置信度信息？
# - 输出结果是否可序列化并跨网络传输？
# - 是否提供结构化输出能力，例如返回固定 schema 的 JSON 数据？
# - 生成内容是否经过安全检查，防止恶意 prompt 注入或泄露训练数据？
#
# >  说明：可通过 `response.get_response()` 提取结构信息、引用节点可通过 `source_nodes` 获取、支持 `PydanticOutputParser` 生成结构化输出。但安全过滤需外部介入。
#
# ---
#
# **业务层**
# - 系统是否适配具体业务场景，如 HR 政策查询、IT 支持、员工自助服务？
# - 不同用户角色（员工、HR、管理员）是否能看到不同范围或精度的结果？
# - 业务规则（如事假需审批、最多3天）是否能与检索结果融合输出？
# - 用户对回答不满意时，是否有反馈机制来收集问题并优化知识库？
# - 高频未命中问题是否可被记录，用于后续知识补全？
#
# >  说明：LlamaIndex 不直接实现权限控制或反馈闭环，但可通过外部逻辑集成实现“按角色过滤文档”、“记录 query 日志”等，框架本身支持元数据过滤和可扩展性。
#
# ---
#
# **工程层**
# - 文件不存在、格式不支持、解析失败等情况是否有异常捕获和处理？
# - 大量文档加载或高并发查询时，系统性能是否可控？是否支持异步处理？
# - 是否记录关键日志用于调试和链路追踪？
# - 是否具备基本监控指标（如查询延迟、命中率、token 消耗）？
# - 整个流程是否可集成到 CI/CD 流水线中，支持自动化部署？
#
# >  说明：异常为标准 Python 异常，可捕获；支持异步加载文档和异步查询；日志使用标准 logging；token 使用可通过回调获取；工程化集成依赖外部系统，但组件本身可编程组装。
#
# ---
#
# **安全层**
# - 加载的文档是否可能包含敏感信息（如身份证号、薪资）？读取时是否需权限控制？
# - 在文本切分和向量化过程中，是否会无意中暴露隐私内容？
# - 是否支持对敏感字段进行自动脱敏或过滤？
# - 输出内容是否经过合规性校验，避免生成违法或不当言论？
# - 整个系统是否符合企业级安全审计和数据保护要求？
#
# > 说明：LlamaIndex 本身不提供脱敏、内容过滤、权限校验等安全机制，但这些问题是合理的设计考量，可在其基础上由应用层实现。
#
# ---
#
# **扩展层**
# - 是否允许第三方开发者注册自定义数据连接器或解析插件？
# - 是否支持接入图像、表格、扫描件等多模态内容的理解能力？
# - 大语言模型是否可自由替换，支持本地部署模型或私有化服务？
# - 是否提供开放接口或 SDK，供外部系统集成调用？
# - 是否具备扩展能力以支持未来新增的数据源、索引类型或查询模式？
#
# >  说明：LlamaIndex 设计为高度可扩展，支持自定义 Reader、NodeParser、Retriever、LLM、Embedding、Tool 等；支持 HuggingFace、Ollama、本地模型；提供 Python SDK，适合集成。
