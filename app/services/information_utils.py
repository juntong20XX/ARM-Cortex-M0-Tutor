"""

"""
from .. import database as db

from sqlalchemy.orm import Session


def get_user_base_info_dict(session: Session, uuid: str) -> dict:
    user = db.find_user_by_uuid(session, uuid)[0]
    return {
        "success": True,
        "msg": "",
        "uuid": user.uuid,
        "display_name": user.username,
        "email": user.email,
        "groups": [i.name for i in user.user_groups],
        "join_date": user.created_at,
        "last_login": user.last_login,
        "login_source": user.last_login_source,
    }
