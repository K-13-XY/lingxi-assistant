"""LLM 工厂：统一通过 DeepSeek（OpenAI 兼容接口）提供对话模型。

- get_agent_llm()：对话智能体用，温度较高、支持工具调用，关闭 thinking 输出
- get_rag_llm()：RAG 问答用，温度较低、偏严谨，保证回答稳定
"""
from langchain_openai import ChatOpenAI

import settings as config


def _base():
    return dict(
        model=config.DEEPSEEK_MODEL,
        base_url=config.DEEPSEEK_BASE_URL,
        api_key=config.DEEPSEEK_API_KEY,
    )


def get_agent_llm() -> ChatOpenAI:
    """对话智能体模型（对话/工具调用）"""
    return ChatOpenAI(
        **_base(),
        temperature=0.7,
        max_retries=3,
        extra_body={"thinking": {"type": "disabled"}},  # DeepSeek：关闭思考链输出
    )


def get_rag_llm() -> ChatOpenAI:
    """RAG 知识库问答模型（严谨、低温度）"""
    return ChatOpenAI(
        **_base(),
        temperature=0.3,
        timeout=60,
        max_retries=2,
    )
