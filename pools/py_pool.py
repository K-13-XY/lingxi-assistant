"""封装 PostgreSQL 连接池：获取连接、查询、关闭连接"""
import json
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg


class PyPool:
    # 类变量
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def _init_connection(cls, conn):
        """每个新连接建立时调用：让 JSONB 列直接返回 dict，而不是 JSON 字符串"""
        await conn.set_type_codec(
            "jsonb",
            encoder=lambda obj: json.dumps(obj, ensure_ascii=False),
            decoder=json.loads,
            schema="pg_catalog",
        )

    @classmethod
    async def ainit(cls, dsn: str, min_size: int = 5, max_size: int = 20):
        """初始化连接池（服务器启动时调用）"""
        cls._pool = await asyncpg.create_pool(
            dsn, min_size=min_size, max_size=max_size, init=cls._init_connection
        )

    @classmethod
    @asynccontextmanager
    async def aconnect(cls):
        """获取数据库连接"""
        async with cls._pool.acquire() as conn:  # type: ignore
            yield conn

    @classmethod
    async def afetchval(cls, sql: str, *args):
        """异步查询单个标量值"""
        async with cls.aconnect() as conn:  # type: ignore
            return await conn.fetchval(sql, *args)

    @classmethod
    async def afetch(cls, sql: str, *args):
        """查询列表"""
        async with cls.aconnect() as conn:  # type: ignore
            return await conn.fetch(sql, *args)

    @classmethod
    async def afetchrow(cls, sql: str, *args):
        """查询单条数据"""
        async with cls.aconnect() as conn:  # type: ignore
            return await conn.fetchrow(sql, *args)

    @classmethod
    async def aexecute(cls, sql: str, *args):
        """执行 SQL，返回影响的行数"""
        async with cls.aconnect() as conn:  # type: ignore
            return await conn.execute(sql, *args)

    @classmethod
    async def aclose(cls):
        """关闭连接池"""
        if cls._pool:
            await cls._pool.close()
