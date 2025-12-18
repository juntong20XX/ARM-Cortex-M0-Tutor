"""

"""

from .enter import init_database, get_db, db_context
from .dbtools import (
    GroupMappingStrategy, GroupPermissionStrategy,
    find_project_by_name, find_project_by_owner_name, find_project_by_owner_id,
    find_user_by_username, find_user_by_email_host, find_user_by_email, find_user_by_uuid,
    find_user_by_provider, find_user_by_provider_and_sub,
    find_oauth_provider_by_name,
    add_provider, update_provider,
    add_user, update_user, update_user_last_login,
    # 用户组相关函数
    find_group_by_name, find_group_by_uuid, find_all_groups,
    add_group, update_group, delete_group,
    add_user_to_group, remove_user_from_group,
    get_user_groups, get_group_users, find_users_by_group,
    # 组可管理用户相关函数
    add_managed_user_to_group, remove_managed_user_from_group,
    get_group_managed_users,
    # 组可管理项目相关函数
    add_managed_project_to_group, remove_managed_project_from_group,
    get_group_managed_projects,
    # 组可管理组相关函数
    add_managed_group_to_group, remove_managed_group_from_group,
    get_group_managed_groups)

from . import models

__all__ = ["models",
           "init_database", "get_db", "db_context",
           "GroupMappingStrategy", "GroupPermissionStrategy",
           "find_project_by_name", "find_user_by_username", "find_user_by_email_host", "find_user_by_email",
           "find_project_by_owner_name",
           "find_user_by_provider", "find_user_by_provider_and_sub", "find_user_by_uuid",
           "find_project_by_owner_id",
           "find_oauth_provider_by_name",
           "add_provider", "update_provider",
           "add_user", "update_user", "update_user_last_login",
           # 用户组相关
           "find_group_by_name", "find_group_by_uuid", "find_all_groups",
           "add_group", "update_group", "delete_group",
           "add_user_to_group", "remove_user_from_group",
           "get_user_groups", "get_group_users", "find_users_by_group",
           # 组可管理用户相关
           "add_managed_user_to_group", "remove_managed_user_from_group",
           "get_group_managed_users",
           # 组可管理项目相关
           "add_managed_project_to_group", "remove_managed_project_from_group",
           "get_group_managed_projects",
           # 组可管理组相关
           "add_managed_group_to_group", "remove_managed_group_from_group",
           "get_group_managed_groups"]
