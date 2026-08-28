"""文档注册表：data/documents.json，doc_id -> {filename, uploaded_at, chunk_count}

列表接口直接读注册表，避免每次查询 Milvus；删除/上传时同步维护。
"""
import json
import threading
from datetime import datetime

import settings as config

# 线程锁：保护读写（FastAPI 多线程并发上传/删除）
_lock = threading.Lock()


def _load() -> dict:
    if not config.MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(config.MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(manifest: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def register(doc_id: str, filename: str, chunk_count: int) -> None:
    with _lock:
        manifest = _load()
        manifest[doc_id] = {
            "filename": filename,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chunk_count": chunk_count,
        }
        _save(manifest)


def list_documents() -> list[dict]:
    with _lock:
        manifest = _load()
    return [{"doc_id": doc_id, **info} for doc_id, info in manifest.items()]


def remove(doc_id: str) -> dict | None:
    with _lock:
        manifest = _load()
        info = manifest.pop(doc_id, None)
        if info is not None:
            _save(manifest)
    return info


def find_by_filename(filename: str) -> tuple[str, dict] | None:
    """同名文件先删旧的"""
    with _lock:
        for doc_id, info in _load().items():
            if info.get("filename") == filename:
                return doc_id, info
    return None
