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
)


class DBBase(DeclarativeBase):
    """
    The basic class for database.
    """


class DBUser(DBBase):
    """
    User Model for database.
    """
    __tablename__ = "users"

    # 使用 UUID 字符串作为主键
    uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
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
