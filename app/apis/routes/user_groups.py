"""
用户组相关路由。创建/修改/删除需 administrator 权限。
"""
from ... import database as db
from .. import models

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["user_groups"])


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


@router.get("/user-groups", response_model=models.UserGroupsListResponse)
async def list_user_groups(request: Request):
    """获取所有用户组。需 administrator 权限。"""
    with db.db_context() as session:
        _require_admin(request, session)
        all_groups = db.find_all_user_groups(session)
        items = [
            models.UserGroupItem(
                uuid=ug.uuid,
                name=ug.name,
                description=ug.description,
                memberCount=len(ug.users),
            )
            for ug in all_groups
        ]
        return models.UserGroupsListResponse(items=items)


@router.post("/user-groups", response_model=models.BaseResponse)
async def create_user_group(request: Request, body: models.UserGroupCreateRequest):
    """创建用户组。需 administrator 权限。"""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")
    with db.db_context() as session:
        _require_admin(request, session)
        try:
            db.add_user_group(
                session,
                name=name,
                description=body.description.strip() if body.description else None,
                commit=True,
            )
            return models.BaseResponse(success=True, msg="User group created successfully")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put("/user-groups/{name}", response_model=models.BaseResponse)
async def update_user_group_endpoint(request: Request, name: str, body: models.UserGroupUpdateRequest):
    """更新用户组。需 administrator 权限。"""
    with db.db_context() as session:
        _require_admin(request, session)
        new_name = body.newName.strip() if body.newName else None
        description = (body.description or "").strip() or None
        if new_name == "":
            new_name = None
        if new_name is None and description is None:
            return models.BaseResponse(success=True, msg="Nothing to update")
        try:
            db.update_user_group(
                session,
                name=name,
                new_name=new_name,
                description=description,
                commit=True,
            )
            return models.BaseResponse(success=True, msg="User group updated successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user-groups/{name}", response_model=models.BaseResponse)
async def delete_user_group_endpoint(request: Request, name: str):
    """删除用户组。需 administrator 权限。系统组 everyone、administrator 不可删除。"""
    with db.db_context() as session:
        _require_admin(request, session)
        try:
            db.delete_user_group(session, name, commit=True)
            return models.BaseResponse(success=True, msg="User group deleted successfully")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
