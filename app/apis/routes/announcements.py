"""
告示相关路由.

GET /api/announcements 返回当前用户可见的告示列表，与前端 AnnouncementsResponse 约定一致。
权限：告示的 visible_user_groups 为空表示公开；非空表示仅指定用户组可见。
"""
from ... import database as db
from .. import models

from fastapi import APIRouter, Request

router = APIRouter(tags=["announcements"])


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
            )
            for r in rows
        ]
        return models.AnnouncementsResponse(items=items)
