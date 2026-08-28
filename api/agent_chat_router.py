"""智能对话路由：多轮对话 + 工具调用 + SSE 流式输出

基于 LangGraph 的 ReAct 智能体，Redis 持久化检查点实现跨会话记忆，
支持 local_date / remember_user_info 工具。
"""
import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from core.llm import get_agent_llm
from resp import sse_resp
from service.user_service import UserService
from tools.user_info import current_username, remember_user_info

router = APIRouter(tags=["agent"])

# 全局智能体实例，由 main.py 的 lifespan 在启动时注入
agent = None


@tool(description="获得当前系统时间")
def local_date():
    return datetime.datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")


def build_agent(checkpointer):
    """组装智能体"""
    return create_react_agent(
        model=get_agent_llm(),
        checkpointer=checkpointer,  # Redis 记忆
        tools=[local_date, remember_user_info],
        prompt="""
你是一个聊天的 AI 智能助手，你叫灵犀

- 工具列表
  local_date：获取当前系统时间
  remember_user_info：记住并存储用户提到的个人偏好、习惯、喜好等个人信息
""",
    )


def set_agent(a):
    global agent
    agent = a


class ChatRequest(BaseModel):
    message: str
    session_id: str


def get_current_user(authorization: str = Header(default="")):
    """校验 Authorization: Bearer <token>，返回用户名"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    uname = UserService.validate_token(authorization[7:])
    if uname is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return uname


@router.post("/chat")
async def chat(request: ChatRequest, uname: str = Depends(get_current_user)):
    if agent is None:
        raise HTTPException(status_code=503, detail="智能体未就绪，请检查 Redis 配置后重启")

    # 注入当前用户名，供 remember_user_info 等工具读取
    current_username.set(uname)
    # 获取用户信息，拼接到提示词中
    user_info = await UserService.get_user_info(uname)
    messages = [{"role": "user", "content": request.message}]
    if user_info:
        context = (
            f"当前用户信息，用户名={user_info['uname']}"
            f"，生日={user_info['birth'] or '未知'}"
            f"，注册时间={user_info['ctime'] or '未知'}"
            f"，个人详细信息={user_info['info']}"
        )
        messages.insert(0, {"role": "system", "content": context})

    config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}

    async def event_generate():
        stream = agent.astream_events(
            input={"messages": messages},
            config=config,
        )
        async for event in stream:
            if event.get("event") == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield sse_resp.token(content)
        yield sse_resp.done()

    return StreamingResponse(
        event_generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-Accel-Buffering": "no",
        },
    )
