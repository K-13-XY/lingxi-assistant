"""RAG 问答链：检索 → 阈值过滤 → 基于上下文的生成 → 引用来源

检索在 /api/chat/stream 场景需要复用，因此 search 单独暴露；
answer 由 DeepSeek 生成，流式场景逐块产出文本，最后附来源分隔行。
"""
import json
from typing import Iterable

from langchain_core.prompts import PromptTemplate

import settings as config
from core.llm import get_rag_llm
from core.vector_store import search

# 流式响应中，答案文本与来源 JSON 之间以此分隔
SOURCES_MARKER = "===SOURCES==="

PROMPT_TEMPLATE = """你是一个严谨的中文知识库问答助手，请只根据下面提供的【资料】回答用户问题
    规则：
    1.严格基于【资料】内容作答，不得编造资料中没有的信息；
    2.若【资料】与问题无关或未包含相关内容，必须明确回答"资料库中没有找到相关内容"；
    3.回答中请标注所依据的资料编号，如[1]、[2]、[3]；
    4.使用简洁、准确的中文回答

    【资料】
    {context}

    【问题】
    {question}
"""


def _build_prompt() -> PromptTemplate:
    return PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])


def search_with_filter(question: str, k: int | None = None) -> list[dict]:
    """检索 + 阈值过滤，返回 [{"text","source","score"}]

    score 是 COSINE 相似度（越大越相似）；低于 SCORE_THRESHOLD 的命中视为无关内容丢弃，
    避免模型基于噪声作答。
    """
    hits = search(question, k=k or config.TOP_K)
    return [
        {
            "text": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(score, 4),
        }
        for doc, score in hits
        if score >= config.SCORE_THRESHOLD
    ]


def ask(question: str) -> dict:
    """非流式问答：{answer, has_sources, sources}"""
    sources = search_with_filter(question)
    context = "\n\n".join(f"[{i + 1}] {s['text']}" for i, s in enumerate(sources))
    chain = _build_prompt() | get_rag_llm()
    answer = chain.invoke({"context": context, "question": question}).content
    return {"answer": answer, "has_sources": bool(sources), "sources": sources}


def stream_answer(question: str) -> Iterable[str]:
    """流式问答：先输出答案文本块，再输出 \\n===SOURCES===\\n{json} 一行

    流式协议：文本块逐段产出（前端实时渲染），最后追加 SOURCES_MARKER
    分隔行 + 引用来源 JSON，前端按分隔行切分渲染来源卡片。
    """
    sources = search_with_filter(question)
    context = "\n\n".join(f"[{i + 1}] {s['text']}" for i, s in enumerate(sources))
    chain = _build_prompt() | get_rag_llm()
    for chunk in chain.stream({"context": context, "question": question}):
        if chunk.content:
            yield chunk.content
    yield f"\n{SOURCES_MARKER}\n{json.dumps(sources, ensure_ascii=False)}"
