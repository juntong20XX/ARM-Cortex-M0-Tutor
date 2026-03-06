"""

"""
from .models import (DBUser, DBProject, DBAnnouncement, OAuthProvider, PasswordAuth, OAuthAuthentication, DBUserGroup,
                     GroupMappingStrategy, GroupPermissionStrategy, UserLoginSource)
from ..core.security import get_password_hash

from sqlalchemy import select
from sqlalchemy.orm import Session

import typing
import uuid as uuid_module
from datetime import datetime, UTC

DEFAULT_GROUP_EVERYONE = "everyone"
DEFAULT_GROUP_ADMINISTRATOR = "administrator"


def find_all_projects(session: Session) -> list[DBProject]:
    """
    获取所有项目.
    :param session: a db Session
    :return: 所有项目列表
    """
    return session.query(DBProject).all()


def find_all_announcements(session: Session) -> list[DBAnnouncement]:
    """
    获取所有告示，按 created_at 倒序（内部用，不校验权限）。
    :param session: a db Session
    :return: 所有告示列表
    """
    return session.query(DBAnnouncement).order_by(DBAnnouncement.created_at.desc()).all()


def find_visible_announcements(session: Session, user_uuid: str | None = None) -> list[DBAnnouncement]:
    """
    获取当前用户可见的告示，按 created_at 倒序。
    - user_uuid 为 None（未登录）：仅返回公开告示（visible_user_groups 为空）
    - user_uuid 有值：返回公开告示 + 用户所属组可见的告示
    :param session: a db Session
    :param user_uuid: 当前用户 UUID，未登录为 None
    :return: 可见告示列表
    """
    all_rows = session.query(DBAnnouncement).order_by(DBAnnouncement.created_at.desc()).all()
    if user_uuid is None:
        return [r for r in all_rows if not r.visible_user_groups]
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        return [r for r in all_rows if not r.visible_user_groups]
    user_group_uuids = {ug.uuid for ug in user.user_groups}
    result = []
    for r in all_rows:
        if not r.visible_user_groups:
            result.append(r)
        elif any(ug.uuid in user_group_uuids for ug in r.visible_user_groups):
            result.append(r)
    return result


def find_announcement_by_uuid(session: Session, announcement_uuid: str) -> list[DBAnnouncement]:
    """
    根据 UUID 查找告示。
    :param session: a db Session
    :param announcement_uuid: str, 告示的 UUID
    :return: 匹配的告示列表
    """
    return session.query(DBAnnouncement).filter_by(uuid=announcement_uuid).all()


def add_announcement(
    session: Session,
    title: str,
    content: str,
    visible_group_names: list[str] | None = None,
    commit: bool = False,
) -> DBAnnouncement:
    """
    添加新告示到数据库。
    :param session: a db Session
    :param title: str, 告示标题
    :param content: str, 告示内容
    :param visible_group_names: list[str] | None, 可见用户组名列表；None 或空表示公开
    :param commit: bool, 是否提交会话 (default: False)
    :return: 创建的 DBAnnouncement 对象
    :raise KeyError: 如果指定了不存在的用户组名
    """
    new_announcement = DBAnnouncement(title=title, content=content)
    session.add(new_announcement)
    session.flush()  # 确保 uuid 已生成，以便关联 visible_user_groups

    if visible_group_names:
        for group_name in visible_group_names:
            ugs = find_user_group_by_name(session, group_name)
            if not ugs:
                raise KeyError(f"User group '{group_name}' not found")
            new_announcement.visible_user_groups.append(ugs[0])

    if commit:
        session.commit()
        session.refresh(new_announcement)

    return new_announcement


def delete_announcement(session: Session, announcement_uuid: str, commit: bool = False) -> bool:
    """
    删除告示。
    :param session: a db Session
    :param announcement_uuid: str, 要删除的告示 UUID
    :param commit: bool, 是否提交会话 (default: False)
    :return: bool, 删除成功返回 True
    :raise KeyError: 如果告示不存在
    """
    announcements = find_announcement_by_uuid(session, announcement_uuid)
    if not announcements:
        raise KeyError(f"Announcement with UUID '{announcement_uuid}' not found")

    announcement = announcements[0]
    session.delete(announcement)

    if commit:
        session.commit()

    return True


def find_project_by_name(session: Session, project_name: str) -> list[DBProject]:
    """
    Found user sequence with project name, the name need be full-matched.
    :param session: a db Session
    :param project_name: str, the project name.
    :return:
    """
    return session.query(DBProject).filter_by(name=project_name).all()


