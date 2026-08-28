"""SSE（Server-Sent Events）统一响应格式"""
from pydantic import BaseModel


class Result(BaseModel):
    type: str
    content: str


def token(content: str) -> str:
    """发送 token 文本块"""
    return f"data: {Result(type='token', content=content).model_dump_json()}\n\n"


def done() -> str:
    """发送完成事件"""
    return f"data: {Result(type='done', content='').model_dump_json()}\n\n"


def error(error_msg: str) -> str:
    """发送错误事件"""
    return f"data: {Result(type='error', content=error_msg).model_dump_json()}\n\n"


def timeout() -> str:
    """发送超时事件"""
    return f"data: {Result(type='timeout', content='请求处理超时，请稍后再试').model_dump_json()}\n\n"


def heartbeat_visible() -> str:
    """发送可见心跳事件"""
    return f"data: {Result(type='heartbeat', content='').model_dump_json()}\n\n"
