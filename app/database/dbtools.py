"""

"""
from .models import DBUser, DBProject, OAuthProvider, PasswordAuth, OAuthAuthentication, DBGroup
from ..core.security import get_password_hash

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

import typing
import uuid as uuid_module
from datetime import datetime, UTC


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



def add_user(session: Session,
             username: str,
             email: str,
             uuid: None | str = None,
             oauth_name_sub: None | typing.Iterable[str] = None,
             username_password: None | typing.Iterable[str] = None,
             created_at: None | datetime = None,
             is_active: bool = True,
             groups: None | list[str] = None,
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
    :param groups: list[str], optional list of group names to add the user to
    :param commit: bool, whether to commit the session (default: False)
    :return: DBUser object that was created
    :raise ValueError: if user with the email already exists
    :raise KeyError: if oauth provider or group not found
    """
    # Check if email already exists
    existing_users_by_email = find_user_by_email(session, email)
    if existing_users_by_email:
        raise ValueError(f"User with email '{email}' already exists")

    kwarg = {
        'username': username,
        'email': email,
        'is_active': is_active,
        'updated_at': datetime.now(UTC),
    }

    if created_at:
        kwarg["created_at"] = created_at

    if uuid:
        kwarg["uuid"] = uuid

    if oauth_name_sub:
        provider_name, sub = oauth_name_sub
        providers = find_oauth_provider_by_name(session, provider_name)
        if not providers:
            raise KeyError(f"OAuth provider '{oauth_name_sub}' not found")
        if not uuid:
            uuid = str(uuid_module.uuid4())
            kwarg["uuid"] = uuid
        oauth_auth_kwargs = {"user_id": uuid, "provider_name": oauth_name_sub, "user_sub": sub}
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

    new_user = DBUser(**kwarg)
    # Add to session and optionally commit
    session.add(new_user)

    if oauth_name_sub:
        oauth_auth = OAuthAuthentication(user=new_user, **oauth_auth_kwargs)
        session.add(oauth_auth)
    if username_password:
        up_auth = PasswordAuth(user=new_user, **up_kwargs)
        session.add(up_auth)

    # 将用户添加到指定的组
    if groups:
        for group_name in groups:
            group_list = find_group_by_name(session, group_name)
            if not group_list:
                raise KeyError(f"Group '{group_name}' not found")
            new_user.groups.append(group_list[0])

    if commit:
        session.commit()
        session.refresh(new_user)

    return new_user


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
        scope=scope
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

    if commit:
        session.commit()
        session.refresh(provider)

    return provider


# ==================== 用户组相关函数 ====================

def find_group_by_name(session: Session, group_name: str) -> list[DBGroup]:
    """
    根据组名查找用户组，组名需要完全匹配。
    :param session: a db Session
    :param group_name: str, 组名
    :return: 匹配的用户组列表
    """
    return session.query(DBGroup).filter_by(name=group_name).all()


def find_group_by_uuid(session: Session, group_uuid: str) -> list[DBGroup]:
    """
    根据 UUID 查找用户组。
    :param session: a db Session
    :param group_uuid: str, 组的 UUID
    :return: 匹配的用户组列表
    """
    return session.query(DBGroup).filter_by(uuid=group_uuid).all()


def find_all_groups(session: Session) -> list[DBGroup]:
    """
    获取所有用户组。
    :param session: a db Session
    :return: 所有用户组列表
    """
    return session.query(DBGroup).all()


def add_group(session: Session,
              name: str,
              description: str = None,
              uuid: str = None,
              commit: bool = False) -> DBGroup:
    """
    添加新的用户组到数据库。
    
    :param session: a db Session
    :param name: str, 唯一的组名
    :param description: str, 可选的组描述
    :param uuid: str, 可选的 UUID，不提供则自动生成
    :param commit: bool, 是否提交会话 (default: False)
    :return: 创建的 DBGroup 对象
    :raise ValueError: 如果组名已存在
    """
    # 检查组名是否已存在
    existing_groups = find_group_by_name(session, name)
    if existing_groups:
        raise ValueError(f"Group with name '{name}' already exists")

    kwargs = {
        'name': name,
        'updated_at': datetime.now(UTC),
    }
    
    if description is not None:
        kwargs['description'] = description
    
    if uuid is not None:
        kwargs['uuid'] = uuid

    new_group = DBGroup(**kwargs)
    session.add(new_group)
    
    if commit:
        session.commit()
        session.refresh(new_group)

    return new_group


def update_group(session: Session,
                 name: str,
                 new_name: str = None,
                 description: str = None,
                 commit: bool = False) -> DBGroup:
    """
    更新现有用户组信息。
    
    :param session: a db Session
    :param name: str, 要更新的组名
    :param new_name: str, 可选的新组名
    :param description: str, 可选的新描述
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBGroup 对象
    :raise KeyError: 如果组名不存在
    :raise ValueError: 如果新组名已被其他组使用
    """
    groups = find_group_by_name(session, name)
    if not groups:
        raise KeyError(f"Group with name '{name}' not found")

    group = groups[0]

    if new_name is not None and new_name != name:
        # 检查新名称是否已被使用
        existing = find_group_by_name(session, new_name)
        if existing:
            raise ValueError(f"Group with name '{new_name}' already exists")
        group.name = new_name

    if description is not None:
        group.description = description

    group.updated_at = datetime.now(UTC)

    if commit:
        session.commit()
        session.refresh(group)

    return group


def delete_group(session: Session, name: str, commit: bool = False) -> bool:
    """
    删除用户组。
    
    :param session: a db Session
    :param name: str, 要删除的组名
    :param commit: bool, 是否提交会话 (default: False)
    :return: bool, 删除成功返回 True
    :raise KeyError: 如果组名不存在
    """
    groups = find_group_by_name(session, name)
    if not groups:
        raise KeyError(f"Group with name '{name}' not found")

    group = groups[0]
    session.delete(group)
    
    if commit:
        session.commit()

    return True


# ==================== 用户-组关系管理函数 ====================

def add_user_to_group(session: Session, 
                      user_uuid: str, 
                      group_name: str,
                      commit: bool = False) -> DBUser:
    """
    将用户添加到指定用户组。
    
    :param session: a db Session
    :param user_uuid: str, 用户的 UUID
    :param group_name: str, 组名
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBUser 对象
    :raise KeyError: 如果用户或组不存在
    :raise ValueError: 如果用户已在该组中
    """
    # 查找用户
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")

    # 查找组
    groups = find_group_by_name(session, group_name)
    if not groups:
        raise KeyError(f"Group with name '{group_name}' not found")
    
    group = groups[0]

    # 检查用户是否已在组中
    if group in user.groups:
        raise ValueError(f"User '{user.username}' is already in group '{group_name}'")

    user.groups.append(group)

    if commit:
        session.commit()
        session.refresh(user)

    return user


def remove_user_from_group(session: Session, 
                           user_uuid: str, 
                           group_name: str,
                           commit: bool = False) -> DBUser:
    """
    将用户从指定用户组中移除。
    
    :param session: a db Session
    :param user_uuid: str, 用户的 UUID
    :param group_name: str, 组名
    :param commit: bool, 是否提交会话 (default: False)
    :return: 更新后的 DBUser 对象
    :raise KeyError: 如果用户或组不存在
    :raise ValueError: 如果用户不在该组中
    """
    # 查找用户
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")

    # 查找组
    groups = find_group_by_name(session, group_name)
    if not groups:
        raise KeyError(f"Group with name '{group_name}' not found")
    
    group = groups[0]

    # 检查用户是否在组中
    if group not in user.groups:
        raise ValueError(f"User '{user.username}' is not in group '{group_name}'")

    user.groups.remove(group)

    if commit:
        session.commit()
        session.refresh(user)

    return user


def get_user_groups(session: Session, user_uuid: str) -> list[DBGroup]:
    """
    获取用户所属的所有用户组。
    
    :param session: a db Session
    :param user_uuid: str, 用户的 UUID
    :return: 用户所属的用户组列表
    :raise KeyError: 如果用户不存在
    """
    user = session.query(DBUser).filter_by(uuid=user_uuid).first()
    if not user:
        raise KeyError(f"User with UUID '{user_uuid}' not found")

    return list(user.groups)


def get_group_users(session: Session, group_name: str) -> list[DBUser]:
    """
    获取用户组中的所有用户。
    
    :param session: a db Session
    :param group_name: str, 组名
    :return: 组中的用户列表
    :raise KeyError: 如果组不存在
    """
    groups = find_group_by_name(session, group_name)
    if not groups:
        raise KeyError(f"Group with name '{group_name}' not found")

    group = groups[0]
    return list(group.users)


def find_users_by_group(session: Session, group_name: str) -> list[DBUser]:
    """
    通过组名查找属于该组的所有用户。
    
    :param session: a db Session
    :param group_name: str, 组名
    :return: 属于该组的用户列表
    :raise KeyError: 如果组不存在
    """
    return get_group_users(session, group_name)