def find_project_by_owner_name(session: Session, owner_name: str) -> list[DBProject]:
    """
    Found user sequence with project's owner's name, the name need be full-matched.
    :param session: a db Session
    :param owner_name: str, the project owner's name.
    :raise KeyError: the user for `owner_name` not found
    :return:
    """
    users = find_user_by_username(session, owner_name)
    try:
        user = users[0]
    except IndexError:
        raise KeyError(f"the user for `{owner_name}` not found")
    return find_project_by_owner_id(session, user.uuid)


def find_project_by_owner_id(session: Session, owner_id: str) -> list[DBProject]:
    """
    Found user sequence with owner id (user.uuid), the id need be full-matched.
    :param session: a db Session
    :param owner_id: str, user.uuid.
    :return:
    """
    return session.query(DBProject).filter_by(owner_id=owner_id).all()


def find_project_by_uuid(session: Session, project_uuid: str) -> list[DBProject]:
    """
    根据 UUID 查找项目。
    :param session: a db Session
    :param project_uuid: str, 项目的 UUID
    :return: 匹配的项目列表
    """
    return session.query(DBProject).filter_by(uuid=project_uuid).all()


def add_project(session: Session,
                name: str,
                content: str,
                owner_id: str,
                description: str = None,
                source: str = "",
                code: list = None,
                executed: list = None,
                uuid: str = None,
                commit: bool = False) -> DBProject:
    """
    添加新项目到数据库。
    
    :param session: a db Session
    :param name: str, 项目名称
    :param content: str, 项目内容
    :param owner_id: str, 项目所有者的 UUID
    :param description: str, 可选的项目描述
    :param source: str, 源代码 (default: "")
    :param code: list, 序列化后的 list[ASMLine] (default: [])
    :param executed: list, 单步执行数据 (default: [])
    :param uuid: str, 可选的 UUID，不提供则自动生成
    :param commit: bool, 是否提交会话 (default: False)
    :return: 创建的 DBProject 对象
    :raise KeyError: 如果所有者不存在
    """
    # 检查所有者是否存在
    owner = session.query(DBUser).filter_by(uuid=owner_id).first()
    if not owner:
        raise KeyError(f"User with UUID '{owner_id}' not found")

    kwargs = {
        'name': name,
        'content': content,
        'owner_id': owner_id,
        'source': source,
        'code': code if code is not None else [],
        'executed': executed if executed is not None else [],
        'updated_at': datetime.now(UTC),
    }
    
    if description is not None:
        kwargs['description'] = description
    
    if uuid is not None:
        kwargs['uuid'] = uuid

    new_project = DBProject(**kwargs)
    session.add(new_project)
    
    if commit:
        session.commit()
        session.refresh(new_project)

    return new_project


def update_project(session: Session,
                   project_uuid: str,
                   name: str = None,
                   content: str = None,
                   description: str = None,
                   source: str = None,
                   code: list = None,
                   executed: list = None,
                   commit: bool = False) -> DBProject:
    """
    更新现有项目信息。
    
    :param session: a db Session
    :param project_uuid: str, 要更新的项目 UUID
    :param name: str, 可选的新项目名称
    :param content: str, 可选的新项目内容
    :param description: str, 可选的新项目描述
    :param source: str, 可选的新源代码
    :param code: list, 可选的新序列化后的 list[ASMLine]
    :param executed: list, 可选的新单步执行数据
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBProject 对象
    :raise KeyError: 如果项目不存在
    """
    projects = find_project_by_uuid(session, project_uuid)
    if not projects:
        raise KeyError(f"Project with UUID '{project_uuid}' not found")

    project = projects[0]

    if name is not None:
        project.name = name
    if content is not None:
        project.content = content
    if description is not None:
        project.description = description
    if source is not None:
        project.source = source
    if code is not None:
        project.code = code
    if executed is not None:
        project.executed = executed

    project.updated_at = datetime.now(UTC)

    if commit:
        session.commit()
        session.refresh(project)

    return project


def delete_project(session: Session, project_uuid: str, commit: bool = False) -> bool:
    """
    删除项目。
    
    :param session: a db Session
    :param project_uuid: str, 要删除的项目 UUID
    :param commit: bool, 是否提交会话 (default: False)
    :return: bool, 删除成功返回 True
    :raise KeyError: 如果项目不存在
    """
    projects = find_project_by_uuid(session, project_uuid)
    if not projects:
        raise KeyError(f"Project with UUID '{project_uuid}' not found")

    project = projects[0]
    session.delete(project)
    
    if commit:
        session.commit()

    return True


