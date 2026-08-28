"""入库流程编排：保存文件 → 加载 → 切分 → 向量化入库 → 更新注册表"""
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

import settings as config
from core import manifest, vector_store
from ingestion.loaders import load_file
from ingestion.splitter import split_documents

# 最大上传大小（MB）
MAX_UPLOAD_MB = 50


def _fix_mojibake(name: str) -> str:
    """修复 Windows 下 curl 等工具上传中文文件名产生的乱码

    工具把文件名的 GBK/UTF-8 字节按 Latin-1 编码后放进 HTTP 头，服务端收到 mojibake，
    反向恢复：Latin-1 编码回原始字节，再按 GBK/UTF-8 解码；恢复成功才采用，否则保留原名。
    """
    try:
        raw = name.encode("latin-1", errors="strict")
    except UnicodeEncodeError:
        return name
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc, errors="strict")
        except UnicodeDecodeError:
            continue
    return name


def _save_upload(file: UploadFile, doc_id: str) -> Path:
    """把上传文件保存到 data/uploads/{doc_id}_{filename}"""
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.UPLOAD_DIR / f"{doc_id}_{file.filename}"
    file.file.seek(0)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


def delete_document(doc_id: str) -> Optional[dict]:
    """删除：Milvus 切片 + 注册表 + 原始文件"""
    info = manifest.remove(doc_id)
    if info is None:
        return None
    vector_store.delete_by_doc_id(doc_id)
    for f in config.UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink(missing_ok=True)
    return info


def ingest_upload(file: UploadFile) -> dict:
    """上传入库（同名文件先删除旧的），返回 {doc_id, filename, chunk_count, status}

    流程：保存临时文件 → 加载/切分 → 向量化写入 Milvus → 更新注册表；
    中途失败会清理已保存的临时文件，避免半成品残留。
    """
    filename = _fix_mojibake(file.filename or "unnamed")
    ext = Path(filename).suffix.lower()
    if ext not in {".txt", ".pdf", ".md", ".csv", ".xlsx"}:
        raise ValueError(f"不支持的文件类型：{ext}，只支持 txt/pdf/md/csv/xlsx 格式")

    # 同名文件先删除旧的，避免重复入库
    existing = manifest.find_by_filename(filename)
    if existing:
        delete_document(existing[0])

    doc_id = uuid.uuid4().hex[:12]
    saved_path = _save_upload(file, doc_id)
    try:
        docs = load_file(saved_path)
        for d in docs:
            d.metadata["source"] = filename  # 引用来源用原始文件名
        chunks = split_documents(docs, doc_id)
        if not chunks:
            raise ValueError(f"文件 {filename} 未能提取出任何文本内容")
        vector_store.add_documents(chunks)
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

    manifest.register(doc_id, filename, len(chunks))
    return {"doc_id": doc_id, "filename": filename, "chunk_count": len(chunks), "status": "indexed"}


def ingest_file(path: Path) -> dict:
    """本地文件入库（供 seed 脚本使用）"""
    doc_id = uuid.uuid4().hex[:12]
    filename = path.name
    dest = config.UPLOAD_DIR / f"{doc_id}_{filename}"
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    try:
        docs = load_file(dest)
        for d in docs:
            d.metadata["source"] = filename
        chunks = split_documents(docs, doc_id)
        if not chunks:
            raise ValueError(f"文件 {filename} 未能提取出任何文本内容")
        vector_store.add_documents(chunks)
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    manifest.register(doc_id, filename, len(chunks))
    return {"doc_id": doc_id, "filename": filename, "chunk_count": len(chunks), "status": "indexed"}
