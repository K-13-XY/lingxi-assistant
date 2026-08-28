"""用户信息记忆工具：把用户提到的个人信息写入数据库（智能体工具）"""
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import tool

from service.user_service import UserService

current_username: ContextVar[str] = ContextVar("current_username")


@tool
async def remember_user_info(info: dict[str, Any]):
    """
    当用户在对话框中提及个人偏好、习惯、喜好、个人信息、教育背景、恋爱史等，调用此工具
    把这些信息存入数据库（info 中）。
    触发示例：
     - 用户说："我喜欢吃香蕉"、"我家住在南京市"、"我今年18岁"……
     - 用户分享生活习惯、兴趣爱好等个人信息
     - 用户一句话中包含多条信息，这些可以全部收集到数据库中
     - 例如存储：{"爱好": ["篮球", "足球"], "年龄": 18}
    """
    uname = current_username.get()
    await UserService.update_info_by_name(uname, info)
    return f"已保存{len(info)}条信息:{info}"
