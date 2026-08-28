"""统一配置中心：读取项目根目录的 .env 文件，供全项目使用。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（settings.py 所在目录）
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ===================== DeepSeek（对话/生成） ====================
DEEPSEEK_API_KEY = _get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _get("DEEPSEEK_MODEL", "deepseek-v4-flash")

# ===================== 阿里云百炼（Embedding 向量化） ====================
EMBEDDING_API_KEY = _get("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = _get("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = _get("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIM = int(_get("EMBEDDING_DIM", "1024"))

# ===================== Redis（对话记忆 Checkpointer） ====================
REDIS_URL = _get("REDIS_URL")

# ===================== PostgreSQL（用户数据） ====================
DATABASE_URL = _get("DATABASE_URL")

# ===================== Milvus（向量数据库） ====================
MILVUS_URI = _get("KB_MILVUS_URI", "./data/milvus_kb.db")
MILVUS_DB = _get("KB_MILVUS_DB", "default")
MILVUS_COLLECTION = _get("KB_MILVUS_COLLECTION", "rag_kb")

# ===================== 检索与切分 ====================
TOP_K = int(_get("TOP_K", "4"))
SCORE_THRESHOLD = float(_get("SCORE_THRESHOLD", "0.6"))
CHUNK_SIZE = int(_get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(_get("CHUNK_OVERLAP", "50"))

# ===================== 数据目录 ====================
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MANIFEST_PATH = DATA_DIR / "documents.json"
