"""用户认证路由：注册 / 登录"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.user_service import UserService, UserCreate, UserLogin

router = APIRouter(prefix="/api", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(request: RegisterRequest):
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    try:
        await UserService.create_user(UserCreate(uname=request.username, pwd=request.password))
        return {"username": request.username, "message": "注册成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest):
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    try:
        return await UserService.login_user(UserLogin(uname=request.username, pwd=request.password))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
