"""
user operations: get/set information, add, remove, etc.
"""
from ..models import LoginSource
from ... import database as db
from ... import services
from ...core import settings
from .. import models

from fastapi import APIRouter, Request, HTTPException

import datetime
from logging import getLogger

logger = getLogger(__name__)

router = APIRouter(tags=["user"])


def _require_admin(request: Request, session):
    """校验当前用户为 administrator 组，否则抛出 HTTPException。返回 user_uuid。"""
    user = request.session.get("user")
    if not user or not isinstance(user, dict) or not user.get("uuid"):
        raise HTTPException(status_code=401, detail="Please login first")
    users = db.find_user_by_uuid(session, user["uuid"])
    if not users:
        raise HTTPException(status_code=401, detail="Please login first")
    if not any(ug.name == db.DEFAULT_GROUP_ADMINISTRATOR for ug in users[0].user_groups):
        raise HTTPException(status_code=403, detail="Admin permission required")
    return user["uuid"]


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


@router.get("/users", response_model=models.UsersListResponse)
async def list_users(request: Request):
    """列出所有用户。需已登录且为 administrator 组用户。"""
    with db.db_context() as session:
        _require_admin(request, session)
        all_users = db.find_all_users(session)
        items = [services.get_user_base_info_dict(session, u.uuid) for u in all_users]
        return models.UsersListResponse(items=items)


@router.delete("/users/{uuid}", response_model=models.BaseResponse)
async def delete_user_endpoint(request: Request, uuid: str):
    """删除用户。需已登录且为 administrator 组用户。禁止删除自己。"""
    with db.db_context() as session:
        current_uuid = _require_admin(request, session)
        if uuid == current_uuid:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        try:
            db.delete_user(session, uuid, commit=True)
            return models.BaseResponse(success=True, msg="User deleted successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
