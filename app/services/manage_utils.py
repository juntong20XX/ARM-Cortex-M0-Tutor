"""

"""
from .. import database as db

from sqlalchemy.orm import Session


def add_user_from_oauth_info(session: Session, provider_name: str, user_info: dict, commit: bool = False):
    """
    同步创建 OAuth 用户，调用方需在外部管理事务(如 with db.db_context)
    期望 user_info 至少包含 name/email/sub/groups; 异常透出自 db.add_user.
    """
    db.add_user(session,
                username=user_info["name"],
                email=user_info["email"],
                oauth_name_sub=(provider_name, user_info["sub"]),
                oauth_groups=user_info["groups"],
                commit=commit,
                )


def check_group_permission_of_other_group(session: Session, group_uuid: str, other_group_uuid: str) -> bool:
    """
    检查当前用户组是否有权限访问指定用户组。
    :param session:
    :param group_uuid: 当前用户组 UUID
    :param other_group_uuid: 待检查的用户组 UUID
    :return:
    """
    if group_uuid == other_group_uuid:
        return True
    try:
        group = db.find_user_group_by_uuid(session, group_uuid)[0]
        other = db.find_user_group_by_uuid(session, other_group_uuid)[0]
    except IndexError:
        raise KeyError(f"User group uuid {group_uuid} not found.")
    if group.unmapped_group_strategy == db.GroupPermissionStrategy.PERMIT:
        return True
    if other.uuid in (i.uuid for i in group.managed_groups):
        return True
    return False


def check_user_permission_of_other_user(session: Session, user_uuid: str, other_user_uuid: str) -> bool:
    """

    :param session:
    :param user_uuid:
    :param other_user_uuid:
    :raise KeyError: user not found
    :return:
    """
    if user_uuid == other_user_uuid:
        return True
    try:
        user = db.find_user_by_uuid(session, user_uuid)[0]
        other = db.find_user_by_uuid(session, other_user_uuid)[0]
    except IndexError:
        raise KeyError(f"User uuid {user_uuid} not found.")
    for user_group in user.user_groups:
        if user_group.unmapped_group_strategy == db.GroupPermissionStrategy.PERMIT:
            return True
        for other_user_group in other.user_groups:
            if other_user_group.uuid == user_group.uuid:
                return True
            if other_user_group.uuid in (i.uuid for i in user_group.managed_groups):
                return True
    return False

def check_user_permission_of_project(session: Session, user_uuid: str, project_uuid: str) -> bool:
    """
    检查用户是否有权限访问项目。仅项目属主有权限（用户组不再管理项目）。
    :param session:
    :param user_uuid:
    :param project_uuid:
    :raise KeyError: user not found
    :return:
    """
    user = db.find_user_by_uuid(session, user_uuid)[0]
    return project_uuid in (i.uuid for i in user.projects)


def can_manage_project(session: Session, user: dict | None, project) -> bool:
    """
    检查用户是否有权管理项目（更新/删除）：项目属主或 administrator 组用户。
    :param session: 数据库 Session
    :param user: request.session 中的 user 字典，可为 None
    :param project: 项目对象，需有 owner_id 属性
    :return: 是否有管理权限
    """
    if not user or not isinstance(user, dict) or not user.get("uuid"):
        return False
    if getattr(project, "owner_id", None) == user["uuid"]:
        return True
    users = db.find_user_by_uuid(session, user["uuid"])
    if not users:
        return False
    return any(ug.name == db.DEFAULT_GROUP_ADMINISTRATOR for ug in users[0].user_groups)