def find_user_by_uuid(session: Session, uuid: str) -> list[DBUser]:
    """
    Found user sequence with uuid, the uuid need be full-matched.
    :param session: a db Session
    :param uuid: str.
    :return:
    """
    return session.query(DBUser).filter_by(uuid=uuid).all()


def find_all_users(session: Session) -> list[DBUser]:
    """
    获取所有用户。
    :param session: a db Session
    :return: 所有用户列表
    """
    return session.query(DBUser).all()


def delete_user(session: Session, user_uuid: str, commit: bool = True) -> None:
    """
    删除用户。会级联删除其 projects；需先移除 user_groups 关联并删除 password_auth/oauth_auth。
    :param session: a db Session
    :param user_uuid: str, 要删除的用户 UUID
    :param commit: bool, 是否提交 (default: True)
    :raise KeyError: 用户不存在
    """
    users = find_user_by_uuid(session, user_uuid)
    if not users:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    user = users[0]
    user.user_groups.clear()
    if user.password_auth:
        session.delete(user.password_auth)
    if user.oauth_auth:
        session.delete(user.oauth_auth)
    session.delete(user)
    if commit:
        session.commit()


def find_user_by_email_host(session: Session, email_host: str) -> list[DBUser]:
    """
    Found user sequence with the host of email, like `@outlook.com` or `liv.ac.uk`.
    :param session: a db Session
    :param email_host: str, with `@` or not.
    :return:
    """
    endswith = email_host if email_host.startswith("@") else f'@{email_host}'
    query = select(DBUser).where(DBUser.email.endswith(endswith))
    return session.execute(query).scalars().all()


def find_user_by_username(session: Session, username: str) -> list[DBUser]:
    """
    Found user sequence with username, the username need be full-matched.
    :param session: a db Session
    :param username: str, the username.
    :return:
    """
    return session.query(DBUser).filter_by(username=username).all()


def find_user_by_email(session: Session, email: str) -> list[DBUser]:
    """
    Found user sequence with email, the email need be full-matched.
    :param session: a db Session
    :param email: str, the email address.
    :return:
    """
    return session.query(DBUser).filter_by(email=email).all()


def find_user_by_provider(session: Session, provider: str) -> list[DBUser]:
    """
    Found user sequence with provider, the provider need be full-matched.
    :param session: a db Session
    :param provider: str, the provider name.
    :return:
    """
    # 通过 OAuthAuthentication 表联合查询用户
    query = select(DBUser).join(OAuthAuthentication).where(
        OAuthAuthentication.provider_name == provider
    )
    return session.execute(query).scalars().all()


def find_user_by_provider_and_sub(session: Session, provider: str, sub: str) -> list[DBUser]:
    """
    Found user sequence with provider and user's sub, the provider and sub need be full-matched.
    :param session: a db Session
    :param provider: str, the provider name.
    :param sub: str, the user sub.
    :return:
    """
    # 通过 OAuthAuthentication 表联合查询用户
    query = select(DBUser).join(OAuthAuthentication).where(
        OAuthAuthentication.provider_name == provider
    ).where(OAuthAuthentication.user_sub == sub)
    return session.execute(query).scalars().all()



def apply_oauth_group_mapping(group_mapping: dict,
                               unmapped_group_strategy: GroupMappingStrategy,
                               oauth_groups: list[str]) -> list[str]:
    """
    根据 OAuth provider 的配置，将供应商组名映射到项目组名。
    
    :param group_mapping: dict, 供应商组名到项目组名的映射表，格式：{"供应商组名": "项目组名", ...}
    :param unmapped_group_strategy: GroupMappingStrategy, 当供应商组名没有映射时的处理策略
    :param oauth_groups: list[str], 来自 OAuth 供应商的组名列表
    :return: list[str], 映射后的项目组名列表（已去重）
    :raise ValueError: 如果未映射的组策略是 REJECT
    """
    project_group_names = []
    
    for provider_group_name in oauth_groups:
        # 查找组映射
        project_group_name = group_mapping.get(provider_group_name)
        
        if project_group_name:
            # 找到映射，添加到结果列表（去重）
            if project_group_name not in project_group_names:
                project_group_names.append(project_group_name)
        else:
            # 未找到映射
            if unmapped_group_strategy == GroupMappingStrategy.REJECT:
                raise ValueError(f"Provider group '{provider_group_name}' is not mapped and unmapped_group_strategy is REJECT")
            # IGNORE 策略：忽略未映射的组，不添加
    
    return project_group_names


