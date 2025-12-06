"""
FastApi Models
"""
from pydantic import BaseModel

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
    login_source: LoginSource
