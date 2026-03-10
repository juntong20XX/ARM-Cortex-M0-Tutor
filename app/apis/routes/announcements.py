"""
告示相关路由.

GET /api/announcements 返回当前用户可见的告示列表，与前端 AnnouncementsResponse 约定一致。
POST /api/announcements 创建告示（需 administrator 权限）。
DELETE /api/announcements/{uuid} 删除告示（需 administrator 权限）。
权限：告示的 visible_user_groups 为空表示公开；非空表示仅指定用户组可见。
"""
from ... import database as db
from .. import models

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["announcements"])


def _require_admin(request: Request, session) -> str:
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


@router.get("/announcements", response_model=models.AnnouncementsResponse)
async def get_announcements(request: Request):
    """
    获取当前用户可见的告示。
    未登录用户仅见公开告示；已登录用户可见公开告示及所属组可见的告示。
    :return: { items: Announcement[] }
    """
    user = request.session.get("user")
    user_uuid = (user or {}).get("uuid") or None
    with db.db_context() as session:
        rows = db.find_visible_announcements(session, user_uuid=user_uuid)
        items = [
            models.Announcement(
                id=r.uuid,
                title=r.title,
                content=r.content,
                createdAt=r.created_at.isoformat() if r.created_at else None,
                visibleGroupNames=[ug.name for ug in r.visible_user_groups],
            )
            for r in rows
        ]
        return models.AnnouncementsResponse(items=items)


@router.post("/announcements")
async def create_announcement(request: Request, body: models.AnnouncementCreateRequest):
    """
    创建告示。需已登录且为 administrator 组用户。
    """
    with db.db_context() as session:
        _require_admin(request, session)
        try:
            visible_names = body.visibleGroupNames if body.visibleGroupNames else None
            db.add_announcement(
                session,
                title=body.title,
                content=body.content,
                visible_group_names=visible_names,
                commit=True,
            )
            return JSONResponse(
                status_code=201,
                content={"success": True, "msg": "Announcement created successfully"},
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.delete("/announcements/{announcement_uuid}", response_model=models.BaseResponse)
async def delete_announcement_endpoint(request: Request, announcement_uuid: str):
    """
    删除告示。需已登录且为 administrator 组用户。
    """
    with db.db_context() as session:
        _require_admin(request, session)
        try:
            db.delete_announcement(session, announcement_uuid, commit=True)
            return models.BaseResponse(success=True, msg="Announcement deleted successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
