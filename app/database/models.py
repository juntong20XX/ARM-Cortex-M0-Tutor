"""

"""
import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Table,
    Enum,
    JSON,
)


class DBBase(DeclarativeBase):
    """
    The basic class for database.
    """


class GroupMappingStrategy(str, PyEnum):
    """
    组映射策略枚举类，用于定义当供应商组名没有映射到项目组名时的处理策略。
    """
    IGNORE = "ignore"  # 无视，允许登录但不分配组
    REJECT = "reject"  # 拒绝，不允许登录


class GroupPermissionStrategy(str, PyEnum):
    """
    组映射策略枚举类，用于定义当供应商组名没有映射到项目组名时的处理策略。
    """
    PERMIT = "permit"  # 无视，允许登录但不分配组
    REJECT = "reject"  # 拒绝，不允许登录


# 用户-组 多对多关联表
user_group_association = Table(
    "user_group_association",
    DBBase.metadata,
    Column("user_id", String(36), ForeignKey("users.uuid"), primary_key=True),
    Column("group_id", String(36), ForeignKey("groups.uuid"), primary_key=True),
)

# 组-可管理用户 多对多关联表
group_managed_users_association = Table(
    "group_managed_users_association",
    DBBase.metadata,
    Column("group_id", String(36), ForeignKey("groups.uuid"), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.uuid"), primary_key=True),
)

# 组-可管理项目 多对多关联表
group_managed_projects_association = Table(
    "group_managed_projects_association",
    DBBase.metadata,
    Column("group_id", String(36), ForeignKey("groups.uuid"), primary_key=True),
    Column("project_id", String(36), ForeignKey("projects.uuid"), primary_key=True),
)

# 组-可管理组 多对多关联表（自引用）
group_managed_groups_association = Table(
    "group_managed_groups_association",
    DBBase.metadata,
    Column("manager_group_id", String(36), ForeignKey("groups.uuid"), primary_key=True),
    Column("managed_group_id", String(36), ForeignKey("groups.uuid"), primary_key=True),
)


class DBGroup(DBBase):
    """
    用户组模型，用于权限管理。
    每个用户可以属于多个组，每个组可以包含多个用户。
    组可以管理用户、项目和其它组。
    """
    __tablename__ = "groups"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))  # 组描述
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime,
                                                          default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # 未匹配处理策略：当组名没有映射到项目组名时的处理策略
    unmapped_group_strategy: Mapped[GroupPermissionStrategy] = mapped_column(
        Enum(GroupPermissionStrategy, native_enum=False, length=20),
        nullable=False,
        default=GroupPermissionStrategy.REJECT
    )

    # 多对多关系: 组包含的用户
    users: Mapped[list["DBUser"]] = relationship(
        "DBUser", secondary=user_group_association, back_populates="groups"
    )

    # 多对多关系: 组可管理的用户
    managed_users: Mapped[list["DBUser"]] = relationship(
        "DBUser", secondary=group_managed_users_association
    )

    # 多对多关系: 组可管理的项目
    managed_projects: Mapped[list["DBProject"]] = relationship(
        "DBProject", secondary=group_managed_projects_association
    )

    # 多对多关系: 组可管理的其他组（自引用）
    managed_groups: Mapped[list["DBGroup"]] = relationship(
        "DBGroup",
        secondary=group_managed_groups_association,
        primaryjoin="DBGroup.uuid == group_managed_groups_association.c.manager_group_id",
        secondaryjoin="DBGroup.uuid == group_managed_groups_association.c.managed_group_id"
    )


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

    # 组映射：存储供应商组名到项目组名的对应关系
    # 格式：{"供应商组名1": "项目组名1", "供应商组名2": "项目组名2", ...}
    group_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)

    # 未映射组策略：当供应商组名没有在 group_mapping 中找到对应关系时的处理策略
    unmapped_group_strategy: Mapped[GroupMappingStrategy] = mapped_column(
        Enum(GroupMappingStrategy, native_enum=False, length=20),
        nullable=False,
        default=GroupMappingStrategy.IGNORE
    )


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


class UserLoginSource(str, PyEnum):
    """
    用户登录方式枚举类
    """
    NONE = "none"  # 无登录方式, 或未记录
    PASSWORD = "password"
    OAUTH = "oauth"


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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime,
                                                          default=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_login: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    last_login_source: Mapped[UserLoginSource] = mapped_column(
        Enum(UserLoginSource, native_enum=False, length=20),
        nullable=False,
        default=UserLoginSource.NONE
    )

    # 一对一关系: 任选其一就好，由业务逻辑保证 XXX: 没有检查是否声明了定义方式
    password_auth: Mapped[Optional["PasswordAuth"]] = relationship(
        "PasswordAuth", back_populates="user", uselist=False
    )
    oauth_auth: Mapped[Optional["OAuthAuthentication"]] = relationship(
        "OAuthAuthentication", back_populates="user", uselist=False
    )

    # 多对多关系: 用户所属的组
    groups: Mapped[list["DBGroup"]] = relationship(
        "DBGroup", secondary=user_group_association, back_populates="users"
    )

    # 关系的定义
    projects: Mapped[list["DBProject"]] = relationship(
        "DBProject", back_populates="owner", cascade="all, delete-orphan"
    )


class DBProject(DBBase):
    """
    Project Model for database.

    设计约定：
    - source：仅保存原始汇编源代码文本。
    - code：保存由 source 解析得到的 ASMLine 序列化缓存（list[dict]），由上层逻辑在解析成功后写回。
    - executed：保存单步执行产生的快照/事件等序列化结果。
    """
    __tablename__ = "projects"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 原始汇编源代码（多行文本）
    source: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 序列化后的 list[ASMLine]，由 source 解析成功后写回，用作缓存/调试
    code: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # 单步执行数据的序列化结果（例如寄存器快照、内存变化、事件等）
    executed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[Optional[str]] = mapped_column(String(500))  # 可选字段

    # 外键使用与 users.uuid 相同的 UUID 字符串类型
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.uuid"), nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime,
                                                          default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    owner: Mapped["DBUser"] = relationship("DBUser", back_populates="projects")
