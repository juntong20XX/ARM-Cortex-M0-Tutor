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


class UsersListResponse(BaseModel):
    """
    用户列表响应模型，供管理员使用。
    """
    items: list[UserBaseInfo]


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


class AnnouncementCreateRequest(BaseModel):
    """
    创建告示的请求模型。
    visibleGroupNames 空或 None 表示公开。
    """
    title: str
    content: str
    visibleGroupNames: list[str] | None = None


class Announcement(BaseModel):
    """
    告示响应模型，与前端 Announcement 约定一致。
    """
    id: str
    title: str
    content: str
    createdAt: str | None = None  # ISO 日期字符串，可选
    visibleGroupNames: list[str] = []  # 空列表表示公开


class AnnouncementsResponse(BaseModel):
    """
    告示列表响应模型。
    """
    items: list[Announcement]


class UserGroupItem(BaseModel):
    """用户组单项，用于列表展示。"""
    uuid: str
    name: str
    description: str | None
    memberCount: int


class UserGroupsListResponse(BaseModel):
    """用户组列表响应。"""
    items: list[UserGroupItem]


class UserGroupCreateRequest(BaseModel):
    """创建用户组请求。"""
    name: str
    description: str | None = None


class UserGroupUpdateRequest(BaseModel):
    """更新用户组请求，字段均为可选。"""
    newName: str | None = None
    description: str | None = None
