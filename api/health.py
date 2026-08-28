"""健康检查路由：环境与向量库状态一览"""
from fastapi import APIRouter

import settings as config
from core import vector_store
from core.embeddings import probe_embeddings_dim

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    dim = None
    embedding_ok = False
    try:
        dim = probe_embeddings_dim()
        embedding_ok = dim == config.EMBEDDING_DIM
    except Exception:
        pass

    stats = vector_store.collection_stats()
    return {
        "status": "ok" if embedding_ok else "degraded",
        "milvus": {"uri": config.MILVUS_URI, **stats},
        "embedding": {
            "connected": embedding_ok,
            "model": config.EMBEDDING_MODEL,
            "dim": dim,
        },
        "embedding_dim_expected": config.EMBEDDING_DIM,
        "deepseek": {
            "configured": bool(config.DEEPSEEK_API_KEY and config.DEEPSEEK_API_KEY != "sk-xxxx"),
            "model": config.DEEPSEEK_MODEL,
        },
    }
