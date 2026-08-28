"""RAG 知识库问答路由：非流式 + 流式"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import settings as config
from core.rag_chain import ask, stream_answer

router = APIRouter(prefix="/api/chat", tags=["rag-chat"])


class ChatRequest(BaseModel):
    question: str


def _require_deepseek() -> None:
    """未配置 DeepSeek API KEY 时给出友好提示"""
    if not config.DEEPSEEK_API_KEY or config.DEEPSEEK_API_KEY == "sk-xxxx":
        raise HTTPException(status_code=400, detail="未配置 DEEPSEEK_API_KEY，请在 .env 中配置后重启")


@router.post("/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    _require_deepseek()
    return StreamingResponse(
        stream_answer(question),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("")
def chat(req: ChatRequest) -> dict:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    _require_deepseek()
    return ask(question)
