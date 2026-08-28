"""Milvus 向量库封装

- connection_args={"uri": ...} 指向本地 .db 文件（Milvus Lite 文件模式）或服务器地址
- collection 首次插入时自动创建，向量维度由 embedding 实测（text-embedding-v4 = 1024）
"""
from typing import List, Sequence, Tuple

from langchain_core.documents import Document
from langchain_milvus import Milvus
from pymilvus import MilvusClient

import settings as config
from core.embeddings import get_embeddings

# MilvusClient 线程安全可复用，进程内只建一个连接
_client: MilvusClient | None = None


def _get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=config.MILVUS_URI, db_name=config.MILVUS_DB)
    return _client


def _query_rows(filter_expr: str, output_fields: list[str], *, limit: int | None = None) -> list[dict]:
    """加载 collection 并查询（重启后 collection 处于 released 状态，不 load 查不到）"""
    client = _get_client()
    client.load_collection(config.MILVUS_COLLECTION)
    kwargs: dict = {
        "collection_name": config.MILVUS_COLLECTION,
        "filter": filter_expr,
        "output_fields": output_fields,
        "consistency_level": "Strong",  # 默认 Bounded 一致性下删除后立即查询会读到旧数据
    }
    if limit is not None:  # query 的 limit 上限 16384（服务器模式），Lite 不受限
        kwargs["limit"] = limit
    return client.query(**kwargs)


def get_store() -> Milvus:
    return Milvus(
        collection_name=config.MILVUS_COLLECTION,
        embedding_function=get_embeddings(),
        connection_args={"uri": config.MILVUS_URI, "db_name": config.MILVUS_DB},
        index_params={
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 8, "efConstruction": 64},
        },
        auto_id=True,   # 主键自增
        drop_old=False,  # 不重建已有 collection
    )


def add_documents(docs: Sequence[Document]) -> int:
    """collection 不存在时由 langchain-milvus 按首个文档 schema 自动创建"""
    store = get_store()
    store.add_documents(docs)
    return len(docs)


def search(query: str, k: int | None = None) -> List[Tuple[Document, float]]:
    """相似度检索，返回 [(Document, score)]，score 越大越相似"""
    store = get_store()
    k = k or config.TOP_K
    return store.similarity_search_with_score(query, k=k)


def delete_by_doc_id(doc_id: str) -> int:
    """按 doc_id 删除所有切片"""
    pks = _query_rows(f'doc_id == "{doc_id}"', ["pk"])
    ids = [p["pk"] for p in pks]
    if ids:
        _get_client().delete(collection_name=config.MILVUS_COLLECTION, ids=ids)
    return len(ids)


def collection_stats() -> dict:
    """返回 collection 基础统计（无数据/未创建时返回 0）"""
    try:
        rows = _query_rows(
            "pk >= 0",
            ["doc_id"],
            limit=16384,  # Milvus 服务器模式下 offset+limit 上限 16384
        )
        doc_ids = {r["doc_id"] for r in rows}
        return {
            "chunk_count": len(rows),
            "doc_count": len(doc_ids),
            "has_rows": bool(rows),
        }
    except Exception:
        return {"chunk_count": 0, "doc_count": 0, "has_rows": False}
