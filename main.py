"""灵犀智能助手 —— 服务入口

提供智能对话与知识库问答两类能力：
  - 智能对话：多轮对话 + 工具调用 + Redis 记忆 + 用户系统
  - 知识库问答：文档上传/检索/带引用溯源的流式问答

启动：python main.py  或  uvicorn main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.redis import AsyncRedisSaver

from api import agent_chat_router, auth_router, documents, health, rag_chat_router
from pools.py_pool import PyPool
from settings import DATABASE_URL, REDIS_URL

STATIC_DIR = Path(__file__).resolve().parent / "static"

# 异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("访问地址：http://localhost:8000/login.html")
    print("接口文档：http://localhost:8000/docs")
    # 1. 用户系统依赖 PostgreSQL（连接失败不阻塞 RAG 功能）
    try:
        await PyPool.ainit(DATABASE_URL)
    except Exception as e:
        print(f"[warn] PostgreSQL 连接失败，用户/登录功能不可用：{e}")

    # 2. 智能体依赖 Redis（检查点记忆）
    try:
        async with AsyncRedisSaver.from_conn_string(
            redis_url=REDIS_URL,
            ttl={"default_ttl": -1, "refresh_on_read": True},  # -1：永不过期
        ) as checkpointer:
            # Langgraph异步持久化初始方法asetup)
            await checkpointer.asetup()
            # 创建带记忆的agent放到路由中
            agent_chat_router.set_agent(agent_chat_router.build_agent(checkpointer))
            print("[ok] 灵犀智能体就绪（Redis 记忆已启用）")
            yield
    except Exception as e:
        print(f"[warn] Redis/智能体初始化失败，智能对话功能不可用：{e}")
        yield
    finally:
        try:
            await PyPool.aclose()
        except Exception:
            pass
    print("服务已关闭")

# 绑定应用的生命周期
app = FastAPI(title="灵犀智能助手", version="1.0.1", lifespan=lifespan)

# 注册所有路由（认证 / 智能体对话 / RAG 问答 / 文档管理 / 健康检查）
app.include_router(auth_router.router)
app.include_router(agent_chat_router.router)
app.include_router(rag_chat_router.router)
app.include_router(documents.router)
app.include_router(health.router)

# 前端静态资源
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# include_in_schema=False 将这个接口从自动生成的 API 文档中隐藏起来
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login.html", include_in_schema=False)
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
