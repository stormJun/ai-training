"""LlamaIndex 检索后处理示例：相似度阈值过滤。

功能目标：
1. 构建向量索引并执行原始检索
2. 打印检索到的节点和相似度分数
3. 使用 SimilarityPostprocessor 过滤低相关节点
4. 对比过滤前后结果
"""

import os
from pathlib import Path
from llama_index.core import Settings
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels

# 需要时可打开调试日志。
# import logging
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# logging.getLogger("llama_index").addHandler(logging.StreamHandler(stream=sys.stdout))


# 1) 配置全局 LLM。
Settings.llm = OpenAILike(
    model="qwen-plus",
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    is_chat_model=True
)

# 2) 配置全局 Embedding。
Settings.embed_model = DashScopeEmbedding(
    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    embed_batch_size=6,
    embed_input_length=8192
)

# 3) 读取数据并建立向量索引。
data_dir = Path(__file__).resolve().parents[1] / "data"
documents = SimpleDirectoryReader(str(data_dir)).load_data()
index = VectorStoreIndex.from_documents(documents)

# 4) 创建向量检索器。
# similarity_top_k=5 表示先取最相似的 5 个节点候选。
vector_retriever = index.as_retriever(similarity_top_k=5)

# 5) 查看原始检索结果（未做过滤）。
print("=== 原始检索结果 ===")
nodes = vector_retriever.retrieve("怎么休事假？")
for i, node in enumerate(nodes):
    # node.score 越高，通常表示节点与 query 的语义相关性越高。
    print(f"Node {i+1} (相似度: {node.score:.4f}): {node.text[:50]}...")
    print("\n")
    print("-" * 30)


# 6) 添加相似度后处理器。
# similarity_cutoff=0.71：低于阈值的节点会被过滤掉。
from llama_index.core.postprocessor import SimilarityPostprocessor
similarity_postprocessor = SimilarityPostprocessor(similarity_cutoff=0.71)

# 7) 应用后处理器并观察过滤结果。
print("\n=== 应用相似度后处理器后 (cutoff=0.7) ===")
filtered_nodes = similarity_postprocessor.postprocess_nodes(nodes)
for i, node in enumerate(filtered_nodes):
    print(f"Node {i+1} (相似度: {node.score:.4f}): {node.text[:50]}...")
    print("\n")
    print("-" * 30)

# 8) 输出过滤前后数量，快速判断阈值是否过严/过松。
print(f"\n原始 Node 数: {len(nodes)}, 过滤后 Node 数: {len(filtered_nodes)}")
