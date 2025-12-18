"""

"""
from ..models import LoginSource
from ... import database as db
from ... import services
from ...core import settings
from .. import models

from fastapi import APIRouter, Request

import datetime
from logging import getLogger

logger = getLogger(__name__)

router = APIRouter(tags=["user"])


@router.get("/user/info/{uuid}", response_model=models.UserBaseInfo)
async def user_info(request: Request, uuid: str):
    user = request.session.get('user')
    permitted = bool(user)
    with db.db_context() as session:
        try:
            permitted = permitted and services.check_user_permission_of_other_user(session, user["uuid"], uuid)
        except KeyError:
            return {
                "success": False,
                "msg": "user not found",
                "uuid": "0",
                "display_name": "0",
                "email": "0",
                "groups": [],
                "join_date": datetime.datetime.now(),
                "last_login": datetime.datetime.now(),
                "login_source": LoginSource.oauth,
            }
        if not permitted:
            return {
                "success": False,
                "msg": "no permission",
                "uuid": "0",
                "display_name": "0",
                "email": "0",
                "groups": [],
                "join_date": datetime.datetime.now(),
                "last_login": datetime.datetime.now(),
                "login_source": LoginSource.oauth,
            }
        return services.get_user_base_info_dict(session, uuid)