def add_user(session: Session,
             username: str,
             email: str,
             uuid: None | str = None,
             oauth_name_sub: None | typing.Iterable[str] = None,
             username_password: None | typing.Iterable[str] = None,
             created_at: None | datetime = None,
             is_active: bool = True,
             last_login_source: UserLoginSource = UserLoginSource.NONE,
             groups: None | list[str] = None,
             oauth_groups: None | list[str] = None,
             commit: bool = False) -> DBUser:
    """
    Add a new user to the database.
    
    :param session: a db Session
    :param username: str, unique username for the user
    :param email: str, unique email address for the user
    :param uuid: uuid
    :param oauth_name_sub: oauth (provider name, user sub)
    :param username_password:
    :param created_at:
    :param is_active: bool, whether the user account is active (default: True)
    :param last_login_source: UserLoginSource, the last login source (default: UserLoginSource.NONE)
    :param groups: list[str], optional list of group names to add the user to
    :param oauth_groups: list[str], optional list of provider group names from OAuth provider.
                        When provided with oauth_name_sub, these groups will be mapped to project groups
                        using the provider's group_mapping configuration.
    :param commit: bool, whether to commit the session (default: False)
    :return: DBUser object that was created
    :raise ValueError: if user with the email already exists
    :raise KeyError: if oauth provider or group not found
    :raise ValueError: if oauth_groups is provided without oauth_name_sub, or if unmapped group strategy is REJECT
    """
    # Check if email already exists
    existing_users_by_email = find_user_by_email(session, email)
    if existing_users_by_email:
        raise ValueError(f"User with email '{email}' already exists")

    # Validate oauth_groups usage
    if oauth_groups is not None and not oauth_name_sub:
        raise ValueError("oauth_groups can only be used when oauth_name_sub is provided")

    kwarg = {
        'username': username,
        'email': email,
        'is_active': is_active,
        'last_login_source': last_login_source,
        'last_login': datetime.now(UTC),
    }

    if created_at:
        kwarg["created_at"] = created_at

    if uuid:
        kwarg["uuid"] = uuid

    provider = None
    if oauth_name_sub:
        provider_name, sub = oauth_name_sub
        providers = find_oauth_provider_by_name(session, provider_name)
        if not providers:
            raise KeyError(f"OAuth provider '{provider_name}' not found")
        provider = providers[0]
        if not uuid:
            uuid = str(uuid_module.uuid4())
            kwarg["uuid"] = uuid
        oauth_auth_kwargs = {"user_id": uuid, "provider_name": provider_name, "user_sub": sub}
    if username_password:
        username, password = username_password
        if not uuid:
            uuid = str(uuid_module.uuid4())
            kwarg["uuid"] = uuid
        up_kwargs = {
            'user_id': uuid,
            'username': username,
            'password_hash': get_password_hash(password)
        }

    # 处理 user_group
    user_group_objs: list[DBUserGroup] = []
    # 每个用户必属于 everyone；首个用户自动加入 administrator
    everyone_ugs = find_user_group_by_name(session, DEFAULT_GROUP_EVERYONE)
    if not everyone_ugs:
        raise KeyError(f"Default user group '{DEFAULT_GROUP_EVERYONE}' not found. Run ensure_default_groups first.")
    user_group_objs.append(everyone_ugs[0])
    is_first_user = session.query(DBUser).count() == 0
    if is_first_user:
        admin_ugs = find_user_group_by_name(session, DEFAULT_GROUP_ADMINISTRATOR)
        if not admin_ugs:
            raise KeyError(f"Default user group '{DEFAULT_GROUP_ADMINISTRATOR}' not found. Run ensure_default_groups first.")
        user_group_objs.append(admin_ugs[0])
    # -- 处理 OAuth 用户组
    if oauth_groups and provider:
        group_mapping = provider.group_mapping or {}
        unmapped_strategy = provider.unmapped_group_strategy
        mapped_group_names = apply_oauth_group_mapping(group_mapping, unmapped_strategy, oauth_groups)

        # 将映射后的用户组添加到用户
        for group_name in mapped_group_names:
            ug_list = find_user_group_by_name(session, group_name)
            if not ug_list:
                raise KeyError(f"Mapped user group '{group_name}' not found")
            if ug_list[0] not in user_group_objs:
                user_group_objs.append(ug_list[0])
    # -- 将用户添加到指定的用户组（直接指定，不经过映射）
    if groups:
        for group_name in groups:
            ug_list = find_user_group_by_name(session, group_name)
            if not ug_list:
                raise KeyError(f"User group '{group_name}' not found")
            if ug_list[0] not in user_group_objs:
                user_group_objs.append(ug_list[0])

    new_user = DBUser(**kwarg)
    # Add to session and optionally commit
    session.add(new_user)
    # set user_groups
    new_user.user_groups.extend(user_group_objs)

    if oauth_name_sub:
        oauth_auth = OAuthAuthentication(user=new_user, **oauth_auth_kwargs)
        session.add(oauth_auth)
    if username_password:
        up_auth = PasswordAuth(user=new_user, **up_kwargs)
        session.add(up_auth)

    if commit:
        session.commit()
        session.refresh(new_user)

    return new_user


