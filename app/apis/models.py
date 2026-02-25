"""
FastApi Models
"""
from pydantic import BaseModel, Field

from enum import Enum
from datetime import datetime


class LoginSource(str, Enum):
    oauth = "oauth"
    passwd = "passwd"


class Login(BaseModel):
    """

    """
    login_source: LoginSource

class UserBaseInfo(BaseModel):
    success: bool
    msg: str
    uuid: str
    display_name: str
    email: str
    groups: list[str]
    join_date: datetime
    last_login: datetime
    login_source: LoginSource


class ProjectInfo(BaseModel):
    """
    项目信息响应模型
    """
    success: bool
    msg: str
    uuid: str
    name: str
    content: str
    description: str | None
    source: str
    code: list
    executed: list
    owner_id: str
    owner_name: str
    created_at: datetime
    updated_at: datetime


class ProjectSourceUpdate(BaseModel):
    """
    更新项目源代码的请求模型
    """
    source: str


class ProjectUpdateRequest(BaseModel):
    """
    更新项目元信息（名称、描述、内容）的请求模型，字段均为可选。
    """
    name: str | None = None
    description: str | None = None
    content: str | None = None


class BaseResponse(BaseModel):
    """
    通用响应模型
    """
    success: bool
    msg: str
