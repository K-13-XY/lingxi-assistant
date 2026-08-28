"""用户服务：注册、登录（token 生成/校验）、用户信息读写"""
import datetime
import json
import uuid
from typing import Any

from pydantic import BaseModel

from pools.py_pool import PyPool


class User(BaseModel):
    """用户模型"""
    uid: int
    uname: str
    pwd: str
    birth: datetime.date
    ctime: datetime.datetime
    info: dict[str, Any]


class UserCreate(BaseModel):
    uname: str
    pwd: str


class UserLogin(BaseModel):
    uname: str
    pwd: str


class UserService:
    # token -> uname（内存态会话表）
    _tokens: dict[str, str] = {}

    @staticmethod
    async def create_user(user: UserCreate):
        """注册用户"""
        exist = await PyPool.afetchrow("select uid from tb_user where uname=$1", user.uname)
        if exist:
            raise ValueError("用户名已存在")
        return await PyPool.aexecute("insert into tb_user(uname,pwd)values($1,$2)", user.uname, user.pwd)

    @staticmethod
    async def login_user(user: UserCreate):
        """登录：校验用户名密码，成功生成 token 返回"""
        row = await PyPool.afetchrow(
            "select uid,uname,pwd from tb_user where uname=$1 and pwd=$2",
            user.uname, user.pwd,
        )
        if row is None:
            raise ValueError("用户名或密码错误")
        token = uuid.uuid4().hex
        UserService._tokens[token] = user.uname
        return {"access_token": token, "username": user.uname}

    @staticmethod
    async def update_info_by_id(uid: int, info: dict[str, Any]):
        """通过用户 id 更新用户信息"""
        row = await PyPool.afetchrow("select uid,info from tb_user where uid=$1", uid)
        if row is None:
            raise ValueError("用户不存在")
        return await PyPool.aexecute("update tb_user set info=$1 where uid=$2", info, uid)

    @staticmethod
    async def update_info_by_name(uname: str, info: dict[str, Any]):
        """通过用户名更新用户信息"""
        row = await PyPool.afetchrow("select uid,info from tb_user where uname=$1", uname)
        if row is None:
            raise ValueError("用户不存在")
        return await PyPool.aexecute("update tb_user set info=$1 where uname=$2", info, uname)

    @staticmethod
    def validate_token(token: str) -> str | None:
        """校验 token：返回用户名或 None"""
        return UserService._tokens.get(token)

    @staticmethod
    async def get_user_info(uname: str) -> dict | None:
        """根据用户名获取用户信息（不含密码字段）"""
        row = await PyPool.afetchrow(
            "select uid,uname,birth,ctime,info from tb_user where uname=$1", uname
        )
        if row is None:
            return None
        return {
            "uid": row["uid"],
            "uname": row["uname"],
            "birth": row["birth"].isoformat() if row["birth"] else None,
            "ctime": row["ctime"].isoformat() if row["ctime"] else None,
            "info": UserService._info_to_dict(row["info"]),
        }

    @staticmethod
    def _info_to_dict(value) -> dict:
        """asyncpg 默认把 JSON 列表返回字符串，这里统一转成 dict"""
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            return json.loads(value)
        return {}