def update_user(session: Session,
                user_uuid: str,
                username: str = None,
                email: str = None,
                is_active: bool = None,
                last_login_source: UserLoginSource = None,
                commit: bool = False) -> DBUser:
    """
    更新现有用户信息。
    
    :param session: a db Session
    :param user_uuid: str, 要更新的用户 UUID
    :param username: str, 可选的新用户名
    :param email: str, 可选的新邮箱
    :param is_active: bool, 可选的账户激活状态
    :param last_login_source: UserLoginSource, 可选的最后登录方式
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBUser 对象
    :raise KeyError: 如果用户不存在
    :raise ValueError: 如果新用户名或邮箱已被其他用户使用
    """
    users = find_user_by_uuid(session, user_uuid)
    if not users:
        raise KeyError(f"User with UUID '{user_uuid}' not found")

    user = users[0]

    if username is not None and username != user.username:
        # 检查新用户名是否已被使用
        existing = find_user_by_username(session, username)
        if existing:
            raise ValueError(f"User with username '{username}' already exists")
        user.username = username

    if email is not None and email != user.email:
        # 检查新邮箱是否已被使用
        existing = find_user_by_email(session, email)
        if existing:
            raise ValueError(f"User with email '{email}' already exists")
        user.email = email

    if is_active is not None:
        user.is_active = is_active

    if last_login_source is not None:
        user.last_login_source = last_login_source

    user.last_login = datetime.now(UTC)

    if commit:
        session.commit()
        session.refresh(user)

    return user


def update_user_last_login(session: Session,
                           user_uuid: str,
                           last_login_source: UserLoginSource,
                           commit: bool = False) -> DBUser:
    """
    更新用户的最后登录方式和登录时间。
    
    :param session: a db Session
    :param user_uuid: str, 用户的 UUID
    :param last_login_source: UserLoginSource, 最后登录方式
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBUser 对象
    :raise KeyError: 如果用户不存在
    """
    users = find_user_by_uuid(session, user_uuid)
    if not users:
        raise KeyError(f"User with UUID '{user_uuid}' not found")

    user = users[0]
    user.last_login_source = last_login_source
    user.last_login = datetime.now(UTC)

    if commit:
        session.commit()
        session.refresh(user)

    return user


def find_oauth_provider_by_name(session: Session, provider_name: str) -> list[OAuthProvider]:
    """

    :param session:
    :param provider_name:
    :return:
    """
    return session.query(OAuthProvider).filter_by(name=provider_name).all()


def add_provider(session: Session,
                 name: str,
                 client_id: str,
                 client_secret: str,
                 authorize_url: str,
                 token_url: str,
                 user_info_url: str,
                 scope: str,
                 group_mapping: None | dict = None,
                 unmapped_group_strategy: GroupMappingStrategy = GroupMappingStrategy.IGNORE,
                 commit: bool = False) -> OAuthProvider:
    """
    Add a new OAuth provider to the database.
    
    :param session: a db Session
    :param name: str, unique name for the OAuth provider
    :param client_id: str, OAuth client ID from the provider
    :param client_secret: str, OAuth client secret from the provider  
    :param authorize_url: str, OAuth authorization endpoint URL
    :param token_url: str, OAuth token endpoint URL
    :param user_info_url: str, URL to get user information from provider
    :param scope: str, OAuth scope permissions
    :param group_mapping: dict, optional mapping from provider group names to project group names
                         Format: {"provider_group_name": "project_group_name", ...}
    :param unmapped_group_strategy: GroupMappingStrategy, strategy when provider group name is not mapped
                                    (default: GroupMappingStrategy.IGNORE)
    :return: OAuthProvider object that was created
    :raise ValueError: if provider with the same name already exists
    """
    # Check if provider already exists
    existing_providers = find_oauth_provider_by_name(session, name)
    if existing_providers:
        raise ValueError(f"OAuth provider with name '{name}' already exists")

    # Create new provider
    new_provider = OAuthProvider(
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=authorize_url,
        token_url=token_url,
        user_info_url=user_info_url,
        scope=scope,
        group_mapping=group_mapping,
        unmapped_group_strategy=unmapped_group_strategy
    )

    # Add to session and commit
    session.add(new_provider)
    if commit:
        session.commit()
        session.refresh(new_provider)

    return new_provider


