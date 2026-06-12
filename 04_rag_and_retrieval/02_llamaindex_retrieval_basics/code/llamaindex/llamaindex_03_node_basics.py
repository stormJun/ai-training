# -*- coding: utf-8 -*-
# Converted from llamaindex_03_node_basics.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%

import os
from llama_index.core import Settings
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels

# 增加调试日志
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("llama_index").addHandler(logging.StreamHandler(stream=sys.stdout))


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


# %%
print(documents)

# %%
# 添加一个新的 Document
from llama_index.core import Document
text = "CEO 可以直接请假，无需向直接领导汇报"

doc = Document(
    text = text,
    metadata = {
        "author": "wilson yin",
        "title": "CEO 请假申请",
        "id": "1234567890"
    }
)

# %%
print(doc)

# %%
#  手动切分Documents

from  llama_index.core.schema import TextNode

n1 = TextNode(text=doc.text[0:8],doc_id=doc.id_)
n2 = TextNode(text=doc.text[9:16],doc_id=doc.id_)

print(n1)
print(n2)

# %%
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core import Document

doc = Document(
    text=("""
    ### 第七条 事假
    1. 员工因私事必须本人处理的，可申请事假。
    2. 事假需提前申请并获直属主管批准，紧急情况可事后补办手续。
    3. 事假为无薪假，按日扣除相应工资。
    4. 每月事假原则上不超过3天，全年累计不超过15天，特殊情况需经人力资源部及公司领导审批。
    """
    ),
    metadata={"title": "Vacation Questions"}
)

# 内置切分器

splitter = TokenTextSplitter(
    chunk_size=64,
    chunk_overlap=4,
    separator="\n"
)

nodes = splitter.get_nodes_from_documents([doc])

for node in nodes:
    print(node.text)
    print(node.metadata)
