"""Embedding 工厂：阿里云百炼 DashScope 的 text-embedding-v4"""
from langchain_openai import OpenAIEmbeddings

import settings as config


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        base_url=config.EMBEDDING_BASE_URL,
        api_key=config.EMBEDDING_API_KEY,
        timeout=30,
        max_retries=2,
        check_embedding_ctx_length=False,  # OpenAI 提供商：发原始文本而非 token 数组
        tiktoken_enabled=False,            # 配合上述关闭，避免 tiktoken 编码路径
    )


def probe_embeddings_dim() -> int:
    """测试 DashScope embedding 输出维度（text-embedding-v4 默认 1024）"""
    return len(get_embeddings().embed_query("维度探针"))