def update_provider(session: Session,
                    name: str,
                    client_id: str = None,
                    client_secret: str = None,
                    authorize_url: str = None,
                    token_url: str = None,
                    user_info_url: str = None,
                    scope: str = None,
                    group_mapping: None | dict = None,
                    unmapped_group_strategy: None | GroupMappingStrategy = None,
                    commit: bool = False) -> OAuthProvider:
    """
    Update an existing OAuth provider in the database.
    
    :param session: a db Session
    :param name: str, name of the OAuth provider to update
    :param client_id: str, optional new OAuth client ID
    :param client_secret: str, optional new OAuth client secret
    :param authorize_url: str, optional new OAuth authorization endpoint URL
    :param token_url: str, optional new OAuth token endpoint URL
    :param user_info_url: str, optional new URL to get user information
    :param scope: str, optional new OAuth scope permissions
    :param group_mapping: dict, optional mapping from provider group names to project group names
                         Format: {"provider_group_name": "project_group_name", ...}
                         Pass empty dict {} to clear the mapping
    :param unmapped_group_strategy: GroupMappingStrategy, optional strategy when provider group name is not mapped
    :return: OAuthProvider object that was updated
    :raise KeyError: if provider with the given name doesn't exist
    """
    providers = find_oauth_provider_by_name(session, name)
    if not providers:
        raise KeyError(f"OAuth provider with name '{name}' not found")

    provider = providers[0]

    # Update only the fields that are provided
    if client_id is not None:
        provider.client_id = client_id
    if client_secret is not None:
        provider.client_secret = client_secret
    if authorize_url is not None:
        provider.authorize_url = authorize_url
    if token_url is not None:
        provider.token_url = token_url
    if user_info_url is not None:
        provider.user_info_url = user_info_url
    if scope is not None:
        provider.scope = scope
    if group_mapping is not None:
        provider.group_mapping = group_mapping
    if unmapped_group_strategy is not None:
        provider.unmapped_group_strategy = unmapped_group_strategy

    if commit:
        session.commit()
        session.refresh(provider)

    return provider


# ==================== 用户组相关函数 ====================

def ensure_default_groups(session: Session) -> None:
    """
    确保默认组 everyone 和 administrator 存在；
    若数据库中已有用户，将未在 everyone 中的用户加入 everyone，
    若 administrator 组内无用户，则将 created_at 最早的用户加入 administrator。
    幂等，可多次调用。
    """
    # 创建 everyone 和 administrator 组（若不存在）
    for name, desc in [
        (DEFAULT_GROUP_EVERYONE, "All users belong to this group"),
        (DEFAULT_GROUP_ADMINISTRATOR, "Administrators"),
    ]:
        if not find_user_group_by_name(session, name):
            add_user_group(session, name=name, description=desc, commit=False)

    # 存量迁移：所有用户加入 everyone
    everyone_ugs = find_user_group_by_name(session, DEFAULT_GROUP_EVERYONE)
    if everyone_ugs:
        everyone_ug = everyone_ugs[0]
        for user in session.query(DBUser).all():
            if everyone_ug not in user.user_groups:
                user.user_groups.append(everyone_ug)

    # 存量迁移：若 administrator 无成员，将 created_at 最早的用户加入
    admin_ugs = find_user_group_by_name(session, DEFAULT_GROUP_ADMINISTRATOR)
    if admin_ugs and not admin_ugs[0].users:
        first_user = session.query(DBUser).order_by(DBUser.created_at.asc()).first()
        if first_user:
            first_user.user_groups.append(admin_ugs[0])


def find_user_group_by_name(session: Session, user_group_name: str) -> list[DBUserGroup]:
    """
    根据组名查找用户组，组名需要完全匹配。
    :param session: a db Session
    :param user_group_name: str, 用户组名
    :return: 匹配的用户组列表
    """
    return session.query(DBUserGroup).filter_by(name=user_group_name).all()


def find_user_group_by_uuid(session: Session, user_group_uuid: str) -> list[DBUserGroup]:
    """
    根据 UUID 查找用户组。
    :param session: a db Session
    :param user_group_uuid: str, 用户组的 UUID
    :return: 匹配的用户组列表
    """
    return session.query(DBUserGroup).filter_by(uuid=user_group_uuid).all()


