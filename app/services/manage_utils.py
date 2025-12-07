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
