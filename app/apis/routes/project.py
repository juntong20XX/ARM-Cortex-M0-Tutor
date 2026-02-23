"""
项目相关路由.

XXX: 跳过权限认证.
"""
from ... import database as db
from .. import models

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from logging import getLogger

logger = getLogger(__name__)

router = APIRouter(tags=["project"])


def _setup_project_info(project: db.models.DBProject, simplified=False) -> models.ProjectInfo:
    return models.ProjectInfo(
        success=True,
        msg="",
        uuid=project.uuid,
        name=project.name,
        content=project.content,
        description=project.description,
        source=project.source if not simplified else "",
        code=project.code if not simplified else [],
        executed=project.executed if not simplified else [],
        owner_id=project.owner_id,
        owner_name=project.owner.username,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/project/info/{project_uuid}", response_model=models.ProjectInfo)
async def get_project_info(project_uuid: str):
    """
    获取项目信息
    :param project_uuid: 项目 UUID
    :return: 项目信息
    :raise HTTPException: 项目未找到
    """
    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_uuid}' not found")

        project = projects[0]
        return _setup_project_info(project)


@router.put("/project/source/{project_uuid}", response_model=models.BaseResponse)
async def update_project_source(project_uuid: str, body: models.ProjectSourceUpdate):
    """
    更新项目源代码
    :param project_uuid: 项目 UUID
    :param body: 包含新源代码的请求体
    :return: 操作结果
    :raise HTTPException: 项目未找到
    """
    with db.db_context() as session:
        try:
            db.update_project(session, project_uuid, source=body.source, commit=True)
            return models.BaseResponse(success=True, msg="Source updated successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/project/create")
async def create_project(request: Request, project_info: models.ProjectInfo):
    """
    创建新项目，需要已登录会话。
    """
    user = request.session.get("user")
    if not user or not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Please login first")
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Please login first")
    with db.db_context() as session:
        user_list = db.find_user_by_uuid(session, user_uuid)
        if not user_list:
            raise HTTPException(status_code=401, detail="Please login first")
        user_obj = user_list[0]
        db.add_project(
            session,
            project_info.name,
            project_info.content,
            user_obj.uuid,
            project_info.description,
            project_info.source,
            project_info.code if project_info.code is not None else [],
        )
    return JSONResponse(
        status_code=201,
        content={"success": True, "msg": "Project created successfully"},
    )


@router.get("/project/list", response_model=list[models.ProjectInfo])
async def get_project_list(request: Request):
    """
    获取可见的项目.
    :return:
    """
    user = request.session.get('user')
    # TODO: check permission, just return all projects here
    with db.db_context() as session:
        all_projects = db.find_all_projects(session)
        return [_setup_project_info(p, simplified=True) for p in all_projects]