def find_all_user_groups(session: Session) -> list[DBUserGroup]:
    """
    获取所有用户组。
    :param session: a db Session
    :return: 所有用户组列表
    """
    return session.query(DBUserGroup).all()


def add_user_group(session: Session,
                   name: str,
                   description: str = None,
                   uuid: str = None,
                   unmapped_group_strategy: GroupPermissionStrategy = GroupPermissionStrategy.REJECT,
                   commit: bool = False) -> DBUserGroup:
    """
    添加新的用户组到数据库。
    
    :param session: a db Session
    :param name: str, 唯一的组名
    :param description: str, 可选的组描述
    :param uuid: str, 可选的 UUID，不提供则自动生成
    :param unmapped_group_strategy: GroupPermissionStrategy, 未匹配处理策略 (default: REJECT)
    :param commit: bool, 是否提交会话 (default: False)
    :return: 创建的 DBUserGroup 对象
    :raise ValueError: 如果组名已存在
    """
    existing = find_user_group_by_name(session, name)
    if existing:
        raise ValueError(f"User group with name '{name}' already exists")

    kwargs = {
        'name': name,
        'unmapped_group_strategy': unmapped_group_strategy,
        'updated_at': datetime.now(UTC),
    }
    if description is not None:
        kwargs['description'] = description
    if uuid is not None:
        kwargs['uuid'] = uuid

    new_ug = DBUserGroup(**kwargs)
    session.add(new_ug)
    if commit:
        session.commit()
        session.refresh(new_ug)
    return new_ug


def update_user_group(session: Session,
                      name: str,
                      new_name: str = None,
                      description: str = None,
                      unmapped_group_strategy: GroupPermissionStrategy = None,
                      commit: bool = False) -> DBUserGroup:
    """
    更新现有用户组信息。
    """
    ugs = find_user_group_by_name(session, name)
    if not ugs:
        raise KeyError(f"User group with name '{name}' not found")
    ug = ugs[0]

    if new_name is not None and new_name != name:
        existing = find_user_group_by_name(session, new_name)
        if existing:
            raise ValueError(f"User group with name '{new_name}' already exists")
        ug.name = new_name
    if description is not None:
        ug.description = description
    if unmapped_group_strategy is not None:
        ug.unmapped_group_strategy = unmapped_group_strategy
    ug.updated_at = datetime.now(UTC)

    if commit:
        session.commit()
        session.refresh(ug)
    return ug


def delete_user_group(session: Session, name: str, commit: bool = False) -> bool:
    """
    删除用户组。
    """
    if name in (DEFAULT_GROUP_EVERYONE, DEFAULT_GROUP_ADMINISTRATOR):
        raise ValueError(f"Cannot delete system group '{name}'")
    ugs = find_user_group_by_name(session, name)
    if not ugs:
        raise KeyError(f"User group with name '{name}' not found")
    session.delete(ugs[0])
    if commit:
        session.commit()
    return True


# ==================== 用户-用户组关系管理函数 ====================

def add_user_to_user_group(session: Session,
                           user_uuid: str,
                           user_group_name: str,
                           commit: bool = False) -> DBUser:
    """
    将用户添加到指定用户组。
    """
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    ug = ugs[0]
    if ug in user.user_groups:
        raise ValueError(f"User '{user.username}' is already in user group '{user_group_name}'")
    user.user_groups.append(ug)
    if commit:
        session.commit()
        session.refresh(user)
    return user


def remove_user_from_user_group(session: Session,
                                user_uuid: str,
                                user_group_name: str,
                                commit: bool = False) -> DBUser:
    """
    将用户从指定用户组中移除。
    """
    if user_group_name == DEFAULT_GROUP_EVERYONE:
        raise ValueError("User cannot be removed from the 'everyone' group")
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    ug = ugs[0]
    if ug not in user.user_groups:
        raise ValueError(f"User '{user.username}' is not in user group '{user_group_name}'")
    user.user_groups.remove(ug)
    if commit:
        session.commit()
        session.refresh(user)
    return user


def get_user_managed_user_groups(session: Session, user_uuid: str) -> list[DBUserGroup]:
    """
    获取用户所属的所有用户组。
    注意不会展开 user_group manage user_group，此函数不能作为权限检查。
    """
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    return list(user.user_groups)


def get_user_group_users(session: Session, user_group_name: str) -> list[DBUser]:
    """
    获取用户组中的所有用户。
    """
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    return list(ugs[0].users)


def find_users_by_user_group(session: Session, user_group_name: str) -> list[DBUser]:
    """
    通过用户组名查找属于该组的所有用户。
    """
    return get_user_group_users(session, user_group_name)


