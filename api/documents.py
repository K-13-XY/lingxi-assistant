"""文档管理路由：上传入库 / 列表 / 删除"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from core import manifest
from ingestion.pipeline import delete_document, ingest_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
def upload_document(file: UploadFile = File(...)) -> dict:
    try:
        return ingest_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"入库失败：{e}")


@router.get("")
def list_documents() -> dict:
    return {"documents": manifest.list_documents()}


@router.delete("/{doc_id}")
def remove_document(doc_id: str) -> dict:
    info = delete_document(doc_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"文档不存在：{doc_id}")
    return {"deleted": doc_id, "filename": info.get("filename")}
