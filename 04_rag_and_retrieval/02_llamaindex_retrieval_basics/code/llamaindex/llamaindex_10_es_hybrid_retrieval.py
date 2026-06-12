# -*- coding: utf-8 -*-
# Converted from llamaindex_10_es_hybrid_retrieval.ipynb

# %% [markdown]
# # 来源：https://zhaozhiming.github.io/2024/06/01/llamaindex-llama3-es-hybrid-search/

# %%
from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding
from llama_index.core.bridge.pydantic import PrivateAttr
from typing import Any, List

# %%
import requests

def send_request(model_uid: str, text: str, url: str):
    url = f"{url}/v1/embeddings"
    request_body = {"model": model_uid, "input": text}
    response = requests.post(url, json=request_body)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to create the embeddings, detail: {response.text}"
        )
    return response.json()

def get_embedding(text: str, model_uid: str, url: str) -> Embedding:
    """Get embedding."""
    text = text.replace("\n", " ")
    response_data = send_request(model_uid, text, url)
    return response_data["data"][0]["embedding"]

def get_embeddings(
    list_of_text: List[str], model_uid: str, url: str
) -> List[Embedding]:
    """Get embeddings."""
    assert len(list_of_text) <= 2048, "The batch size should not be larger than 2048."

    list_of_text = [text.replace("\n", " ") for text in list_of_text]
    response_data = send_request(model_uid, list_of_text, url)
    return [d["embedding"] for d in response_data["data"]]

# %%
class CustomEmbeddings(BaseEmbedding):
    """Custom class for embeddings.

    Args:
        model_name (str): Mode for embedding.
        url(str): Url for embedding model.
    """

    _model_name: str = PrivateAttr()
    _url: str = PrivateAttr()

    def __init__(self, model_name: str, url: str, **kwargs: Any) -> None:
        self._model_name = model_name
        self._url = url
        super().__init__(**kwargs)

    @classmethod
    def class_name(cls) -> str:
        return "custom_embedding"

    def _aget_query_embedding(self, query: str) -> Embedding:
        return get_embedding(text=query, model_uid=self._model_name, url=self._url)

    def _aget_text_embedding(self, text: str) -> Embedding:
        return get_embedding(text=text, model_uid=self._model_name, url=self._url)

    def _get_query_embedding(self, query: str) -> Embedding:
        return get_embedding(text=query, model_uid=self._model_name, url=self._url)

    def _get_text_embedding(self, text: str) -> Embedding:
        return get_embedding(text=text, model_uid=self._model_name, url=self._url)

    def _get_text_embeddings(self, texts: List[str]) -> List[Embedding]:
        return get_embeddings(
            list_of_text=texts, model_uid=self._model_name, url=self._url
        )

# %%
# 数据入库

from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.node_parser import SentenceSplitter

store = ElasticsearchStore(
    index_name="a",
    es_url="http://localhost:9200",
)
documents = SimpleDirectoryReader("./data").load_data()
node_parser = SentenceSplitter(chunk_size=256, chunk_overlap=50)
storage_context = StorageContext.from_defaults(vector_store=store)
embed_model = CustomEmbeddings(
    model="BAAI/bge-base-en-v1.5", url="http://localhost:6006"
)
VectorStoreIndex.from_documents(
    documents,
    transformations=[node_parser],
    embed_model=embed_model,
    storage_context=storage_context,
)

# %%
# 全文检索
from llama_index.vector_stores.elasticsearch import AsyncBM25Strategy
from llama_index.core import Settings

text_store = ElasticsearchStore(
    index_name="a",
    es_url="http://localhost:9200",
    retrieval_strategy=AsyncBM25Strategy(),
)
Settings.embed_model = embed_model
text_index = VectorStoreIndex.from_vector_store(
    vector_store=text_store,
)
text_retriever = text_index.as_retriever(similarity_top_k=2)

# %%
# 向量检索
from llama_index.vector_stores.elasticsearch import AsyncDenseVectorStrategy, AsyncSparseVectorStrategy

vector_store = ElasticsearchStore(
    index_name="a",
    es_url="http://localhost:9200",
    retrieval_strategy=AsyncDenseVectorStrategy(),
    # retrieval_strategy=AsyncSparseVectorStrategy(model_id=".elser_model_2"),
)
Settings.embed_model = embed_model
vector_index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
)
vector_retriever = vector_index.as_retriever(similarity_top_k=2)

# %%
# 混合检索
from llama_index.vector_stores.elasticsearch import AsyncDenseVectorStrategy

vector_store = ElasticsearchStore(
    index_name="avengers",
    es_url="http://localhost:9200",
    retrieval_strategy=AsyncDenseVectorStrategy(hybrid=True),
)

# %%
# 混合检索
from typing import List
from llama_index.core.schema import NodeWithScore

def fuse_results(results_dict, similarity_top_k: int = 2):
    """Fuse results."""
    k = 60.0
    fused_scores = {}
    text_to_node = {}

    # 计算倒数排名分数
    for nodes_with_scores in results_dict.values():
        for rank, node_with_score in enumerate(
            sorted(
                nodes_with_scores, key=lambda x: x.score or 0.0, reverse=True
            )
        ):
            text = node_with_score.node.get_content()
            text_to_node[text] = node_with_score
            if text not in fused_scores:
                fused_scores[text] = 0.0
            fused_scores[text] += 1.0 / (rank + k)

    # 结果按分数排序
    reranked_results = dict(
        sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    )

    # 结果还原为节点集合
    reranked_nodes: List[NodeWithScore] = []
    for text, score in reranked_results.items():
        reranked_nodes.append(text_to_node[text])
        reranked_nodes[-1].score = score

    return reranked_nodes[:similarity_top_k]