# ==================== 用户组可管理用户相关函数 ====================

def add_managed_user_to_user_group(session: Session,
                                   user_group_name: str,
                                   user_uuid: str,
                                   commit: bool = False) -> DBUserGroup:
    """
    将用户添加到用户组可管理用户列表。
    """
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    ug = ugs[0]
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    if user in ug.managed_users:
        raise ValueError(f"User '{user.username}' is already in managed users list of user group '{user_group_name}'")
    ug.managed_users.append(user)
    if commit:
        session.commit()
        session.refresh(ug)
    return ug


def remove_managed_user_from_user_group(session: Session,
                                        user_group_name: str,
                                        user_uuid: str,
                                        commit: bool = False) -> DBUserGroup:
    """
    从用户组可管理用户列表中移除用户。
    """
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    ug = ugs[0]
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")
    if user not in ug.managed_users:
        raise ValueError(f"User '{user.username}' is not in managed users list of user group '{user_group_name}'")
    ug.managed_users.remove(user)
    if commit:
        session.commit()
        session.refresh(ug)
    return ug


def get_user_group_managed_users(session: Session, user_group_name: str) -> list[DBUser]:
    """
    获取用户组可管理的所有用户。
    """
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    return list(ugs[0].managed_users)


# ==================== 用户组可管理组相关函数 ====================

def add_managed_user_group_to_user_group(session: Session,
                                         manager_user_group_name: str,
                                         managed_user_group_name: str,
                                         commit: bool = False) -> DBUserGroup:
    """
    将用户组添加到另一个用户组的可管理组列表。
    """
    manager_ugs = find_user_group_by_name(session, manager_user_group_name)
    if len(manager_ugs) != 1:
        raise KeyError(f"Manager user group with name '{manager_user_group_name}' not found")
    manager_ug = manager_ugs[0]
    managed_ugs = find_user_group_by_name(session, managed_user_group_name)
    if len(managed_ugs) != 1:
        raise KeyError(f"Managed user group with name '{managed_user_group_name}' not found")
    managed_ug = managed_ugs[0]
    if manager_user_group_name == managed_user_group_name:
        raise ValueError("User group cannot manage itself")
    if managed_ug in manager_ug.managed_groups:
        raise ValueError(f"User group '{managed_user_group_name}' is already in managed groups list of '{manager_user_group_name}'")
    # 循环依赖：若被管理组已管理当前管理组，则形成环
    if manager_ug in managed_ug.managed_groups:
        raise ValueError("Circular dependency: managed user group already manages the manager user group")
    manager_ug.managed_groups.append(managed_ug)
    if commit:
        session.commit()
        session.refresh(manager_ug)
    return manager_ug


def remove_managed_user_group_from_user_group(session: Session,
                                             manager_user_group_name: str,
                                             managed_user_group_name: str,
                                             commit: bool = False) -> DBUserGroup:
    """
    从用户组可管理组列表中移除用户组。
    """
    manager_ugs = find_user_group_by_name(session, manager_user_group_name)
    if not manager_ugs:
        raise KeyError(f"Manager user group with name '{manager_user_group_name}' not found")
    manager_ug = manager_ugs[0]
    managed_ugs = find_user_group_by_name(session, managed_user_group_name)
    if not managed_ugs:
        raise KeyError(f"Managed user group with name '{managed_user_group_name}' not found")
    managed_ug = managed_ugs[0]
    if managed_ug not in manager_ug.managed_groups:
        raise ValueError(f"User group '{managed_user_group_name}' is not in managed groups list of '{manager_user_group_name}'")
    manager_ug.managed_groups.remove(managed_ug)
    if commit:
        session.commit()
        session.refresh(manager_ug)
    return manager_ug


def get_user_group_managed_groups(session: Session, user_group_name: str) -> list[DBUserGroup]:
    """
    获取用户组可管理的所有其他用户组。
    """
    ugs = find_user_group_by_name(session, user_group_name)
    if not ugs:
        raise KeyError(f"User group with name '{user_group_name}' not found")
    return list(ugs[0].managed_groups)


def get_user_group_managed_groups_uuid(session: Session, user_group_uuid: str) -> list[DBUserGroup]:
    """
    根据用户组 UUID 获取该组可管理的所有其他用户组。
    """
    ugs = find_user_group_by_uuid(session, user_group_uuid)
    if not ugs:
        raise KeyError(f"User group with UUID '{user_group_uuid}' not found")
    return list(ugs[0].managed_groups)

