"""

"""
import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
)


class DBBase(DeclarativeBase):
    """
    The basic class for database.
    """


class PasswordAuth(DBBase):
    """
    用户名密码认证方式
    """
    __tablename__ = "password_authentication"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.uuid"), primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["DBUser"] = relationship("DBUser", back_populates="password_auth")


class OAuthProvider(DBBase):
    """
    OAuth provider configuration.
    """
    __tablename__ = "oauth_providers"
    name: Mapped[str] = mapped_column(String(50), primary_key=True, unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    authorize_url: Mapped[str] = mapped_column(String(500), nullable=False)
    token_url: Mapped[str] = mapped_column(String(500), nullable=False)
    user_info_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(String(500), nullable=False)


class OAuthAuthentication(DBBase):
    """
    OAuth 认证方式，存储第三方提供商及身份标识
    """
    __tablename__ = "oauth_authentication"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.uuid"), primary_key=True, unique=True)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)

    # 使用外键关联到 OAuthProvider 模型
    provider_name: Mapped[str] = mapped_column(String(50), ForeignKey("oauth_providers.name"), nullable=False)


    user: Mapped["DBUser"] = relationship("DBUser", back_populates="oauth_auth")

    # 建立与 OAuthProvider 的关系
    provider: Mapped["OAuthProvider"] = relationship()

    # 确保每个提供商的用户 ID 是唯一的
    __table_args__ = (UniqueConstraint('provider_name', name='_provider_openid_uc'),)


class DBUser(DBBase):
    """
    User Model for database.
    """
    __tablename__ = "users"

    # 使用 UUID 字符串作为主键
    uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

     # 一对一关系: 任选其一就好，由业务逻辑保证 XXX: 没有检查是否声明了定义方式
    password_auth: Mapped[Optional["PasswordAuth"]] = relationship(
        "PasswordAuth", back_populates="user", uselist=False
    )
    oauth_auth: Mapped[Optional["OAuthAuthentication"]] = relationship(
        "OAuthAuthentication", back_populates="user", uselist=False
    )

    # 关系的定义
    projects: Mapped[list["DBProject"]] = relationship(
        "DBProject", back_populates="owner", cascade="all, delete-orphan"
    )


class DBProject(DBBase):
    """
    Project Model for database.
    """
    __tablename__ = "projects"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))  # 可选字段

    # 外键使用与 users.uuid 相同的 UUID 字符串类型
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.uuid"))

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    owner: Mapped["DBUser"] = relationship("DBUser", back_populates="projects")
